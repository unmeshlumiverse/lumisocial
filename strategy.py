"""
Strategic targeting & positive-image planning.

Turns the collected mentions into decisions:
  * priority_issue   -> the single biggest problem (volume x hostility)
  * priority_region  -> the Indian state most in need of attention
  * priority_age     -> the age band most negative about the person
  * build_action_plan-> a sequenced Now / 30-day / 60-90-day plan, each step
                        mapped to a concrete remediation scenario and its
                        modelled sentiment lift.

Everything is derived from data the pipeline already produced (sentiment,
emotion, inferred region, inferred age group, engagement). The region/age
signals are CONTENT-BASED INFERENCE, not real geolocation or verified
demographics — the plan says so, and the numbers are directional, not promises.
"""

import re

import pandas as pd

from analysis import extract_hot_topics
from remediation import REMEDIATION_SCENARIOS, simulate_remediation

# Keyword cues that route a topic to the right remediation playbook.
_LOCAL_CUES = {
    "flood", "floods", "flooded", "waterlogging", "water", "road", "roads",
    "pothole", "traffic", "infrastructure", "power", "electricity", "garbage",
    "sewage", "metro", "bus", "transport", "civic", "municipal", "drainage",
    "pipeline", "outage", "strike",
}
_POLICY_CUES = {
    "exam", "exams", "job", "jobs", "unemployment", "recruitment", "vacancy",
    "policy", "bill", "reform", "scheme", "reservation", "tax", "gst", "fee",
    "fees", "salary", "pension", "statement", "remark", "speech", "promise",
    "delay", "paper", "leak", "result", "results",
}
_FAKE_CUES = {
    "fake", "hoax", "rumor", "rumour", "morphed", "edited", "doctored",
    "misleading", "propaganda", "bot", "botnet", "viral", "clip", "deepfake",
    "fabricated", "manipulated", "misinformation", "disinformation",
}


def _route_scenario(topic_terms):
    """Pick the best-fit remediation scenario key from a topic's words."""
    words = set()
    for t in topic_terms:
        words |= set(re.findall(r"[a-z']+", str(t).lower()))
    if words & _FAKE_CUES:
        return "fake_news"
    if words & _LOCAL_CUES:
        return "local_issue"
    if words & _POLICY_CUES:
        return "policy_backlash"
    return "policy_backlash"  # safe default: treat as a messaging/statement problem


def _topic_slice(df, term):
    mask = df["text"].astype(str).str.contains(
        r"\b" + re.escape(term) + r"\b", case=False, regex=True, na=False
    )
    return df[mask]


def priority_issue(df, search_term="", top_k=12):
    """
    The biggest issue = the hot topic whose posts are both high-volume and
    hostile. Score = mentions * negativity_fraction.
    Returns None if there isn't enough signal.
    """
    if df is None or df.empty or len(df) < 4:
        return None
    stop = search_term.replace("#", "").replace("@", "").split()
    words, _ = extract_hot_topics(df["text"].tolist(), extra_stop=stop, top_n=top_k)
    best = None
    for term, _count in words:
        sub = _topic_slice(df, term)
        if len(sub) < 2:
            continue
        neg_frac = (sub["sentiment"] == "negative").mean()
        volume = len(sub)
        pain = round(volume * neg_frac, 2)
        if pain <= 0:
            continue
        if best is None or pain > best["pain"]:
            reach = int(sub["engagement"].sum()) if "engagement" in sub.columns else 0
            top_state = (sub["india_state"].dropna().value_counts().idxmax()
                         if "india_state" in sub.columns and sub["india_state"].notna().any()
                         else None)
            top_age = (sub["age_group"].value_counts().idxmax()
                       if "age_group" in sub.columns and not sub["age_group"].isna().all()
                       else None)
            emo = sub["emotion"].value_counts() if "emotion" in sub.columns else None
            drive = "concern"
            if emo is not None and not emo.empty:
                non_neu = emo.drop(labels=["neutral"], errors="ignore")
                drive = str(non_neu.idxmax()) if not non_neu.empty else str(emo.idxmax())
            sample = (sub.sort_values("engagement", ascending=False).iloc[0]
                      if "engagement" in sub.columns else sub.iloc[0])
            best = {
                "topic": term,
                "pain": pain,
                "volume": volume,
                "neg_pct": round(100 * neg_frac, 1),
                "reach": reach,
                "top_state": top_state,
                "top_age": top_age,
                "driving_emotion": drive,
                "scenario_key": _route_scenario([term]),
                "sample_text": str(sample.get("text", ""))[:280],
                "sample_url": sample.get("url", ""),
                "sample_platform": sample.get("platform", ""),
            }
    return best


def priority_region(df):
    """Indian state most in need of attention = mentions * negativity."""
    if df is None or df.empty or "india_state" not in df.columns:
        return None
    india = df[df["india_state"].notna()]
    if india.empty:
        return None
    best = None
    for state, grp in india.groupby("india_state"):
        vol = len(grp)
        neg_frac = (grp["sentiment"] == "negative").mean()
        pain = vol * neg_frac
        if pain <= 0:
            continue
        if best is None or pain > best["pain"]:
            top_city = (grp["india_city"].dropna().value_counts().idxmax()
                        if "india_city" in grp.columns and grp["india_city"].notna().any()
                        else None)
            local_words, _ = extract_hot_topics(grp["text"].tolist(), top_n=3)
            best = {
                "state": state,
                "pain": round(pain, 2),
                "mentions": vol,
                "neg_pct": round(100 * neg_frac, 1),
                "top_city": top_city,
                "local_drivers": [w for w, _ in local_words],
            }
    return best


def priority_age(df):
    """Age band most negative (weighted by volume)."""
    if df is None or df.empty or "age_group" not in df.columns:
        return None
    best = None
    for age, grp in df.groupby("age_group"):
        vol = len(grp)
        if vol < 2:
            continue
        neg_frac = (grp["sentiment"] == "negative").mean()
        pain = vol * neg_frac
        if best is None or pain > best["pain"]:
            best = {
                "age_group": age,
                "pain": round(pain, 2),
                "mentions": vol,
                "neg_pct": round(100 * neg_frac, 1),
            }
    return best


# Channel guidance keyed to the age band that most needs winning over.
_AGE_CHANNELS = {
    "18-24 (Gen Z)": "short-form video (YouTube Shorts, Instagram Reels), meme-literate and fast; lead with authenticity, not formality",
    "25-34 (Millennials)": "explainer threads and Q&A formats (Reddit AMA, long-form posts, podcasts); lead with competence and specifics",
    "35-50 (Gen X)": "news interviews and op-eds in mainstream outlets; lead with track record and stability",
    "50+ (Seniors)": "regional-language TV, newspaper op-eds and community events; lead with continuity and values",
}


def build_action_plan(df, stats, search_term=""):
    """
    Assemble a sequenced positive-image plan grounded in the data.
    Returns {"issue":..., "region":..., "age":..., "phases":[...], "forecast":{...}}.
    """
    issue = priority_issue(df, search_term)
    region = priority_region(df)
    age = priority_age(df)

    phases = []

    # ---- NOW: neutralise the single biggest issue -----------------------
    if issue:
        sc = REMEDIATION_SCENARIOS.get(issue["scenario_key"], {})
        actions = sc.get("actions", [])
        steps = [f"{a['name']} — {a['details']}" for a in actions]
        phases.append({
            "window": "Now (0–7 days)",
            "goal": f"Contain the biggest live issue: “{issue['topic']}” "
                    f"({issue['neg_pct']}% negative, driven by {issue['driving_emotion']}).",
            "playbook": sc.get("title", "Rapid response"),
            "steps": steps or ["Issue a clear, factual response and monitor uptake."],
            "primary_action": actions[0]["name"] if actions else None,
        })

    # ---- 30 DAYS: fix the worst region ----------------------------------
    if region:
        loc = region["state"] + (f" (esp. {region['top_city']})" if region.get("top_city") else "")
        drivers = ", ".join(region.get("local_drivers", [])) or "local grievances"
        phases.append({
            "window": "Next 30 days",
            "goal": f"Recover the hardest-hit region: {loc} "
                    f"({region['neg_pct']}% negative across {region['mentions']} mentions).",
            "playbook": "📍 Geo-Fenced PR",
            "steps": [
                f"Release {region['state']}-specific updates tied to the local drivers: {drivers}.",
                "Brief and coordinate with local/regional-language news outlets rather than only national desks.",
                "Show visible on-the-ground action (site visits, local officials) and publish joint status reports.",
            ],
            "primary_action": "Geo-Fenced PR Release",
        })

    # ---- 30 DAYS: reach the coldest age band ----------------------------
    if age:
        channel = _AGE_CHANNELS.get(age["age_group"], "the channels that band actually uses")
        phases.append({
            "window": "Next 30 days",
            "goal": f"Win back the coldest audience: {age['age_group']} "
                    f"({age['neg_pct']}% negative).",
            "playbook": "🎯 Audience-Matched Messaging",
            "steps": [
                f"Meet them where they are: {channel}.",
                "Address their specific grievance directly instead of generic messaging.",
                "Recruit credible voices that segment already trusts to carry the message.",
            ],
            "primary_action": "Targeted Video Clarification",
        })

    # ---- 60–90 DAYS: build a durable positive narrative -----------------
    positives = _positive_pillars(df, search_term)
    phases.append({
        "window": "60–90 days",
        "goal": "Shift from defence to offence — build a durable positive story.",
        "playbook": "🌱 Positive Narrative Building",
        "steps": [
            (f"Amplify what is already landing well: {', '.join(positives)}."
             if positives else
             "Identify 2–3 genuine wins and make them the recurring headline."),
            "Publish a steady cadence of proof-point content (outcomes, testimonials, data).",
            "Re-measure sentiment monthly and rotate messaging toward whatever is gaining.",
        ],
        "primary_action": "Policy Pivot / Focus Group Engagement",
    })

    # ---- Modelled forecast if the primary actions are taken -------------
    # Dedupe (order-preserving) so the same lever isn't applied twice.
    primary_actions, _seen = [], set()
    for p in phases:
        a = p.get("primary_action")
        if a and a not in _seen:
            _seen.add(a)
            primary_actions.append(a)
    forecast = None
    if stats and stats.get("total"):
        forecast = simulate_remediation(stats, primary_actions)

    return {
        "issue": issue,
        "region": region,
        "age": age,
        "phases": phases,
        "primary_actions": primary_actions,
        "forecast": forecast,
    }


def _positive_pillars(df, search_term, top_n=3):
    """Topics whose posts skew positive — the material for the offence phase."""
    if df is None or df.empty:
        return []
    stop = search_term.replace("#", "").replace("@", "").split()
    words, _ = extract_hot_topics(df["text"].tolist(), extra_stop=stop, top_n=15)
    scored = []
    for term, _c in words:
        sub = _topic_slice(df, term)
        if len(sub) < 2:
            continue
        pos_frac = (sub["sentiment"] == "positive").mean()
        if pos_frac >= 0.45:
            scored.append((term, pos_frac, len(sub)))
    scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [t for t, _p, _n in scored[:top_n]]
