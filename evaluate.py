"""
Starlink Pulse - honest test

Step 1  python evaluate.py sample
        Picks 50 random posts about the connection and writes test/label_sheet.csv.
        The model's answer is NOT in that file, so it can't influence your labels.
        Fill in the column my_label with: negative, neutral or positive.

Step 2  python evaluate.py score
        Compares your labels with
          (a) the transformer  (cardiffnlp/twitter-roberta-base-sentiment-latest)
          (b) a simple word-list baseline (VADER)
        and writes test/test_table.csv and test/results.md.

Both steps can also be started from the GitHub Actions tab ("Honest test" workflow),
so you don't need Python on your own computer.
"""

import sys
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "posts.csv"
SHEET = ROOT / "test" / "label_sheet.csv"
TABLE = ROOT / "test" / "test_table.csv"
REPORT = ROOT / "test" / "results.md"
LABELS = ["negative", "neutral", "positive"]
N_ITEMS = 50


def sample() -> None:
    if SHEET.exists():
        done = pd.read_csv(SHEET, encoding="utf-8-sig")["my_label"].notna().sum()
        if done:
            print(f"{SHEET} already has {done} labels; not overwriting it. Delete it first to start over.")
            sys.exit(1)
    posts = pd.read_csv(DATA, dtype={"id": str})
    posts = posts[posts["in_scope"].astype(str).str.lower() == "true"]
    picked = posts.sample(n=min(N_ITEMS, len(posts)), random_state=42)
    sheet = picked[["id", "created_at", "text"]].copy()
    sheet["my_label"] = ""
    SHEET.parent.mkdir(exist_ok=True)
    sheet.to_csv(SHEET, index=False, encoding="utf-8-sig")   # utf-8-sig so Excel shows emoji/accents
    print(f"Wrote {len(sheet)} posts to {SHEET}. Fill in my_label (negative / neutral / positive).")


def vader_label(text: str, analyzer: SentimentIntensityAnalyzer) -> str:
    c = analyzer.polarity_scores(text)["compound"]
    # the standard VADER thresholds
    if c >= 0.05:
        return "positive"
    if c <= -0.05:
        return "negative"
    return "neutral"


def confusion(df: pd.DataFrame, col: str) -> str:
    m = pd.crosstab(df["my_label"], df[col]).reindex(index=LABELS, columns=LABELS, fill_value=0)
    m.index.name = "our label ↓ / predicted →"
    return m.to_markdown()


def score() -> None:
    sheet = pd.read_csv(SHEET, dtype={"id": str}, encoding="utf-8-sig")
    sheet["my_label"] = sheet["my_label"].astype(str).str.strip().str.lower()
    missing = sheet[~sheet["my_label"].isin(LABELS)]
    if len(missing):
        print(f"{len(missing)} rows have no valid my_label yet (use negative / neutral / positive). Stopping.")
        sys.exit(1)

    posts = pd.read_csv(DATA, dtype={"id": str})[["id", "label", "neg", "neu", "pos"]]
    df = sheet.merge(posts, on="id", how="left").rename(columns={"label": "model_label"})
    analyzer = SentimentIntensityAnalyzer()
    df["vader_label"] = [vader_label(t, analyzer) for t in df["text"]]
    df["model_correct"] = df["model_label"] == df["my_label"]
    df["vader_correct"] = df["vader_label"] == df["my_label"]
    df["model_confidence"] = df[["neg", "neu", "pos"]].max(axis=1).round(2)

    out = df[["id", "text", "my_label", "model_label", "model_confidence", "vader_label",
              "model_correct", "vader_correct"]]
    out.to_csv(TABLE, index=False, encoding="utf-8-sig")

    n = len(df)
    model_acc, vader_acc = df["model_correct"].mean(), df["vader_correct"].mean()
    wrong = df[~df["model_correct"]]
    both_wrong = df[~df["model_correct"] & ~df["vader_correct"]]
    vader_only_right = df[~df["model_correct"] & df["vader_correct"]]

    lines = [
        "# Honest test: model vs our own labels",
        "",
        f"We labelled **{n}** randomly chosen posts ourselves before looking at the model's answers.",
        "",
        "| | Agrees with us | Count |",
        "|---|---|---|",
        f"| Transformer (`cardiffnlp/twitter-roberta-base-sentiment-latest`) | **{model_acc:.0%}** | {df['model_correct'].sum()} / {n} |",
        f"| Word-list baseline (VADER) | **{vader_acc:.0%}** | {df['vader_correct'].sum()} / {n} |",
        "",
        "## Where the transformer goes wrong",
        "",
        confusion(df, "model_label"),
        "",
        "## Where the word-list baseline goes wrong",
        "",
        confusion(df, "vader_label"),
        "",
        f"Both wrong on the same post: {len(both_wrong)}. Baseline right where the transformer was wrong: {len(vader_only_right)}.",
        "",
        "## Every post the transformer got wrong",
        "",
        "Pick at least three and explain *why* (sarcasm, negation, jargon, mixed message, not really about the connection ...).",
        "",
        "| Post | Us | Transformer (confidence) | VADER | Why it went wrong (fill in) |",
        "|---|---|---|---|---|",
    ]
    for _, r in wrong.iterrows():
        text = str(r["text"]).replace("|", "/").replace("\n", " ")
        lines.append(f"| {text} | {r['my_label']} | {r['model_label']} ({r['model_confidence']:.0%}) | {r['vader_label']} | |")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Transformer agrees {model_acc:.0%}, VADER agrees {vader_acc:.0%}. See {REPORT} and {TABLE}.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("sample", "score"):
        print(__doc__)
        sys.exit(1)
    sample() if sys.argv[1] == "sample" else score()
