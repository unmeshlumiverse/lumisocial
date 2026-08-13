"""
Google News connector (RSS) — Multi-window, multi-language intelligence sweep.

Completely free — no API key, no signup, no rate limit worth worrying about.
Fetches Google News across multiple time windows AND multiple language/region editions
to give a FULL intelligence picture of any prospect — national or regional politician.
"""

from urllib.parse import quote_plus
import feedparser
import requests

BASE = "https://news.google.com/rss/search"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PublicFigureMonitor/1.0"

# Time window suffixes for Google News RSS
TIME_WINDOWS = [
    "",          # all-time / no filter
    " when:1m",  # past month
    " when:7d",  # past week
]

# Language+Country combos to cover national + regional Indian media
EDITIONS = [
    ("IN", "en"),   # English India — national press
    ("IN", "hi"),   # Hindi India — Dainik Jagran, Amar Ujala etc.
    ("IN", "mr"),   # Marathi India — Lokmat, Sakal, Maharashtra Times
    ("IN", "te"),   # Telugu — Eenadu, Sakshi
    ("IN", "ta"),   # Tamil — Dinamalar, Daily Thanthi
    ("IN", "bn"),   # Bengali — Anandabazar
]


def _feed_url(query, country, lang):
    return (f"{BASE}?q={quote_plus(query)}"
            f"&hl={lang}-{country}&gl={country}&ceid={country}:{lang}")


def _clean_title(title):
    return title.rsplit(" - ", 1)[0] if " - " in title else title


def _resolve_source(e):
    src = getattr(e, "source", None)
    if src and getattr(src, "title", None):
        return src.title
    if " - " in getattr(e, "title", ""):
        return e.title.rsplit(" - ", 1)[-1]
    return ""


def search_news(query, limit=100, country="IN", lang="en"):
    """
    Search Google News across multiple time windows AND multiple language editions
    for comprehensive regional + national coverage of any prospect.
    Returns deduplicated posts.
    """
    q_clean = query.strip()
    words = [w.lower() for w in q_clean.lstrip("#@").split() if len(w) > 1]

    # Build both exact-phrase and unquoted variants
    exact_q = f'"{q_clean}"' if len(words) >= 2 and not q_clean.startswith('"') else q_clean

    all_entries = {}     # dedup by link/id
    trusted_keys = set()  # entries found via the quoted exact-phrase query

    for (ed_country, ed_lang) in EDITIONS:
        for window in TIME_WINDOWS:
            queries_to_try = [(exact_q + window, True)]
            if exact_q != q_clean:
                queries_to_try.append((q_clean + window, False))  # also try unquoted

            for q_variant, is_exact in queries_to_try:
                url = _feed_url(q_variant, ed_country, ed_lang)
                try:
                    resp = requests.get(url, timeout=10, headers={"User-Agent": USER_AGENT})
                    if resp.status_code != 200:
                        continue
                    feed = feedparser.parse(resp.content)
                    for e in feed.entries:
                        key = e.get("id") or e.get("link") or ""
                        if not key:
                            continue
                        if key not in all_entries:
                            all_entries[key] = e
                        # Trust the quoted exact-phrase match as pre-verified relevance
                        # (Google matched it against the FULL article text, not just the
                        # headline we get back) — but ONLY for the English edition. Non-
                        # English editions turned out to loosely fuzzy-match a quoted
                        # phrase rather than enforce it, letting in unrelated regional
                        # content; the ASCII-text sanity check below still applies there.
                        if is_exact and ed_lang == "en":
                            trusted_keys.add(key)
                except Exception:
                    continue

    posts = []
    for key, e in all_entries.items():
        title = _clean_title(e.get("title", ""))
        summary = e.get("summary") or ""
        source = _resolve_source(e)

        # Relevance re-check only for entries NOT already vetted by Google's own
        # full-text exact-phrase match. And strip the outlet's own name first —
        # Google's summary boilerplate embeds it (e.g. every Amar Ujala article's
        # summary literally contains "Amar Ujala"), which falsely satisfies a
        # first-name match against an unrelated person's article.
        if key not in trusted_keys and len(words) >= 2:
            searchable = f"{title} {summary}".lower()
            if source and len(source) > 2:
                searchable = searchable.replace(source.lower(), " ")
            if not (q_clean.lower() in searchable or all(w in searchable for w in words)):
                continue

        posts.append({
            "platform": "news",
            "id": e.get("id") or e.get("link"),
            "author": source or "Google News",
            "author_name": source or "Google News",
            "text": title,
            "summary": summary,
            "created_at": e.get("published"),
            "likes": 0,
            "shares": 0,
            "replies": 0,
            "url": e.get("link"),
        })

    return posts[:limit]
