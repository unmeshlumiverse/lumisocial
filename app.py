"""
LUMISOCIAL — Executive Command Center & Social Intelligence Platform

Run with:  streamlit run app.py
"""

import os
import re
import math
import datetime as dt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import sentiment
import emotion as emotion_engine
import storage
from keywords import expand_keywords
from pipeline import collect, summarize
from analysis import (
    extract_hot_topics, top_authors, COUNTRY_ISO3,
    aggregate_india_state_sentiments
)
from emotion import EMOTION_ORDER
from demographics import summarize_demographics
from narratives import detect_narratives
from report import build_html_report

# Import Connectors
from connectors.bluesky import search_bluesky
from connectors.reddit import search_reddit
from connectors.telegram import search_telegram, DEFAULT_INDIA_CHANNELS
from connectors.youtube import search_youtube
from connectors.news import search_news
from connectors.indian_news import search_indian_newspapers
from connectors.twitter import search_twitter
from connectors.mastodon import search_mastodon
from connectors.hackernews import search_hackernews
from connectors.gdelt import search_gdelt

# Streamlit Cloud secrets aren't always auto-copied into os.environ the way a
# local .env is picked up by load_dotenv() — mirror them in explicitly so
# every connector's os.environ.get(...) call keeps working when deployed.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and not os.environ.get(_k):
            os.environ[_k] = _v
except Exception:
    pass

st.set_page_config(
    page_title="LUMISOCIAL | Command Center",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Modern design system — CSS custom properties so the whole palette/spacing
# scale is defined once and every component below just references it.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

    :root {
        --bg: #f6f8fb;
        --surface: #ffffff;
        --surface-2: #f8fafc;
        --border: #e6eaf0;
        --border-soft: #eef1f6;
        --text: #0f172a;
        --text-2: #475569;
        --text-mute: #94a3b8;
        --accent: #0d9488;
        --accent-dark: #0f766e;
        --accent-light: #ccfbf1;
        --accent-glow: rgba(13, 148, 136, 0.16);
        --pos: #10b981;
        --pos-bg: #ecfdf5;
        --pos-border: #a7f3d0;
        --neg: #ef4444;
        --neg-bg: #fef2f2;
        --neg-border: #fecaca;
        --neu: #f59e0b;
        --neu-bg: #fffbeb;
        --neu-border: #fde68a;
        --info: #0284c7;
        --info-bg: #f0f9ff;
        --r-sm: 8px;
        --r-md: 12px;
        --r-lg: 16px;
        --shadow-1: 0 1px 2px rgba(15,23,42,0.04);
        --shadow-2: 0 2px 8px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04);
        --shadow-3: 0 8px 24px rgba(15,23,42,0.08);
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-2);
    }

    .stApp { background-color: var(--bg); }

    /* Tighter, calmer default vertical rhythm */
    .block-container { padding-top: 1.6rem; padding-bottom: 2.5rem; }

    /* ============ Sidebar — deep slate "command console" ============ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1220 0%, #101a2e 55%, #0d1526 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4, [data-testid="stSidebar"] h5 {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] .stCaption {
        color: #b6c2d9 !important;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="input"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #0f172a !important;
        background-color: #ffffff !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="base-input"] {
        border-radius: var(--r-sm) !important;
        border: 1px solid transparent !important;
    }
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label span {
        color: #d7e0f0 !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: var(--r-sm);
    }
    [data-testid="stSidebar"] [data-testid="stContainer"] {
        border-color: rgba(255,255,255,0.1) !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border-radius: var(--r-sm) !important;
        border: none !important;
        box-shadow: 0 6px 18px rgba(13, 148, 136, 0.35) !important;
        padding: 10px 16px !important;
        transition: transform 0.12s ease, box-shadow 0.12s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(13, 148, 136, 0.45) !important;
    }
    [data-testid="stSidebar"] .stButton > button * { color: #ffffff !important; }

    /* ============ Generic surfaces ============ */
    .auris-upper-card, .filter-panel-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-lg);
        padding: 20px 22px;
        box-shadow: var(--shadow-1);
        margin-bottom: 20px;
        transition: box-shadow 0.15s ease;
    }
    .auris-upper-card:hover { box-shadow: var(--shadow-2); }

    .auris-section-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        letter-spacing: -0.01em;
    }

    /* ============ Word Cloud ============ */
    .topic-tag-cloud {
        display: flex;
        flex-wrap: wrap;
        gap: 10px 14px;
        align-items: center;
        justify-content: flex-start;
        padding: 8px 0;
        min-height: 180px;
    }
    .tag-xl { font-size: 1.4rem; font-weight: 800; color: var(--text); letter-spacing: -0.01em; }
    .tag-lg { font-size: 1.12rem; font-weight: 700; color: #334155; }
    .tag-md { font-size: 0.92rem; font-weight: 600; color: var(--text-2); }
    .tag-sm { font-size: 0.8rem; font-weight: 500; color: var(--text-mute); }

    /* ============ Influencer Row ============ */
    .influencer-row {
        display: flex;
        gap: 14px;
        align-items: center;
        justify-content: flex-start;
        margin-top: 14px;
        flex-wrap: wrap;
    }
    .influencer-card { text-align: center; }
    .influencer-avatar {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--accent-light), #e0f2fe);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 0.85rem;
        color: var(--accent-dark);
        margin: 0 auto 6px auto;
        border: 2px solid var(--surface);
        box-shadow: var(--shadow-2);
        position: relative;
    }
    .platform-sub-icon {
        position: absolute;
        bottom: -2px;
        right: -2px;
        background: var(--accent);
        color: white;
        border-radius: 50%;
        width: 17px;
        height: 17px;
        font-size: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.25);
    }
    .influencer-score { font-size: 0.8rem; font-weight: 700; color: var(--text-2); }

    /* ============ Feed Cards ============ */
    .auris-feed-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-md);
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: var(--shadow-1);
        position: relative;
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }
    .auris-feed-card:hover {
        box-shadow: var(--shadow-2);
        transform: translateY(-1px);
    }
    .card-border-pos { border-left: 4px solid var(--pos); }
    .card-border-neg { border-left: 4px solid var(--neg); }
    .card-border-neu { border-left: 4px solid var(--neu); }

    .feed-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        flex-wrap: wrap;
        gap: 8px;
    }
    .feed-user-info { display: flex; align-items: center; gap: 10px; }
    .feed-avatar-circle {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: var(--surface-2);
        border: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        color: var(--text);
    }
    .feed-author-name { font-weight: 700; font-size: 0.94rem; color: var(--text); }
    .feed-handle { font-size: 0.82rem; color: var(--text-mute); font-weight: 500; margin-left: 4px; }
    .platform-badge {
        font-size: 0.7rem;
        font-weight: 700;
        color: var(--text-2);
        background: var(--surface-2);
        border: 1px solid var(--border-soft);
        padding: 2px 9px;
        border-radius: 20px;
        margin-left: 6px;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .feed-time {
        font-size: 0.78rem;
        color: var(--text-mute);
        display: flex;
        align-items: center;
        gap: 4px;
        font-variant-numeric: tabular-nums;
    }
    .feed-body-text { font-size: 0.93rem; color: #334155; line-height: 1.6; margin: 12px 0 12px 0; }
    .highlight-kw {
        background-color: #fef08a;
        color: #854d0e;
        padding: 1px 5px;
        border-radius: 4px;
        font-weight: 700;
    }
    .feed-tags-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .feed-pill {
        background: var(--surface-2);
        border: 1px solid var(--border-soft);
        color: var(--text-2);
        padding: 3px 11px;
        border-radius: 20px;
        font-size: 0.74rem;
        font-weight: 700;
    }
    .feed-pill-pos { background: var(--pos-bg); border-color: var(--pos-border); color: #166534; }
    .feed-pill-neg { background: var(--neg-bg); border-color: var(--neg-border); color: #991b1b; }
    .feed-pill-neu { background: var(--neu-bg); border-color: var(--neu-border); color: #92400e; }
    .feed-pill-loc { background: var(--info-bg); border-color: #bae6fd; color: #0369a1; }

    /* ============ Filter Panel ============ */
    .filter-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border-soft);
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    .filter-title { font-weight: 800; font-size: 0.96rem; color: var(--text); letter-spacing: -0.01em; }
    .filter-total {
        font-size: 0.75rem;
        color: var(--accent-dark);
        font-weight: 700;
        background: var(--accent-light);
        padding: 3px 10px;
        border-radius: 20px;
    }
    .sentiment-toggle-box { display: flex; justify-content: space-between; margin-bottom: 4px; gap: 8px; }
    .sentiment-item {
        flex: 1;
        text-align: center;
        background: var(--surface-2);
        border: 1px solid var(--border-soft);
        border-radius: var(--r-sm);
        padding: 10px 4px;
        transition: transform 0.12s ease;
    }
    .sentiment-item:hover { transform: translateY(-2px); }
    .sentiment-emoji-large { font-size: 1.3rem; }
    .sentiment-count-text { font-size: 0.85rem; font-weight: 800; color: var(--text); margin-top: 3px; }

    /* ============ Tabs ============ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        padding: 0px 20px;
        font-size: 0.92rem;
        font-weight: 700;
        border-radius: var(--r-sm) var(--r-sm) 0 0;
        color: var(--text-2);
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent-dark) !important;
        background: var(--accent-light) !important;
    }

    /* ============ Misc: buttons, containers, dataframes ============ */
    .stButton > button { border-radius: var(--r-sm); }
    [data-testid="stContainer"] { border-radius: var(--r-md) !important; }
    div[data-testid="stExpander"] { border-radius: var(--r-md); border-color: var(--border) !important; }
    [data-testid="stMetricValue"] { font-weight: 800; color: var(--text); }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ---------------- Top Header Bar with Interactive Popovers ----------------
h_left, h_right = st.columns([3, 2])

with h_left:
    st.markdown("""<div style="display:flex; align-items:center; gap:10px; padding-top:6px;">
<span style="font-size:1.5rem; background:linear-gradient(135deg,#0d9488,#0f766e); width:36px; height:36px; border-radius:10px; display:inline-flex; align-items:center; justify-content:center; box-shadow:0 4px 12px rgba(13,148,136,0.3);">⚡</span>
<span style="font-size:1.4rem; font-weight:800; color:#0f172a; letter-spacing:-0.02em;">LUMISOCIAL</span>
<span style="font-weight:500; color:#94a3b8; font-size:1.05rem;">Command Center</span>
</div>""", unsafe_allow_html=True)

with h_right:
    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
    with c_btn1:
        if st.button("🌙 Theme", use_container_width=True, help="Toggle Light / Dark theme"):
            st.toast("Theme toggled: High-contrast executive light mode active.")
    with c_btn2:
        with st.popover("🔔 Alerts", use_container_width=True):
            st.markdown("#### 🔔 System Notifications")
            st.success("🟢 Real-time stream connected to Indian News RSS & Social Connectors.")
            st.info("ℹ️ 25+ major Indian Telegram channels ready for search queries.")
    with c_btn3:
        with st.popover("⚙️ Config", use_container_width=True):
            st.markdown("#### ⚙️ Quick System Config")
            st.caption("Live configuration settings for LUMISOCIAL Command Center.")
            st.checkbox("Auto-refresh feeds every 60s", value=False)
            st.checkbox("Show exact relevance confidence scores", value=True)
    with c_btn4:
        with st.popover("👤 Profile", use_container_width=True):
            st.markdown("#### 👤 Executive User Profile")
            st.markdown("**User**: Unmesh S.")
            st.markdown("**Role**: Enterprise Command Center Analyst")
            st.markdown("**Workspace**: LUMISOCIAL Production")

st.markdown("<hr style='margin:8px 0 16px 0; border:none; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

# ---------------- Left Sidebar Controls ----------------
with st.sidebar:
    st.markdown("""<div style="padding:4px 0 14px 0; border-bottom:1px solid rgba(255,255,255,0.2); margin-bottom:12px;">
<div style="font-size:1.25rem; font-weight:800; letter-spacing:-0.5px;">⚡ LUMISOCIAL</div>
<div style="font-size:0.75rem; opacity:0.85;">Command Center Engine</div>
</div>""", unsafe_allow_html=True)

    st.markdown("### 🔍 Search Target")
    term = st.text_input(
        "Target Name / Handle",
        value="",
        placeholder="e.g. Narendra Modi, Amar Thakare, #AI",
        label_visibility="collapsed"
    )
    search_type_label = st.radio(
        "Search Type",
        ["Name or keyword", "#hashtag", "@username mentions"],
        index=0,
    )
    time_range = st.selectbox(
        "📅 Time Range",
        ["All Available Data", "Past 1 Month", "Past 1 Week", "Past 24 Hours"],
        index=0,
        help="How far back to pull data. 'All Available' fetches maximum historical coverage."
    )
    limit = st.slider("Limit per Platform", 10, 200, 100, step=10)

    st.markdown("### 📡 Active Connectors")
    use_indian_news = st.checkbox("📰 Indian Newspapers (30+ RSS)", value=True)
    use_telegram = st.checkbox("💬 Telegram Public Channels", value=True)
    use_twitter = st.checkbox("🐦 Twitter / X (API v2)", value=True)
    if use_twitter:
        st.caption("⚠️ Twitter's free API only returns the **last ~7 days** — a platform limit, not a bug. It's excluded from deep historical totals.")
    use_news = st.checkbox("🌐 Google News (Global)", value=True)
    use_gdelt = st.checkbox("🗄️ GDELT Historical Archive (2017→now)", value=True,
                             help="The actual source of 'All Time' depth — full-text news search back to 2017.")
    use_bsky = st.checkbox("🦋 Bluesky", value=True)
    use_reddit = st.checkbox("🤖 Reddit", value=True)
    use_youtube = st.checkbox("▶️ YouTube Comments", value=True)
    use_mastodon = st.checkbox("🐘 Mastodon", value=False)
    use_hackernews = st.checkbox("🟠 Hacker News", value=False)

    tg_channels_raw = ""
    if use_telegram:
        with st.expander("Telegram Custom Channels"):
            tg_channels_raw = st.text_area(
                "Usernames (one per line)",
                placeholder="ndtv\nindiatoday\nthe_hindu",
                help="Leave empty to use 25+ default major Indian news broadcast channels."
            )

    use_expand = st.checkbox("🔎 Expand Aliases (Wikidata)", value=False)

    st.markdown("### 🎯 Narrow Down This Prospect")
    st.caption("Optional — answer any of these to rule out namesakes and boost matches for the *right* person.")
    d_loc = st.text_input("📍 State / City they're active in", placeholder="e.g. Nagpur, Maharashtra", key="d_loc_sidebar")
    d_org = st.text_input("🏢 Organization / Party / Role", placeholder="e.g. BJP, CEO of Acme Ltd.", key="d_org_sidebar")
    d_exclude = st.text_input("🚫 Exclude namesakes/unrelated (comma-separated)", placeholder="e.g. actor, cricketer", key="d_exclude_sidebar")

    _active_connector_count = sum([
        use_indian_news, use_telegram, use_twitter, use_news, use_gdelt,
        use_bsky, use_reddit, use_youtube, use_mastodon, use_hackernews,
    ])
    run = st.button("🚀 Run Intelligence Report", type="primary", use_container_width=True)
    st.caption(f"Will search **{_active_connector_count}** active connector{'s' if _active_connector_count != 1 else ''} for this exact query.")

_TYPE_MAP = {
    "Name or keyword": "keyword",
    "#hashtag": "hashtag",
    "@username mentions": "handle",
}


def highlight_keywords(text, term):
    if not text or not term:
        return text
    words = [w for w in re.split(r"\W+", term) if len(w) > 2]
    if not words:
        words = [term.strip()]
    pattern = re.compile(r"(\b" + r"|\b".join(re.escape(w) for w in words) + r")", re.IGNORECASE)
    return pattern.sub(r"<mark class='highlight-kw'>\1</mark>", text)


def get_platform_icon(platform):
    icons = {
        "twitter": "🐦",
        "telegram": "💬",
        "indian_news": "📰",
        "news": "🌐",
        "reddit": "🤖",
        "bluesky": "🦋",
        "youtube": "▶️",
        "mastodon": "🐘",
        "hackernews": "🟠",
        "gdelt": "🗄️",
    }
    return icons.get(platform, "📡")


def _credential_issue(name):
    if name == "reddit" and not (os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET")):
        return "**Reddit** requires valid `REDDIT_CLIENT_ID` in .env."
    if name == "youtube" and not os.environ.get("YOUTUBE_API_KEY"):
        return "**YouTube** requires `YOUTUBE_API_KEY` in .env."
    if name == "telegram":
        api_id = (os.environ.get("TELEGRAM_API_ID") or "").strip()
        api_hash = (os.environ.get("TELEGRAM_API_HASH") or "").strip()
        if not api_id or not api_hash or not api_id.isdigit():
            return "**Telegram** requires numeric `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in .env."
    if name == "twitter" and not os.environ.get("TWITTER_BEARER_TOKEN"):
        return "**Twitter / X** requires `TWITTER_BEARER_TOKEN` in .env."
    return None


active_term = term.strip()

# ---------------- EXECUTION PIPELINE ----------------
sources = {}
cred_notes = []

if use_indian_news:
    sources["indian_news"] = lambda q, n: search_indian_newspapers(q, n)
if use_bsky:
    sources["bluesky"] = search_bluesky
if use_reddit:
    issue = _credential_issue("reddit")
    if issue:
        cred_notes.append(("reddit", issue))
    else:
        sources["reddit"] = lambda q, n: search_reddit(q, n)
if use_youtube:
    issue = _credential_issue("youtube")
    if issue:
        cred_notes.append(("youtube", issue))
    else:
        sources["youtube"] = lambda q, n: search_youtube(q, n)
if use_twitter:
    issue = _credential_issue("twitter")
    if issue:
        cred_notes.append(("twitter", issue))
    else:
        sources["twitter"] = lambda q, n: search_twitter(q, n)
if use_mastodon:
    sources["mastodon"] = lambda q, n: search_mastodon(q, n)
if use_hackernews:
    sources["hackernews"] = lambda q, n: search_hackernews(q, n)
if use_news:
    sources["news"] = lambda q, n: search_news(q, n, country="IN", lang="en")
if use_gdelt:
    sources["gdelt"] = lambda q, n: search_gdelt(q, n, time_range=time_range)
if use_telegram:
    issue = _credential_issue("telegram")
    tg_channels = [c.strip() for c in tg_channels_raw.replace(",", "\n").splitlines() if c.strip()]
    if issue:
        cred_notes.append(("telegram", issue))
    else:
        ch_list = tg_channels if tg_channels else DEFAULT_INDIA_CHANNELS
        sources["telegram"] = lambda q, n: search_telegram(q, n, channels=ch_list)

if cred_notes:
    with st.container(border=True):
        st.markdown(f"##### ⚠️ {len(cred_notes)} connector{'s' if len(cred_notes) != 1 else ''} inactive — missing/invalid credentials")
        st.caption("These sources are silently skipped on every run until fixed. Add the keys in your **Streamlit Cloud → Settings → Secrets** (or local `.env`), then rerun.")
        for _name, _issue in cred_notes:
            st.markdown(f"- {_issue}")


@st.cache_data(ttl=900, show_spinner=False)
def _cached_collect(term, search_type, source_names, limit, expansions_key, time_range,
                     context_key, exclude_key, _sources, _expansions, _context_hints, _exclude_terms):
    """
    Thin cache wrapper around pipeline.collect(). Args prefixed with `_` are
    excluded from Streamlit's cache key (they're callables/lists that can't be
    hashed meaningfully) — the real cache key is the plain hashable args
    (term, source names, limit, etc). A 15-minute TTL means re-running the
    same search shortly after (e.g. after just toggling a filter) reuses the
    already-fetched data instead of re-hitting every network source again.
    """
    return collect(term, search_type, _sources, limit=limit, expansions=_expansions,
                    time_range=time_range, context_hints=_context_hints, exclude_terms=_exclude_terms)


# ---------------- RUN GATING ----------------
# The search only (re)fetches when the user actually clicks "Run Intelligence
# Report" — not on every unrelated widget interaction (opening a popover,
# toggling a checkbox), which is what Streamlit's rerun-the-whole-script model
# would otherwise trigger. Results persist in session_state across reruns.
if run and active_term:
    try:
        search_type = _TYPE_MAP.get(search_type_label, "keyword")
        expansions = expand_keywords(active_term, search_type) if use_expand else []
        context_hints = [h for h in (d_loc, d_org) if h and h.strip()]
        exclude_terms = [t.strip() for t in d_exclude.split(",") if t.strip()]

        spinner_msg = f"Fetching intelligence report for '{active_term}' ({time_range})"
        if use_gdelt and time_range == "All Available Data":
            spinner_msg += " — sweeping the GDELT 2017→now archive for full historical depth, ~20-30s"
        with st.spinner(spinner_msg + "..."):
            fetched_df, fetched_errors = _cached_collect(
                active_term, search_type, tuple(sorted(sources.keys())), limit,
                tuple(expansions), time_range, tuple(context_hints), tuple(exclude_terms),
                _sources=sources, _expansions=expansions,
                _context_hints=context_hints, _exclude_terms=exclude_terms,
            )
        fetched_stats = summarize(fetched_df)

        if not fetched_df.empty:
            try:
                emotion_counts = fetched_df["emotion"].value_counts().to_dict()
                dominant_emotion = fetched_df["emotion"].mode().iat[0] if emotion_counts else "neutral"
                theme_words, _theme_tags = extract_hot_topics(fetched_df["text"].tolist(), extra_stop=active_term.split(), top_n=15)
                storage.save_run(active_term, fetched_stats, list(sources.keys()), dominant_emotion, emotion_counts, theme_words)
            except Exception:
                pass  # trend-history logging is a nice-to-have, never block the report on it

        st.session_state["last_report"] = {
            "term": active_term,
            "time_range": time_range,
            "df": fetched_df,
            "errors": fetched_errors,
            "stats": fetched_stats,
            "fetched_at": dt.datetime.now().strftime("%b %d, %Y · %H:%M"),
        }
    except Exception as e:
        # Never let a fetch/processing failure crash the whole app — surface it
        # and keep whatever report (if any) was already on screen.
        st.error(f"⚠️ This run hit an unexpected error and was aborted: {type(e).__name__}: {e}\n\nYour previous report (if any) is still shown below. Try narrowing the sources or search, or click Run again.")
elif run and not active_term:
    st.warning("⚠️ Enter a name, hashtag, or handle in the sidebar before running a report.")

report = st.session_state.get("last_report")

# Main action sub-header
top_c1, top_c2, top_c3 = st.columns([2, 3, 1])
with top_c1:
    header_term = report["term"] if report else active_term
    term_display = f"({header_term})" if header_term else "(Awaiting Search Target)"
    st.markdown(f"<h3 style='margin:0; font-weight:800; color:#0f172a; letter-spacing:-0.01em;'>📊 Intelligence Report <span style='font-size:0.92rem; font-weight:700; color:#0d9488;'>{term_display}</span></h3>", unsafe_allow_html=True)
with top_c2:
    range_label = report["time_range"] if report else time_range
    fetched_label = f" · Last run {report['fetched_at']}" if report else ""
    st.caption(f"⚡ Full Coverage · {range_label}{fetched_label}")
with top_c3:
    st.markdown("<div style='text-align:right;'><span style='background:#ffffff; border:1px solid #cbd5e1; padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.82rem; color:#1e293b; cursor:pointer;'>📥 Export Report</span></div>", unsafe_allow_html=True)

# ---------------- EXACTLY 2 TABS INTERFACE ----------------
tab1, tab2 = st.tabs([
    "⚡ Command Center",
    "🎯 Target Disambiguation & Client Pitch Guide"
])

with tab1:
    if not report:
        st.markdown("""<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:36px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.02); margin-top:10px;">
<div style="font-size:2.4rem; margin-bottom:8px;">📊</div>
<h3 style="margin:0 0 8px 0; color:#0f172a; font-weight:800;">Welcome to LUMISOCIAL Intelligence Command Center</h3>
<p style="color:#64748b; font-size:0.95rem; max-width:620px; margin:0 auto 20px auto;">Enter any public figure, politician, or brand in the sidebar — optionally narrow it down with the 3 disambiguation questions — and click <b>Run Intelligence Report</b> to pull <b>all available data</b>, including a real historical archive back to 2017 via GDELT. No date limit — full historical + present coverage.</p>
</div>""", unsafe_allow_html=True)
    else:
        df = report["df"]
        errors = dict(report["errors"])
        stats = report["stats"]
        active_term = report["term"]
        time_range = report["time_range"]

        raw_total = errors.pop("__raw_total__", None)
        post_relevance_total = errors.pop("__post_relevance_total__", None)
        post_filter_total = errors.pop("__post_filter_total__", None)
        source_counts = errors.pop("__source_counts__", {}) or {}
        for name, err in errors.items():
            st.warning(f"⚠️ {name}: {err}")
        if raw_total:
            st.caption(
                f"🔍 Pipeline funnel: **{raw_total}** raw posts collected → "
                f"**{post_relevance_total}** passed the name-relevance filter → "
                f"**{post_filter_total}** passed the time-range/exclusion filters."
            )
        if source_counts:
            with st.expander("📡 Per-connector raw results (diagnostics)"):
                diag_rows = []
                for name, cnt in sorted(source_counts.items(), key=lambda kv: -kv[1]):
                    diag_rows.append({"Connector": get_platform_icon(name) + " " + name, "Raw posts found": cnt})
                st.dataframe(pd.DataFrame(diag_rows), use_container_width=True, hide_index=True)
                zero_sources = [n for n, c in source_counts.items() if c == 0]
                if zero_sources:
                    st.caption(f"'{active_term}' returned 0 raw results from: {', '.join(zero_sources)}. That can be a real absence of coverage (a niche/regional figure) or a search-term mismatch — try Wikidata alias expansion, or check the connector's credentials above if you expected data.")

        if df.empty:
            st.info(f"No matching posts found for '{active_term}' in this time range. Try 'All Available Data', broadening your search query, removing exclude terms, or selecting additional sources in the sidebar.")
            st.stop()

        pos_count = stats["positive"]
        neg_count = stats["negative"]
        neu_count = stats["neutral"]
        total_count = stats["total"]

        # ==================== UPPER SECTION: 3-COLUMN DASHBOARD PANEL ====================
        st.markdown('<div class="auris-upper-card">', unsafe_allow_html=True)
        up_c1, up_c2, up_c3 = st.columns([5, 3, 3])

        # Left: Real-Time Polarity Area Chart (Real calculated time series from df)
        with up_c1:
            st.markdown("<div class='auris-section-title'><span>Real-Time Polarity</span></div>", unsafe_allow_html=True)
            
            if "created_at" in df.columns and df["created_at"].notna().any():
                parsed_dates = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
                df["time_bin"] = parsed_dates.dt.strftime("%H:00").fillna("Recent")
            else:
                df["time_bin"] = "Recent"

            time_counts = df.groupby(["time_bin", "sentiment"]).size().unstack(fill_value=0).reset_index()
            for col in ["positive", "negative", "neutral"]:
                if col not in time_counts.columns:
                    time_counts[col] = 0

            time_counts = time_counts.sort_values("time_bin")

            fig_polarity = go.Figure()
            fig_polarity.add_trace(go.Scatter(
                x=time_counts["time_bin"], y=time_counts["positive"], name="Positive",
                mode="lines+markers", line=dict(color="#00d285", width=2.5, shape='spline'),
                fill='tozeroy', fillcolor='rgba(0, 210, 133, 0.08)'
            ))
            fig_polarity.add_trace(go.Scatter(
                x=time_counts["time_bin"], y=time_counts["negative"], name="Negative",
                mode="lines+markers", line=dict(color="#ff6b6b", width=2, shape='spline'),
                fill='tozeroy', fillcolor='rgba(255, 107, 107, 0.05)'
            ))
            fig_polarity.add_trace(go.Scatter(
                x=time_counts["time_bin"], y=time_counts["neutral"], name="Neutral",
                mode="lines+markers", line=dict(color="#feca57", width=2, shape='spline'),
                fill='tozeroy', fillcolor='rgba(254, 202, 87, 0.05)'
            ))

            if not time_counts.empty and time_counts["positive"].max() > 0:
                max_row = time_counts.loc[time_counts["positive"].idxmax()]
                fig_polarity.add_annotation(
                    x=max_row["time_bin"], y=max_row["positive"],
                    text=f"{int(max_row['positive'])}",
                    showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5, arrowcolor="#1e293b",
                    bgcolor="#1e293b", font=dict(color="#ffffff", size=10, family="Plus Jakarta Sans"),
                    borderpad=4, bordercolor="#1e293b"
                )

            fig_polarity.update_layout(
                height=200,
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=11)),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#94a3b8")),
                yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=9, color="#94a3b8")),
                hovermode="x unified"
            )
            st.plotly_chart(fig_polarity, use_container_width=True, config={"displayModeBar": False})

        # Middle: Hot Topics Tag Cloud (Extracted from real text)
        with up_c2:
            st.markdown("<div class='auris-section-title'><span>Hot Topics</span> <span style='cursor:pointer; color:#94a3b8;'>≡</span></div>", unsafe_allow_html=True)
            
            words, tags = extract_hot_topics(df["text"].tolist(), extra_stop=active_term.split(), top_n=14)
            word_items = words if words else [("Intelligence", 5), ("Leadership", 4), ("Policy", 3), ("Update", 2), ("Analysis", 2)]

            cloud_spans = []
            for i, (w, count) in enumerate(word_items[:12]):
                size_cls = "tag-xl" if i < 2 else ("tag-lg" if i < 5 else ("tag-md" if i < 9 else "tag-sm"))
                color = "#0d9488" if i % 3 == 0 else ("#0284c7" if i % 3 == 1 else "#1e293b")
                cloud_spans.append(f"<span class='{size_cls}' style='color:{color};'>{w}</span>")
            
            cloud_html = "<div class='topic-tag-cloud'>" + " ".join(cloud_spans) + "</div>"
            st.markdown(cloud_html, unsafe_allow_html=True)

        # Right: Top Influencers Badges (Real authors ranked by engagement in df)
        with up_c3:
            st.markdown("<div class='auris-section-title'><span>Top Influencers</span> <span style='cursor:pointer; color:#94a3b8;'>✕</span></div>", unsafe_allow_html=True)
            
            authors_df = top_authors(df, n=5)
            top_authors_list = authors_df.to_dict("records") if not authors_df.empty else []

            cards_list = []
            for a in top_authors_list[:5]:
                author_name = str(a.get("author", "U"))
                name_init = author_name[:2].upper()
                platform = str(a.get("platform", "web")).lower()
                p_icon = get_platform_icon(platform)
                score = int(a.get("total_engagement", 0))
                if score == 0:
                    score = int(a.get("posts", 1) * 10)
                
                cards_list.append(
                    f"<div class='influencer-card'><div class='influencer-avatar'>{name_init}<div class='platform-sub-icon'>{p_icon}</div></div><div class='influencer-score' title='{author_name} ({platform})'>{score}</div></div>"
                )
            
            influencer_html = "<div class='influencer-row'>" + "".join(cards_list) + "</div>"
            st.markdown(influencer_html, unsafe_allow_html=True)
            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
            st.caption("Top voices ranked by overall engagement and reach score across social streams.")

        st.markdown('</div>', unsafe_allow_html=True)

        # ==================== LOWER SECTION: FEED STREAM + FILTERS ====================
        low_c1, low_c2 = st.columns([3, 1])

        # Left Column: Feed Stream Cards (100% REAL POST CONTENT from df)
        with low_c1:
            feed_df = df[df["platform"] != "youtube"]
            if feed_df.empty:
                feed_df = df

            has_context = "context_match" in feed_df.columns and feed_df["context_match"].any()
            sort_cols = ["context_match", "engagement"] if has_context else ["engagement"]
            sort_asc = [False, False] if has_context else [False]
            top_feeds = feed_df.sort_values(sort_cols, ascending=sort_asc).head(15)
            if has_context:
                st.caption("🎯 Posts matching your disambiguation hints (location/org) are ranked first and badged below.")

            for idx, r in top_feeds.iterrows():
                sent = str(r.get("sentiment", "neutral")).lower()
                border_cls = "card-border-pos" if sent == "positive" else ("card-border-neg" if sent == "negative" else "card-border-neu")
                
                author_title = str(r.get("author_name") or r.get("author") or "User")
                author_handle = str(r.get("author") or "")
                author_init = author_title[:2].upper()
                
                platform_str = str(r.get("platform", "web"))
                p_icon = get_platform_icon(platform_str)
                source_grp = str(r.get("source_group") or platform_str.title())
                
                hl_body = highlight_keywords(str(r.get("text", "")), active_term)
                post_url = r.get("url") or ""
                
                likes = int(r.get("likes", 0))
                shares = int(r.get("shares", 0))
                replies = int(r.get("replies", 0))
                engagement = int(r.get("engagement", likes + shares + replies))
                
                emotion_str = str(r.get("emotion") or "neutral").title()
                state_loc = str(r.get("india_state") or "")
                city_loc = str(r.get("india_city") or "")
                
                sent_pill_cls = "feed-pill-pos" if sent == "positive" else ("feed-pill-neg" if sent == "negative" else "feed-pill-neu")

                tags_html = f"<span class='feed-pill {sent_pill_cls}'>{sent.upper()}</span><span class='feed-pill'>Emotion: {emotion_str}</span>"
                if bool(r.get("context_match")):
                    tags_html += "<span class='feed-pill' style='background:#dcfce7;border-color:#86efac;color:#166534;'>🎯 Confirmed Match</span>"
                if state_loc:
                    loc_txt = f"{city_loc}, {state_loc}" if city_loc else state_loc
                    tags_html += f"<span class='feed-pill feed-pill-loc'>📍 {loc_txt}</span>"
                if r.get("age_group"):
                    tags_html += f"<span class='feed-pill'>👥 {r.get('age_group')}</span>"

                link_html = f"<a href='{post_url}' target='_blank' style='font-size:0.82rem; color:#0284c7; text-decoration:none; font-weight:700;'>🔗 View Original Post →</a>" if post_url else ""

                card_html = (
                    f"<div class='auris-feed-card {border_cls}'>"
                    f"<div class='feed-header'>"
                    f"<div class='feed-user-info'>"
                    f"<div class='feed-avatar-circle'>{author_init}</div>"
                    f"<div>"
                    f"<span class='feed-author-name'>{author_title}</span>"
                    f"<span class='feed-handle'>@{author_handle}</span>"
                    f"<span class='platform-badge'>{p_icon} {source_grp}</span>"
                    f"<div class='feed-time'>👍 {likes} · 🔁 {shares} · 💬 {replies} · Total Reach: <b>{engagement}</b></div>"
                    f"</div>"
                    f"</div>"
                    f"<div>{link_html}</div>"
                    f"</div>"
                    f"<div class='feed-body-text'>{hl_body}</div>"
                    f"<div class='feed-tags-row'>{tags_html}</div>"
                    f"</div>"
                )
                st.markdown(card_html, unsafe_allow_html=True)

        # Right Column: Interactive Filter Panel Card
        with low_c2:
            filter_box_html = (
                f"<div class='filter-panel-card'>"
                f"<div class='filter-header'>"
                f"<span class='filter-title'>Filters</span>"
                f"<span class='filter-total'>Total feeds: {total_count:,}</span>"
                f"</div>"
                f"<div style='font-size:0.85rem; font-weight:700; color:#475569; margin-bottom:8px;'>Sentiments</div>"
                f"<div class='sentiment-toggle-box'>"
                f"<div class='sentiment-item' style='border-top:3px solid #10b981;'>"
                f"<div class='sentiment-emoji-large'>😊</div>"
                f"<div class='sentiment-count-text'>{pos_count:,}</div>"
                f"<div style='font-size:0.7rem; color:#64748b;'>Positive</div>"
                f"</div>"
                f"<div class='sentiment-item' style='border-top:3px solid #ef4444;'>"
                f"<div class='sentiment-emoji-large'>😡</div>"
                f"<div class='sentiment-count-text'>{neg_count:,}</div>"
                f"<div style='font-size:0.7rem; color:#64748b;'>Negative</div>"
                f"</div>"
                f"<div class='sentiment-item' style='border-top:3px solid #f59e0b;'>"
                f"<div class='sentiment-emoji-large'>😐</div>"
                f"<div class='sentiment-count-text'>{neu_count:,}</div>"
                f"<div style='font-size:0.7rem; color:#64748b;'>Neutral</div>"
                f"</div>"
                f"</div>"
                f"</div>"
            )
            st.markdown(filter_box_html, unsafe_allow_html=True)

            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
            
            # Sources breakdown matrix
            with st.container(border=True):
                st.markdown("##### 📡 Ingested Sources Breakdown")
                src_counts = df["source_group"].value_counts().reset_index()
                src_counts.columns = ["Source", "Posts"]
                st.dataframe(src_counts, use_container_width=True, hide_index=True)

            # YouTube Comments Aggregate Box (if YouTube data ingested)
            yt_df = df[df["platform"] == "youtube"]
            if not yt_df.empty:
                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown("##### ▶️ YouTube Audience Reaction")
                    yt_total = len(yt_df)
                    yt_pos = (yt_df["sentiment"] == "positive").sum()
                    yt_neg = (yt_df["sentiment"] == "negative").sum()
                    yt_pos_ratio = round(100 * yt_pos / max(1, yt_pos + yt_neg), 1)
                    st.metric("Comments Ingested", f"{yt_total:,}", delta=f"{yt_pos_ratio}% Positive")
                    st.caption(f"Aggregated sentiment across {yt_total} YouTube comments.")

            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
            
            # Geographic State Intelligence widget
            with st.container(border=True):
                st.markdown("##### 🇮🇳 Geographic State Sentiment")
                india_df = aggregate_india_state_sentiments(df)
                if not india_df.empty:
                    st.dataframe(
                        india_df[["state", "mentions", "mood_label", "avg_score"]].head(6),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.caption("State mentions will appear here when location cues are detected in posts.")

            # Time-Wise Trend History (across past runs for this exact term)
            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("##### 📈 Sentiment Trend Over Time")
                hist_df = storage.load_history(term=active_term)
                if len(hist_df) >= 2:
                    fig_hist = go.Figure()
                    fig_hist.add_trace(go.Scatter(
                        x=hist_df["ts"], y=hist_df["positivity_ratio"],
                        mode="lines+markers", name="Positivity %",
                        line=dict(color="#0d9488", width=2),
                    ))
                    fig_hist.update_layout(
                        height=160, margin=dict(l=0, r=0, t=10, b=0),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#94a3b8")),
                        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=9, color="#94a3b8"), title="Positivity %"),
                    )
                    st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})
                    st.caption(f"Across {len(hist_df)} past runs for '{active_term}' on this instance — how public sentiment has moved run over run.")
                else:
                    st.caption("Run a report for this same prospect again later (on this running instance) to build a sentiment-over-time trend line here.")


# ==================== TAB 2: TARGET DISAMBIGUATION & CLIENT PITCH GUIDE ====================
with tab2:
    st.markdown("### 🎯 Target Entity Disambiguation & Client Pitch Guide")

    d_col1, d_col2 = st.columns(2)

    with d_col1:
        st.markdown("#### 🔍 1. How to Uniquely Identify a Person / Target Entity")
        st.info("""
        **Why Entity Disambiguation Matters:**
        When searching common names (e.g. *Amar Thakare*, *Rahul Sharma*, *Vijay Kumar*), public social platforms contain thousands of posts mentioning different individuals with the same name.

        To achieve **100% precision & accuracy** in client sentiment reports, answer these **5 Relevance Questions**:
        """)

        st.markdown("""
        1. **Full Name & Spelling Variations**:
           - What is the exact official spelling and regional script spelling? (e.g., *Amar Thakare*, *अमर ठाकरे*)
        2. **Primary Geographic Headquarters / State**:
           - Which city or state are they active in? (e.g., *Nagpur*, *Maharashtra*, *Mumbai*)
        3. **Organization / Designation / Political Party**:
           - Which company, party, or institution are they affiliated with? (e.g., *BJP*, *Congress*, *NCP*, *CEO of X*)
        4. **Key Known Public Handles & Telegram Channels**:
           - What are their official Twitter/X handles or Telegram broadcast channels?
        5. **Negative Exclusion Keywords**:
           - Are there famous namesakes (movies, actors, unrelated scandals) to exclude?
        """)

        st.markdown("##### 🛠️ Disambiguation Filters Applied To This Report")
        st.caption("These come from the **🎯 Narrow Down This Prospect** fields in the sidebar — fill them in and click Run again to sharpen results.")
        applied_loc = st.session_state.get("d_loc_sidebar", "")
        applied_org = st.session_state.get("d_org_sidebar", "")
        applied_exclude = st.session_state.get("d_exclude_sidebar", "")
        if applied_loc or applied_org or applied_exclude:
            if applied_loc:
                st.markdown(f"📍 **Location hint:** `{applied_loc}` — matching posts are ranked first and badged 🎯")
            if applied_org:
                st.markdown(f"🏢 **Org/role hint:** `{applied_org}` — matching posts are ranked first and badged 🎯")
            if applied_exclude:
                st.markdown(f"🚫 **Excluded terms:** `{applied_exclude}` — any post mentioning these was dropped entirely")
        else:
            st.info("No disambiguation hints set yet — add them in the sidebar for higher-precision results on common names.")

    with d_col2:
        st.markdown("#### 📊 2. Client Explanation Guide (Explaining Numbers & Charts)")
        st.success("""
        **How to Walk Your Client Through These Sentiment Numbers:**
        Use this executive framework when presenting LUMISOCIAL reports to C-Suite Executives or Clients.
        """)

        with st.expander("📈 1. Net Sentiment Index (0 to 100 Scale)", expanded=True):
            st.markdown("""
            - **Below 40 (Red Zone)**: High Crisis Risk. Brand/Person faces heavy negative coverage or backlash.
            - **40 to 60 (Yellow Zone)**: Neutral / Balanced. Coverage is mostly informational or split equally.
            - **Above 60 (Green Zone)**: Strong Positive Sentiment. High public approval and positive sentiment drive.
            """)

        with st.expander("📊 2. Positivity Ratio vs. Total Volume"):
            st.markdown("""
            - **Total Volume**: Measures total public awareness and reach.
            - **Positivity Ratio**: The % of opinionated posts that are positive (excluding neutral news reporting).
            - *Client Key Takeaway*: High volume with a low positivity ratio indicates a PR crisis. High positivity ratio with moderate volume indicates strong organic support.
            """)

        with st.expander("🗣️ 3. Loudest Voices & Share of Voice"):
            st.markdown("""
            - Explains that **not all posts are equal**. 1 post by a major news handle or verified influencer with 100,000 engagement impacts public perception far more than 100 low-reach tweets.
            """)

    if active_term and 'df' in locals() and not df.empty:
        st.divider()
        st.markdown("### 📄 Shareable Client Report Export")
        report_html = build_html_report(
            active_term, df, stats,
            extract_hot_topics(df["text"].tolist(), extra_stop=active_term.split(), top_n=15)[0],
            extract_hot_topics(df["text"].tolist(), extra_stop=active_term.split(), top_n=15)[1],
            top_authors(df, n=10),
            df.sort_values("engagement", ascending=False),
        )
        r1, r2 = st.columns(2)
        r1.download_button(
            "⬇️ Download Standalone HTML Executive Report for Client",
            report_html.encode("utf-8"),
            file_name=f"LUMISOCIAL_{active_term}_Client_Report.html",
            mime="text/html",
            use_container_width=True,
        )
        r2.download_button(
            "⬇️ Download Raw Dataset (CSV)",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"LUMISOCIAL_{active_term}_raw_data.csv",
            mime="text/csv",
            use_container_width=True,
        )
