"""
Starlink Pulse - collector

Fetches new public Bluesky posts that mention Starlink, scores each one with a
pre-trained Hugging Face sentiment transformer, and appends the results to
data/posts.csv with a timestamp.

Runs automatically every 30 minutes via GitHub Actions (.github/workflows/collect.yml).
Run it by hand with:
    python collector.py                    # live run: only posts not seen before
    python collector.py --backfill-hours 48  # first run only: also catch up on the last 48 h

Needs two environment variables (stored as GitHub secrets):
    BSKY_HANDLE        e.g. yourname.bsky.social
    BSKY_APP_PASSWORD  an app password from Bluesky Settings > Privacy and security > App passwords

Privacy: we store only the post text, its time and its sentiment. No handles,
display names, profile links or post URLs are stored. @mentions and links are
removed from the text.
"""

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------- settings
SEARCH_QUERY = "starlink"           # what we search for on Bluesky
LANGUAGE = "en"                     # the model is English-only, so we ask Bluesky for English posts
MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
DATA_FILE = Path(__file__).parent / "data" / "posts.csv"
PDS = "https://bsky.social/xrpc"    # Bluesky server we log in to
MAX_PAGES_LIVE = 60                 # up to 6,000 posts per run, so a run can catch up after a gap of many hours
MAX_PAGES_BACKFILL = 60             # safety cap for the one-off catch-up run
MIN_TEXT_LENGTH = 15                # skip posts that are basically empty after cleaning

# Which posts count as "about the connection" lives in scope.py (shared with the dashboard).
from scope import is_in_scope

COLUMNS = ["id", "created_at", "collected_at", "collection", "lang", "in_scope",
           "text", "label", "neg", "neu", "pos", "score", "model"]


# ---------------------------------------------------------------- Bluesky
def login(handle: str, app_password: str) -> str:
    """Log in with an app password and return an access token."""
    r = requests.post(f"{PDS}/com.atproto.server.createSession",
                      json={"identifier": handle, "password": app_password}, timeout=30)
    r.raise_for_status()
    return r.json()["accessJwt"]


def search_page(token: str, cursor: str | None = None) -> dict:
    """One page (up to 100 posts) of the newest posts matching SEARCH_QUERY."""
    params = {"q": SEARCH_QUERY, "sort": "latest", "limit": 100, "lang": LANGUAGE}
    if cursor:
        params["cursor"] = cursor
    r = requests.get(f"{PDS}/app.bsky.feed.searchPosts", params=params,
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def post_id(uri: str) -> str:
    """Short hash of the post address, used only to avoid storing the same post twice.
    The address itself (which contains the author's account id) is not stored."""
    return hashlib.sha256(uri.encode()).hexdigest()[:16]


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", "", text)        # links
    text = re.sub(r"@[\w.\-]+", "@user", text)                # mentions -> @user
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_time(value: str) -> datetime | None:
    try:
        t = pd.Timestamp(value)
        if t.tzinfo is None:
            t = t.tz_localize("UTC")
        return t.tz_convert("UTC").to_pydatetime()
    except Exception:
        return None


def fetch_new_posts(token: str, seen_ids: set, stop_before: datetime, max_pages: int) -> list[dict]:
    """Page backwards through the newest posts until we reach posts we already
    have, posts older than stop_before, or the page cap."""
    found, cursor = [], None
    for _ in range(max_pages):
        page = search_page(token, cursor)
        posts = page.get("posts", [])
        if not posts:
            break
        reached_old = False
        for p in posts:
            record = p.get("record", {})
            created = parse_time(record.get("createdAt") or p.get("indexedAt", ""))
            if created is None:
                continue
            if created < stop_before:
                reached_old = True
                continue
            pid = post_id(p["uri"])
            if pid in seen_ids:
                continue
            text = clean_text(record.get("text", ""))
            if len(text) < MIN_TEXT_LENGTH:
                continue
            seen_ids.add(pid)
            found.append({
                "id": pid,
                "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lang": ",".join(record.get("langs", []) or []),
                "text": text,
                "in_scope": is_in_scope(text),
            })
        cursor = page.get("cursor")
        if reached_old or not cursor:
            break
    return found


# ---------------------------------------------------------------- model
def score_posts(rows: list[dict]) -> list[dict]:
    """Run every post through the pre-trained sentiment transformer."""
    from transformers import pipeline  # imported here so the rest of the file loads fast

    clf = pipeline("sentiment-analysis", model=MODEL_NAME, tokenizer=MODEL_NAME,
                   top_k=None, truncation=True, max_length=512)
    outputs = clf([r["text"] for r in rows], batch_size=16)
    for row, out in zip(rows, outputs):
        scores = {d["label"].lower(): float(d["score"]) for d in out}
        row["neg"] = round(scores.get("negative", 0.0), 4)
        row["neu"] = round(scores.get("neutral", 0.0), 4)
        row["pos"] = round(scores.get("positive", 0.0), 4)
        row["label"] = max(("negative", "neutral", "positive"),
                           key=lambda k: scores.get(k, 0.0))
        row["score"] = round(row["pos"] - row["neg"], 4)   # -1 = very negative, +1 = very positive
        row["model"] = MODEL_NAME
    return rows


# ---------------------------------------------------------------- storage
def load_existing() -> pd.DataFrame:
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE, dtype={"id": str})
    return pd.DataFrame(columns=COLUMNS)


def save(existing: pd.DataFrame, new_rows: list[dict]) -> pd.DataFrame:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(new_rows, columns=COLUMNS)
    combined = new if existing.empty else pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates("id").sort_values("created_at")
    combined.to_csv(DATA_FILE, index=False)
    return combined


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill-hours", type=float, default=0,
                    help="Catch up on posts from the last N hours (use once, on the first run).")
    args = ap.parse_args()

    handle = os.environ.get("BSKY_HANDLE")
    password = os.environ.get("BSKY_APP_PASSWORD")
    if not handle or not password:
        print("Missing BSKY_HANDLE or BSKY_APP_PASSWORD (set them as GitHub secrets).")
        return 1

    existing = load_existing()
    seen = set(existing["id"].astype(str))
    now = datetime.now(timezone.utc)

    if args.backfill_hours > 0:
        stop_before = now - timedelta(hours=args.backfill_hours)
        collection, max_pages = "backfill", MAX_PAGES_BACKFILL
    else:
        # live run: go back to the newest post we already have (minus a margin
        # for posts that show up in search a little late), at most 24 hours
        if not existing.empty:
            newest = pd.Timestamp(existing["created_at"].max()).to_pydatetime()
            stop_before = max(newest - timedelta(hours=2), now - timedelta(hours=24))
        else:
            stop_before = now - timedelta(hours=2)
        collection, max_pages = "live", MAX_PAGES_LIVE

    token = login(handle, password)
    rows = fetch_new_posts(token, seen, stop_before, max_pages)
    if not rows:
        print("No new posts this run.")
        return 0

    for r in rows:
        r["collected_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        r["collection"] = collection
    rows = score_posts(rows)
    combined = save(existing, rows)

    n_scope = sum(r["in_scope"] for r in rows)
    print(f"Added {len(rows)} posts ({n_scope} about the connection). Total stored: {len(combined)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
