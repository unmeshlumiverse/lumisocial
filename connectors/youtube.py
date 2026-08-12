"""
YouTube connector (Data API v3).

Finds videos about your search term, then pulls their comments — a huge, free
source of raw public opinion about public figures.

Setup:
  1. Go to https://console.cloud.google.com/ , create a project.
  2. Enable "YouTube Data API v3".
  3. Create an API key (Credentials -> Create credentials -> API key).
  4. Set it:  export YOUTUBE_API_KEY="your_key"

Free quota is 10,000 units/day: each video search costs 100 units, each
comment page costs 1 unit, so this is comfortably free for monitoring.
"""

import os

import requests

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


def _key():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError(
            "YouTube API key missing. Set YOUTUBE_API_KEY (create one free at "
            "console.cloud.google.com with 'YouTube Data API v3' enabled)."
        )
    return key


def _find_videos(query, key, max_videos=5):
    params = {
        "part": "snippet", "q": query, "type": "video",
        "order": "relevance", "maxResults": max_videos, "key": key,
    }
    resp = requests.get(SEARCH_URL, params=params, timeout=20)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [(it["id"]["videoId"], it["snippet"]["title"]) for it in items
            if it.get("id", {}).get("videoId")]


def _fetch_comments(video_id, video_title, key, max_comments=40):
    params = {
        "part": "snippet", "videoId": video_id, "order": "relevance",
        "maxResults": min(max_comments, 100), "textFormat": "plainText", "key": key,
    }
    resp = requests.get(COMMENTS_URL, params=params, timeout=20)
    if resp.status_code == 403:
        # Comments disabled on this video — skip quietly.
        return []
    resp.raise_for_status()

    posts = []
    for item in resp.json().get("items", []):
        top = item["snippet"]["topLevelComment"]
        snip = top["snippet"]
        posts.append(
            {
                "platform": "youtube",
                "id": top["id"],
                "author": snip.get("authorDisplayName", "unknown"),
                "author_name": snip.get("authorDisplayName", "unknown"),
                "text": snip.get("textDisplay", ""),
                "created_at": snip.get("publishedAt"),
                "likes": snip.get("likeCount", 0) or 0,
                "shares": 0,
                "replies": item["snippet"].get("totalReplyCount", 0) or 0,
                "url": f"https://www.youtube.com/watch?v={video_id}&lc={top['id']}",
            }
        )
    return posts


def search_youtube(query, limit=50, max_videos=5):
    """Find videos matching `query`, then collect their comments as posts."""
    key = _key()
    videos = _find_videos(query, key, max_videos=max_videos)
    if not videos:
        return []

    per_video = max(5, limit // len(videos))
    posts = []
    for vid, title in videos:
        try:
            posts.extend(_fetch_comments(vid, title, key, max_comments=per_video))
        except Exception:
            continue
    return posts
