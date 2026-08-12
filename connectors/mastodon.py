"""
Mastodon connector.

Free and open hashtag timeline search.
"""

import re
import datetime as dt
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_INSTANCE = "mastodon.social"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PublicFigureMonitor/1.0"


def _strip_html(s):
    return re.sub(r"<[^>]+>", " ", s or "").replace("&amp;", "&").strip()


def search_mastodon(query, limit=50, instance=DEFAULT_INSTANCE):
    """Search a public hashtag timeline. Returns normalized posts."""
    tag = re.sub(r"[^0-9a-zA-Z]+", "", query.lstrip("#@"))
    if not tag:
        return []
    url = f"https://{instance}/api/v1/timelines/tag/{tag}"
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, params={"limit": min(limit, 40)}, timeout=15, headers=headers)
    except requests.exceptions.SSLError:
        resp = requests.get(url, params={"limit": min(limit, 40)}, timeout=15, headers=headers, verify=False)

    resp.raise_for_status()

    posts = []
    for s in resp.json():
        acct = s.get("account", {}) or {}
        posts.append({
            "platform": "mastodon",
            "id": s.get("id"),
            "author": acct.get("acct", "unknown"),
            "author_name": acct.get("display_name") or acct.get("acct", "unknown"),
            "text": _strip_html(s.get("content", "")),
            "created_at": s.get("created_at"),
            "likes": s.get("favourites_count", 0) or 0,
            "shares": s.get("reblogs_count", 0) or 0,
            "replies": s.get("replies_count", 0) or 0,
            "url": s.get("url"),
        })
    return posts
