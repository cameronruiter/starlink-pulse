"""
Starlink Pulse - dashboard

Shows how the tone of public Bluesky posts about Starlink connections changes
over time, and lets you open the posts behind any peak or dip.

Run locally:   streamlit run app.py
Run online:    deploy this repo on https://share.streamlit.io (free), main file: app.py
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# The dashboard reads the data file straight from GitHub, so it is always up to date.
DATA_URL = "https://raw.githubusercontent.com/cameronruiter/starlink-pulse/main/data/posts.csv"
LOCAL_FILE = Path(__file__).parent / "data" / "posts.csv"
MIN_ITEMS = 5           # periods with fewer posts than this are too thin to judge

COLORS = {"negative": "#e34948", "neutral": "#9c9a92", "positive": "#2a78d6"}
ORDER = ["negative", "neutral", "positive"]

st.set_page_config(page_title="Starlink Pulse", page_icon="📡", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, str]:
    try:
        df, source = pd.read_csv(DATA_URL, dtype={"id": str}), "GitHub (live)"
    except Exception:
        if not LOCAL_FILE.exists():
            return pd.DataFrame(), "no data yet"
        df, source = pd.read_csv(LOCAL_FILE, dtype={"id": str}), "local file"
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True)
    df["in_scope"] = df["in_scope"].astype(str).str.lower().eq("true")
    return df, source


df, source = load_data()

# ---------------------------------------------------------------- header
st.title("📡 Starlink Pulse")
st.caption("How people on Bluesky talk about their Starlink connection, hour by hour. "
           "For a municipal broadband officer preparing advice on a Starlink pilot or subsidy.")

st.warning(
    "**Read this before using the chart.** It shows the *tone* of public, English-language "
    "Bluesky posts that mention Starlink. It is **not** a measurement of outages or speed, and "
    "**not** what residents think: people who are offline, don't use Bluesky, or write in other "
    "languages are missing. The sentiment is guessed by an AI model that misreads sarcasm and "
    "jargon. Treat a rise in negative posts as a reason to look closer, never as proof.",
    icon="⚠️",
)

if df.empty:
    st.info("No data collected yet. The collector runs every 30 minutes.")
    st.stop()

# ---------------------------------------------------------------- filters
f1, f2, f3 = st.columns([1, 1, 2])
with f1:
    step = st.radio("Group per", ["hour", "day"], horizontal=True)
with f2:
    only_scope = st.toggle("Only posts about the connection", value=True,
                           help="Keeps posts that mention things like internet, outage, speed, "
                                "dish or rural, and leaves out posts about rockets and launches.")
with f3:
    include_backfill = st.toggle("Include the catch-up run", value=True,
                                 help="On the first run the tool collected posts from the 48 hours "
                                      "before it started. Switch off to see only posts collected live.")

view = df.copy()
if only_scope:
    view = view[view["in_scope"]]
if not include_backfill:
    view = view[view["collection"] == "live"]
if view.empty:
    st.info("No posts match these filters yet.")
    st.stop()

freq = "h" if step == "hour" else "D"
view["period"] = view["created_at"].dt.floor(freq)

# ---------------------------------------------------------------- headline numbers
last_run = df["collected_at"].max()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Posts in view", f"{len(view):,}")
k2.metric("Negative", f"{(view['label'] == 'negative').mean():.0%}")
k3.metric("Positive", f"{(view['label'] == 'positive').mean():.0%}")
k4.metric("Last collected", last_run.strftime("%d %b %H:%M UTC"))

# ---------------------------------------------------------------- per-period table
per = (view.groupby("period")
           .agg(posts=("id", "size"),
                negative=("label", lambda s: (s == "negative").sum()),
                neutral=("label", lambda s: (s == "neutral").sum()),
                positive=("label", lambda s: (s == "positive").sum()))
           .reset_index())
per["neg_share"] = per["negative"] / per["posts"]
per["enough"] = per["posts"] >= MIN_ITEMS

# A period is "unusual" when its share of negative posts is clearly above normal:
# more than two standard deviations above the average of periods with enough posts.
solid = per[per["enough"]]
if len(solid) >= 4:
    threshold = solid["neg_share"].mean() + 2 * solid["neg_share"].std()
else:
    threshold = 1.01   # not enough history to call anything unusual yet
per["unusual"] = per["enough"] & (per["neg_share"] > threshold)
fmt = "%d %b %H:00" if step == "hour" else "%a %d %b"
per["label"] = per["period"].dt.strftime(fmt)

# ---------------------------------------------------------------- chart 1: share negative
st.subheader(f"Share of negative posts per {step}")
st.caption(f"Dots for periods with fewer than {MIN_ITEMS} posts are faded: too few to judge. "
           "Red rings mark an unusual rise in negative posts.")

base = alt.Chart(per).encode(
    x=alt.X("period:T", title=None, axis=alt.Axis(format="%d %b %H:%M" if step == "hour" else "%d %b")),
)
tooltip = [alt.Tooltip("label:N", title="Period"),
           alt.Tooltip("posts:Q", title="Posts"),
           alt.Tooltip("neg_share:Q", title="Negative", format=".0%"),
           alt.Tooltip("negative:Q", title="Negative posts"),
           alt.Tooltip("positive:Q", title="Positive posts")]
# the line only connects periods with enough posts, so one lonely post can't draw a 100% spike
line = base.transform_filter("datum.enough").mark_line(color=COLORS["negative"], strokeWidth=2).encode(
    y=alt.Y("neg_share:Q", title="Negative posts", axis=alt.Axis(format="%"),
            scale=alt.Scale(domain=[0, 1])))
dots = base.mark_circle(size=70, color=COLORS["negative"]).encode(
    y="neg_share:Q",
    opacity=alt.condition("datum.enough", alt.value(1), alt.value(0.25)),
    tooltip=tooltip)
rings = base.transform_filter("datum.unusual").mark_point(
    size=320, color=COLORS["negative"], strokeWidth=2.5, filled=False).encode(y="neg_share:Q", tooltip=tooltip)
st.altair_chart((line + dots + rings).properties(height=280), width="stretch")

# ---------------------------------------------------------------- chart 2: volume & mix
st.subheader(f"Number of posts per {step}, by tone")
st.caption("Always read the share above together with how many posts it is based on.")
long = per.melt(id_vars=["period", "label", "posts"], value_vars=ORDER,
                var_name="tone", value_name="count")
bars = alt.Chart(long).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
    x=alt.X("period:T", title=None, axis=alt.Axis(format="%d %b %H:%M" if step == "hour" else "%d %b")),
    y=alt.Y("count:Q", title="Posts", stack=True),
    color=alt.Color("tone:N", scale=alt.Scale(domain=ORDER, range=[COLORS[t] for t in ORDER]),
                    legend=alt.Legend(title=None, orient="top")),
    order=alt.Order("tone_order:Q"),
    tooltip=[alt.Tooltip("label:N", title="Period"), alt.Tooltip("tone:N", title="Tone"),
             alt.Tooltip("count:Q", title="Posts"), alt.Tooltip("posts:Q", title="All posts")],
).transform_calculate(tone_order="indexof(['negative','neutral','positive'], datum.tone)")
st.altair_chart(bars.properties(height=220), width="stretch")

# ---------------------------------------------------------------- posts behind a peak
st.subheader("What's behind a peak or dip?")
options = per.sort_values("period", ascending=False)
# default: the most recent unusual period, otherwise the most negative period with enough posts
if per["unusual"].any():
    default_period = per[per["unusual"]]["period"].max()
elif per["enough"].any():
    default_period = per[per["enough"]].sort_values("neg_share").iloc[-1]["period"]
else:
    default_period = per["period"].max()


def describe(p):
    row = per[per["period"] == p].iloc[0]
    flag = "  ⚠️ unusual" if row["unusual"] else ""
    return f"{row['label']}  ·  {row['posts']} posts  ·  {row['neg_share']:.0%} negative{flag}"


periods = list(options["period"])
chosen = st.selectbox("Pick a period", periods, index=periods.index(default_period), format_func=describe)
posts = view[view["period"] == chosen].copy()
posts["confidence"] = posts[["neg", "neu", "pos"]].max(axis=1)
posts = posts.sort_values("score")[["created_at", "label", "confidence", "text"]]
posts["created_at"] = posts["created_at"].dt.strftime("%d %b %H:%M")
st.dataframe(
    posts.rename(columns={"created_at": "Posted (UTC)", "label": "Model says",
                          "confidence": "Model confidence", "text": "Post"}),
    hide_index=True, width="stretch",
    column_config={"Model confidence": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1),
                   "Post": st.column_config.TextColumn(width="large")},
)

# ---------------------------------------------------------------- footer
with st.expander("How this works"):
    st.markdown(f"""
- **Stream:** public English Bluesky posts containing "starlink", fetched every 30 minutes by `collector.py` (GitHub Actions).
- **Model:** `cardiffnlp/twitter-roberta-base-sentiment-latest`, a pre-trained transformer from Hugging Face, trained on tweets. Labels: negative / neutral / positive.
- **Stored:** only the post text (links and @mentions removed), the time and the sentiment. No names, handles or profiles.
- **Unusual rise:** a period whose share of negative posts is more than two standard deviations above the average, counting only periods with at least {MIN_ITEMS} posts.
- **Data:** {len(df):,} posts stored in total ({(df['collection'] == 'live').sum():,} collected live, {(df['collection'] == 'backfill').sum():,} from the first catch-up run). Source: {source}.
""")
