"""
Narrative / theme detection.

Groups posts into the main storylines people are pushing, each with its own
size, average sentiment, dominant emotion, and a representative post.

Three tiers, chosen automatically:
  1. AI embeddings (sentence-transformers, multilingual) + KMeans  — best, semantic.
  2. TF-IDF + KMeans (scikit-learn only, no torch)                  — good default.
  3. Keyword grouping (pure Python)                                 — last-resort.
"""

import pandas as pd

from analysis import extract_hot_topics

# Multilingual embedder (covers Hindi + English). Part of the optional AI stack.
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_st_model = None
_st_failed = False


def _get_st_model():
    global _st_model, _st_failed
    if _st_model is not None or _st_failed:
        return _st_model
    try:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(EMBED_MODEL)
    except Exception:
        _st_failed = True
        _st_model = None
    return _st_model


def _vectorize(texts, use_ai):
    """Return a dense matrix of vectors, or None if no vectorizer is available."""
    if use_ai:
        model = _get_st_model()
        if model is not None:
            try:
                return model.encode(texts, show_progress_bar=False)
            except Exception:
                pass
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(max_features=500, stop_words="english", ngram_range=(1, 2))
        return vec.fit_transform(texts).toarray()
    except Exception:
        return None


def _cluster(vectors, k):
    try:
        from sklearn.cluster import KMeans
        return KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(vectors)
    except Exception:
        return None


def _theme_from_group(grp, label):
    rep = grp.sort_values("engagement", ascending=False).iloc[0]
    emo = grp["emotion"].value_counts()
    non_neutral = emo.drop(labels=["neutral"], errors="ignore")
    dom_emo = (non_neutral.idxmax() if not non_neutral.empty
               else (emo.idxmax() if not emo.empty else "neutral"))
    return {
        "label": label or "misc",
        "size": len(grp),
        "avg_sentiment": round(float(grp["score"].mean()), 3),
        "emotion": dom_emo,
        "example": str(rep["text"])[:260],
        "example_author": str(rep["author"]),
        "example_url": rep["url"],
        "platforms": ", ".join(sorted(grp["platform"].unique())),
    }


def _fallback_keyword_groups(df, max_themes):
    words, _ = extract_hot_topics(df["text"].tolist(), top_n=max_themes)
    top_words = [w for w, _ in words]
    buckets = {}
    for _, r in df.iterrows():
        low = str(r["text"]).lower()
        key = next((w for w in top_words if w in low), "other")
        buckets.setdefault(key, []).append(r)
    themes = [_theme_from_group(pd.DataFrame(rows), key) for key, rows in buckets.items()]
    themes.sort(key=lambda t: t["size"], reverse=True)
    return themes[:max_themes]


def detect_narratives(df, max_themes=6, use_ai=False, search_term=""):
    """Return a list of theme dicts, largest first."""
    if df is None or len(df) < 4:
        return []

    texts = [str(t) for t in df["text"].tolist()]
    n = len(texts)
    k = min(max_themes, max(2, n // 8))

    vectors = _vectorize(texts, use_ai)
    labels = _cluster(vectors, k) if vectors is not None else None
    if labels is None:
        return _fallback_keyword_groups(df, max_themes)

    work = df.copy()
    work["_cluster"] = labels
    stop = search_term.replace("#", "").replace("@", "").split()

    themes = []
    for _, grp in work.groupby("_cluster"):
        top_words, _ = extract_hot_topics(grp["text"].tolist(), extra_stop=stop, top_n=3)
        label = ", ".join(w for w, _ in top_words[:3])
        themes.append(_theme_from_group(grp, label))

    themes.sort(key=lambda t: t["size"], reverse=True)
    return themes
