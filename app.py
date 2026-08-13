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
        min-height: 70vh;
    }
    .login-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: var(--r-lg);
        padding: 40px;
        max-width: 480px;
        width: 100%;
        box-shadow: var(--shadow-2);
        backdrop-filter: blur(12px);
        text-align: center;
        border-top: 4px solid var(--accent);
    }
    .login-header {
        font-size: 1.8rem;
        font-weight: 800;
        color: white;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }
    .login-subtitle {
        font-size: 0.9rem;
        color: var(--text-mute);
        margin-bottom: 30px;
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
    # Render premium glassmorphic login page
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    col_l, col_login, col_r = st.columns([1, 2, 1])
    with col_login:
        st.markdown("""
        <div class="login-card">
            <span style="font-size:2.5rem;">⚡</span>
            <div class="login-header">LUMISOCIAL</div>
            <div class="login-subtitle">Executive Command Center & Social Intelligence Platform</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
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
        <div style="text-align:center; margin-top:20px; font-size:0.8rem; color:#64748b;">
            <b>Default Admin Sandbox Access:</b><br/>
            Email: <code style="color:#2dd4bf;">admin@lumisocial.com</code> &nbsp;|&nbsp; Password: <code style="color:#2dd4bf;">admin123</code>
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
    
    # Filter navigation options by User Role
    menu_options = ["📊 Monitor Dashboard", "🤖 Crisis Remediation"]
    
    if st.session_state["user_role"] in ["SUPER_ADMIN", "ORATOR/PR_LEAD"]:
        menu_options.insert(1, "🎯 Targets Onboarding")
        
    if st.session_state["user_role"] == "SUPER_ADMIN":
        menu_options.append("👥 Team Management")
        menu_options.append("⚙️ API Configuration")
        
    page = st.selectbox("Navigation Desk", menu_options, index=0)
    
    st.divider()
    
    # Quick Logout Button
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = None
        st.session_state["user_role"] = "ANALYST"
        st.toast("Logged out successfully.")
        st.rerun()

# ----------------- PAGE ROUTING & RENDERING -----------------

# ==================== PAGE 1: MONITOR DASHBOARD ====================
if page == "📊 Monitor Dashboard":
    st.markdown("### 📊 Executive Monitoring Dashboard")
    
    # Load targets list from DB
    targets = storage.list_targets()
    target_names = [t["name"] for t in targets]
    
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
            <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); padding:12px; border-radius:8px;">
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
        
    run_btn = st.button("🚀 Run Social Listening Scan", type="primary", use_container_width=True)
    
    # ---------------- DASHBOARD EXECUTION PIPELINE ----------------
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
            pos_cnt = stats["positive"]
            neg_cnt = stats["negative"]
            neu_cnt = stats["neutral"]
            total_cnt = stats["total"]
            positivity = stats["positivity_ratio"]
            avg_score = stats["avg_score"]
            
            # Metrics Row (Socioboard Style)
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.markdown(f"""
                <div class="socio-card" style="border-top: 4px solid var(--info);">
                    <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Total Mentions</div>
                    <div style="font-size:1.8rem; font-weight:800; color:white; margin-top:5px;">{total_cnt:,}</div>
                </div>
                """, unsafe_allow_html=True)
            with m_col2:
                border_color = "var(--pos)" if positivity and positivity > 50 else "var(--neg)"
                ratio_str = f"{positivity}%" if positivity is not None else "N/A"
                st.markdown(f"""
                <div class="socio-card" style="border-top: 4px solid {border_color};">
                    <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Positivity Index</div>
                    <div style="font-size:1.8rem; font-weight:800; color:white; margin-top:5px;">{ratio_str}</div>
                </div>
                """, unsafe_allow_html=True)
            with m_col3:
                st.markdown(f"""
                <div class="socio-card" style="border-top: 4px solid var(--pos);">
                    <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Positive / Negative</div>
                    <div style="font-size:1.4rem; font-weight:800; color:white; margin-top:5px;">🟢 {pos_cnt} &nbsp;|&nbsp; 🔴 {neg_cnt}</div>
                </div>
                """, unsafe_allow_html=True)
            with m_col4:
                # Calculate Net Sentiment Score
                st.markdown(f"""
                <div class="socio-card" style="border-top: 4px solid var(--neu);">
                    <div style="font-size:0.8rem; color:var(--text-mute); font-weight:700; text-transform:uppercase;">Average Compound Score</div>
                    <div style="font-size:1.8rem; font-weight:800; color:white; margin-top:5px;">{avg_score}</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Chart breakdown Section
            c_col1, c_col2 = st.columns(2)
            
            with c_col1:
                st.markdown('<div class="socio-card">', unsafe_allow_html=True)
                st.markdown("<b>Real-Time Polarity Stream</b>", unsafe_allow_html=True)
                
                # Polarity time series
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
                
            # Live Feed stream (Socioboard Feed Cards)
            st.markdown("#### 📬 Social Listening Feed Stream")
            
            top_feeds = df.sort_values("engagement", ascending=False).head(15)
            
            for idx, r in top_feeds.iterrows():
                sent = str(r.get("sentiment", "neutral")).lower()
                border_cls = "card-border-pos" if sent == "positive" else ("card-border-neg" if sent == "negative" else "card-border-neu")
                
                author_title = str(r.get("author_name") or r.get("author") or "User")
                author_handle = str(r.get("author") or "")
                platform_str = str(r.get("platform", "web"))
                p_icon = get_platform_icon(platform_str)
                
                hl_body = highlight_keywords(str(r.get("text", "")), report["term"])
                likes = int(r.get("likes", 0))
                
                tags_html = f"<span style='background:rgba(255,255,255,0.06); border:1px solid var(--border); padding:2px 8px; border-radius:12px; font-size:0.7rem; font-weight:700;'>{sent.upper()}</span>"
                if r.get("india_state"):
                    tags_html += f" &nbsp;<span style='background:var(--info-bg); border:1px solid #0284c7; padding:2px 8px; border-radius:12px; font-size:0.7rem; color:#bae6fd;'>📍 {r['india_state']}</span>"
                    
                st.markdown(f"""
                <div class="socio-card {border_cls}">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="font-weight:700; color:white; font-size:0.9rem;">
                            {p_icon} {author_title} <span style="color:var(--text-mute); font-weight:500; font-size:0.8rem;">@{author_handle}</span>
                        </div>
                        <div style="font-size:0.75rem; color:var(--text-mute);">Likes: {likes}</div>
                    </div>
                    <div style="font-size:0.88rem; line-height:1.5; color:var(--text-2); margin-bottom:8px;">{hl_body}</div>
                    <div>{tags_html}</div>
                </div>
                """, unsafe_allow_html=True)
                
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


# ==================== PAGE 2: TARGETS ONBOARDING ====================
elif page == "🎯 Targets Onboarding":
    st.markdown("### 🎯 Tracked Targets & Rules Onboarding")
    
    t_tab1, t_tab2 = st.tabs(["📋 Tracked Entities", "🔎 Social-Analyzer Profile Validator"])
    
    with t_tab1:
        st.markdown("#### Currently Tracked Profiles")
        targets = storage.list_targets()
        
        if not targets:
            st.info("No figures or brand targets registered yet. Use the onboarding builder below to register one.")
        else:
            for t in targets:
                st.markdown(f"""
                <div class="socio-card" style="border-left: 4px solid var(--accent);">
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

    with t_tab2:
        st.markdown("#### 🔎 Social-Analyzer Profile Validator & Name Origin")
        st.caption("Verify handle profiles across social networks to select the correct username strings.")
        
        sa_col1, sa_col2 = st.columns(2)
        
        with sa_col1:
            st.markdown("##### 1. Query Profile Verification (Social-Analyzer)")
            sa_username = st.text_input("Social Handle Username", placeholder="e.g. narendramodi, taylorswift")
            
            if st.button("Check Handle Existences", type="primary"):
                if sa_username:
                    with st.spinner("Checking username presence across key sites..."):
                        sa_res = verify_profile_username(sa_username)
                        
                    detected = sa_res.get("detected", [])
                    if not detected:
                        st.warning("No profiles confirmed. Handle might be available or highly private.")
                    else:
                        st.success(f"Detected {len(detected)} public profiles matching username '{sa_username}'!")
                        
                        for p in detected:
                            rate = p.get("rate", "100%")
                            p_icon = get_platform_icon(p.get("type", "web"))
                            
                            st.markdown(f"""
                            <div class="profile-suggestion-card">
                                <div class="profile-info">
                                    <span class="profile-title">{p_icon} {p.get('type','Social Platform').upper()}</span>
                                    <a class="profile-link" href="{p.get('link','#')}" target="_blank">{p.get('link')}</a>
                                </div>
                                <span style="background:var(--pos-bg); border:1px solid var(--pos-border); padding:2px 8px; border-radius:10px; font-size:0.75rem; color:#10b981; font-weight:700;">Confidence: {rate}</span>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.warning("Please type a username first.")
                    
        with sa_col2:
            st.markdown("##### 2. Name Origin & Gender Lookup")
            st.caption("Looks up origin and gender estimations inside Social-Analyzer's names database.")
            sa_name = st.text_input("Target Name to Analyze", placeholder="e.g. Ajay, John, Aisha")
            
            if st.button("Analyze Name Metadata"):
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
                            <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); padding:10px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
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


# ==================== PAGE 3: CRISIS REMEDIATION ====================
elif page == "🤖 Crisis Remediation":
    st.markdown("### 🤖 Crisis Remediation & Strategic Action Engine")
    
    report = st.session_state.get("last_report")
    
    if not report:
        st.info("Please perform a search scan in the Monitor Dashboard first to load active sentiment metrics.")
    else:
        df = report["df"]
        stats = report["stats"]
        
        positivity = stats["positivity_ratio"]
        is_crisis = positivity is not None and positivity < 50.0
        
        if is_crisis:
            st.markdown(f"""
            <div style="background:var(--neg-bg); border:1px solid var(--neg-border); padding:16px; border-radius:8px; margin-bottom:20px;">
                <span style="font-size:1.5rem;">🚨</span> &nbsp;<b style="color:#f87171; font-size:1.1rem;">High Crisis Risk: Negativity dominance detected.</b><br/>
                Current positivity index is at <b>{positivity}%</b>. The Remediation Matrix below is activated.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:var(--pos-bg); border:1px solid var(--pos-border); padding:16px; border-radius:8px; margin-bottom:20px;">
                <span style="font-size:1.5rem;">🟢</span> &nbsp;<b style="color:#34d399; font-size:1.1rem;">Stable Sentiment Profile</b><br/>
                Current positivity index is at <b>{positivity}%</b>. You can run PR simulations to forecast potential spikes.
            </div>
            """, unsafe_allow_html=True)
            
        # Display scenario-remediation cards
        st.markdown("#### 🛠️ Recommended Action Matrix")
        
        sc_col1, sc_col2, sc_col3 = st.columns(3)
        
        with sc_col1:
            sc = REMEDIATION_SCENARIOS["fake_news"]
            st.markdown(f"""
            <div class="socio-card" style="min-height:300px; display:flex; flex-direction:column; justify-content:space-between;">
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
            <div class="socio-card" style="min-height:300px; display:flex; flex-direction:column; justify-content:space-between;">
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
            <div class="socio-card" style="min-height:300px; display:flex; flex-direction:column; justify-content:space-between;">
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
        st.markdown("#### 🎯 Interactive PR Simulation Forecast")
        st.caption("Check options below to simulate how executing recommended PR strategies would affect forecast index values.")
        
        sim_col1, sim_col2 = st.columns(2)
        
        with sim_col1:
            st.markdown("##### Select Actions to Deploy")
            act_release = st.checkbox("Counter-Narrative Release")
            act_appeal = st.checkbox("Platform Moderation Appeals")
            act_video = st.checkbox("Targeted Video Clarification")
            act_pivot = st.checkbox("Policy Pivot / Focus Group Engagement")
            act_geofence = st.checkbox("Geo-Fenced PR Release")
            act_liaison = st.checkbox("Direct Authority Liaison")
            
            selected_actions = []
            if act_release: selected_actions.append("Counter-Narrative Release")
            if act_appeal: selected_actions.append("Platform Moderation Appeals")
            if act_video: selected_actions.append("Targeted Video Clarification")
            if act_pivot: selected_actions.append("Policy Pivot / Focus Group Engagement")
            if act_geofence: selected_actions.append("Geo-Fenced PR Release")
            if act_liaison: selected_actions.append("Direct Authority Liaison")
            
        with sim_col2:
            st.markdown("##### Forecast Sentiment Result")
            
            # Prepare current count metrics
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
                
            # Draw before/after comparison chart
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


# ==================== PAGE 4: TEAM MANAGEMENT ====================
elif page == "👥 Team Management" and st.session_state["user_role"] == "SUPER_ADMIN":
    st.markdown("### 👥 Corporate Team & Role Access Control (RBAC)")
    st.caption("Manage analyst accounts and role scopes.")
    
    col_u1, col_u2 = st.columns(2)
    
    with col_u1:
        st.markdown("#### Registered Command Center Users")
        users = storage.list_users()
        
        for u in users:
            st.markdown(f"""
            <div class="socio-card" style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-weight:700; color:white; font-size:1rem;">{u['email']}</span><br/>
                    <span style="font-size:0.75rem; color:var(--text-mute);">Added on: {u['created_at']}</span>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="background:var(--accent-glow); border:1px solid var(--accent); padding:2px 8px; border-radius:10px; font-size:0.7rem; color:#2dd4bf; font-weight:700; text-transform:uppercase;">{u['role']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Prevent self-deletion
            if u["email"] != st.session_state["user_email"]:
                if st.button("Delete User", key=f"del_u_{u['id']}"):
                    storage.delete_user(u["id"])
                    st.toast(f"Deleted user account: {u['email']}")
                    st.rerun()
                    
    with col_u2:
        st.markdown("#### Create New Team Access User")
        
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


# ==================== PAGE 5: API CONFIGURATION ====================
elif page == "⚙️ API Configuration" and st.session_state["user_role"] == "SUPER_ADMIN":
    st.markdown("### ⚙️ API Configuration Desk")
    st.caption("Configure developer keys directly in the active application environment.")
    
    # Save helper
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
                # Mirror in active execution environment
                for k, v in new_keys.items():
                    os.environ[k] = v
                st.success("Successfully persisted keys to local environment config (.env)!")
            except Exception as e:
                st.error(f"Failed to write configuration: {e}")
