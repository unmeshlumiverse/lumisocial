"""Offline smoke test for the full engine (no live network needed)."""

from pipeline import collect, summarize, build_query
from analysis import extract_hot_topics, top_authors, estimate_region, aggregate_india_state_sentiments
from demographics import summarize_demographics


def mock_bluesky(query, limit):
    return [
        {"platform": "bluesky", "id": "b1", "author": "alice", "author_name": "Alice",
         "text": "TestPerson gave an amazing speech in Delhi today, so inspiring! #leadership",
         "created_at": "2026-01-01T10:00:00Z", "likes": 120, "shares": 30, "replies": 12, "url": "http://x/1"},
        {"platform": "bluesky", "id": "b2", "author": "bob", "author_name": "Bob",
         "text": "Honestly TestPerson is a total disaster. Worst policy ever fr ngl. #fail",
         "created_at": "2026-01-01T11:00:00Z", "likes": 5, "shares": 1, "replies": 40, "url": "http://x/2"},
    ]


def mock_indian_news(query, limit):
    return [
        {"platform": "indian_news", "id": "n1", "author": "The Indian Express", "author_name": "The Indian Express",
         "text": "TestPerson announces major infrastructure reform in Mumbai Maharashtra",
         "created_at": "2026-01-01T08:00:00Z", "likes": 0, "shares": 0, "replies": 0, "url": "http://x/3",
         "state_hint": "Maharashtra", "lang": "en"},
        {"platform": "indian_news", "id": "n2", "author": "Eenadu", "author_name": "Eenadu",
         "text": "ఆంధ్రప్రదేశ్ అభివృద్ది పై మాట్లాడిన నాయకుడు",
         "created_at": "2026-01-01T07:00:00Z", "likes": 0, "shares": 0, "replies": 0, "url": "http://x/4",
         "state_hint": "Andhra Pradesh", "lang": "te"},
    ]


def mock_telegram(query, limit):
    return [
        {"platform": "telegram", "id": "tg1", "author": "ndtv", "author_name": "NDTV",
         "text": "Breaking: TestPerson inaugurates new tech hub in Bengaluru Karnataka.",
         "created_at": "2026-01-01T09:30:00Z", "likes": 45, "shares": 10, "replies": 5, "url": "http://x/5"},
    ]


def main():
    assert build_query("modi", "hashtag", "bluesky") == "#modi"
    assert build_query("@modi", "handle", "indian_news") == "modi"

    df, errors = collect("TestPerson", "keyword",
                         {"bluesky": mock_bluesky, "indian_news": mock_indian_news, "telegram": mock_telegram}, limit=10)
    print("Errors:", errors)
    print("\nScored + region + state + age group + category:")
    print(df[["platform", "source_group", "author", "sentiment", "score", "india_state", "age_group", "engagement"]].to_string(index=False))

    print("\nSummary:", summarize(df))

    india_df = aggregate_india_state_sentiments(df)
    print("\nIndia State Sentiments Map Data:")
    print(india_df.to_string(index=False))

    demo_df = summarize_demographics(df)
    print("\nDemographics Summary:")
    print(demo_df.to_string(index=False))

    assert "India (est.)" in set(df["region"]) or "India" in set(df["country"]), "State tagged post should be India"
    assert not india_df.empty, "India state map aggregation should not be empty"
    assert not demo_df.empty, "Demographics aggregation should not be empty"
    print("\n[OK] Full upgraded engine works.")


if __name__ == "__main__":
    main()
