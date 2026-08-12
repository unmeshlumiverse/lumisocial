"""
Pipeline: fetch -> normalize -> score -> aggregate.

This is the reusable "engine." Adding a new platform later (Telegram, YouTube,
News RSS...) means writing one more connector that returns the same normalized
dict shape and appending it in `collect`.
"""

import datetime as dt

import pandas as pd

from sentiment import score_sentiment, score_many
from analysis import estimate_region, estimate_country, detect_india_location
from emotion import detect_emotion, detect_many
from demographics import estimate_age_group

TIME_RANGE_WINDOWS = {
    "Past 24 Hours": dt.timedelta(hours=24),
    "Past 1 Week": dt.timedelta(days=7),
    "Past 1 Month": dt.timedelta(days=30),
    "All Available Data": None,
}


def time_range_bounds(time_range: str):
    """Return (start_utc, end_utc) for a time_range label, or (None, None) for all-time."""
    window = TIME_RANGE_WINDOWS.get(time_range)
    if window is None:
        return None, None
    end = dt.datetime.now(dt.timezone.utc)
    return end - window, end


def _assign_source_group(platform: str) -> str:
    if platform == "indian_news":
        return "Indian Newspaper RSS"
    if platform == "telegram":
        return "Telegram Intel"
    if platform == "twitter":
        return "Twitter / X"
    if platform == "news":
        return "Google News"
    if platform == "gdelt":
        return "GDELT Historical Archive"
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


def collect(term: str, search_type: str, sources: dict, limit: int = 50, expansions=None,
            time_range: str = "All Available Data", context_hints=None, exclude_terms=None):
    """
    `sources` maps a platform name ('bluesky'/'reddit'/...) -> callable(query, limit).
    The raw `term` is shaped per platform via build_query. If `expansions` (a list
    of extra query strings) is given, each source is also searched for those, and
    the per-query limit is split so total volume stays ~`limit` per platform.
    Each source is wrapped so one platform failing doesn't kill the whole run.

    `time_range` restricts the returned rows to a window of `created_at` (rows with
    an unparseable/missing date are dropped unless time_range is "All Available Data").
    `context_hints` (e.g. ["Maharashtra", "BJP"]) are disambiguation answers — rows that
    mention at least one hint get flagged via a `context_match` column so the UI can
    rank/badge them, without hard-dropping legitimate matches that omit the hint text.
    `exclude_terms` are hard-dropped: any row whose text contains one is removed
    (used to rule out known namesakes / unrelated entities).
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

    def _searchable(row):
        return (str(row.get("text") or "") + " " + str(row.get("summary") or "")).lower()

    # ── Strict Relevance Filter ──────────────────────────────────────────────
    # For multi-word person names, BOTH words must appear in the article.
    # Surname-only fallback is intentionally removed — it causes false positives
    # (e.g. "thakare" alone matches Shiv Thakare, Ramvijay Thakare, etc.)
    term_words = [w.lower() for w in term.strip().lstrip("#@").split() if len(w) > 1]
    errors["__raw_total__"] = str(len(rows))  # shown as debug info in UI

    if len(term_words) >= 2 and not df.empty:
        term_clean = term.strip().lower()

        # Require exact phrase OR all words present — no surname-only shortcut
        strict_mask = df.apply(
            lambda r: term_clean in _searchable(r) or all(w in _searchable(r) for w in term_words),
            axis=1
        )
        strict_df = df[strict_mask].reset_index(drop=True)

        # Only apply if it keeps results — don't replace with empty
        # (if truly 0 match, empty df is correct — show no results message)
        df = strict_df

    errors["__post_relevance_total__"] = str(len(df))

    # ── Disambiguation: exclude terms (hard drop) ────────────────────────────
    # Answers to "who is NOT this person" — a known namesake, movie, unrelated
    # scandal, etc. Any row mentioning one is dropped outright.
    exclude_terms = [t.strip().lower() for t in (exclude_terms or []) if t and t.strip()]
    if exclude_terms and not df.empty:
        exclude_mask = df.apply(lambda r: any(x in _searchable(r) for x in exclude_terms), axis=1)
        df = df[~exclude_mask].reset_index(drop=True)

    # ── Disambiguation: context hints (soft boost, never drops rows) ─────────
    # Answers to "where / what org is this person tied to" — a state, city,
    # party, company. We can't require it (most headlines omit it) so we just
    # flag matches; the UI ranks/badges them as higher-confidence.
    context_hints = [c.strip().lower() for c in (context_hints or []) if c and c.strip()]
    if not df.empty:
        if context_hints:
            df["context_match"] = df.apply(lambda r: any(c in _searchable(r) for c in context_hints), axis=1)
        else:
            df["context_match"] = False

    # ── Time range filter ─────────────────────────────────────────────────────
    # Rows with no parseable date are dropped for a specific window (can't verify
    # they belong in it) but kept for "All Available Data".
    if not df.empty:
        start, end = time_range_bounds(time_range)
        parsed = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        if start is not None:
            in_window = parsed.notna() & (parsed >= start) & (parsed <= end)
            df = df[in_window].reset_index(drop=True)

    errors["__post_filter_total__"] = str(len(df))

    if df.empty:
        return pd.DataFrame(columns=NORMALIZED_FIELDS + ["sentiment", "score", "source_group", "age_group"]), errors

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
