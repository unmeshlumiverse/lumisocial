"""
Indian Newspaper RSS Feed Aggregator.

Fetches RSS feeds of major Indian national and regional newspapers in parallel
(English, Hindi, Marathi, Bengali, Tamil, Telugu, Malayalam, Gujarati, Kannada, Punjabi).

Filters articles with strict multi-word relevance matching so that searching for a person
(e.g. "Ramvijay Thakare") requires all name tokens to match, preventing false positives.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
import requests

INDIAN_NEWSPAPER_FEEDS = {
    "The Times of India": {"url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "state": "National", "lang": "en"},
    "Hindustan Times": {"url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "state": "National", "lang": "en"},
    "The Indian Express": {"url": "https://indianexpress.com/feed/", "state": "National", "lang": "en"},
    "The Hindu": {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "state": "Tamil Nadu", "lang": "en"},
    "Deccan Herald": {"url": "https://www.deccanherald.com/rss/national.rss", "state": "Karnataka", "lang": "en"},
    "The Telegraph": {"url": "https://www.telegraphindia.com/feeds/rss/india", "state": "West Bengal", "lang": "en"},
    "Livemint": {"url": "https://www.livemint.com/rss/news", "state": "National", "lang": "en"},
    "The Economic Times": {"url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms", "state": "National", "lang": "en"},
    "Financial Express": {"url": "https://www.financialexpress.com/feed/", "state": "National", "lang": "en"},
    "The Tribune": {"url": "https://www.tribuneindia.com/rss/feed", "state": "Punjab", "lang": "en"},
    "India Today": {"url": "https://www.indiatoday.in/rss/home", "state": "National", "lang": "en"},
    "NDTV News": {"url": "https://feeds.feedburner.com/ndtvnews-india-news", "state": "National", "lang": "en"},
    "Zee News": {"url": "https://zeenews.india.com/rss/india-national-news.xml", "state": "National", "lang": "en"},
    "News18 India": {"url": "https://www.news18.com/rss/india.xml", "state": "National", "lang": "en"},
    "Business Standard": {"url": "https://www.business-standard.com/rss/home_page.rss", "state": "National", "lang": "en"},
    "ABP News": {"url": "https://news.abplive.com/home/feed", "state": "National", "lang": "en"},
    "Amar Ujala": {"url": "https://www.amarujala.com/rss/india-news.xml", "state": "Uttar Pradesh", "lang": "hi"},
    "Dainik Jagran": {"url": "https://rss.jagran.com/rss/news/national.xml", "state": "Uttar Pradesh", "lang": "hi"},
    "Navbharat Times": {"url": "https://navbharattimes.indiatimes.com/rssfeedstopstories.cms", "state": "Delhi", "lang": "hi"},
    "Punjab Kesari": {"url": "https://www.punjabkesari.in/rss/india.xml", "state": "Punjab", "lang": "hi"},
    "Rajasthan Patrika": {"url": "https://www.patrika.com/rss/india-news.xml", "state": "Rajasthan", "lang": "hi"},
    "Lokmat": {"url": "https://www.lokmat.com/rss/national.xml", "state": "Maharashtra", "lang": "mr"},
    "Maharashtra Times": {"url": "https://maharashtratimes.com/rssfeedstopstories.cms", "state": "Maharashtra", "lang": "mr"},
    "Mathrubhumi": {"url": "https://www.mathrubhumi.com/rss/news.xml", "state": "Kerala", "lang": "ml"},
    "Malayala Manorama": {"url": "https://www.manoramaonline.com/news/india.rss.xml", "state": "Kerala", "lang": "ml"},
    "Eenadu": {"url": "https://www.eenadu.net/rss/eenadunews.xml", "state": "Andhra Pradesh", "lang": "te"},
    "Sakshi": {"url": "https://www.sakshi.com/rss.xml", "state": "Andhra Pradesh", "lang": "te"},
    "Dinakaran": {"url": "https://www.dinakaran.com/feed/", "state": "Tamil Nadu", "lang": "ta"},
    "Daily Thanthi": {"url": "https://www.dailythanthi.com/rss", "state": "Tamil Nadu", "lang": "ta"},
    "Anandabazar Patrika": {"url": "https://www.anandabazar.com/rss/india-news.xml", "state": "West Bengal", "lang": "bn"},
    "Assam Tribune": {"url": "https://assamtribune.com/feed", "state": "Assam", "lang": "en"},
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PublicFigureMonitor/1.0"


def _fetch_feed(source_name, meta, query_clean, query_words, max_per_feed=15):
    posts = []
    try:
        resp = requests.get(meta["url"], headers={"User-Agent": USER_AGENT}, timeout=6)
        if resp.status_code != 200:
            return []
        feed = feedparser.parse(resp.content)
        count = 0
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary") or entry.get("description") or ""
            full_text = f"{title} {summary}".strip()
            text_low = full_text.lower()

            # Strict relevance matching: for multi-word queries (e.g. "Ramvijay Thakare"),
            # require the exact phrase or ALL query words so we never match different people
            if len(query_words) >= 2:
                if not (query_clean in text_low or all(qw in text_low for qw in query_words)):
                    continue
            elif query_words:
                if not any(qw in text_low for qw in query_words):
                    continue

            pub_date = entry.get("published") or entry.get("updated") or None
            link = entry.get("link") or ""

            posts.append({
                "platform": "indian_news",
                "id": entry.get("id") or link or f"{source_name}:{title[:20]}",
                "author": source_name,
                "author_name": source_name,
                "text": title,
                "summary": summary,
                "created_at": pub_date,
                "likes": 0,
                "shares": 0,
                "replies": 0,
                "url": link,
                "state_hint": meta["state"],
                "lang": meta["lang"],
            })
            count += 1
            if count >= max_per_feed:
                break
    except Exception:
        pass
    return posts


def search_indian_newspapers(query: str, limit: int = 50):
    """
    Search major Indian newspaper RSS feeds concurrently for `query`.
    Returns normalized posts list with strict name relevance.
    """
    query_clean = query.strip().lstrip("#@").lower()
    query_words = [w for w in query_clean.split() if len(w) > 1] if query_clean else []

    all_posts = []
    max_workers = min(15, len(INDIAN_NEWSPAPER_FEEDS))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_feed, name, meta, query_clean, query_words): name
            for name, meta in INDIAN_NEWSPAPER_FEEDS.items()
        }
        for future in as_completed(futures):
            res = future.result()
            if res:
                all_posts.extend(res)

    all_posts.sort(key=lambda p: p.get("created_at") or "", reverse=True)
    return all_posts[:limit]
