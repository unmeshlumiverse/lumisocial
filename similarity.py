"""
Topic Similarity / Co-occurrence Matrix.

Reveals the "narrative web": which themes travel together in the same posts.
When two topics keep showing up in the same messages, they are being welded into
a single story about the person — that linkage IS the image being constructed.

Method (free, offline, deterministic):
  1. Take the top-K hot-topic terms (search term excluded upstream).
  2. For every post, mark which of those terms it mentions.
  3. Build the K x K co-occurrence count matrix.
  4. Normalise to a cosine-style similarity:
         sim(i, j) = cooccur(i, j) / sqrt(count_i * count_j)
     (0 = never together, 1 = always together).
  5. Attach each topic's volume and average sentiment so the heatmap can show
     not just what is linked, but whether the linked cluster is hostile.

Returns plain Python / lists so the caller can hand it straight to a Plotly
heatmap without extra dependencies.
"""

import math
import re

import pandas as pd

from analysis import extract_hot_topics


def _mentions(text, term):
    return re.search(r"\b" + re.escape(term) + r"\b", text) is not None


def build_topic_matrix(df, search_term="", top_k=10, min_topic_count=2):
    """
    Return a dict:
      {
        "labels": [term, ...],
        "matrix": [[sim, ...], ...],      # K x K, diagonal = 1.0
        "counts": {term: n_posts},
        "sentiment": {term: avg_score},   # -1..1
        "neg_pct": {term: pct_negative},
        "links": [(term_a, term_b, sim), ...],  # strongest off-diagonal pairs
      }
    Empty-safe: returns empty structures if there isn't enough data.
    """
    empty = {"labels": [], "matrix": [], "counts": {}, "sentiment": {},
             "neg_pct": {}, "links": []}
    if df is None or df.empty or len(df) < 4:
        return empty

    stop = [w for w in search_term.replace("#", "").replace("@", "").split()]
    words, _tags = extract_hot_topics(df["text"].tolist(), extra_stop=stop, top_n=top_k * 2)
    topics = [w for w, c in words if c >= min_topic_count][:top_k]
    if len(topics) < 2:
        return empty

    texts = [str(t).lower() for t in df["text"].tolist()]
    scores = df["score"].tolist() if "score" in df.columns else [0.0] * len(df)
    sents = df["sentiment"].tolist() if "sentiment" in df.columns else ["neutral"] * len(df)

    # Which posts mention which topic.
    present = {t: [] for t in topics}          # topic -> list of post indices
    for i, txt in enumerate(texts):
        for t in topics:
            if _mentions(txt, t):
                present[t].append(i)

    counts = {t: len(present[t]) for t in topics}
    # Drop topics that ended up with nothing after word-boundary matching.
    topics = [t for t in topics if counts[t] > 0]
    if len(topics) < 2:
        return empty

    # Co-occurrence + similarity.
    index_sets = {t: set(present[t]) for t in topics}
    n = len(topics)
    matrix = [[0.0] * n for _ in range(n)]
    for a in range(n):
        for b in range(n):
            ta, tb = topics[a], topics[b]
            if a == b:
                matrix[a][b] = 1.0
                continue
            co = len(index_sets[ta] & index_sets[tb])
            denom = math.sqrt(counts[ta] * counts[tb]) or 1.0
            matrix[a][b] = round(co / denom, 3)

    # Per-topic sentiment.
    sentiment = {}
    neg_pct = {}
    for t in topics:
        idxs = present[t]
        if idxs:
            sentiment[t] = round(sum(scores[i] for i in idxs) / len(idxs), 3)
            negs = sum(1 for i in idxs if sents[i] == "negative")
            neg_pct[t] = round(100 * negs / len(idxs), 1)
        else:
            sentiment[t] = 0.0
            neg_pct[t] = 0.0

    # Strongest linked pairs (the tightest narrative bundles).
    links = []
    for a in range(n):
        for b in range(a + 1, n):
            links.append((topics[a], topics[b], matrix[a][b]))
    links.sort(key=lambda x: x[2], reverse=True)

    return {
        "labels": topics,
        "matrix": matrix,
        "counts": {t: counts[t] for t in topics},
        "sentiment": sentiment,
        "neg_pct": neg_pct,
        "links": links[:8],
    }
