"""
Deeper analysis helpers: hot topics, rough region estimate, influential voices.

IMPORTANT ON REGION: Bluesky and Reddit do not expose reliable user location.
`estimate_region` is a CONTENT-BASED HEURISTIC (Indic scripts + India keywords),
not real geolocation. Treat it as directional only. Real geo needs a paid data
provider or platform enterprise access.
"""

import re
from collections import Counter

# ---- Region estimate ----------------------------------------------------

# Unicode blocks for major Indic scripts (Devanagari, Bengali, Gurmukhi,
# Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam).
_INDIC_RANGES = [
    (0x0900, 0x097F), (0x0980, 0x09FF), (0x0A00, 0x0A7F), (0x0A80, 0x0AFF),
    (0x0B00, 0x0B7F), (0x0B80, 0x0BFF), (0x0C00, 0x0C7F), (0x0C80, 0x0CFF),
    (0x0D00, 0x0D7F),
]

_INDIA_KEYWORDS = {
    "india", "indian", "bharat", "bharath", "desi", "delhi", "mumbai", "bengaluru",
    "bangalore", "kolkata", "chennai", "hyderabad", "pune", "ahmedabad", "jaipur",
    "lucknow", "kerala", "punjab", "gujarat", "maharashtra", "tamil", "telugu",
    "kannada", "bengali", "marathi", "hindi", "modi", "bjp", "congress", "rupee",
    "rupees", "lakh", "crore", "bollywood", "ipl", "rahul", "gandhi", "yogi",
}


def _has_indic_script(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        for lo, hi in _INDIC_RANGES:
            if lo <= cp <= hi:
                return True
    return False


def estimate_region(text: str) -> str:
    """Return 'India (est.)' or 'Other / Unknown'. Heuristic only."""
    return "India (est.)" if estimate_country(text) == "India" else "Other / Unknown"


# Country keyword lexicons for the estimate map. Rough and non-exhaustive.
_COUNTRY_KEYWORDS = {
    "India": _INDIA_KEYWORDS,
    "United States": {
        "usa", "america", "american", "biden", "trump", "washington", "dollar",
        "nyc", "california", "texas", "florida", "gop", "republican", "democrat",
    },
    "United Kingdom": {
        "uk", "britain", "british", "london", "england", "brexit", "tory",
        "labour", "westminster", "scotland", "wales",
    },
    "Pakistan": {"pakistan", "pakistani", "imran", "karachi", "lahore", "islamabad", "pti"},
    "Canada": {"canada", "canadian", "trudeau", "toronto", "ottawa", "ontario"},
    "Australia": {"australia", "australian", "sydney", "melbourne", "canberra", "aussie"},
    "Nigeria": {"nigeria", "nigerian", "lagos", "abuja", "naira"},
}


def estimate_country(text: str) -> str:
    """
    Best-effort country from text content. Returns a plotly-compatible country
    name or 'Unknown'. NOT real geolocation — content clues only.
    """
    if not text:
        return "Unknown"
    if _has_indic_script(text):
        return "India"

    words = set(re.findall(r"[a-z]+", text.lower()))
    best, best_hits = "Unknown", 0
    for country, lex in _COUNTRY_KEYWORDS.items():
        hits = len(words & lex)
        if hits > best_hits:
            best, best_hits = country, hits
    return best


# ISO-3 codes for the choropleth (more robust than country names in plotly).
COUNTRY_ISO3 = {
    "India": "IND", "United States": "USA", "United Kingdom": "GBR",
    "Pakistan": "PAK", "Canada": "CAN", "Australia": "AUS", "Nigeria": "NGA",
}


# ---- India state / city estimate (content-based, NOT geolocation) -------

# Major Indian cities -> state. Used to infer state when a city is mentioned.
_INDIA_CITY_STATE = {
    "mumbai": "Maharashtra", "pune": "Maharashtra", "nagpur": "Maharashtra",
    "nashik": "Maharashtra", "thane": "Maharashtra",
    "delhi": "Delhi", "new delhi": "Delhi",
    "bengaluru": "Karnataka", "bangalore": "Karnataka", "mysuru": "Karnataka", "mysore": "Karnataka",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "hyderabad": "Telangana", "warangal": "Telangana",
    "kolkata": "West Bengal", "howrah": "West Bengal",
    "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat", "rajkot": "Gujarat",
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "udaipur": "Rajasthan", "kota": "Rajasthan",
    "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh", "varanasi": "Uttar Pradesh",
    "noida": "Uttar Pradesh", "ghaziabad": "Uttar Pradesh", "agra": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
    "patna": "Bihar", "gaya": "Bihar",
    "bhopal": "Madhya Pradesh", "indore": "Madhya Pradesh", "gwalior": "Madhya Pradesh",
    "kochi": "Kerala", "thiruvananthapuram": "Kerala", "kozhikode": "Kerala",
    "guwahati": "Assam", "bhubaneswar": "Odisha", "cuttack": "Odisha",
    "ranchi": "Jharkhand", "jamshedpur": "Jharkhand", "raipur": "Chhattisgarh",
    "amritsar": "Punjab", "ludhiana": "Punjab", "chandigarh": "Chandigarh",
    "gurugram": "Haryana", "gurgaon": "Haryana", "faridabad": "Haryana",
    "dehradun": "Uttarakhand", "shimla": "Himachal Pradesh", "panaji": "Goa",
    "srinagar": "Jammu and Kashmir", "jammu": "Jammu and Kashmir",
}

# States + common aliases -> canonical state name.
_INDIA_STATES = {
    "andhra pradesh": "Andhra Pradesh", "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam", "bihar": "Bihar", "chhattisgarh": "Chhattisgarh", "goa": "Goa",
    "gujarat": "Gujarat", "haryana": "Haryana", "himachal pradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand", "karnataka": "Karnataka", "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh", "maharashtra": "Maharashtra", "manipur": "Manipur",
    "meghalaya": "Meghalaya", "mizoram": "Mizoram", "nagaland": "Nagaland",
    "odisha": "Odisha", "punjab": "Punjab", "rajasthan": "Rajasthan", "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu", "telangana": "Telangana", "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand", "west bengal": "West Bengal",
    "delhi": "Delhi", "jammu and kashmir": "Jammu and Kashmir", "ladakh": "Ladakh",
    "puducherry": "Puducherry", "chandigarh": "Chandigarh",
}


def detect_india_location(text: str) -> dict:
    """
    Estimate an Indian state and/or city from text mentions. Content-based only —
    NOT geolocation. Returns {'state': str|None, 'city': str|None}.
    """
    if not text:
        return {"state": None, "city": None}
    low = " " + text.lower() + " "

    # Cities first (they also pin the state). Longer names checked first.
    for city in sorted(_INDIA_CITY_STATE, key=len, reverse=True):
        if re.search(r"\b" + re.escape(city) + r"\b", low):
            return {"state": _INDIA_CITY_STATE[city], "city": city.title()}

    # Then explicit state names.
    for name in sorted(_INDIA_STATES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(name) + r"\b", low):
            return {"state": _INDIA_STATES[name], "city": None}

    return {"state": None, "city": None}


# ---- India state centroids (for the interactive map) --------------------
# Approx lat/lon centre of each state/UT. Used to plot a bubble/scatter map offline
# (no GeoJSON download needed). Coordinates are indicative centroids.
INDIA_STATE_CENTROIDS = {
    "Andhra Pradesh": (15.9129, 79.7400), "Arunachal Pradesh": (28.2180, 94.7278),
    "Assam": (26.2006, 92.9376), "Bihar": (25.0961, 85.3131),
    "Chhattisgarh": (21.2787, 81.8661), "Goa": (15.2993, 74.1240),
    "Gujarat": (22.2587, 71.1924), "Haryana": (29.0588, 76.0856),
    "Himachal Pradesh": (31.1048, 77.1734), "Jharkhand": (23.6102, 85.2799),
    "Karnataka": (15.3173, 75.7139), "Kerala": (10.8505, 76.2711),
    "Madhya Pradesh": (22.9734, 78.6569), "Maharashtra": (19.7515, 75.7139),
    "Manipur": (24.6637, 93.9063), "Meghalaya": (25.4670, 91.3662),
    "Mizoram": (23.1645, 92.9376), "Nagaland": (26.1584, 94.5624),
    "Odisha": (20.9517, 85.0985), "Punjab": (31.1471, 75.3412),
    "Rajasthan": (27.0238, 74.2179), "Sikkim": (27.5330, 88.5122),
    "Tamil Nadu": (11.1271, 78.6569), "Telangana": (18.1124, 79.0193),
    "Tripura": (23.9408, 91.9882), "Uttar Pradesh": (26.8467, 80.9462),
    "Uttarakhand": (30.0668, 79.0193), "West Bengal": (22.9868, 87.8550),
    "Delhi": (28.7041, 77.1025), "Jammu and Kashmir": (33.7782, 76.5762),
    "Ladakh": (34.1526, 77.5770), "Puducherry": (11.9416, 79.8083),
    "Chandigarh": (30.7333, 76.7794),
}


def state_centroid(state):
    """Return (lat, lon) for an Indian state, or None."""
    return INDIA_STATE_CENTROIDS.get(state)


def aggregate_india_state_sentiments(df):
    """
    Aggregate sentiment stats per Indian state for interactive map visualization.
    Returns DataFrame with lat, lon, state, mentions, avg_score, positive_pct, negative_pct, neutral_pct, top_emotion, mood_label.
    """
    import pandas as pd
    if df.empty or "india_state" not in df.columns:
        return pd.DataFrame()

    india = df[df["india_state"].notna()].copy()
    if india.empty:
        return pd.DataFrame()

    records = []
    for state, group in india.groupby("india_state"):
        centroid = state_centroid(state)
        if not centroid:
            continue
        lat, lon = centroid
        total = len(group)
        pos = (group["sentiment"] == "positive").sum()
        neg = (group["sentiment"] == "negative").sum()
        neu = (group["sentiment"] == "neutral").sum()
        avg_score = round(group["score"].mean(), 3)
        pos_pct = round(100 * pos / total, 1)
        neg_pct = round(100 * neg / total, 1)
        neu_pct = round(100 * neu / total, 1)

        emo_counts = group["emotion"].value_counts()
        non_neu = emo_counts.drop("neutral", errors="ignore")
        top_emo = non_neu.idxmax() if not non_neu.empty else (emo_counts.idxmax() if not emo_counts.empty else "neutral")

        mood = "Positive" if avg_score >= 0.05 else ("Negative" if avg_score <= -0.05 else "Neutral")

        # Top city mentioned if any
        top_city = group["india_city"].dropna().value_counts().idxmax() if not group["india_city"].dropna().empty else "N/A"

        records.append({
            "state": state,
            "lat": lat,
            "lon": lon,
            "mentions": total,
            "avg_score": avg_score,
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "neutral_pct": neu_pct,
            "top_emotion": top_emo.title(),
            "mood_label": mood,
            "top_city": top_city,
        })

    return pd.DataFrame(records).sort_values("mentions", ascending=False)


# ---- Hot topics ---------------------------------------------------------

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "her",
    "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "man",
    "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its", "let",
    "put", "say", "says", "said", "she", "too", "use", "that", "this", "with", "have", "from",
    "they", "will", "your", "what", "when", "just", "like", "them", "then",
    "than", "were", "been", "more", "some", "such", "only", "over", "also",
    "into", "about", "would", "there", "their", "which", "these", "those",
    "http", "https", "com", "www", "amp", "via", "rt", "im", "dont", "doesnt",
    "isnt", "after", "before", "short", "cut", "read", "watch", "video", "news",
    "post", "posts", "time", "latest", "first", "full", "know", "make", "well",
    "back", "even", "much", "many", "take", "good", "come", "told", "year",
    "month", "today", "yesterday", "tomorrow", "people", "show", "shows", "look",
    "looks", "seen", "call", "called", "give", "given", "take", "taken", "here",
    "where", "why", "going", "goes", "gone", "knows", "find", "made", "want",
}


def extract_hot_topics(texts, extra_stop=None, top_n: int = 15):
    """
    Return (top_words, top_hashtags) as lists of (term, count).
    `extra_stop` should include the search term so it doesn't dominate.
    """
    stop = set(_STOPWORDS)
    if extra_stop:
        stop |= {w.lower() for w in extra_stop}

    words, tags = Counter(), Counter()
    for t in texts:
        low = (t or "").lower()
        for tag in re.findall(r"#(\w+)", low):
            tags[tag] += 1
        for w in re.findall(r"[a-z']{3,}", low):
            if w in stop:
                continue
            words[w] += 1
    return words.most_common(top_n), tags.most_common(top_n)


# ---- Influential voices -------------------------------------------------

def top_authors(df, n: int = 10):
    """Rank authors by total engagement across their posts."""
    if df.empty:
        return df
    grouped = (
        df.groupby(["platform", "author"])
        .agg(posts=("id", "count"),
             total_engagement=("engagement", "sum"),
             avg_sentiment=("score", "mean"))
        .reset_index()
        .sort_values("total_engagement", ascending=False)
        .head(n)
    )
    grouped["avg_sentiment"] = grouped["avg_sentiment"].round(3)
    return grouped

