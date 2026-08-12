"""
Reddit connector.

Uses PRAW in READ-ONLY mode.
"""

import os
import datetime as dt
import praw


def _get_reddit():
    client_id = (os.environ.get("REDDIT_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("REDDIT_CLIENT_SECRET") or "").strip()
    user_agent = os.environ.get("REDDIT_USER_AGENT", "public-figure-monitor/0.1")

    if not client_id or not client_secret or "YOUR_" in client_id.upper():
        raise RuntimeError(
            "Reddit credentials missing or placeholder used. Set real REDDIT_CLIENT_ID and "
            "REDDIT_CLIENT_SECRET in .env file."
        )

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    reddit.read_only = True
    return reddit


def search_reddit(query: str, limit: int = 50, include_comments: bool = True,
                  comments_per_post: int = 3):
    """
    Search Reddit submissions mentioning `query` across all subreddits.
    Returns normalized post dicts.
    """
    try:
        reddit = _get_reddit()
        posts = []

        for sub in reddit.subreddit("all").search(query, sort="new", limit=limit):
            created = dt.datetime.fromtimestamp(
                sub.created_utc, tz=dt.timezone.utc
            ).isoformat()
            body = f"{sub.title}\n{sub.selftext or ''}".strip()
            posts.append(
                {
                    "platform": "reddit",
                    "id": sub.id,
                    "author": str(sub.author) if sub.author else "[deleted]",
                    "author_name": str(sub.author) if sub.author else "[deleted]",
                    "text": body,
                    "created_at": created,
                    "likes": sub.score or 0,
                    "shares": 0,
                    "replies": sub.num_comments or 0,
                    "url": f"https://reddit.com{sub.permalink}",
                }
            )

            if include_comments and comments_per_post > 0:
                try:
                    sub.comment_sort = "top"
                    sub.comments.replace_more(limit=0)
                    for c in sub.comments[:comments_per_post]:
                        c_created = dt.datetime.fromtimestamp(
                            c.created_utc, tz=dt.timezone.utc
                        ).isoformat()
                        posts.append(
                            {
                                "platform": "reddit",
                                "id": c.id,
                                "author": str(c.author) if c.author else "[deleted]",
                                "author_name": str(c.author) if c.author else "[deleted]",
                                "text": c.body or "",
                                "created_at": c_created,
                                "likes": c.score or 0,
                                "shares": 0,
                                "replies": 0,
                                "url": f"https://reddit.com{c.permalink}",
                            }
                        )
                except Exception:
                    pass

        return posts
    except Exception as e:
        if "401" in str(e) or "unauthorized" in str(e).lower():
            raise RuntimeError("Reddit 401 Unauthorized: Verify REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env.") from e
        raise
