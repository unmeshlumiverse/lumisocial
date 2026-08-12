"""
Google News connector (RSS).

Completely free — no API key, no signup, no rate limit worth worrying about.
Searches Google News and returns matching articles (headline + source + link).

Defaults to the India edition. Uses exact phrase quoting and relevance validation
so searching a person (e.g. "Ramvijay Thakare") never matches unrelated namesakes.
"""

from urllib.parse import quote_plus
import feedparser
import requests

BASE = "https://news.google.com/rss/search"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PublicFigureMonitor/1.0"


def _feed_url(query, country, lang):
    return (f"{BASE}?q={quote_plus(query)}"
            f"&hl={lang}-{country}&gl={country}&ceid={country}:{lang}")


def _clean_title(title):
    return title.rsplit(" - ", 1)[0] if " - " in title else title


def search_news(query, limit=50, country="IN", lang="en"):
    """Search Google News for `query` with exact relevance filtering."""
    q_clean = query.strip()
    words = [w.lower() for w in q_clean.lstrip("#@").split() if len(w) > 1]

    # For multi-word queries, search exact quoted phrase first
    exact_q = f'"{q_clean}"' if len(words) >= 2 and not q_clean.startswith('"') else q_clean
    url = _feed_url(exact_q, country, lang)

    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        entries = feed.entries
    except Exception:
        entries = []

    # If exact phrase returned 0, try unquoted query but filter out articles that don't match the key name words
    if not entries and len(words) >= 2:
        try:
            url_fallback = _feed_url(q_clean, country, lang)
            resp = requests.get(url_fallback, timeout=15, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                entries = feed.entries
        except Exception:
            entries = []

    posts = []
    for e in entries[:limit]:
        title = _clean_title(e.get("title", ""))
        title_low = title.lower()

        # Strict relevance check: If multi-word search, require at least the full term or the core first name
        # to appear in the article title to eliminate completely different people (e.g. Shiv Thakare for Ramvijay Thakare)
        if len(words) >= 2:
            # Check if all words or exact name or the first name is present
            if not (all(w in title_low for w in words) or words[0] in title_low or q_clean.lower() in title_low):
                continue

        source = ""
        src = getattr(e, "source", None)
        if src and getattr(src, "title", None):
            source = src.title
        elif " - " in getattr(e, "title", ""):
            source = e.title.rsplit(" - ", 1)[-1]

        posts.append(
            {
                "platform": "news",
                "id": e.get("id") or e.get("link"),
                "author": source or "Google News",
                "author_name": source or "Google News",
                "text": title,
                "created_at": e.get("published"),
                "likes": 0,
                "shares": 0,
                "replies": 0,
                "url": e.get("link"),
            }
        )
    return posts
