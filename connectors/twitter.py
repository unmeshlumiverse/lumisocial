"""
Twitter / X connector (Official API v2).

Compliant search using official Twitter API v2 endpoints.
Requires TWITTER_BEARER_TOKEN environment variable.
"""

import os
import requests

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


def search_twitter(query: str, limit: int = 50):
    """
    Search Twitter/X via official API v2.
    Returns normalized posts.
    """
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        raise RuntimeError(
            "Twitter credentials missing. Set TWITTER_BEARER_TOKEN in your environment or .env file."
        )

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "PublicFigureMonitor/1.0",
    }

    q_str = query.strip()
    words = [w for w in q_str.lstrip("#@").split() if len(w) > 1]
    if len(words) >= 2 and not q_str.startswith('"'):
        q_str = f'"{q_str}"'

    params = {
        "query": q_str,
        "max_results": min(100, max(10, limit)),
        "tweet.fields": "created_at,public_metrics,author_id,lang",
        "expansions": "author_id",
        "user.fields": "username,name",
    }

    resp = requests.get(TWITTER_SEARCH_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    tweets = data.get("data", [])
    includes = data.get("includes", {})
    users = {u["id"]: u for u in includes.get("users", [])}

    posts = []
    for t in tweets:
        author_id = t.get("author_id", "")
        u_info = users.get(author_id, {})
        username = u_info.get("username", author_id)
        name = u_info.get("name", username)
        metrics = t.get("public_metrics", {})

        posts.append({
            "platform": "twitter",
            "id": t.get("id"),
            "author": username,
            "author_name": name,
            "text": t.get("text", ""),
            "created_at": t.get("created_at"),
            "likes": metrics.get("like_count", 0),
            "shares": metrics.get("retweet_count", 0) + metrics.get("quote_count", 0),
            "replies": metrics.get("reply_count", 0),
            "url": f"https://x.com/{username}/status/{t.get('id')}",
        })

    return posts
