"""
Keyword expansion module.

Expands search queries with exact variants and real Wikidata aliases (incl. Hindi/regional scripts).
Prevents isolated surname splitting to eliminate false positive matches.
"""

import requests

WIKIDATA_SEARCH = "https://www.wikidata.org/w/api.php"


def _rule_variants(core: str, search_type: str):
    core = core.strip()
    variants = []
    nospace = core.replace(" ", "")
    if search_type != "hashtag":
        variants.append(f"#{nospace}")
    parts = core.split()
    if len(parts) >= 2:
        variants.append(f'"{core}"')
    return variants


def _wikidata_aliases(core: str, langs=("en", "hi", "mr")):
    """Fetch 'also known as' aliases for the entity. Returns [] on any failure."""
    try:
        r = requests.get(WIKIDATA_SEARCH, params={
            "action": "wbsearchentities", "search": core, "language": "en",
            "format": "json", "limit": 1,
        }, timeout=8, headers={"User-Agent": "public-figure-monitor/0.1"})
        r.raise_for_status()
        hits = r.json().get("search", [])
        if not hits:
            return []
        qid = hits[0]["id"]

        r2 = requests.get(WIKIDATA_SEARCH, params={
            "action": "wbgetentities", "ids": qid, "props": "aliases",
            "languages": "|".join(langs), "format": "json",
        }, timeout=8, headers={"User-Agent": "public-figure-monitor/0.1"})
        r2.raise_for_status()
        entity = r2.json().get("entities", {}).get(qid, {})
        aliases = entity.get("aliases", {})
        out = []
        for lang in langs:
            for a in aliases.get(lang, []):
                val = a.get("value", "").strip()
                if val:
                    out.append(val)
        return out
    except Exception:
        return []


def expand_keywords(term: str, search_type: str = "keyword",
                    use_wikidata: bool = True, max_variants: int = 5):
    """Return a deduped list of EXTRA query variants (excludes the original term)."""
    base = term.strip()
    core = base.lstrip("#@").strip()
    if not core:
        return []

    candidates = _rule_variants(core, search_type)
    if use_wikidata:
        candidates += _wikidata_aliases(core)

    seen = {base.lower(), core.lower()}
    out = []
    for c in candidates:
        cl = c.lower()
        if cl in seen:
            continue
        seen.add(cl)
        out.append(c)
        if len(out) >= max_variants:
            break
    return out
