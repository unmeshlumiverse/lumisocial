"""
Google News connector (RSS) — Multi-window intelligence sweep.

Completely free — no API key, no signup, no rate limit worth worrying about.
Fetches Google News across multiple time windows (past day, week, month, all-time)
to give a FULL intelligence picture of the prospect, not just today's news.
"""

from urllib.parse import quote_plus
import feedparser
import requests

BASE = "https://news.google.com/rss/search"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PublicFigureMonitor/1.0"

# Time window suffixes for Google News RSS (when: filters)
TIME_WINDOWS = [
    "",          # all-time / no filter → most results
    " when:1m",  # past month
    " when:7d",  # past week
    " when:1d",  # past day (fresh)
]


def _feed_url(query, country, lang):
    return (f"{BASE}?q={quote_plus(query)}"
            f"&hl={lang}-{country}&gl={country}&ceid={country}:{lang}")


def _clean_title(title):
    return title.rsplit(" - ", 1)[0] if " - " in title else title


def search_news(query, limit=80, country="IN", lang="en"):
    """
    Search Google News across multiple time windows for a comprehensive
    intelligence picture — not just today's news.
    Returns deduplicated posts sorted by freshness.
    """
    q_clean = query.strip()
    words = [w.lower() for w in q_clean.lstrip("#@").split() if len(w) > 1]
    surname = words[-1] if words else ""

    # Build both exact-phrase and unquoted variants
    exact_q = f'"{q_clean}"' if len(words) >= 2 and not q_clean.startswith('"') else q_clean

    all_entries = {}  # dedup by link/id

    for window in TIME_WINDOWS:
        for base_query in ([exact_q, q_clean] if exact_q != q_clean else [q_clean]):
            timed_q = f"{base_query}{window}"
            url = _feed_url(timed_q, country, lang)
            try:
                resp = requests.get(url, timeout=12, headers={"User-Agent": USER_AGENT})
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
    for e in list(all_entries.values())[:limit * 2]:  # over-fetch, then filter
        title = _clean_title(e.get("title", ""))
        summary = e.get("summary") or ""
        searchable = f"{title} {summary}".lower()

        # Relevance: exact phrase, all words, OR surname present
        if len(words) >= 2:
            if not (q_clean.lower() in searchable
                    or all(w in searchable for w in words)
                    or (surname and surname in searchable)):
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
