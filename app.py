"""
LUMISOCIAL — Socioboard Dashboard & Social Intelligence Command Center

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

# App DB and core storage imports
import storage
import sentiment
import emotion as emotion_engine
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

# Import helper integrations
from social_analyzer_helper import verify_profile_username, analyze_name
from remediation import REMEDIATION_SCENARIOS, simulate_remediation

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

# Streamlit secrets mirroring
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and not os.environ.get(_k):
            os.environ[_k] = _v
except Exception:
    pass

st.set_page_config(
    page_title="LUMISOCIAL | Executive Command Center",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Initialize storage DB
storage.init_db()

# Custom Socioboard-Style CSS design properties
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

    :root {
        --bg: #0f172a;
        --surface: #1e293b;
        --surface-2: #334155;
        --border: #38455a;
        --border-soft: #475569;
        --text: #f8fafc;
        --text-2: #cbd5e1;
        --text-mute: #94a3b8;
        --accent: #0d9488;
        --accent-dark: #0f766e;
        --accent-light: #ccfbf1;
        --accent-glow: rgba(13, 148, 136, 0.25);
        --pos: #10b981;
        --pos-bg: rgba(16, 185, 129, 0.1);
        --pos-border: #059669;
        --neg: #ef4444;
        --neg-bg: rgba(239, 68, 68, 0.1);
        --neg-border: #dc2626;
        --neu: #f59e0b;
        --neu-bg: rgba(245, 158, 11, 0.1);
        --neu-border: #d97706;
        --info: #0284c7;
        --info-bg: rgba(2, 132, 199, 0.1);
        --r-sm: 8px;
        --r-md: 12px;
        --r-lg: 16px;
        --shadow-1: 0 4px 10px rgba(0,0,0,0.3);
        --shadow-2: 0 10px 25px rgba(0,0,0,0.5);
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-2);
        background-color: var(--bg);
    }

    .stApp { background-color: var(--bg); }

    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* ============ Sidebar Design ============ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b0f19 0%, #111827 60%, #0d111d 100%) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #cbd5e1 !important;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.08) !important; }

    /* ============ Socioboard-style dashboard cards ============ */
    .socio-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-md);
        padding: 16px 20px;
        box-shadow: var(--shadow-1);
        margin-bottom: 16px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .socio-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-2);
        border-color: var(--accent);
    }

    .card-border-pos { border-left: 5px solid var(--pos); }
    .card-border-neg { border-left: 5px solid var(--neg); }
    .card-border-neu { border-left: 5px solid var(--neu); }

    /* ============ Login Screen Layout ============ */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 75vh;
        position: relative;
    }
    .login-bg-glow-1 {
        position: absolute;
        width: 250px;
        height: 250px;
        border-radius: 50%;
        background: radial-gradient(circle, var(--accent) 0%, rgba(13, 148, 136, 0) 70%);
        top: -20px;
        left: -40px;
        opacity: 0.25;
        filter: blur(60px);
        animation: floatNebula1 12s infinite alternate ease-in-out;
        z-index: 1;
    }
    .login-bg-glow-2 {
        position: absolute;
        width: 320px;
        height: 320px;
        border-radius: 50%;
        background: radial-gradient(circle, var(--info) 0%, rgba(2, 132, 199, 0) 70%);
        bottom: -40px;
        right: -60px;
        opacity: 0.22;
        filter: blur(80px);
        animation: floatNebula2 16s infinite alternate ease-in-out;
        z-index: 1;
    }
    @keyframes floatNebula1 {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(30px, 20px) scale(1.1); }
    }
    @keyframes floatNebula2 {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(-40px, -15px) scale(1.05); }
    }
    div[data-testid="stForm"] {
        background: rgba(30, 41, 59, 0.45) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 4px solid var(--accent) !important;
        border-radius: var(--r-lg) !important;
        padding: 45px 35px !important;
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5) !important;
        backdrop-filter: blur(25px) !important;
        max-width: 460px !important;
        width: 100%;
        margin: 0 auto !important;
        position: relative;
        z-index: 10;
    }
    div[data-testid="stForm"] label {
        color: #e2e8f0 !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 8px !important;
    }
    /* Style input elements and wrapper divs in Streamlit */
    div[data-testid="stForm"] input[type="text"],
    div[data-testid="stForm"] input[type="password"],
    div[data-testid="stForm"] div[data-testid="stTextInput"] > div,
    div[data-testid="stForm"] [data-testid="stTextInputRootElement"],
    div[data-testid="stForm"] [data-baseweb="input"],
    div[data-testid="stForm"] [data-baseweb="base-input"] {
        background-color: rgba(15, 23, 42, 0.7) !important;
        border: 1px solid var(--border) !important;
        color: #ffffff !important;
        border-radius: var(--r-sm) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: border-color 0.25s, box-shadow 0.25s !important;
    }
    div[data-testid="stForm"] input[type="text"]:focus,
    div[data-testid="stForm"] input[type="password"]:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
    }
    /* Streamlit forms submit button styling */
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        border: none !important;
        border-radius: var(--r-sm) !important;
        padding: 14px 20px !important;
        box-shadow: 0 4px 15px rgba(13, 148, 136, 0.3) !important;
        transition: transform 0.15s, box-shadow 0.15s, background 0.15s !important;
        width: 100% !important;
        cursor: pointer !important;
        margin-top: 15px !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(13, 148, 136, 0.45) !important;
        background: linear-gradient(135deg, #14b8a6 0%, var(--accent) 100%) !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button p {
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
    }

    /* ============ Active Connection Grid ============ */
    .connector-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
    }
    .connector-item {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid var(--border);
        border-radius: var(--r-sm);
        padding: 10px;
        text-align: center;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .connector-item.active {
        border-color: var(--pos);
        background: rgba(16, 185, 129, 0.05);
    }
    .connector-item.inactive {
        border-color: var(--neg);
        background: rgba(239, 68, 68, 0.05);
    }
    .connector-item.pending {
        border-color: var(--neu);
        background: rgba(245, 158, 11, 0.05);
    }

    /* ============ Profile suggestions ============ */
    .profile-suggestion-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid var(--border);
        border-radius: var(--r-sm);
        padding: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .profile-info {
        display: flex;
        flex-direction: column;
    }
    .profile-title {
        font-weight: 700;
        color: white;
        font-size: 0.9rem;
    }
    .profile-link {
        font-size: 0.75rem;
        color: var(--accent);
        text-decoration: none;
    }

    /* ============ Word Cloud / Hot Topics ============ */
    .topic-tag-cloud {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        min-height: 120px;
        align-items: center;
        padding: 10px 0;
    }
    .tag-xl { font-size: 1.3rem; font-weight: 800; color: #ffffff; }
    .tag-lg { font-size: 1.1rem; font-weight: 700; color: var(--text); }
    .tag-md { font-size: 0.95rem; font-weight: 600; color: var(--text-2); }
    .tag-sm { font-size: 0.8rem; font-weight: 500; color: var(--text-mute); }

    /* ============ Influencer Row ============ */
    .influencer-row {
        display: flex;
        gap: 12px;
        margin-top: 10px;
        flex-wrap: wrap;
    }
    .influencer-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--accent), var(--info));
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        color: white;
        position: relative;
    }
    .platform-sub-icon {
        position: absolute;
        bottom: -2px;
        right: -2px;
        background: var(--bg);
        border-radius: 50%;
        width: 14px;
        height: 14px;
        font-size: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* ============ Highlight Keywords ============ */
    .highlight-kw {
        background-color: rgba(13, 148, 136, 0.3);
        color: #2dd4bf;
        padding: 1px 4px;
        border-radius: 4px;
        font-weight: 700;
    }

    /* ============ Tabs / Buttons styling ============ */
    .stButton > button {
        border-radius: var(--r-sm) !important;
        font-weight: 700 !important;
        transition: background-color 0.1s ease, transform 0.1s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE AUTHENTICATION GATING -----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "ANALYST"

if not st.session_state["authenticated"]:
    # Render background glowing nebulas
    st.markdown("""
    <div class="login-bg-glow-1"></div>
    <div class="login-bg-glow-2"></div>
    """, unsafe_allow_html=True)
    
    # Render premium glassmorphic login page
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    col_l, col_login, col_r = st.columns([1, 2, 1])
    with col_login:
        with st.form("login_form"):
            st.markdown("""
            <div style="text-align:center; margin-bottom: 25px;">
                <span style="font-size:2.5rem; filter: drop-shadow(0 0 10px var(--accent-glow));">⚡</span>
                <h2 style="font-size:2.1rem; font-weight:900; color:white; margin:10px 0 6px 0; letter-spacing:-0.03em; background:linear-gradient(135deg, #ffffff 30%, #a5f3fc 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">LUMISOCIAL</h2>
                <div style="font-size:0.92rem; color:#94a3b8; font-weight:500;">Executive Command Center & Social Intelligence Platform</div>
            </div>
            """, unsafe_allow_html=True)
            
            email = st.text_input("Corporate Email", placeholder="e.g. analyst@company.com")
            password = st.text_input("Access Password", type="password", placeholder="••••••••")
            login_btn = st.form_submit_button("Enter Command Center", use_container_width=True)
            
            if login_btn:
                user = storage.verify_user(email, password)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = user["email"]
                    st.session_state["user_role"] = user["role"]
                    st.toast(f"Success: Logged in as {user['role']}")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please verify your email and access keys.")
                    
        st.markdown("""
        <div style="text-align:center; margin-top:20px; font-size:0.8rem; color:#64748b; position:relative; z-index:10;">
            <b>Default Admin Sandbox Access:</b><br/>
            Email: <code style="color:#2dd4bf; background:rgba(0,0,0,0.2); padding:2px 6px; border-radius:4px;">admin@lumisocial.com</code> &nbsp;|&nbsp; Password: <code style="color:#2dd4bf; background:rgba(0,0,0,0.2); padding:2px 6px; border-radius:4px;">admin123</code>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ----------------- SESSION AUTHENTICATED: RENDER SOCIOBOARD LAYOUT -----------------

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


def highlight_keywords(text, term):
    if not text or not term:
        return text
    words = [w for w in re.split(r"\W+", term) if len(w) > 2]
    if not words:
        words = [term.strip()]
    pattern = re.compile(r"(\b" + r"|\b".join(re.escape(w) for w in words) + r")", re.IGNORECASE)
    return pattern.sub(r"<mark class='highlight-kw'>\1</mark>", text)


def _credential_issue(name):
    if name == "reddit" and not (os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET")):
        return "Missing Credentials"
    if name == "youtube" and not os.environ.get("YOUTUBE_API_KEY"):
        return "Missing Credentials"
    if name == "telegram":
        api_id = (os.environ.get("TELEGRAM_API_ID") or "").strip()
        api_hash = (os.environ.get("TELEGRAM_API_HASH") or "").strip()
        if not api_id or not api_hash or not api_id.isdigit():
            return "Missing Credentials"
    if name == "twitter" and not os.environ.get("TWITTER_BEARER_TOKEN"):
        return "Missing Credentials"
    return None


@st.cache_data(ttl=900, show_spinner=False)
def _cached_collect(term, search_type, source_names, limit, expansions_key, time_range,
                     context_key, exclude_key, _sources, _expansions, _context_hints, _exclude_terms):
    return collect(term, search_type, _sources, limit=limit, expansions=_expansions,
                    time_range=time_range, context_hints=_context_hints, exclude_terms=_exclude_terms)


# ----------------- SIDEBAR MENU NAVIGATION (Socioboard Pattern) -----------------
with st.sidebar:
    st.markdown("""<div style="padding:4px 0 14px 0; border-bottom:1px solid rgba(255,255,255,0.08); margin-bottom:12px;">
<div style="font-size:1.4rem; font-weight:800; letter-spacing:-0.5px; color:#ffffff;">⚡ LUMISOCIAL</div>
<div style="font-size:0.75rem; color:#94a3b8;">Socioboard social intelligence module</div>
</div>""", unsafe_allow_html=True)
    
    # User Profile card
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.06); padding:10px; border-radius:8px; margin-bottom:15px;">
        <div style="font-size:0.8rem; font-weight:700; color:#ffffff;">👤 {st.session_state["user_email"]}</div>
        <div style="font-size:0.7rem; color:#2dd4bf; text-transform:uppercase; font-weight:600; margin-top:2px;">Role: {st.session_state["user_role"]}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Logout Button
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = None
        st.session_state["user_role"] = "ANALYST"
        st.toast("Logged out successfully.")
        st.rerun()

# ----------------- LANGUAGE CLASSIFIER HELPER -----------------
def get_clean_lang(row):
    lang_code = row.get("lang") or ""
    if isinstance(lang_code, str):
        lang_code = lang_code.lower().strip()
    
    code_map = {
        "en": "English",
        "mr": "Marathi",
        "hi": "Hindi",
        "te": "Telugu",
        "ta": "Tamil",
        "ml": "Malayalam",
        "bn": "Bengali",
        "gu": "Gujarati",
        "kn": "Kannada",
        "pa": "Punjabi",
    }
    if lang_code in code_map:
        return code_map[lang_code]
        
    # Estimate language from text
    t_val = row.get("text")
    s_val = row.get("summary")
    
    # Handle pandas NaN (which is a float unequal to itself) and None safely
    t_str = "" if (t_val is None or (isinstance(t_val, float) and t_val != t_val)) else str(t_val)
    s_str = "" if (s_val is None or (isinstance(s_val, float) and s_val != s_val)) else str(s_val)
    
    text = (t_str + " " + s_str).strip()
    text_lower = text.lower()
    
    # Devanagari Script (Marathi & Hindi)
    import re
    if re.search(r'[\u0900-\u097F]', text):
        marathi_words = ["आहे", "करून", "झाले", "मराठी", "निवडणूक", "महाराष्ट्र", "त्यांनी", "होता"]
        if any(w in text_lower for w in marathi_words):
            return "Marathi"
        return "Hindi"
        
    # Telugu
    if re.search(r'[\u0c00-\u0c7f]', text):
        return "Telugu"
        
    # Tamil
    if re.search(r'[\u0b80-\u0bff]', text):
        return "Tamil"
        
    return "English"


# ==================== OPERATIONS PANEL DESK ====================
phase_options = [
    "📥 Phase 1: Ingested Feeds",
    "📊 Phase 2: Sentiment & Topic Analysis",
    "🤖 Phase 3: Crisis Remediation Desk",
    "⚙️ Phase 4: Command Center Administration"
]

if "dashboard_phase" not in st.session_state:
    st.session_state["dashboard_phase"] = phase_options[0]
    
if st.session_state["dashboard_phase"] not in phase_options:
    st.session_state["dashboard_phase"] = phase_options[0]
    
phase_idx = phase_options.index(st.session_state["dashboard_phase"])
selected_phase = st.radio("Operations Phase Select", phase_options, index=phase_idx, horizontal=True, label_visibility="collapsed")
st.session_state["dashboard_phase"] = selected_phase
st.divider()

# Load targets globally
targets = storage.list_targets()
target_names = [t["name"] for t in targets]

if selected_phase in ["📥 Phase 1: Ingested Feeds", "📊 Phase 2: Sentiment & Topic Analysis", "🤖 Phase 3: Crisis Remediation Desk"]:
    st.markdown("#### 🔍 Social Ingestion & Listening Engine")
    
    # Query builder selection
    q_col1, q_col2 = st.columns([2, 1])
    
    with q_col1:
        use_custom = st.checkbox("🔍 Perform custom query on-the-fly (bypass tracked targets)")
        
        if use_custom or not target_names:
            term = st.text_input("Search Name / Keyword", placeholder="e.g. Narendra Modi, Amar Thakare, #AI")
            exclude_input = st.text_input("Exclude keywords (comma-separated)", placeholder="e.g. actor, cricketer")
            loc_input = st.text_input("Location focus (state/city)", placeholder="e.g. Maharashtra")
            org_input = st.text_input("Affiliated organization", placeholder="e.g. BJP")
            search_type_lbl = st.radio("Search Type", ["Name or keyword", "#hashtag", "@username mentions"], horizontal=True)
        else:
            selected_t_name = st.selectbox("Select Monitored Target Profile", target_names)
            selected_t = next(t for t in targets if t["name"] == selected_t_name)
            
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); padding:12px; border-radius:8px; text-align:left;">
                <b>Keywords:</b> <code style="color:#2dd4bf;">{selected_t['keywords']}</code><br/>
                <b>Excluded:</b> <code style="color:#f87171;">{selected_t['excluded_keywords'] or 'None'}</code><br/>
                <b>Contexts:</b> 📍 {selected_t['location_hint'] or 'None'} &nbsp;|&nbsp; 🏢 {selected_t['org_hint'] or 'None'}
            </div>
            """, unsafe_allow_html=True)
            
            term = selected_t["name"]
            exclude_input = selected_t["excluded_keywords"]
            loc_input = selected_t["location_hint"]
            org_input = selected_t["org_hint"]
            search_type_lbl = "Name or keyword"
            
    with q_col2:
        time_range = st.selectbox("📅 Time Scope", ["All Available Data", "Past 1 Month", "Past 1 Week", "Past 24 Hours"], index=0)
        limit = st.slider("Max Posts per Connector", 10, 200, 100, step=10)
        use_expand = st.checkbox("🔎 Expand aliases via Wikidata", value=False)
        
    st.divider()
    
    # Active connectors options
    st.markdown("##### Selected Sources")
    c_btn1, c_btn2, c_btn3, c_btn4, c_btn5 = st.columns(5)
    with c_btn1:
        use_rss = st.checkbox("📰 Indian Newspapers", value=True)
        use_telegram = st.checkbox("💬 Telegram Channels", value=True)
    with c_btn2:
        use_twitter = st.checkbox("🐦 Twitter / X API", value=True)
        use_news = st.checkbox("🌐 Google News", value=True)
    with c_btn3:
        use_gdelt = st.checkbox("🗄️ GDELT Historical", value=True)
        use_bsky = st.checkbox("🦋 Bluesky", value=True)
    with c_btn4:
        use_reddit = st.checkbox("🤖 Reddit API", value=True)
        use_youtube = st.checkbox("▶️ YouTube Comments", value=True)
    with c_btn5:
        use_mastodon = st.checkbox("🐘 Mastodon", value=False)
        use_hn = st.checkbox("🟠 Hacker News", value=False)
        
    run_btn = st.button("🚀 Run Social Ingestion Scan", type="primary", use_container_width=True)
    
    # Render quick connectors status cards
    st.markdown("#### 📡 Connected Channels Status Grid")
    
    connector_status = {}
    for conn in ["reddit", "youtube", "telegram", "twitter"]:
        issue = _credential_issue(conn)
        connector_status[conn] = "inactive" if issue else "active"
        
    # Standard APIs (Always available for free)
    connector_status["bluesky"] = "active"
    connector_status["news"] = "active"
    connector_status["indian_news"] = "active"
    connector_status["gdelt"] = "active"
    
    grid_html = '<div class="connector-grid">'
    for name, status in connector_status.items():
        icon = get_platform_icon(name)
        status_lbl = "Active" if status == "active" else "Missing Key"
        cls = "active" if status == "active" else "inactive"
        grid_html += f'<div class="connector-item {cls}"><b>{icon} {name.title()}</b><br/><span style="font-size:0.65rem; opacity:0.8;">{status_lbl}</span></div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)
    st.divider()

    # Ingestion sources dictionary configuration
    sources = {}
    if use_rss:
        sources["indian_news"] = lambda q, n: search_indian_newspapers(q, n)
    if use_bsky:
        sources["bluesky"] = search_bluesky
    if use_reddit and connector_status["reddit"] == "active":
        sources["reddit"] = lambda q, n: search_reddit(q, n)
    if use_youtube and connector_status["youtube"] == "active":
        sources["youtube"] = lambda q, n: search_youtube(q, n)
    if use_twitter and connector_status["twitter"] == "active":
        sources["twitter"] = lambda q, n: search_twitter(q, n)
    if use_mastodon:
        sources["mastodon"] = lambda q, n: search_mastodon(q, n)
    if use_hn:
        sources["hackernews"] = lambda q, n: search_hackernews(q, n)
    if use_news:
        sources["news"] = lambda q, n: search_news(q, n, country="IN", lang="en")
    if use_gdelt:
        sources["gdelt"] = lambda q, n: search_gdelt(q, n, time_range=time_range)
    if use_telegram and connector_status["telegram"] == "active":
        sources["telegram"] = lambda q, n: search_telegram(q, n, channels=DEFAULT_INDIA_CHANNELS)
        
    active_term = term.strip()
    
    if run_btn and active_term:
        try:
            _TYPE_MAP = {"Name or keyword": "keyword", "#hashtag": "hashtag", "@username mentions": "handle"}
            search_type = _TYPE_MAP.get(search_type_lbl, "keyword")
            expansions = expand_keywords(active_term, search_type) if use_expand else []
            context_hints = [h for h in (loc_input, org_input) if h and h.strip()]
            exclude_terms = [t.strip() for t in exclude_input.split(",") if t.strip()]
            
            with st.spinner(f"Scanning public feeds for '{active_term}'..."):
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
                    pass
                    
            st.session_state["last_report"] = {
                "term": active_term,
                "time_range": time_range,
                "df": fetched_df,
                "errors": fetched_errors,
                "stats": fetched_stats,
                "fetched_at": dt.datetime.now().strftime("%b %d, %Y · %H:%M"),
            }
        except Exception as e:
            st.error(f"Scan aborted due to execution error: {type(e).__name__}: {e}")
            
    # Render report results if available
    report = st.session_state.get("last_report")
    if report:
        df = report["df"]
        stats = report["stats"]
        errors = report["errors"]
        
        st.subheader(f"📊 Social Intelligence for '{report['term']}' ({report['time_range']})")
        st.caption(f"Last scan completed on {report['fetched_at']}")
        
        if df.empty:
            st.warning("No matches found. Try broadening the search keywords or adding alternative spellings.")
        else:
            # Map/estimate clean languages
            df["clean_lang"] = df.apply(get_clean_lang, axis=1)
            
            pos_cnt = stats["positive"]
            neg_cnt = stats["negative"]
            neu_cnt = stats["neutral"]
            total_cnt = stats["total"]
            positivity = stats["positivity_ratio"]
            avg_score = stats["avg_score"]
            
            if selected_phase == "📥 Phase 1: Ingested Feeds":
                st.markdown("#### 📬 Ingested Social & News Streams")
                
                feed_tab1, feed_tab2 = st.tabs(["📱 Social Media Feeds", "📰 News & Press Feeds"])
                
                with feed_tab1:
                    # Filter Social Media sources
                    social_platforms = ["twitter", "telegram", "reddit", "bluesky", "youtube", "mastodon", "hackernews"]
                    social_df = df[df["platform"].isin(social_platforms)].sort_values("engagement", ascending=False)
                    
                    if social_df.empty:
                        st.info("No social media mentions matching search criteria.")
                    else:
                        for idx, r in social_df.head(15).iterrows():
                            sent = str(r.get("sentiment", "neutral")).lower()
                            border_cls = "card-border-pos" if sent == "positive" else ("card-border-neg" if sent == "negative" else "card-border-neu")
                            author_title = str(r.get("author_name") or r.get("author") or "User")
                            author_handle = str(r.get("author") or "")
                            platform_str = str(r.get("platform", "web"))
                            p_icon = get_platform_icon(platform_str)
                            hl_body = highlight_keywords(str(r.get("text", "")), report["term"])
                            likes = int(r.get("likes", 0))
                            post_url = r.get("url") or ""
                            
                            tags_html = f"<span style='background:rgba(255,255,255,0.06); border:1px solid var(--border); padding:2px 8px; border-radius:12px; font-size:0.7rem; font-weight:700;'>{sent.upper()}</span>"
                            if r.get("india_state"):
                                tags_html += f" &nbsp;<span style='background:var(--info-bg); border:1px solid #0284c7; padding:2px 8px; border-radius:12px; font-size:0.7rem; color:#bae6fd;'>📍 {r['india_state']}</span>"
                            
                            card_content = f"""
                            <div class="socio-card {border_cls}" style="text-align:left;">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                    <div style="font-weight:700; color:white; font-size:0.9rem;">
                                        {p_icon} {author_title} <span style="color:var(--text-mute); font-weight:500; font-size:0.8rem;">@{author_handle}</span>
                                    </div>
                                    <div style="font-size:0.75rem; color:var(--text-mute);">Likes/Engage: {likes}</div>
                                </div>
                                <div style="font-size:0.88rem; line-height:1.5; color:var(--text-2); margin-bottom:8px;">{hl_body}</div>
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div>{tags_html}</div>
                                    {f'<span style="font-size:0.75rem; color:var(--accent); font-weight:700;">🔗 Redirect to Post →</span>' if post_url else ''}
                                </div>
                            </div>
                            """
                            if post_url:
                                st.markdown(f'<a href="{post_url}" target="_blank" style="text-decoration:none; color:inherit;">{card_content}</a>', unsafe_allow_html=True)
                            else:
                                st.markdown(card_content, unsafe_allow_html=True)
                                
                with feed_tab2:
                    # Filter News & Press sources
                    news_platforms = ["indian_news", "news", "gdelt"]
                    news_df = df[df["platform"].isin(news_platforms)].sort_values("engagement", ascending=False)
                    
                    if news_df.empty:
                        st.info("No news publications or press archives matching search criteria.")
                    else:
                        f_col1, f_col2 = st.columns(2)
                        with f_col1:
                            lang_options = ["All Languages"] + sorted(list(news_df["clean_lang"].dropna().unique()))
                            selected_lang = st.selectbox("Language Filter", lang_options, key="news_lang_filter")
                        with f_col2:
                            state_options = ["All Regions"] + sorted(list(news_df["india_state"].dropna().unique()))
                            selected_state = st.selectbox("State/Region Filter", state_options, key="news_state_filter")
                        
                        filtered_news_df = news_df.copy()
                        if selected_lang != "All Languages":
                            filtered_news_df = filtered_news_df[filtered_news_df["clean_lang"] == selected_lang]
                        if selected_state != "All Regions":
                            filtered_news_df = filtered_news_df[filtered_news_df["india_state"] == selected_state]
                            
                        if filtered_news_df.empty:
                            st.info("No news matches the selected language or region filters.")
                        else:
                            for idx, r in filtered_news_df.head(15).iterrows():
                                sent = str(r.get("sentiment", "neutral")).lower()
                                border_cls = "card-border-pos" if sent == "positive" else ("card-border-neg" if sent == "negative" else "card-border-neu")
                                author_title = str(r.get("author_name") or r.get("author") or "News Outlet")
                                platform_str = str(r.get("platform", "news"))
                                p_icon = get_platform_icon(platform_str)
                                hl_body = highlight_keywords(str(r.get("text", "")), report["term"])
                                post_url = r.get("url") or ""
                                
                                tags_html = f"<span style='background:rgba(255,255,255,0.06); border:1px solid var(--border); padding:2px 8px; border-radius:12px; font-size:0.7rem; font-weight:700;'>{sent.upper()}</span>"
                                tags_html += f" &nbsp;<span style='background:rgba(0,0,0,0.2); padding:2px 8px; border-radius:12px; font-size:0.7rem; color:#38bdf8;'>🗣️ {r.get('clean_lang','English')}</span>"
                                if r.get("india_state"):
                                    tags_html += f" &nbsp;<span style='background:var(--info-bg); border:1px solid #0284c7; padding:2px 8px; border-radius:12px; font-size:0.7rem; color:#bae6fd;'>📍 {r['india_state']}</span>"
                                
                                card_content = f"""
                                <div class="socio-card {border_cls}" style="text-align:left;">
                                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                        <div style="font-weight:700; color:white; font-size:0.9rem;">
                                            {p_icon} {author_title}
                                        </div>
                                        <span style="font-size:0.75rem; color:var(--text-mute);">News Publication</span>
                                    </div>
                                    <div style="font-size:0.95rem; font-weight:700; line-height:1.4; color:white; margin-bottom:6px;">{hl_body}</div>
                                    {f'<div style="font-size:0.82rem; color:#cbd5e1; margin-bottom:10px;">{r.get("summary","")}</div>' if r.get("summary") else ''}
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div>{tags_html}</div>
                                        {f'<span style="font-size:0.75rem; color:var(--accent); font-weight:700;">🔗 Read Article →</span>' if post_url else ''}
                                    </div>
                                </div>
                                """
                                if post_url:
                                    st.markdown(f'<a href="{post_url}" target="_blank" style="text-decoration:none; color:inherit;">{card_content}</a>', unsafe_allow_html=True)
                                else:
                                    st.markdown(card_content, unsafe_allow_html=True)
                                    
            elif selected_phase == "📊 Phase 2: Sentiment & Topic Analysis":
                st.markdown("#### 📈 Deep Sentiment & Hot Topics Analysis")
                
                # Render polarity metrics row
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                with m_col1:
                    st.markdown(f"""
                    <div class="socio-card" style="border-top: 4px solid var(--accent); text-align:left;">
                        <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Total Ingested Mentions</div>
                        <div style="font-size:1.8rem; font-weight:800; color:white; margin-top:5px;">{total_cnt:,}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m_col2:
                    border_color = "var(--pos)" if positivity and positivity > 50 else "var(--neg)"
                    ratio_str = f"{positivity}%" if positivity is not None else "N/A"
                    st.markdown(f"""
                    <div class="socio-card" style="border-top: 4px solid {border_color}; text-align:left;">
                        <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Positivity Index</div>
                        <div style="font-size:1.8rem; font-weight:800; color:white; margin-top:5px;">{ratio_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m_col3:
                    st.markdown(f"""
                    <div class="socio-card" style="border-top: 4px solid var(--pos); text-align:left;">
                        <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Positive / Negative</div>
                        <div style="font-size:1.4rem; font-weight:800; color:white; margin-top:5px;">🟢 {pos_cnt} &nbsp;|&nbsp; 🔴 {neg_cnt}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m_col4:
                    st.markdown(f"""
                    <div class="socio-card" style="border-top: 4px solid var(--neu); text-align:left;">
                        <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Average Compound Score</div>
                        <div style="font-size:1.8rem; font-weight:800; color:white; margin-top:5px;">{avg_score}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                # Chart breakdown
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    st.markdown('<div class="socio-card">', unsafe_allow_html=True)
                    st.markdown("<b>Real-Time Polarity Stream</b>", unsafe_allow_html=True)
                    
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
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=time_counts["time_bin"], y=time_counts["positive"], name="Pos", line=dict(color="#10b981", width=2)))
                    fig.add_trace(go.Scatter(x=time_counts["time_bin"], y=time_counts["negative"], name="Neg", line=dict(color="#ef4444", width=2)))
                    fig.update_layout(height=180, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#334155"))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                with c_col2:
                    st.markdown('<div class="socio-card">', unsafe_allow_html=True)
                    st.markdown("<b>Hot Topics & Keywords Cloud</b>", unsafe_allow_html=True)
                    
                    words, tags = extract_hot_topics(df["text"].tolist(), extra_stop=report["term"].split(), top_n=15)
                    word_items = words if words else [("Engagement", 5), ("Public", 4), ("Statement", 3)]
                    
                    cloud_spans = []
                    for i, (w, count) in enumerate(word_items[:12]):
                        size_cls = "tag-xl" if i < 2 else ("tag-lg" if i < 5 else ("tag-md" if i < 9 else "tag-sm"))
                        cloud_spans.append(f"<span class='{size_cls}'>{w}</span>")
                        
                    st.markdown("<div class='topic-tag-cloud'>" + " ".join(cloud_spans) + "</div>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                # Hot Topics Remediation Matrix
                st.markdown("#### 🎯 Hot Topics Strategic Remediation Matrix")
                st.caption("Analyzes the sentiments of public opinion on trending topics, targets remediation strategies to demographics/locations, and estimates impact lift.")
                
                matrix_html = """
                <table style="width:100%; border-collapse:collapse; background:rgba(30,41,59,0.3); border:1px solid rgba(255,255,255,0.08); border-radius:8px; overflow:hidden; margin-bottom:20px;">
                    <thead>
                        <tr style="background:rgba(15,23,42,0.6); border-bottom:1px solid rgba(255,255,255,0.08); text-align:left; color:#94a3b8; font-size:0.75rem; text-transform:uppercase;">
                            <th style="padding:12px;">Topic / Issue</th>
                            <th style="padding:12px;">Volume</th>
                            <th style="padding:12px;">Sentiment Profile</th>
                            <th style="padding:12px;">Dominant Age Group</th>
                            <th style="padding:12px;">Top Location</th>
                            <th style="padding:12px;">Remediation Action Plan</th>
                            <th style="padding:12px;">Est. Impact Lift</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                active_warnings = []
                for idx_t, (w, count) in enumerate(word_items[:5]):
                    topic_df = df[df["text"].str.contains(w, case=False, na=False)]
                    if topic_df.empty:
                        continue
                    
                    total = len(topic_df)
                    pos_pct = int((topic_df["sentiment"] == "positive").sum() / total * 100)
                    neg_pct = int((topic_df["sentiment"] == "negative").sum() / total * 100)
                    neu_pct = 100 - pos_pct - neg_pct
                    
                    valid_ages = topic_df["age_group"].dropna()
                    age_grp = valid_ages.mode().iat[0] if not valid_ages.empty else "All Ages"
                    
                    valid_states = topic_df["india_state"].dropna()
                    state_loc = valid_states.mode().iat[0] if not valid_states.empty else "National / Global"
                    
                    if neg_pct > 40:
                        if state_loc not in ["National", "National / Global"]:
                            sc_key = "local_issue"
                            action_desc = "📍 Geo-Fenced Local PR Clarification"
                            lift_desc = "🟢 +25% Positivity Lift"
                        elif "18-24" in age_grp or "25-34" in age_grp:
                            sc_key = "policy_backlash"
                            action_desc = "📱 Digital Youth Counter-Campaign"
                            lift_desc = "🟢 +18% Positivity Lift"
                        else:
                            sc_key = "fake_news"
                            action_desc = "📰 Counter-Narrative Fact Sheet Release"
                            lift_desc = "🟢 +15% Positivity Lift"
                        active_warnings.append((w, neg_pct, age_grp, state_loc, sc_key))
                    else:
                        sc_key = None
                        action_desc = "🛡️ Ongoing Listening (Sentiment Stable)"
                        lift_desc = "Stable"
                        
                    sent_bar = f"""
                    <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; width:120px; background:#475569; margin-bottom:4px;">
                        <div style="width:{pos_pct}%; background:#10b981;"></div>
                        <div style="width:{neu_pct}%; background:#64748b;"></div>
                        <div style="width:{neg_pct}%; background:#ef4444;"></div>
                    </div>
                    <span style="font-size:0.7rem; color:var(--text-mute);">🟢 {pos_pct}% &nbsp;|&nbsp; 🔴 {neg_pct}%</span>
                    """
                    
                    row_html = f"""
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.05); font-size:0.82rem; color:#e2e8f0;">
                        <td style="padding:12px; font-weight:700; color:#38bdf8;">🔥 {w}</td>
                        <td style="padding:12px; font-weight:600;">{total} mentions</td>
                        <td style="padding:12px;">{sent_bar}</td>
                        <td style="padding:12px; color:#cbd5e1;">👥 {age_grp}</td>
                        <td style="padding:12px; color:#cbd5e1;">📍 {state_loc}</td>
                        <td style="padding:12px; font-weight:600; color:#34d399;">{action_desc}</td>
                        <td style="padding:12px; font-weight:700; color:#10b981;">{lift_desc}</td>
                    </tr>
                    """
                    matrix_html += row_html
                    
                matrix_html += """
                    </tbody>
                </table>
                """
                clean_matrix_html = "\n".join(line.strip() for line in matrix_html.split("\n"))
                st.markdown(clean_matrix_html, unsafe_allow_html=True)
                
                if active_warnings:
                    for w, neg_pct, age_grp, state_loc, sc_key in active_warnings:
                        col_txt, col_act = st.columns([4, 1])
                        with col_txt:
                            warn_html = f"""
                            <div style="padding:8px; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:6px; font-size:0.85rem; color:#fca5a5; margin-top:5px;">
                                ⚠️ <b>Crisis Warning:</b> Negativity on <b>'{w}'</b> is at <b>{neg_pct}%</b> in location <b>{state_loc}</b> ({age_grp}).
                            </div>
                            """
                            st.markdown("\n".join(line.strip() for line in warn_html.split("\n")), unsafe_allow_html=True)
                        with col_act:
                            if st.button(f"⚡ Deploy PR Plan: '{w}'", key=f"remed_btn_{w}", use_container_width=True):
                                st.session_state["dashboard_phase"] = "🤖 Phase 3: Crisis Remediation Desk"
                                st.session_state["remediation_selected_scenario"] = sc_key
                                st.toast(f"Switched phase to Crisis Remediation Desk for '{w}'")
                                st.rerun()
                                
            elif selected_phase == "🤖 Phase 3: Crisis Remediation Desk":
                st.markdown("#### 🛡️ Public Image & Remediation Simulator")
                
                positivity = stats["positivity_ratio"]
                is_crisis = positivity is not None and positivity < 50.0
                
                if is_crisis:
                    st.markdown(f"""
                    <div style="background:var(--neg-bg); border:1px solid var(--neg-border); padding:16px; border-radius:8px; margin-bottom:20px; text-align:left;">
                        <span style="font-size:1.5rem;">🚨</span> &nbsp;<b style="color:#f87171; font-size:1.1rem;">High Crisis Risk: Negativity dominance detected.</b><br/>
                        Current positivity index is at <b>{positivity}%</b>. The Remediation Matrix below is activated.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:var(--pos-bg); border:1px solid var(--pos-border); padding:16px; border-radius:8px; margin-bottom:20px; text-align:left;">
                        <span style="font-size:1.5rem;">🟢</span> &nbsp;<b style="color:#34d399; font-size:1.1rem;">Stable Sentiment Profile</b><br/>
                        Current positivity index is at <b>{positivity}%</b>. You can run PR simulations to forecast potential spikes.
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("##### 🛠️ Recommended Action Matrix")
                sc_col1, sc_col2, sc_col3 = st.columns(3)
                
                with sc_col1:
                    sc = REMEDIATION_SCENARIOS["fake_news"]
                    st.markdown(f"""
                    <div class="socio-card" style="min-height:300px; display:flex; flex-direction:column; justify-content:space-between; text-align:left;">
                        <div>
                            <div style="font-weight:800; color:white; font-size:1rem;">{sc['title']}</div>
                            <div style="font-size:0.8rem; color:var(--text-mute); margin-top:5px; line-height:1.4;">{sc['description']}</div>
                            <hr style="margin:10px 0; border-color:rgba(255,255,255,0.05);"/>
                            <b style="font-size:0.75rem; text-transform:uppercase; color:var(--accent);">Actions:</b>
                            <ul style="font-size:0.75rem; padding-left:15px; margin-top:5px; color:var(--text-2);">
                                <li><b>{sc['actions'][0]['name']}</b>: {sc['actions'][0]['impact']}</li>
                                <li><b>{sc['actions'][1]['name']}</b>: {sc['actions'][1]['impact']}</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with sc_col2:
                    sc = REMEDIATION_SCENARIOS["policy_backlash"]
                    st.markdown(f"""
                    <div class="socio-card" style="min-height:300px; display:flex; flex-direction:column; justify-content:space-between; text-align:left;">
                        <div>
                            <div style="font-weight:800; color:white; font-size:1rem;">{sc['title']}</div>
                            <div style="font-size:0.8rem; color:var(--text-mute); margin-top:5px; line-height:1.4;">{sc['description']}</div>
                            <hr style="margin:10px 0; border-color:rgba(255,255,255,0.05);"/>
                            <b style="font-size:0.75rem; text-transform:uppercase; color:var(--accent);">Actions:</b>
                            <ul style="font-size:0.75rem; padding-left:15px; margin-top:5px; color:var(--text-2);">
                                <li><b>{sc['actions'][0]['name']}</b>: {sc['actions'][0]['impact']}</li>
                                <li><b>{sc['actions'][1]['name']}</b>: {sc['actions'][1]['impact']}</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with sc_col3:
                    sc = REMEDIATION_SCENARIOS["local_issue"]
                    st.markdown(f"""
                    <div class="socio-card" style="min-height:300px; display:flex; flex-direction:column; justify-content:space-between; text-align:left;">
                        <div>
                            <div style="font-weight:800; color:white; font-size:1rem;">{sc['title']}</div>
                            <div style="font-size:0.8rem; color:var(--text-mute); margin-top:5px; line-height:1.4;">{sc['description']}</div>
                            <hr style="margin:10px 0; border-color:rgba(255,255,255,0.05);"/>
                            <b style="font-size:0.75rem; text-transform:uppercase; color:var(--accent);">Actions:</b>
                            <ul style="font-size:0.75rem; padding-left:15px; margin-top:5px; color:var(--text-2);">
                                <li><b>{sc['actions'][0]['name']}</b>: {sc['actions'][0]['impact']}</li>
                                <li><b>{sc['actions'][1]['name']}</b>: {sc['actions'][1]['impact']}</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.divider()
                st.markdown("##### 🎯 Interactive PR Simulation Forecast")
                
                sim_col1, sim_col2 = st.columns(2)
                with sim_col1:
                    st.markdown("###### Select Actions to Deploy")
                    sel_scenario = st.session_state.get("remediation_selected_scenario")
                    
                    def_release = sel_scenario == "fake_news"
                    def_video = sel_scenario == "policy_backlash"
                    def_pivot = sel_scenario == "policy_backlash"
                    def_geofence = sel_scenario == "local_issue"
                    
                    act_release = st.checkbox("Counter-Narrative Release", value=def_release, key="remed_chk_release")
                    act_appeal = st.checkbox("Platform Moderation Appeals", value=False, key="remed_chk_appeal")
                    act_video = st.checkbox("Targeted Video Clarification", value=def_video, key="remed_chk_video")
                    act_pivot = st.checkbox("Policy Pivot / Focus Group Engagement", value=def_pivot, key="remed_chk_pivot")
                    act_geofence = st.checkbox("Geo-Fenced PR Release", value=def_geofence, key="remed_chk_geofence")
                    act_liaison = st.checkbox("Direct Authority Liaison", value=False, key="remed_chk_liaison")
                    
                    selected_actions = []
                    if act_release: selected_actions.append("Counter-Narrative Release")
                    if act_appeal: selected_actions.append("Platform Moderation Appeals")
                    if act_video: selected_actions.append("Targeted Video Clarification")
                    if act_pivot: selected_actions.append("Policy Pivot / Focus Group Engagement")
                    if act_geofence: selected_actions.append("Geo-Fenced PR Release")
                    if act_liaison: selected_actions.append("Direct Authority Liaison")
                    
                with sim_col2:
                    st.markdown("###### Forecast Sentiment Result")
                    
                    current_metrics = {
                        "total": stats["total"],
                        "positive": stats["positive"],
                        "negative": stats["negative"],
                        "neutral": stats["neutral"]
                    }
                    
                    sim_res = simulate_remediation(current_metrics, selected_actions)
                    
                    sf_col1, sf_col2 = st.columns(2)
                    with sf_col1:
                        st.metric("Current Positivity Ratio", f"{positivity}%")
                        st.metric("Simulated Positivity Ratio", f"{sim_res['positivity_ratio']}%", delta=f"{round(sim_res['positivity_ratio'] - (positivity or 0.0), 1)}%")
                    with sf_col2:
                        st.metric("Current Average Score", f"{stats['avg_score']}")
                        st.metric("Simulated Average Score", f"{sim_res['avg_score']}", delta=f"{round(sim_res['avg_score'] - (stats['avg_score'] or 0.0), 3)}")
                        
                    comparison_df = pd.DataFrame([
                        {"State": "Current Status", "Sentiment": "Positive", "Count": stats["positive"]},
                        {"State": "Current Status", "Sentiment": "Negative", "Count": stats["negative"]},
                        {"State": "Forecast Result", "Sentiment": "Positive", "Count": sim_res["positive"]},
                        {"State": "Forecast Result", "Sentiment": "Negative", "Count": sim_res["negative"]}
                    ])
                    
                    fig_compare = px.bar(
                        comparison_df, x="State", y="Count", color="Sentiment",
                        barmode="group", color_discrete_map={"Positive": "#10b981", "Negative": "#ef4444"},
                        height=180
                    )
                    fig_compare.update_layout(margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
                    st.plotly_chart(fig_compare, use_container_width=True, config={"displayModeBar": False})
                
            # Report Export Buttons
            st.divider()
            report_html = build_html_report(
                report["term"], df, stats,
                extract_hot_topics(df["text"].tolist(), extra_stop=report["term"].split(), top_n=15)[0],
                extract_hot_topics(df["text"].tolist(), extra_stop=report["term"].split(), top_n=15)[1],
                top_authors(df, n=10),
                df.sort_values("engagement", ascending=False),
            )
            
            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                st.download_button(
                    "⬇️ Download HTML Executive Client Report",
                    report_html.encode("utf-8"),
                    file_name=f"LUMISOCIAL_{report['term']}_Report.html",
                    mime="text/html",
                    use_container_width=True
                )
            with ex_col2:
                st.download_button(
                    "⬇️ Download Raw Dataset (CSV)",
                    df.to_csv(index=False).encode("utf-8"),
                    file_name=f"LUMISOCIAL_{report['term']}_Data.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    else:
        st.info("💡 Please onboard monitored profiles or enter keywords and run a social listening scan to see analysis data.")

# ==================== PHASE 4: COMMAND CENTER ADMINISTRATION ====================
elif selected_phase == "⚙️ Phase 4: Command Center Administration":
    st.markdown("### ⚙️ Command Center Administration Desk")
    st.caption("Manage target figure keywords, check profile handles, seat provisioning, and environment API credentials.")
    
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "📋 Onboard Targets",
        "🔎 Social-Analyzer Validator",
        "👥 Team Management",
        "⚙️ API Configurations"
    ])
    
    with admin_tab1:
        st.markdown("#### Currently Tracked Profiles")
        targets = storage.list_targets()
        
        if not targets:
            st.info("No figures or brand targets registered yet. Use the onboarding builder below to register one.")
        else:
            for t in targets:
                st.markdown(f"""
                <div class="socio-card" style="border-left: 4px solid var(--accent); text-align:left;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.1rem; font-weight:800; color:white;">🎯 {t['name']}</span>
                        <span style="background:var(--accent-glow); border:1px solid var(--accent); padding:2px 10px; border-radius:12px; font-size:0.75rem; color:#2dd4bf; text-transform:uppercase; font-weight:700;">{t['category']}</span>
                    </div>
                    <div style="font-size:0.82rem; color:var(--text-2); margin-top:8px;">
                        <b>Target keywords:</b> <code>{t['keywords']}</code> &nbsp;|&nbsp; <b>Exclusions:</b> <code style="color:#f87171;">{t['excluded_keywords'] or 'None'}</code><br/>
                        <b>Context Location:</b> 📍 {t['location_hint'] or 'None'} &nbsp;|&nbsp; <b>Organization:</b> 🏢 {t['org_hint'] or 'None'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Delete target button
                if st.button(f"🗑️ Stop Tracking '{t['name']}'", key=f"del_{t['id']}"):
                    storage.delete_target(t["id"])
                    st.toast(f"Removed target profile '{t['name']}'")
                    st.rerun()
                    
        st.divider()
        st.markdown("#### Onboard New Target Figure")
        
        with st.form("new_target_form"):
            t_name = st.text_input("Entity Target Name", placeholder="e.g. Narendra Modi, Tata Motors")
            t_cat = st.selectbox("Category Group", ["Politician", "Executive", "Corporate Brand", "Celebrity", "Civic Body"])
            t_kws = st.text_area("Include Matching Keywords (comma-separated)", placeholder="e.g. Narendra Modi, Modi, PM Modi, @narendramodi")
            t_exs = st.text_input("Exclude Negative Keywords (comma-separated)", placeholder="e.g. actor, cricketer, chef")
            t_loc = st.text_input("Focus City / State (for regional listening)", placeholder="e.g. Mumbai, Maharashtra")
            t_org = st.text_input("Focus Organization / Party", placeholder="e.g. BJP, Tata Group")
            
            submit_target = st.form_submit_button("Onboard Target Profile")
            
            if submit_target:
                if not t_name or not t_kws:
                    st.error("Target name and matching keywords are required for social listening.")
                else:
                    success = storage.save_target(t_name, t_cat, t_kws, t_exs, t_loc, t_org)
                    if success:
                        st.success(f"Successfully onboarded target profile '{t_name}'!")
                        st.rerun()
                    else:
                        st.error("Failed to save target. Database operation error.")

    with admin_tab2:
        st.markdown("#### 🔎 Social-Analyzer Profile Validator & Name Origin")
        st.caption("Verify handle profiles across social networks to select the correct username strings.")
        
        sa_col1, sa_col2 = st.columns(2)
        
        with sa_col1:
            st.markdown("##### Social Profile Checker")
            sa_username = st.text_input("Enter Social Username to Scan", placeholder="e.g. narendramodi, sandeep_news")
            sa_platform = st.selectbox("Target Platform", ["twitter", "reddit", "youtube", "telegram"])
            
            check_profile = st.button("🔎 Check Profile Authenticity")
            
            if check_profile:
                if not sa_username:
                    st.warning("Please enter a username handle.")
                else:
                    with st.spinner(f"Verifying username '{sa_username}' on {sa_platform.upper()}..."):
                        is_valid, profile_url, details = verify_profile_username(sa_username, sa_platform)
                        
                    if is_valid:
                        st.success(f"Profile verified and active on {sa_platform.upper()}!")
                        st.markdown(f"🔗 [View Profile Handle Link]({profile_url})")
                        st.info(f"Metadata summary: {details}")
                    else:
                        st.error(f"Handle profile '{sa_username}' not found or unreachable on {sa_platform.upper()}. Check typing.")
                        
        with sa_col2:
            st.markdown("##### Name Origin & Gender Estimator")
            sa_name = st.text_input("Enter Full Name to Lookup", placeholder="e.g. Unmesh, Narendra")
            
            check_name = st.button("🔎 Analyze Name Characteristics")
            
            if check_name:
                if sa_name:
                    with st.spinner("Searching name database..."):
                        name_matches = analyze_name(sa_name)
                        
                    if not name_matches:
                        st.info("No matching entries found in the origins database.")
                    else:
                        st.success(f"Matched {len(name_matches)} entries in the lookup database!")
                        for m in name_matches:
                            sim_pct = int(m['similarity'] * 100)
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); padding:10px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; text-align:left;">
                                <div>
                                    <span style="font-weight:700; color:white;">{m['name']}</span> &nbsp;|&nbsp; 
                                    <span>Origin: {m['origin']}</span> &nbsp;|&nbsp; 
                                    <span>Gender: {m['gender']}</span>
                                </div>
                                <span style="font-size:0.75rem; color:var(--text-mute);">Similarity: {sim_pct}%</span>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.warning("Please enter a name.")

    with admin_tab3:
        if st.session_state["user_role"] != "SUPER_ADMIN":
            st.warning("Administrative privileges are required to manage corporate team command seats.")
        else:
            st.markdown("#### Registered Command Center Users")
            users = storage.list_users()
            
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                for u in users:
                    st.markdown(f"""
                    <div class="socio-card" style="display:flex; justify-content:space-between; align-items:center; text-align:left;">
                        <div>
                            <span style="font-weight:700; color:white; font-size:1rem;">{u['email']}</span><br/>
                            <span style="font-size:0.75rem; color:var(--text-mute);">Added on: {u['created_at']}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:12px;">
                            <span style="background:var(--accent-glow); border:1px solid var(--accent); padding:2px 8px; border-radius:10px; font-size:0.7rem; color:#2dd4bf; font-weight:700; text-transform:uppercase;">{u['role']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if u["email"] != st.session_state["user_email"]:
                        if st.button("Delete User", key=f"del_u_{u['id']}"):
                            storage.delete_user(u["id"])
                            st.toast(f"Deleted user account: {u['email']}")
                            st.rerun()
                            
            with col_u2:
                st.markdown("##### Create New Team Access User")
                with st.form("new_user_form"):
                    u_email = st.text_input("Corporate Email Address", placeholder="e.g. team_member@company.com")
                    u_pwd = st.text_input("Initial Access Password", type="password", placeholder="Minimum 6 characters")
                    u_role = st.selectbox("Authorization Role", ["ANALYST", "ORATOR/PR_LEAD", "SUPER_ADMIN"])
                    
                    submit_user = st.form_submit_button("Provision Account")
                    
                    if submit_user:
                        if not u_email or not u_pwd:
                            st.error("Both email address and password are required.")
                        elif len(u_pwd) < 6:
                            st.error("Access password must be at least 6 characters.")
                        else:
                            success = storage.create_user(u_email, u_pwd, u_role)
                            if success:
                                st.success(f"Provisioned new user account: {u_email}")
                                st.rerun()
                            else:
                                st.error("Failed to provision account. Email address might already be registered.")

    with admin_tab4:
        if st.session_state["user_role"] != "SUPER_ADMIN":
            st.warning("Administrative privileges are required to write client API keys.")
        else:
            st.markdown("#### API Key Credentials Editor")
            st.caption("Configure developer keys directly in the active environment.")
            
            def save_env_keys(keys_dict):
                lines = []
                if os.path.exists(".env"):
                    with open(".env", "r", encoding="utf-8") as f:
                        lines = f.readlines()
                
                updated_keys = keys_dict.copy()
                new_lines = []
                for line in lines:
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        if k in updated_keys:
                            new_lines.append(f"{k}={updated_keys.pop(k)}\n")
                            continue
                    new_lines.append(line)
                    
                for k, v in updated_keys.items():
                    new_lines.append(f"{k}={v}\n")
                    
                with open(".env", "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                    
            with st.form("api_keys_form"):
                st.markdown("##### Reddit PRAW Client Credentials")
                reddit_id = st.text_input("REDDIT_CLIENT_ID", value=os.environ.get("REDDIT_CLIENT_ID", ""), type="password")
                reddit_secret = st.text_input("REDDIT_CLIENT_SECRET", value=os.environ.get("REDDIT_CLIENT_SECRET", ""), type="password")
                
                st.markdown("##### YouTube Data API Keys")
                yt_key = st.text_input("YOUTUBE_API_KEY", value=os.environ.get("YOUTUBE_API_KEY", ""), type="password")
                
                st.markdown("##### Telegram Telethon API Credentials")
                tg_id = st.text_input("TELEGRAM_API_ID", value=os.environ.get("TELEGRAM_API_ID", ""))
                tg_hash = st.text_input("TELEGRAM_API_HASH", value=os.environ.get("TELEGRAM_API_HASH", ""), type="password")
                
                st.markdown("##### Twitter / X Bearer Tokens")
                tw_token = st.text_input("TWITTER_BEARER_TOKEN", value=os.environ.get("TWITTER_BEARER_TOKEN", ""), type="password")
                
                save_btn = st.form_submit_button("Write Configuration Keys")
                
                if save_btn:
                    new_keys = {
                        "REDDIT_CLIENT_ID": reddit_id,
                        "REDDIT_CLIENT_SECRET": reddit_secret,
                        "YOUTUBE_API_KEY": yt_key,
                        "TELEGRAM_API_ID": tg_id,
                        "TELEGRAM_API_HASH": tg_hash,
                        "TWITTER_BEARER_TOKEN": tw_token
                    }
                    try:
                        save_env_keys(new_keys)
                        for k, v in new_keys.items():
                            os.environ[k] = v
                        st.success("Successfully persisted keys to local environment config (.env)!")
                    except Exception as e:
                        st.error(f"Failed to write configuration: {e}")
