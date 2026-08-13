"""
Media-vs-Public image split.

Answers the question: "What does MAINSTREAM MEDIA show as my image, versus what
the PUBLIC actually thinks?"  We separate the collected mentions into two camps
by platform and compare their sentiment, so a client can see when the press
narrative and the grassroots narrative diverge.

  - Mainstream Media  : Indian newspaper RSS, Google News, GDELT archive.
  - Public Voice      : Reddit, Bluesky, YouTube comments, Telegram, Mastodon,
                        Hacker News, Twitter/X.

Nothing here is real demographics or geolocation — it is a content/platform
split of the mentions the pipeline already collected. Treat it as directional.
"""

MEDIA_PLATFORMS = {"indian_news", "news", "gdelt"}
PUBLIC_PLATFORMS = {
    "twitter", "telegram", "reddit", "bluesky",
    "youtube", "mastodon", "hackernews",
}


def _bucket_stats(sub):
    """Sentiment breakdown for one slice of the dataframe."""
    total = len(sub)
    if total == 0:
        return {
            "total": 0, "positive": 0, "negative": 0, "neutral": 0,
            "pos_pct": 0.0, "neg_pct": 0.0, "neu_pct": 0.0,
            "avg_score": 0.0, "positivity": None, "top_emotion": "neutral",
        }
    pos = int((sub["sentiment"] == "positive").sum())
    neg = int((sub["sentiment"] == "negative").sum())
    neu = int((sub["sentiment"] == "neutral").sum())
    denom = pos + neg
    emo = sub["emotion"].value_counts() if "emotion" in sub.columns else None
    if emo is not None and not emo.empty:
        non_neu = emo.drop(labels=["neutral"], errors="ignore")
        top_emo = non_neu.idxmax() if not non_neu.empty else emo.idxmax()
    else:
        top_emo = "neutral"
    return {
        "total": total,
        "positive": pos, "negative": neg, "neutral": neu,
        "pos_pct": round(100 * pos / total, 1),
        "neg_pct": round(100 * neg / total, 1),
        "neu_pct": round(100 * neu / total, 1),
        "avg_score": round(float(sub["score"].mean()), 3),
        "positivity": (round(100 * pos / denom, 1) if denom else None),
        "top_emotion": str(top_emo),
    }


def split_media_vs_public(df) -> dict:
    """
    Return {"media": {...}, "public": {...}, "gap": {...}, "verdict": str}.

    `gap` is public_positivity - media_positivity (in percentage points): a
    positive number means the public is warmer than the press; a negative
    number means the press is warmer than the public.
    """
    if df is None or df.empty:
        return {
            "media": _bucket_stats(df.iloc[0:0]) if df is not None else _bucket_stats([]),
            "public": _bucket_stats(df.iloc[0:0]) if df is not None else _bucket_stats([]),
            "gap": {"positivity_gap": None, "avg_score_gap": None},
            "verdict": "No data collected yet — run a scan first.",
        }

    media = df[df["platform"].isin(MEDIA_PLATFORMS)]
    public = df[df["platform"].isin(PUBLIC_PLATFORMS)]
    m = _bucket_stats(media)
    p = _bucket_stats(public)

    gap_pos = None
    if m["positivity"] is not None and p["positivity"] is not None:
        gap_pos = round(p["positivity"] - m["positivity"], 1)
    gap_score = round(p["avg_score"] - m["avg_score"], 3)

    verdict = _verdict(m, p, gap_pos)
    return {
        "media": m,
        "public": p,
        "gap": {"positivity_gap": gap_pos, "avg_score_gap": gap_score},
        "verdict": verdict,
    }


def _verdict(m, p, gap_pos):
    if m["total"] == 0 and p["total"] == 0:
        return "No mentions found on either media or public channels."
    if m["total"] == 0:
        return "Only public chatter was found — mainstream media is silent on this topic right now."
    if p["total"] == 0:
        return "Only mainstream media coverage was found — little organic public discussion yet."
    if gap_pos is None:
        return "Not enough opinionated posts to compare the two narratives reliably."

    if gap_pos >= 12:
        return (
            f"The public is markedly warmer than the press (+{gap_pos} pts). The mainstream "
            "narrative is more negative than grassroots opinion — press framing, not public "
            "mood, is dragging the image down."
        )
    if gap_pos <= -12:
        return (
            f"The press is warmer than the public ({gap_pos} pts). Favourable coverage is not "
            "reaching the ground — organic sentiment is more negative than the headlines suggest."
        )
    return (
        f"Media and public narratives are broadly aligned ({gap_pos:+} pts) — the press "
        "framing and grassroots mood are telling a similar story."
    )
