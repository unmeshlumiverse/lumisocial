"""
GDELT connector — real multi-year historical news (the "All Time" data source).

Google News / newspaper RSS feeds only ever show what's currently published —
there is no way to ask them for 2019 coverage of a name. GDELT's free DOC 2.0
API indexes global news full-text back to 2017 (English) / 2020 (translated
non-English), so it's what actually makes "All Available Data" mean something
for a person who was in the news years ago.

No API key required. Public rate limit is ~1 request / 5 seconds, so for
"All Available Data" we chunk the 2017->now range into a handful of windows
and pace the requests instead of firing them all at once.
"""

import datetime as dt
import time

import requests

DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LumisocialMonitor/1.0"

# GDELT's DOC API full-text coverage effectively starts here.
COVERAGE_START = dt.date(2017, 1, 1)
_RATE_LIMIT_SECONDS = 5.1


def _chunks_for_all_time():
    """Yield ~2-year (start, end) date windows from 2017 to today."""
    today = dt.date.today()
    year = COVERAGE_START.year
    while year <= today.year:
        start = dt.date(year, 1, 1)
        end_year = min(year + 1, today.year)
        end = dt.date(end_year, 12, 31) if end_year < today.year else today
        yield start, end
        year += 2


def _fmt(d):
    return f"{d.strftime('%Y%m%d')}000000" if isinstance(d, dt.date) else d


def _query_window(query, start, end, maxrecords=250):
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": maxrecords,
        "format": "json",
        "sort": "hybridrel",
    }
    if start is not None:
        params["startdatetime"] = _fmt(start)
        params["enddatetime"] = _fmt(end)
    resp = requests.get(DOC_URL, params=params, timeout=20,
                         headers={"User-Agent": USER_AGENT})
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    return data.get("articles", [])


def _to_post(article):
    seen = article.get("seendate", "")  # e.g. 20230115T120000Z
    created_at = None
    if seen:
        try:
            created_at = dt.datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=dt.timezone.utc
            ).isoformat()
        except ValueError:
            created_at = None
    title = article.get("title", "")
    domain = article.get("domain", "GDELT")
    return {
        "platform": "gdelt",
        "id": article.get("url"),
        "author": domain,
        "author_name": domain,
        "text": title,
        "summary": "",
        "created_at": created_at,
        "likes": 0,
        "shares": 0,
        "replies": 0,
        "url": article.get("url"),
        "lang": article.get("language", "en"),
    }


def search_gdelt(query: str, limit: int = 100, time_range: str = "All Available Data"):
    """
    Search GDELT's global news index. For "All Available Data" this sweeps
    2017->present in windows to get real historical depth; for a narrower
    time_range it makes a single windowed call (fast).
    """
    q = query.strip()
    words = [w for w in q.lstrip("#@").split() if len(w) > 1]
    q_str = f'"{q}"' if len(words) >= 2 and not q.startswith('"') else q

    if time_range == "Past 24 Hours":
        windows = [(dt.date.today() - dt.timedelta(days=1), dt.date.today())]
    elif time_range == "Past 1 Week":
        windows = [(dt.date.today() - dt.timedelta(days=7), dt.date.today())]
    elif time_range == "Past 1 Month":
        windows = [(dt.date.today() - dt.timedelta(days=30), dt.date.today())]
    else:
        windows = list(_chunks_for_all_time())

    all_posts = {}
    for i, (start, end) in enumerate(windows):
        try:
            articles = _query_window(q_str, start, end)
            for a in articles:
                url = a.get("url")
                if url and url not in all_posts:
                    all_posts[url] = _to_post(a)
        except Exception:
            pass
        if i < len(windows) - 1:
            time.sleep(_RATE_LIMIT_SECONDS)

    posts = list(all_posts.values())
    posts.sort(key=lambda p: p.get("created_at") or "", reverse=True)
    return posts[:limit]
