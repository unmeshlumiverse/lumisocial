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


def search_news(query, limit=100, country="IN", lang="en"):
    """
    Search Google News across multiple time windows AND multiple language editions
    for comprehensive regional + national coverage of any prospect.
    Returns deduplicated posts.
    """
    q_clean = query.strip()
    words = [w.lower() for w in q_clean.lstrip("#@").split() if len(w) > 1]
    surname = words[-1] if words else ""
    firstname = words[0] if words else ""

    # Build both exact-phrase and unquoted variants
    exact_q = f'"{q_clean}"' if len(words) >= 2 and not q_clean.startswith('"') else q_clean

    all_entries = {}  # dedup by link/id

    for (ed_country, ed_lang) in EDITIONS:
        for window in TIME_WINDOWS:
            queries_to_try = [exact_q + window]
            if exact_q != q_clean:
                queries_to_try.append(q_clean + window)  # also try unquoted

            for q_variant in queries_to_try:
                url = _feed_url(q_variant, ed_country, ed_lang)
                try:
                    resp = requests.get(url, timeout=10, headers={"User-Agent": USER_AGENT})
                    if resp.status_code != 200:
                        continue
                    feed = feedparser.parse(resp.content)
                    for e in feed.entries:
                        key = e.get("id") or e.get("link") or ""
                        if key and key not in all_entries:
                            all_entries[key] = e
                except Exception:
                    continue

    posts = []
    for e in list(all_entries.values()):
        title = _clean_title(e.get("title", ""))
        summary = e.get("summary") or ""
        searchable = f"{title} {summary}".lower()

        # Relevance: exact phrase, all words, OR surname present
        # For regional politicians the headline might only use the surname
        if len(words) >= 2:
            if not (q_clean.lower() in searchable
                    or all(w in searchable for w in words)
                    or (surname and surname in searchable)
                    or (firstname and firstname in searchable and len(firstname) > 3)):
                continue

        source = ""
        src = getattr(e, "source", None)
        if src and getattr(src, "title", None):
            source = src.title
        elif " - " in getattr(e, "title", ""):
            source = e.title.rsplit(" - ", 1)[-1]

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
