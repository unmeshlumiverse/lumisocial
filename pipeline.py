"""
Pipeline: fetch -> normalize -> score -> aggregate.

This is the reusable "engine." Adding a new platform later (Telegram, YouTube,
News RSS...) means writing one more connector that returns the same normalized
dict shape and appending it in `collect`.
"""

import datetime as dt
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def _fetch_source(name, fetch):
        """
        Runs one platform's full query set. Kept sequential *within* a source
        (one query after another) so we never burst a single API with parallel
        requests and trip its rate limit — only different platforms (independent
        services) run concurrently with each other, below.
        """
        queries = [build_query(term, search_type, name)]
        queries += [_shape_variant(v, name) for v in variants]
        # Dedupe queries (case-insensitive) while preserving order.
        seen = set()
        deduped = [q for q in queries if q and not (q.lower() in seen or seen.add(q.lower()))]
        source_rows = []
        for q in deduped:
            source_rows.extend(fetch(q, per))
        return source_rows

    rows = []
    errors = {}
    source_counts = {}
    with ThreadPoolExecutor(max_workers=max(1, len(sources))) as pool:
        future_to_name = {pool.submit(_fetch_source, name, fetch): name for name, fetch in sources.items()}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                source_rows = future.result()
                rows.extend(source_rows)
                source_counts[name] = len(source_rows)
            except Exception as e:  # noqa: BLE001 - surface, don't crash
                errors[name] = str(e)
                source_counts[name] = 0
    errors["__source_counts__"] = source_counts  # per-connector raw counts, for UI diagnostics

    if not rows:
        return pd.DataFrame(columns=NORMALIZED_FIELDS + ["sentiment", "score", "source_group", "age_group"]), errors

    df = pd.DataFrame(rows)

    def _searchable(row):
        """
        Text used for relevance matching. Deliberately strips the post's own
        publisher/author name first — Google News RSS descriptions embed the
        outlet's own name as boilerplate (e.g. every Amar Ujala article's
        summary contains the literal text "Amar Ujala"), which was causing
        false-positive matches: searching "Amar Thakare" matched unrelated
        "Shiv Thakare" articles purely because they were published BY Amar
        Ujala, not because they were ABOUT the right person.
        """
        txt = f"{row.get('text') or ''} {row.get('summary') or ''}"
        outlet = str(row.get("author_name") or "").strip()
        if outlet and len(outlet) > 2:
            txt = re.sub(re.escape(outlet), " ", txt, flags=re.IGNORECASE)
        return txt.lower()

    # ── Strict Relevance Filter ──────────────────────────────────────────────
    # For multi-word person names, BOTH words must appear in the article.
    # Surname-only fallback is intentionally removed — it causes false positives
    # (e.g. "thakare" alone matches Shiv Thakare, Ramvijay Thakare, etc.)
    #
    # Some platforms are exempt because their OWN connector already establishes
    # relevance more reliably than a second headline-only text match here could:
    #   - youtube: comments are already scoped to videos YouTube's own search
    #     matched to the query, so requiring a random comment to also literally
    #     repeat the person's full name discards most genuine, relevant ones
    #     ("such an inspiring story!" doesn't say "Amar Thakare" — it doesn't
    #     need to).
    #   - news (Google News): search_news() already ran a quoted exact-phrase
    #     query, i.e. Google verified the phrase against the FULL article text,
    #     not just the (often rewritten/generic) headline we can see. A second
    #     headline-only check here would re-reject legitimately relevant
    #     articles whose headline just doesn't happen to repeat the name.
    #   - gdelt: same reasoning — its query is also a quoted exact-phrase
    #     full-text search, and we only ever get the headline back, no body.
    _UPSTREAM_VETTED_PLATFORMS = {"youtube", "news", "gdelt"}
    term_words = [w.lower() for w in term.strip().lstrip("#@").split() if len(w) > 1]
    errors["__raw_total__"] = str(len(rows))  # shown as debug info in UI

    if len(term_words) >= 2 and not df.empty:
        term_clean = term.strip().lower()

        def _is_relevant(r):
            if r.get("platform") in _UPSTREAM_VETTED_PLATFORMS:
                return True
            return term_clean in _searchable(r) or all(w in _searchable(r) for w in term_words)

        # Require exact phrase OR all words present — no surname-only shortcut
        strict_mask = df.apply(_is_relevant, axis=1)
        strict_df = df[strict_mask].reset_index(drop=True)

        # Only apply if it keeps results — don't replace with empty
        # (if truly 0 match, empty df is correct — show no results message)
        df = strict_df

    errors["__post_relevance_total__"] = str(len(df))

    # ── Disambiguation: exclude terms (hard drop) ────────────────────────────
    # Answers to "who is NOT this person" — a known namesake, movie, unrelated
    # scandal, etc. Any row mentioning one is dropped outright. Best-effort: if
    # this fails for any reason, keep going with the unfiltered rows rather
    # than losing the whole report over an optional refinement.
    try:
        exclude_terms = [t.strip().lower() for t in (exclude_terms or []) if t and t.strip()]
        if exclude_terms and not df.empty:
            exclude_mask = df.apply(lambda r: any(x in _searchable(r) for x in exclude_terms), axis=1)
            df = df[~exclude_mask].reset_index(drop=True)
    except Exception as e:
        errors["__exclude_filter_error__"] = str(e)

    # ── Disambiguation: context hints (soft boost, never drops rows) ─────────
    # Answers to "where / what org is this person tied to" — a state, city,
    # party, company. We can't require it (most headlines omit it) so we just
    # flag matches; the UI ranks/badges them as higher-confidence.
    try:
        context_hints = [c.strip().lower() for c in (context_hints or []) if c and c.strip()]
        if not df.empty:
            if context_hints:
                df["context_match"] = df.apply(lambda r: any(c in _searchable(r) for c in context_hints), axis=1)
            else:
                df["context_match"] = False
    except Exception as e:
        errors["__context_hint_error__"] = str(e)
        df["context_match"] = False

    # ── Time range filter ─────────────────────────────────────────────────────
    # Rows with no parseable date are dropped for a specific window (can't verify
    # they belong in it) but kept for "All Available Data".
    try:
        if not df.empty:
            start, end = time_range_bounds(time_range)
            if start is not None:
                parsed = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
                in_window = parsed.notna() & (parsed >= start) & (parsed <= end)
                df = df[in_window].reset_index(drop=True)
    except Exception as e:
        errors["__time_filter_error__"] = str(e)

    errors["__post_filter_total__"] = str(len(df))

    if df.empty:
        return pd.DataFrame(columns=NORMALIZED_FIELDS + ["sentiment", "score", "source_group", "age_group"]), errors

    # ── Scoring & enrichment ──────────────────────────────────────────────────
    # Wrapped as a whole: any single enrichment step failing (a model backend
    # unavailable on this host, unexpected input shape from a connector, a
    # pandas edge case) should degrade to a still-usable, if less enriched,
    # report instead of crashing the entire run.
    try:
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
    except Exception as e:
        errors["__enrichment_error__"] = f"{type(e).__name__}: {e}"
        # Minimal-but-safe fallback so the UI (which expects these columns to
        # always exist) still renders instead of crashing the whole report.
        df = df.drop_duplicates(subset=["platform", "id"]).reset_index(drop=True)
        if "sentiment" not in df.columns:
            df["sentiment"] = "neutral"
        if "score" not in df.columns:
            df["score"] = 0.0
        df["engagement"] = df.get("likes", 0).fillna(0) + df.get("shares", 0).fillna(0) + df.get("replies", 0).fillna(0)
        df["source_group"] = df["platform"].apply(_assign_source_group)
        for col, default in (
            ("region", "Unknown"), ("country", "Unknown"), ("india_state", None),
            ("india_city", None), ("age_group", "Unknown"), ("emotion", "neutral"),
            ("context_match", False),
        ):
            if col not in df.columns:
                df[col] = default

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
