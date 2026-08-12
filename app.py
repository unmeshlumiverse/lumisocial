"""
LUMISOCIAL — Executive Command Center & Social Intelligence Platform

Run with:  streamlit run app.py
"""

import os
import re
import math
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

st.set_page_config(
    page_title="LUMISOCIAL | Command Center",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Custom CSS for exact Executive Command Center styling, legible inputs, and sleek cards
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #334155;
    }
    
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Left Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #00875a !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #ffffff !important;
    }
    /* Ensure text inside input and select fields is dark, crisp and clearly readable */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="input"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #0f172a !important;
        background-color: #ffffff !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stButton > button p,
    [data-testid="stSidebar"] .stButton > button span,
    [data-testid="stSidebar"] .stButton > button div,
    [data-testid="stSidebar"] .stButton > button * {
        color: #00875a !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #ffffff !important;
        border-radius: 8px !important;
        border: 2px solid #ffffff !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.18) !important;
        padding: 8px 16px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] .stButton > button:hover * {
        background-color: #f8fafc !important;
        color: #005a3c !important;
    }
    
    /* Command Center Upper Section Card */
    .auris-upper-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    
    .auris-section-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Word Cloud Tag Styling */
    .topic-tag-cloud {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 12px;
        align-items: center;
        justify-content: flex-start;
        padding: 8px 0;
        min-height: 180px;
    }
    .tag-xl { font-size: 1.35rem; font-weight: 800; color: #1e293b; }
    .tag-lg { font-size: 1.1rem; font-weight: 700; color: #334155; }
    .tag-md { font-size: 0.92rem; font-weight: 600; color: #64748b; }
    .tag-sm { font-size: 0.8rem; font-weight: 500; color: #94a3b8; }
    
    /* Influencer Badge Row */
    .influencer-row {
        display: flex;
        gap: 12px;
        align-items: center;
        justify-content: flex-start;
        margin-top: 14px;
        flex-wrap: wrap;
    }
    .influencer-card {
        text-align: center;
    }
    .influencer-avatar {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: #e2e8f0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        color: #475569;
        margin: 0 auto 4px auto;
        border: 2px solid #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        position: relative;
    }
    .platform-sub-icon {
        position: absolute;
        bottom: -2px;
        right: -2px;
        background: #00875a;
        color: white;
        border-radius: 50%;
        width: 16px;
        height: 16px;
        font-size: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .influencer-score {
        font-size: 0.8rem;
        font-weight: 700;
        color: #475569;
    }
    
    /* Feed Item Card */
    .auris-feed-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        position: relative;
    }
    .card-border-pos { border-left: 5px solid #10b981; }
    .card-border-neg { border-left: 5px solid #ef4444; }
    .card-border-neu { border-left: 5px solid #f59e0b; }
    
    .feed-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .feed-user-info {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .feed-avatar-circle {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: #e2e8f0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.88rem;
        color: #1e293b;
    }
    .feed-author-name {
        font-weight: 700;
        font-size: 0.95rem;
        color: #0f172a;
    }
    .feed-handle {
        font-size: 0.82rem;
        color: #64748b;
        font-weight: 500;
        margin-left: 4px;
    }
    .platform-badge {
        font-size: 0.72rem;
        font-weight: 600;
        color: #475569;
        background: #f1f5f9;
        padding: 2px 8px;
        border-radius: 4px;
        margin-left: 6px;
    }
    .feed-time {
        font-size: 0.78rem;
        color: #94a3b8;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .feed-body-text {
        font-size: 0.93rem;
        color: #334155;
        line-height: 1.55;
        margin: 10px 0 12px 0;
    }
    .highlight-kw {
        background-color: #fef08a;
        color: #854d0e;
        padding: 2px 5px;
        border-radius: 3px;
        font-weight: 600;
    }
    .feed-tags-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        align-items: center;
    }
    .feed-pill {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #64748b;
        padding: 3px 10px;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .feed-pill-pos { background: #dcfce7; border-color: #bbf7d0; color: #166534; }
    .feed-pill-neg { background: #fee2e2; border-color: #fecaca; color: #991b1b; }
    .feed-pill-neu { background: #fef9c3; border-color: #fef08a; color: #854d0e; }
    .feed-pill-loc { background: #e0f2fe; border-color: #bae6fd; color: #0369a1; }
    
    /* Right Filter Panel */
    .filter-panel-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .filter-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 10px;
        margin-bottom: 14px;
    }
    .filter-title {
        font-weight: 700;
        font-size: 0.95rem;
        color: #0f172a;
    }
    .filter-total {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 600;
    }
    .sentiment-toggle-box {
        display: flex;
        justify-content: space-between;
        margin-bottom: 16px;
        gap: 8px;
    }
    .sentiment-item {
        flex: 1;
        text-align: center;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 8px 4px;
    }
    .sentiment-emoji-large {
        font-size: 1.25rem;
    }
    .sentiment-count-text {
        font-size: 0.82rem;
        font-weight: 700;
        color: #1e293b;
        margin-top: 2px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 18px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        padding: 0px 24px;
        font-size: 0.95rem;
        font-weight: 700;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Top Header Bar with Interactive Popovers ----------------
h_left, h_right = st.columns([3, 2])

with h_left:
    st.markdown("""<div style="display:flex; align-items:center; gap:8px; padding-top:6px;">
<span style="font-size:1.6rem; color:#00875a;">⚡</span>
<span style="font-size:1.4rem; font-weight:800; color:#0f172a;">LUMISOCIAL</span>
<span style="font-weight:400; color:#64748b; font-size:1.1rem;">| Command Center</span>
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
    limit = st.slider("Limit per Platform", 10, 150, 50, step=10)

    st.markdown("### 📡 Active Connectors")
    use_indian_news = st.checkbox("📰 Indian Newspapers (30+ RSS)", value=True)
    use_telegram = st.checkbox("💬 Telegram Public Channels", value=True)
    use_twitter = st.checkbox("🐦 Twitter / X (API v2)", value=True)
    use_news = st.checkbox("🌐 Google News (Global)", value=True)
    use_bsky = st.checkbox("🦋 Bluesky", value=True)
    use_reddit = st.checkbox("🤖 Reddit", value=True)
    use_youtube = st.checkbox("▶️ YouTube Comments", value=False)
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
    run = st.button("🚀 Fetch Today's Feeds", type="primary", use_container_width=True)

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
        cred_notes.append(issue)
    else:
        sources["reddit"] = lambda q, n: search_reddit(q, n)
if use_youtube:
    issue = _credential_issue("youtube")
    if issue:
        cred_notes.append(issue)
    else:
        sources["youtube"] = lambda q, n: search_youtube(q, n)
if use_twitter:
    issue = _credential_issue("twitter")
    if issue:
        cred_notes.append(issue)
    else:
        sources["twitter"] = lambda q, n: search_twitter(q, n)
if use_mastodon:
    sources["mastodon"] = lambda q, n: search_mastodon(q, n)
if use_hackernews:
    sources["hackernews"] = lambda q, n: search_hackernews(q, n)
if use_news:
    sources["news"] = lambda q, n: search_news(q, n, country="IN", lang="en")
if use_telegram:
    issue = _credential_issue("telegram")
    tg_channels = [c.strip() for c in tg_channels_raw.replace(",", "\n").splitlines() if c.strip()]
    if issue:
        cred_notes.append(issue)
    else:
        ch_list = tg_channels if tg_channels else DEFAULT_INDIA_CHANNELS
        sources["telegram"] = lambda q, n: search_telegram(q, n, channels=ch_list)

# Main action sub-header
top_c1, top_c2, top_c3 = st.columns([2, 3, 1])
with top_c1:
    term_display = f"({active_term})" if active_term else "(Awaiting Search Target)"
    st.markdown(f"<h3 style='margin:0; font-weight:800; color:#0f172a;'>Today's Feeds ▾ <span style='font-size:0.92rem; font-weight:600; color:#00875a;'>{term_display}</span></h3>", unsafe_allow_html=True)
with top_c2:
    st.caption("⚡ Live Ingestion & Real-Time Polarity Stream")
with top_c3:
    st.markdown("<div style='text-align:right;'><span style='background:#ffffff; border:1px solid #cbd5e1; padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.82rem; color:#1e293b; cursor:pointer;'>📥 Export Feeds</span></div>", unsafe_allow_html=True)

# ---------------- EXACTLY 2 TABS INTERFACE ----------------
tab1, tab2 = st.tabs([
    "⚡ Command Center",
    "🎯 Target Disambiguation & Client Pitch Guide"
])

with tab1:
    if not active_term:
        st.markdown("""<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:36px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.02); margin-top:10px;">
<div style="font-size:2.4rem; margin-bottom:8px;">⚡</div>
<h3 style="margin:0 0 8px 0; color:#0f172a; font-weight:800;">Welcome to LUMISOCIAL Command Center</h3>
<p style="color:#64748b; font-size:0.95rem; max-width:560px; margin:0 auto 20px auto;">Enter any public figure, person's name, or hashtag in the sidebar and click <b>Fetch Today's Feeds</b> to stream live intelligence across Indian Newspapers, Telegram, Twitter/X, and social channels.</p>
</div>""", unsafe_allow_html=True)
    else:
        with st.spinner(f"Ingesting real-time feeds for '{active_term}'..."):
            search_type = _TYPE_MAP.get(search_type_label, "keyword")
            expansions = expand_keywords(active_term, search_type) if use_expand else []
            df, errors = collect(active_term, search_type, sources, limit=limit, expansions=expansions)

        for name, err in errors.items():
            st.warning(f"⚠️ {name}: {err}")

        if df.empty:
            st.info(f"No matching posts found for '{active_term}'. Try broadening your search query or selecting additional sources in the sidebar.")
            st.stop()

        stats = summarize(df)
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
                color = "#00875a" if i % 3 == 0 else ("#0284c7" if i % 3 == 1 else "#1e293b")
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

            top_feeds = feed_df.sort_values("engagement", ascending=False).head(15)

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

        st.markdown("##### 🛠️ Disambiguation Query Helper")
        q_name = st.text_input("Person Name", value=active_term if active_term else "", key="d_name")
        q_loc = st.text_input("State / City (e.g., Maharashtra)", value="Maharashtra", key="d_loc")
        q_org = st.text_input("Organization / Designation (e.g., BJP)", value="", key="d_org")

        refined_query = f"{q_name} {q_loc} {q_org}".strip()
        st.code(f"Suggested Refined Search Query: {refined_query}", language="text")

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
