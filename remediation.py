"""
LUMISOCIAL — Automated Remediation & Strategic Action Engine
Defines scenarios, strategic actions, and sentiment forecasting logic.
"""

REMEDIATION_SCENARIOS = {
    "fake_news": {
        "title": "📰 Fake News & Misinformation Spike",
        "description": "High-virality bot networks or bad actors sharing unverified clips, distorted images, or doctored statements.",
        "causes": [
            "Coordinated bot networks on Telegram & X/Twitter",
            "Out-of-context video clip spreading rapidly",
            "Unverified rumors published by fringe blogs"
        ],
        "actions": [
            {
                "name": "Counter-Narrative Release",
                "impact": "Reduces negative sentiment by 25% and boosts positive by 15%",
                "details": "Instantly push verified factual press releases and media kits to top 30 Indian RSS/News Connectors (e.g., ANI, PTI, local papers)."
            },
            {
                "name": "Platform Moderation Appeals",
                "impact": "Lowers negative post volume by 10%",
                "details": "Flag posts for platform moderation via API copyright / misinformation hooks and direct liaison channels."
            }
        ]
    },
    "policy_backlash": {
        "title": "🎓 Policy or Statement Backlash",
        "description": "Public dissatisfaction regarding policy changes, exam/employment delays, or controversial public statements.",
        "causes": [
            "High negative reaction in the 18–24 youth demographic",
            "Perceived delay in government exams or job openings",
            "Misconstrued statement during live interviews"
        ],
        "actions": [
            {
                "name": "Targeted Video Clarification",
                "impact": "Converts 30% of negative youth opinions to positive/neutral",
                "details": "Issue youth-focused statements on video-first channels (YouTube Shorts, Instagram, Bluesky video) explaining the timeline and actions."
            },
            {
                "name": "Policy Pivot / Focus Group Engagement",
                "impact": "Increases positive sentiment by 20%",
                "details": "Shift communication away from defensive messaging and towards active solutions, highlighting student/workforce benefits."
            }
        ]
    },
    "local_issue": {
        "title": "📍 Localized Civic / Regional Issue",
        "description": "Localized negativity concentrated in specific cities or states due to infrastructure, utility, or regional governance issues.",
        "causes": [
            "Severe waterlogging/floods in major hubs (e.g. Bengaluru, Mumbai)",
            "Local authority delays in infrastructure delivery",
            "Public transport strikes or service disruptions"
        ],
        "actions": [
            {
                "name": "Geo-Fenced PR Release",
                "impact": "Reduces regional negative sentiment by 35%",
                "details": "Release city-specific updates addressing local authorities and local news media directly, showing active feet-on-the-ground steps."
            },
            {
                "name": "Direct Authority Liaison",
                "impact": "Stabilizes sentiment (shifts 15% negative to neutral)",
                "details": "Establish a coordination desk between the figure/organization and local municipal bodies to post immediate joint response reports."
            }
        ]
    }
}


def simulate_remediation(current_stats: dict, selected_actions: list) -> dict:
    """
    Simulates the impact of PR actions on sentiment stats.
    current_stats: {"total": int, "positive": int, "negative": int, "neutral": int}
    selected_actions: list of action names (e.g. ["Counter-Narrative Release"])
    Returns updated stats dictionary.
    """
    total = current_stats.get("total", 0)
    pos = current_stats.get("positive", 0)
    neg = current_stats.get("negative", 0)
    neu = current_stats.get("neutral", 0)
    
    if total == 0:
        return {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "positivity_ratio": 50.0, "avg_score": 0.0}
        
    sim_pos = pos
    sim_neg = neg
    sim_neu = neu
    
    for action in selected_actions:
        if action == "Counter-Narrative Release":
            # Reduces negative sentiment by 25%, converts to positive (15%) and neutral (10%)
            reduction = int(sim_neg * 0.25)
            sim_neg -= reduction
            sim_pos += int(reduction * 0.6)
            sim_neu += int(reduction * 0.4)
            
        elif action == "Platform Moderation Appeals":
            # Lowers negative post volume by 10%
            reduction = int(sim_neg * 0.10)
            sim_neg -= reduction
            
        elif action == "Targeted Video Clarification":
            # Converts 30% of negative opinions to positive (20%) and neutral (10%)
            reduction = int(sim_neg * 0.30)
            sim_neg -= reduction
            sim_pos += int(reduction * 0.67)
            sim_neu += int(reduction * 0.33)
            
        elif action == "Policy Pivot / Focus Group Engagement":
            # Converts 20% negative to positive
            conversion = int(sim_neg * 0.20)
            sim_neg -= conversion
            sim_pos += conversion
            
        elif action == "Geo-Fenced PR Release":
            # Reduces negative sentiment by 35%, shifts to neutral
            reduction = int(sim_neg * 0.35)
            sim_neg -= reduction
            sim_neu += reduction
            
        elif action == "Direct Authority Liaison":
            # Shifts 15% negative to neutral
            reduction = int(sim_neg * 0.15)
            sim_neg -= reduction
            sim_neu += reduction
            
    sim_total = sim_pos + sim_neg + sim_neu
    if sim_total == 0:
        sim_total = total
        
    # Recalculate positivity ratio
    denom = sim_pos + sim_neg
    positivity_ratio = round(100 * sim_pos / max(1, denom), 1)
    
    # Recalculate average score
    # Score weight: positive = 0.8, negative = -0.8, neutral = 0.0
    avg_score = round((sim_pos * 0.8 + sim_neg * -0.8) / max(1, sim_total), 3)
    
    return {
        "total": sim_total,
        "positive": sim_pos,
        "negative": sim_neg,
        "neutral": sim_neu,
        "positivity_ratio": positivity_ratio,
        "avg_score": avg_score
    }
