"""
Bluesky connector.

Uses Bluesky's PUBLIC search endpoint.
Handles 403/auth errors gracefully and returns empty list.
Docs: https://docs.bsky.app/docs/api/app-bsky-feed-search-posts
"""

import requests

SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
FALLBACK_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PublicFigureMonitor/1.0"


def _post_url(handle: str, uri: str):
    """Turn an at:// URI into a human-clickable bsky.app link."""
    try:
        rkey = uri.split("/")[-1]
        return f"https://bsky.app/profile/{handle}/post/{rkey}"
    except Exception:
        return None


def search_bluesky(query: str, limit: int = 50):
    """
    Search recent Bluesky posts mentioning `query`.
    Returns a list of normalized post dicts.
    Handles 403 Forbidden (API now requires auth) gracefully → returns [].
    """
    q_str = query.strip()
    words = [w for w in q_str.lstrip("#@").split() if len(w) > 1]
    if len(words) >= 2 and not q_str.startswith('"'):
        q_str = f'"{q_str}"'

    params = {"q": q_str, "limit": min(max(limit, 1), 100), "sort": "latest"}
    headers = {"User-Agent": USER_AGENT}

    data = None
    for url in [SEARCH_URL, FALLBACK_URL]:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 403:
                # Bluesky now requires auth for search — skip gracefully
                raise PermissionError("Bluesky search requires authentication. Enable Bluesky credentials or uncheck Bluesky in connectors.")
            resp.raise_for_status()
            data = resp.json()
            break
        except PermissionError:
            raise   # re-raise so pipeline shows it as a friendly warning
        except Exception:
            continue  # try fallback URL

    if not data:
        return []

    posts = []
    for item in data.get("posts", []):
        record = item.get("record", {}) or {}
        author = item.get("author", {}) or {}
        handle = author.get("handle")
        posts.append(
            {
                "platform": "bluesky",
                "id": item.get("uri"),
                "author": handle,
                "author_name": author.get("displayName") or handle,
                "text": record.get("text", "") or "",
                "created_at": record.get("createdAt"),
                "likes": item.get("likeCount", 0) or 0,
                "shares": item.get("repostCount", 0) or 0,
                "replies": item.get("replyCount", 0) or 0,
                "url": _post_url(handle, item.get("uri", "")),
            }
        )
    return posts
