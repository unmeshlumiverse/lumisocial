import os
import sys
import json
from difflib import SequenceMatcher

# Add social-analyzer directory to path so it can be imported correctly
SA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "social-analyzer"))
if SA_PATH not in sys.path:
    sys.path.insert(0, SA_PATH)

from app import SocialAnalyzer

# Load names origins database for offline analysis
NAMES_JSON_PATH = os.path.join(SA_PATH, "data", "names.json")


def verify_profile_username(username: str, platforms: list = None):
    """
    Search for a username across multiple social platforms using social-analyzer.
    Returns a dict with detected, unknown, and failed profile links.
    """
    if not username:
        return {"detected": [], "unknown": [], "failed": []}
    
    # Clean username (strip @ or spaces)
    clean_username = username.strip().lstrip("@")
    
    # If specific platforms requested, space-separate them for social-analyzer
    if not platforms:
        # Check top high-value platforms to keep it fast
        platforms_str = "twitter telegram reddit youtube github facebook instagram"
    else:
        platforms_str = " ".join(platforms)
    
    try:
        sa = SocialAnalyzer(silent=True)
        # Initialize websites_entries and other resources
        sa.init_logic()
        
        # Run social-analyzer in fast mode
        result = sa.run_as_object(
            username=clean_username,
            websites=platforms_str,
            mode="fast",
            silent=True
        )
        return result
    except Exception as e:
        print(f"Error in SocialAnalyzer profile check: {e}")
        return {"detected": [], "unknown": [], "failed": []}


def analyze_name(name: str):
    """
    Look up name origins and genders in the social-analyzer names database.
    Returns a list of match dicts containing: name, origin, gender, and similarity.
    """
    name_clean = name.strip().lower()
    if not name_clean or not os.path.exists(NAMES_JSON_PATH):
        return []
    
    try:
        with open(NAMES_JSON_PATH, "r", encoding="utf-8") as f:
            names_data = json.load(f)
    except Exception:
        return []
        
    matches = []
    
    # Check each origin (e.g. "indian", "arabic", "english")
    for origin, genders_dict in names_data.items():
        for gender in ["boy", "girl", "uni"]:
            names_list = genders_dict.get(gender, [])
            if not isinstance(names_list, list):
                continue
                
            for ref_name in names_list:
                ref_name_str = str(ref_name).lower()
                # Exact or substring match
                if name_clean == ref_name_str or ref_name_str in name_clean or name_clean in ref_name_str:
                    matches.append({
                        "name": ref_name,
                        "origin": origin.capitalize(),
                        "gender": gender.capitalize(),
                        "similarity": 1.0 if name_clean == ref_name_str else 0.85
                    })
                else:
                    # High similarity match
                    sim = SequenceMatcher(None, name_clean, ref_name_str).ratio()
                    if sim > 0.8:
                        matches.append({
                            "name": ref_name,
                            "origin": origin.capitalize(),
                            "gender": gender.capitalize(),
                            "similarity": round(sim, 2)
                        })
                        
    # Deduplicate and sort matches by similarity descending
    seen = set()
    unique_matches = []
    for m in sorted(matches, key=lambda x: x["similarity"], reverse=True):
        key = (m["name"], m["origin"], m["gender"])
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)
            
    return unique_matches[:10]  # Limit to top 10 matches
