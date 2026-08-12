"""
Emotion detection with pluggable backends.

  - "lexicon"     : the built-in word list below — free, offline, instant (default).
  - "transformer" : a free LOCAL model (GoEmotions, 28 fine-grained emotions) mapped
                    onto our set. Needs `pip install transformers torch`. Far more
                    accurate; falls back to the lexicon if unavailable.

Both return one of: love, joy, anger, hate, fear, sadness, neutral.
"""

import os
import re

_LEXICON = {
    "love": {
        "love", "loved", "loving", "adore", "admire", "admired", "respect",
        "respected", "support", "supporting", "wonderful", "appreciate", "hero",
        "legend", "inspiring", "inspiration", "blessing", "grateful", "proud",
        "beautiful", "icon", "goat", "king", "queen",
    },
    "joy": {
        "happy", "glad", "great", "awesome", "amazing", "fantastic", "excellent",
        "celebrate", "win", "winning", "victory", "congrats", "congratulations",
        "brilliant", "superb", "joy", "delighted", "excited", "yay", "lol",
    },
    "anger": {
        "angry", "furious", "outrage", "outrageous", "mad", "rage", "unacceptable",
        "shameful", "shame", "corrupt", "corruption", "liar", "lies", "cheat",
        "betray", "betrayed", "hypocrite",
    },
    "hate": {
        "hate", "hateful", "despise", "loathe", "worst", "evil", "terrible",
        "awful", "pathetic", "garbage", "trash", "disgrace", "enemy", "destroy",
        "idiot", "stupid", "clown", "fraud", "disgusting", "disgust",
    },
    "fear": {
        "fear", "afraid", "scared", "worried", "worry", "anxious", "threat",
        "danger", "dangerous", "risk", "risky", "crisis", "panic", "terrifying",
    },
    "sadness": {
        "sad", "disappointed", "disappointing", "unfortunate", "tragic",
        "heartbroken", "sorrow", "depressing", "miserable", "fail", "failure",
        "loss", "losing", "pain", "cry",
    },
}

# For the map: which emotions read as "negative" vs "positive".
EMOTION_ORDER = ["love", "joy", "neutral", "fear", "sadness", "anger", "hate"]


def _detect_emotion_lexicon(text: str) -> str:
    """Dominant emotion from the built-in lexicon, or 'neutral'."""
    if not text:
        return "neutral"
    words = re.findall(r"[a-z']+", text.lower())
    wordset = set(words)

    scores = {}
    for emotion, lex in _LEXICON.items():
        hits = len(wordset & lex)
        if hits:
            scores[emotion] = hits

    if not scores:
        return "neutral"
    return max(scores, key=scores.get)


# ---- Optional transformer backend (GoEmotions) --------------------------

MODEL_NAME = "SamLowe/roberta-base-go_emotions"

# Map GoEmotions' 28 labels onto our 7.
_GO_MAP = {
    "love": "love", "admiration": "love", "caring": "love", "gratitude": "love", "desire": "love",
    "joy": "joy", "amusement": "joy", "excitement": "joy", "optimism": "joy",
    "approval": "joy", "pride": "joy", "relief": "joy",
    "anger": "anger", "annoyance": "anger", "disapproval": "anger",
    "disgust": "hate",
    "fear": "fear", "nervousness": "fear",
    "sadness": "sadness", "grief": "sadness", "disappointment": "sadness",
    "remorse": "sadness", "embarrassment": "sadness",
    # everything else (neutral, surprise, confusion, curiosity, realization, ...) -> neutral
}

_BACKEND = os.environ.get("EMOTION_BACKEND", "lexicon").lower()
_clf = None
_clf_failed = False


def set_backend(name: str):
    global _BACKEND
    _BACKEND = (name or "lexicon").lower()


def get_backend() -> str:
    return _BACKEND


def _load_clf():
    global _clf, _clf_failed
    if _clf is not None or _clf_failed:
        return _clf
    try:
        from transformers import pipeline
        _clf = pipeline("text-classification", model=MODEL_NAME, top_k=1, truncation=True)
    except Exception:
        _clf_failed = True
        _clf = None
    return _clf


def ensure_backend() -> str:
    """Return the backend actually used (honours fallback)."""
    if _BACKEND == "transformer" and _load_clf() is None:
        return "lexicon"
    return _BACKEND


def detect_many(texts, backend=None):
    """Label a list of texts. Returns list of emotion strings."""
    b = (backend or _BACKEND)
    if b == "transformer":
        clf = _load_clf()
        if clf is not None:
            out = []
            results = clf([(t or "")[:512] for t in texts], batch_size=16)
            for r in results:
                top = r[0]["label"].lower() if isinstance(r, list) else r["label"].lower()
                out.append(_GO_MAP.get(top, "neutral"))
            return out
    return [_detect_emotion_lexicon(t) for t in texts]


def detect_emotion(text: str, backend=None) -> str:
    """Single-text convenience wrapper."""
    return detect_many([text], backend)[0]
