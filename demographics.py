"""
Demographics & Age Group Estimator Module.

Heuristic, content-based age group estimation.
Categories:
  - "18-24 (Gen Z)"
  - "25-34 (Millennials)"
  - "35-50 (Gen X)"
  - "50+ (Seniors)"

NOTE: Real social media APIs do NOT expose user age due to privacy policies.
This module uses linguistic markers, topic indicators, slang patterns, and platform
demographic baselines to provide directional demographic insights.
"""

import re
import pandas as pd

AGE_GROUPS = [
    "18-24 (Gen Z)",
    "25-34 (Millennials)",
    "35-50 (Gen X)",
    "50+ (Seniors)",
]

# Lexical markers for age groups
_GEN_Z_KEYWORDS = {
    "fr", "ngl", "tbh", "skibidi", "rizz", "slay", "vibe", "bro", "lol", "lmao",
    "crypto", "meme", "anime", "gaming", "gta", "edit", "stan", "flex", "sus",
    "goat", "periodt", "bet", "bhai", "dude", "cringe", "epic", "hype", "drop",
}

_MILLENNIAL_KEYWORDS = {
    "career", "job", "mortgage", "salary", "tax", "tech", "ai", "startup", "invest",
    "stocks", "market", "rent", "degree", "resume", "hustle", "workplace", "coffee",
    "travel", "work", "office", "company", "project", "hiring", "code", "dev",
}

_GEN_X_KEYWORDS = {
    "policy", "reform", "government", "election", "minister", "parliament", "scheme",
    "gdp", "inflation", "taxation", "economy", "children", "family", "school",
    "governance", "infrastructure", "corporate", "administration", "budget",
    "development", "industry", "sector", "official",
}

_SENIOR_KEYWORDS = {
    "pension", "retirement", "retiree", "heritage", "tradition", "history",
    "newspaper", "grandchildren", "senior", "healthcare", "ayurveda", "devotional",
    "blessings", "veteran", "generations", "values", "culture", "temple",
}

# Platform default age biases
_PLATFORM_BASELINES = {
    "reddit": "25-34 (Millennials)",
    "bluesky": "25-34 (Millennials)",
    "youtube": "18-24 (Gen Z)",
    "telegram": "25-34 (Millennials)",
    "twitter": "25-34 (Millennials)",
    "indian_news": "35-50 (Gen X)",
    "news": "35-50 (Gen X)",
    "mastodon": "35-50 (Gen X)",
    "hackernews": "25-34 (Millennials)",
}


def estimate_age_group(text: str, platform: str = "") -> str:
    """
    Estimate age group from text content and platform baseline.
    Returns one of AGE_GROUPS.
    """
    if not text:
        return _PLATFORM_BASELINES.get(platform, "25-34 (Millennials)")

    words = set(re.findall(r"[a-z']+", text.lower()))

    scores = {
        "18-24 (Gen Z)": len(words & _GEN_Z_KEYWORDS) * 2.0,
        "25-34 (Millennials)": len(words & _MILLENNIAL_KEYWORDS) * 1.5,
        "35-50 (Gen X)": len(words & _GEN_X_KEYWORDS) * 1.5,
        "50+ (Seniors)": len(words & _SENIOR_KEYWORDS) * 2.0,
    }

    # Add platform weight
    base = _PLATFORM_BASELINES.get(platform, "25-34 (Millennials)")
    scores[base] += 1.0

    best_group = max(scores.items(), key=lambda x: x[1])[0]
    return best_group


def summarize_demographics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate demographic summary table (age group, post count, sentiment score, positivity ratio).
    """
    if df.empty or "age_group" not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby("age_group").agg(
        mentions=("id", "count"),
        avg_sentiment=("score", "mean"),
        positives=("sentiment", lambda s: (s == "positive").sum()),
        negatives=("sentiment", lambda s: (s == "negative").sum()),
        neutrals=("sentiment", lambda s: (s == "neutral").sum()),
    ).reset_index()

    grouped["positivity_ratio"] = grouped.apply(
        lambda r: round(100 * r["positives"] / max(1, r["positives"] + r["negatives"]), 1),
        axis=1
    )
    grouped["avg_sentiment"] = grouped["avg_sentiment"].round(3)
    grouped = grouped.sort_values("mentions", ascending=False)
    return grouped
