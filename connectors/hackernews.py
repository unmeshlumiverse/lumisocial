"""
Hacker News connector (Algolia API).

Completely free, no key. Great for tech / policy / business discussion about a
person or topic. Searches stories and comments.
"""

import datetime as dt

import requests

SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def search_hackernews(query, limit=50):
    """Search Hacker News stories + comments for `query`. Returns normalized posts."""
    q = query.lstrip("#@")
    resp = requests.get(SEARCH_URL, params={
        "query": q, "tags": "(story,comment)", "hitsPerPage": min(limit, 100),
    }, timeout=20, headers={"User-Agent": "public-figure-monitor/0.1"})
    resp.raise_for_status()

    posts = []
    for h in resp.json().get("hits", []):
        text = h.get("title") or h.get("story_title") or h.get("comment_text") or ""
        oid = h.get("objectID")
        created = None
        if h.get("created_at_i"):
            created = dt.datetime.fromtimestamp(h["created_at_i"], tz=dt.timezone.utc).isoformat()
        posts.append({
            "platform": "hackernews",
            "id": oid,
            "author": h.get("author", "unknown"),
            "author_name": h.get("author", "unknown"),
            "text": text,
            "created_at": created,
            "likes": h.get("points", 0) or 0,
            "shares": 0,
            "replies": h.get("num_comments", 0) or 0,
            "url": f"https://news.ycombinator.com/item?id={oid}",
        })
    return posts
