"""
Pipeline: fetch -> normalize -> score -> aggregate.

This is the reusable "engine." Adding a new platform later (Telegram, YouTube,
News RSS...) means writing one more connector that returns the same normalized
dict shape and appending it in `collect`.
"""

import pandas as pd

from sentiment import score_sentiment, score_many
from analysis import estimate_region, estimate_country, detect_india_location
from emotion import detect_emotion, detect_many
from demographics import estimate_age_group


def _assign_source_group(platform: str) -> str:
    if platform == "indian_news":
        return "Indian Newspaper RSS"
    if platform == "telegram":
        return "Telegram Intel"
    if platform == "twitter":
        return "Twitter / X"
    if platform == "news":
        return "Google News"
    return "Social Media"


def build_query(term: str, search_type: str, platform: str) -> str:
    """
    Shape the raw input into a platform-appropriate query.
    search_type: 'keyword' | 'hashtag' | 'handle'
    """
    term = term.strip()
    # These platforms are plain keyword search (no native hashtag/handle syntax).
    keyword_only = platform in ("reddit", "youtube", "news", "indian_news", "mastodon", "hackernews")
    if search_type == "hashtag":
        tag = term.lstrip("#")
        return tag if keyword_only else f"#{tag}"
    if search_type == "handle":
        handle = term.lstrip("@")
        return handle if keyword_only else f"@{handle}"
    return term

NORMALIZED_FIELDS = [
    "platform", "id", "author", "author_name", "text",
    "created_at", "likes", "shares", "replies", "url",
]


def _shape_variant(q: str, platform: str) -> str:
    """Light per-platform normalization for an expansion query string."""
    return q.lstrip("#@") if platform in ("reddit", "youtube", "news", "indian_news") else q


def collect(term: str, search_type: str, sources: dict, limit: int = 50, expansions=None):
    """
    `sources` maps a platform name ('bluesky'/'reddit'/...) -> callable(query, limit).
    The raw `term` is shaped per platform via build_query. If `expansions` (a list
    of extra query strings) is given, each source is also searched for those, and
    the per-query limit is split so total volume stays ~`limit` per platform.
    Each source is wrapped so one platform failing doesn't kill the whole run.
    """
    variants = expansions or []
    n_queries = 1 + len(variants)
    per = max(10, limit // n_queries) if variants else limit

    rows = []
    errors = {}
    for name, fetch in sources.items():
        try:
            queries = [build_query(term, search_type, name)]
            queries += [_shape_variant(v, name) for v in variants]
            # Dedupe queries (case-insensitive) while preserving order.
            seen = set()
            deduped = [q for q in queries if q and not (q.lower() in seen or seen.add(q.lower()))]
            for q in deduped:
                rows.extend(fetch(q, per))
        except Exception as e:  # noqa: BLE001 - surface, don't crash
            errors[name] = str(e)

    if not rows:
        return pd.DataFrame(columns=NORMALIZED_FIELDS + ["sentiment", "score", "source_group", "age_group"]), errors

    df = pd.DataFrame(rows)

    # Relevance filter for multi-word queries:
    # Require the exact phrase OR all words to appear in text+summary combined.
    # Falls back to surname-only match to ensure real mentions are never dropped.
    term_words = [w.lower() for w in term.strip().lstrip("#@").split() if len(w) > 1]
    if len(term_words) >= 2 and not df.empty:
        term_clean = term.strip().lower()
        surname = term_words[-1]  # most specific identifier (last name)

        # Combine text + summary for matching so short headlines don't get dropped
        def _combined(row):
            return (str(row.get("text") or "") + " " + str(row.get("summary") or "")).lower()

        def _is_relevant(row):
            combined = _combined(row)
            # Match if: exact phrase found, ALL words found, or surname is present
            return (term_clean in combined
                    or all(w in combined for w in term_words)
                    or surname in combined)

        mask = df.apply(_is_relevant, axis=1)
        filtered = df[mask].reset_index(drop=True)
        # Only apply the filter if it keeps some results; otherwise show all (better than nothing)
        if not filtered.empty:
            df = filtered

    # Score every post (batched — efficient for the transformer backend).
    pairs = score_many(df["text"].tolist())
    df["sentiment"] = [p[0] for p in pairs]
    df["score"] = [p[1] for p in pairs]

    # De-dupe and compute a simple "reach" weight (engagement).
    df = df.drop_duplicates(subset=["platform", "id"]).reset_index(drop=True)
    df["engagement"] = df["likes"].fillna(0) + df["shares"].fillna(0) + df["replies"].fillna(0)

    # Source Group / Category
    df["source_group"] = df["platform"].apply(_assign_source_group)

    # Rough, content-based region/country estimate (NOT real geolocation).
    df["region"] = df["text"].apply(estimate_region)
    df["country"] = df["text"].apply(estimate_country)

    # India state/city estimate (content mentions only, with regional paper fallback).
    india_loc = df["text"].apply(detect_india_location)
    df["india_state"] = india_loc.apply(lambda d: d["state"])
    df["india_city"] = india_loc.apply(lambda d: d["city"])

    # Fallback to regional paper state hint if state not explicitly found in text
    if "state_hint" in df.columns:
        df["india_state"] = df.apply(
            lambda r: r["state_hint"] if (pd.isna(r["india_state"]) and r.get("state_hint") and r["state_hint"] != "National") else r["india_state"],
            axis=1
        )

    # If state is identified, set country to India
    df["country"] = df.apply(lambda r: "India" if pd.notna(r["india_state"]) else r["country"], axis=1)

    # Demographics: Age group estimation
    df["age_group"] = df.apply(lambda r: estimate_age_group(r["text"], r["platform"]), axis=1)

    # Coarse emotion label (love/joy/anger/hate/fear/sadness/neutral), batched.
    df["emotion"] = detect_many(df["text"].tolist())

    return df, errors



def summarize(df: pd.DataFrame) -> dict:
    """Compute the headline metrics for the dashboard."""
    if df.empty:
        return {
            "total": 0, "positive": 0, "negative": 0, "neutral": 0,
            "positivity_ratio": None, "avg_score": None,
        }

    counts = df["sentiment"].value_counts().to_dict()
    pos = counts.get("positive", 0)
    neg = counts.get("negative", 0)
    neu = counts.get("neutral", 0)
    denom = pos + neg
    positivity = round(100 * pos / denom, 1) if denom else None

    return {
        "total": len(df),
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "positivity_ratio": positivity,   # % of opinionated posts that are positive
        "avg_score": round(df["score"].mean(), 3),
    }
