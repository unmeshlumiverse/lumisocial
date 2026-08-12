"""
Sentiment scoring with pluggable backends.

Backends:
  - "vader"       : free, offline, fast, English-only (default).
  - "transformer" : free LOCAL multilingual AI model (understands Hindi and other
                    languages, better on sarcasm). Needs `pip install transformers
                    torch` and a one-time model download (~1GB). Slower than VADER.
  - "ensemble"    : average of VADER + transformer for robustness.

Anything selecting a transformer backend gracefully FALLS BACK to VADER if the
libraries/model aren't available, so the app always works at $0.

All backends return the same shape: {"label": ..., "score": float in [-1, 1]}.
"""

import os

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_vader = SentimentIntensityAnalyzer()
POS_THRESHOLD = 0.05
NEG_THRESHOLD = -0.05

# Free, multilingual, tuned for social text (covers Hindi, English, and 6+ more).
MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"

_BACKEND = os.environ.get("SENTIMENT_BACKEND", "vader").lower()
_transformer = None
_transformer_failed = False


def set_backend(name: str):
    global _BACKEND
    _BACKEND = (name or "vader").lower()


def get_backend() -> str:
    return _BACKEND


def _label_from_compound(c: float) -> str:
    if c >= POS_THRESHOLD:
        return "positive"
    if c <= NEG_THRESHOLD:
        return "negative"
    return "neutral"


def _vader_scores(texts):
    out = []
    for t in texts:
        c = _vader.polarity_scores(t)["compound"] if t and t.strip() else 0.0
        out.append((_label_from_compound(c), round(c, 4)))
    return out


def _load_transformer():
    """Lazy-load the transformer pipeline; returns None if unavailable."""
    global _transformer, _transformer_failed
    if _transformer is not None or _transformer_failed:
        return _transformer
    try:
        from transformers import pipeline
        _transformer = pipeline("sentiment-analysis", model=MODEL_NAME,
                                top_k=None, truncation=True)
    except Exception:
        _transformer_failed = True
        _transformer = None
    return _transformer


def _transformer_scores(texts):
    clf = _load_transformer()
    if clf is None:
        return None
    results = clf([(t or "")[:512] for t in texts], batch_size=16)
    out = []
    for r in results:
        scores = {d["label"].lower(): d["score"] for d in r}
        comp = round(scores.get("positive", 0.0) - scores.get("negative", 0.0), 4)
        out.append((_label_from_compound(comp), comp))
    return out


def ensure_backend() -> str:
    """Return the backend that will ACTUALLY be used (honours fallback)."""
    if _BACKEND in ("transformer", "ensemble") and _load_transformer() is None:
        return "vader"
    return _BACKEND


def score_many(texts, backend=None):
    """Score a list of texts. Returns list of (label, score)."""
    b = (backend or _BACKEND)
    if b in ("transformer", "ensemble"):
        tr = _transformer_scores(texts)
        if tr is None:
            return _vader_scores(texts)  # graceful fallback
        if b == "transformer":
            return tr
        va = _vader_scores(texts)
        out = []
        for (_vl, vc), (_tl, tc) in zip(va, tr):
            comp = round((vc + tc) / 2, 4)
            out.append((_label_from_compound(comp), comp))
        return out
    return _vader_scores(texts)


def score_sentiment(text: str, backend=None) -> dict:
    label, score = score_many([text], backend)[0]
    return {"label": label, "score": score}
