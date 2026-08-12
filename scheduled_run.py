"""
Headless scheduled run — searches a term and saves a snapshot to the history DB.
Schedule it with cron (Linux/Mac) or Task Scheduler (Windows) to build trends.

Examples:
  python scheduled_run.py "Some Politician" --sources bluesky,reddit,news
  python scheduled_run.py "#SomeTopic" --type hashtag --sources bluesky --limit 80
  python scheduled_run.py "Name" --sources bluesky,telegram --tg-channels ndtv,indiatoday

Cron example (every day at 9am):
  0 9 * * *  cd /path/to/social_monitor && /usr/bin/python scheduled_run.py "Name" --sources bluesky,reddit,news
"""

import argparse
from dotenv import load_dotenv

load_dotenv()

from pipeline import collect, summarize
from narratives import detect_narratives
import storage
from connectors.bluesky import search_bluesky
from connectors.reddit import search_reddit
from connectors.youtube import search_youtube
from connectors.news import search_news
from connectors.telegram import search_telegram


def build_sources(names, tg_channels, news_country):
    src = {}
    for n in names:
        n = n.strip().lower()
        if n == "bluesky":
            src["bluesky"] = search_bluesky
        elif n == "reddit":
            src["reddit"] = lambda q, k: search_reddit(q, k)
        elif n == "youtube":
            src["youtube"] = lambda q, k: search_youtube(q, k)
        elif n == "news":
            src["news"] = lambda q, k: search_news(q, k, country=news_country)
        elif n == "telegram":
            src["telegram"] = lambda q, k: search_telegram(q, k, channels=tg_channels)
    return src


def main():
    ap = argparse.ArgumentParser(description="Headless monitoring run -> history DB")
    ap.add_argument("term")
    ap.add_argument("--type", default="keyword", choices=["keyword", "hashtag", "handle"])
    ap.add_argument("--sources", default="bluesky,reddit,news")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--tg-channels", default="")
    ap.add_argument("--news-country", default="IN")
    args = ap.parse_args()

    tg = [c.strip() for c in args.tg_channels.split(",") if c.strip()]
    sources = build_sources(args.sources.split(","), tg, args.news_country)

    df, errors = collect(args.term, args.type, sources, limit=args.limit)
    for name, err in errors.items():
        print(f"[warn] {name}: {err}")

    if df.empty:
        print("No posts found; nothing saved.")
        return

    stats = summarize(df)
    emo_counts = df["emotion"].value_counts().to_dict()
    non_neutral = {k: v for k, v in emo_counts.items() if k != "neutral"}
    dominant_emotion = (max(non_neutral, key=non_neutral.get) if non_neutral
                        else (max(emo_counts, key=emo_counts.get) if emo_counts else "neutral"))
    themes = detect_narratives(df, search_term=args.term)

    ok = storage.save_run(args.term, stats, sorted(df["platform"].unique()),
                          dominant_emotion, emo_counts, themes)
    print(f"Saved snapshot: {stats['total']} posts, mood avg {stats['avg_score']}, "
          f"top emotion {dominant_emotion}. DB write {'ok' if ok else 'FAILED'}.")


if __name__ == "__main__":
    main()
