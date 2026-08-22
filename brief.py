"""
Executive Strategy Brief — the issues-first landing view.

Renders the full strategic flow for a scanned target, in the order a decision
maker needs it:

  1. Bottom-line verdict on the current image.
  2. ⚠️  What needs your attention now — the loudest criticism, surfaced first.
  3. 🧠 What people actually think (sentiment + emotion + verbatim).
  4. 📰 Media narrative vs. 🗣️ public narrative.
  5. 🗺️ Where (region) and 👥 who (age) — with a real map.
  6. 🕸️ The narrative web — topic similarity matrix.
  7. 📈 Your image over time (from stored run history).
  8. ✅ The plan to turn it around — sequenced, with a modelled forecast.

Design note (deliberate): we lead with the problems because a monitoring tool
earns trust by surfacing what needs attention first — and we pair every problem
with a concrete next step in the same view. The goal is an honest priority
board, not manufactured alarm; each number is a real, directional signal drawn
from the mentions actually collected (region/age are content-based inference,
not verified demographics or GPS).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import storage
import theme
from analysis import aggregate_india_state_sentiments, extract_hot_topics
from demographics import summarize_demographics
from media_analysis import split_media_vs_public
from similarity import build_topic_matrix
from strategy import build_action_plan
from remediation import REMEDIATION_SCENARIOS

# Shared palette (mirrors the dashboard CSS variables). Semantic colors are
# theme-invariant; only text/gridline colors follow the active dark/light mode.
POS, NEG, NEU, ACCENT, INFO = "#10b981", "#ef4444", "#f59e0b", "#0d9488", "#0284c7"

# Incremented on every brief render so Plotly chart keys are always unique,
# even if the brief is (defensively) rendered more than once in a script run.
_RENDER_NONCE = {"v": 0}


def _fig_base(fig, height=280, legend=True):
    pt = theme.plot_theme()
    fig.update_layout(
        height=height,
        margin=dict(l=6, r=6, t=28, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=pt["text"], family="Plus Jakarta Sans"),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=pt["grid"], zeroline=False)
    return fig


def _card(inner, border=None):
    style = "border-left:5px solid %s;" % border if border else ""
    st.markdown(
        f"<div class='socio-card' style='text-align:left;{style}'>{inner}</div>",
        unsafe_allow_html=True,
    )


def _plot(fig, key):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False},
                    key=f"{key}_{_RENDER_NONCE['v']}")


# ──────────────────────────────────────────────────────────────────────────
def render_executive_brief(df, stats, report, term):
    _RENDER_NONCE["v"] += 1
    if df is None or df.empty:
        st.info("Run a scan to generate the executive brief.")
        return

    positivity = stats.get("positivity_ratio")
    total = stats.get("total", 0)

    # ── 0. Bottom-line verdict ────────────────────────────────────────────
    _render_verdict(df, stats, term, positivity, total)

    # ── 1. Priority threat board (issues first) ───────────────────────────
    plan = build_action_plan(df, stats, search_term=term)
    _render_threat_board(df, plan)

    st.divider()

    # ── 2. What people think ──────────────────────────────────────────────
    st.markdown("### 🧠 What people actually think about you")
    _render_sentiment_emotion(df, stats)
    _render_verbatim(df)

    st.divider()

    # ── 3. Media vs public ────────────────────────────────────────────────
    st.markdown("### 📰 Mainstream-media image  vs.  🗣️ public opinion")
    _render_media_vs_public(df)

    st.divider()

    # ── 4. Region & age ───────────────────────────────────────────────────
    st.markdown("### 🗺️ Where they're saying it  &  👥 who is saying it")
    _render_region_age(df, plan)

    st.divider()

    # ── 5. Narrative web ──────────────────────────────────────────────────
    st.markdown("### 🕸️ The narrative web — how topics are being linked")
    _render_similarity(df, term)

    st.divider()

    # ── 6. Image over time ────────────────────────────────────────────────
    st.markdown("### 📈 Your image over time — what story has been building")
    _render_history(term)

    st.divider()

    # ── 7. The plan ───────────────────────────────────────────────────────
    st.markdown("### ✅ The plan to turn it around")
    _render_plan(plan, stats)


# ══════════════════════════════════════════════════════════════════════════
def _render_verdict(df, stats, term, positivity, total):
    if positivity is None:
        tone, color, label = "insufficient", NEU, "Not enough opinionated posts to call it yet"
    elif positivity < 40:
        tone, color, label = "hostile", NEG, "Public image is under pressure"
    elif positivity < 55:
        tone, color, label = "mixed", NEU, "Public image is contested / mixed"
    else:
        tone, color, label = "healthy", POS, "Public image is broadly positive"

    neg = stats.get("negative", 0)
    pos = stats.get("positive", 0)
    st.markdown(
        f"""
        <div class='socio-card' style='text-align:left; border-left:6px solid {color};
             background:linear-gradient(90deg, rgba(255,255,255,0.02), rgba(0,0,0,0));'>
          <div style='font-size:0.8rem; color:var(--text-mute); letter-spacing:0.5px;
               text-transform:uppercase; font-weight:700;'>Executive read on “{term}”</div>
          <div style='font-size:1.5rem; font-weight:800; color:{color}; margin:4px 0;'>{label}</div>
          <div style='color:var(--text-2); font-size:0.95rem;'>
            Across <b>{total:,}</b> collected mentions,
            <b style='color:{POS}'>{pos:,}</b> read positive and
            <b style='color:{NEG}'>{neg:,}</b> read negative —
            a positivity index of <b style='color:{color}'>{positivity if positivity is not None else '—'}%</b>.
            The priority issues and the recovery plan are below.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_threat_board(df, plan):
    st.markdown("### ⚠️ What needs your attention right now")
    st.caption("The loudest criticism, surfaced first — each item is paired with a next step further down.")

    issue = plan.get("issue")
    if issue:
        state = issue.get("top_state") or "multiple regions"
        age = issue.get("top_age") or "a broad audience"
        _card(
            f"""
            <div style='display:flex; justify-content:space-between; align-items:flex-start; gap:12px;'>
              <div>
                <div style='font-size:0.75rem; color:{NEG}; font-weight:800; text-transform:uppercase;'>#1 Priority Issue</div>
                <div style='font-size:1.35rem; font-weight:800; color:#fff; margin:2px 0;'>“{issue['topic']}”</div>
                <div style='color:var(--text-2); font-size:0.9rem;'>
                  Driven by <b>{issue['driving_emotion']}</b> · loudest in <b>{state}</b> · resonates most with <b>{age}</b>
                </div>
              </div>
              <div style='text-align:right; min-width:120px;'>
                <div style='font-size:2rem; font-weight:800; color:{NEG};'>{issue['neg_pct']}%</div>
                <div style='font-size:0.72rem; color:var(--text-mute);'>negative · {issue['volume']} posts · reach {issue['reach']:,}</div>
              </div>
            </div>
            <div style='margin-top:10px; padding:8px 10px; background:var(--neg-bg); border-radius:8px;
                 font-size:0.85rem; color:#fecaca;'>💬 “{issue['sample_text']}”</div>
            """,
            border=NEG,
        )

    # A dense feed of the loudest negative items (news + social mixed).
    neg_df = df[df["sentiment"] == "negative"].copy()
    if not neg_df.empty:
        neg_df = neg_df.sort_values("engagement", ascending=False).head(6)
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (_, r) in enumerate(neg_df.iterrows()):
            with cols[i % 2]:
                who = str(r.get("author_name") or r.get("author") or "user")
                plat = str(r.get("platform", ""))
                loc = f" · 📍{r['india_state']}" if r.get("india_state") else ""
                url = r.get("url") or ""
                body = str(r.get("text", ""))[:180]
                inner = (
                    f"<div style='font-size:0.72rem; color:var(--text-mute); font-weight:700;'>"
                    f"{plat.upper()} · {who}{loc}</div>"
                    f"<div style='font-size:0.85rem; color:var(--text-2); margin-top:4px;'>{body}…</div>"
                    + (f"<div style='margin-top:6px;'><span style='font-size:0.72rem; color:{ACCENT}; font-weight:700;'>🔗 open →</span></div>" if url else "")
                )
                if url:
                    st.markdown(
                        f"<a href='{url}' target='_blank' style='text-decoration:none;color:inherit;'>"
                        f"<div class='socio-card card-border-neg' style='text-align:left;'>{inner}</div></a>",
                        unsafe_allow_html=True,
                    )
                else:
                    _card(inner, border=NEG)


def _render_sentiment_emotion(df, stats):
    c1, c2 = st.columns([1, 1])
    with c1:
        donut = go.Figure(go.Pie(
            labels=["Positive", "Negative", "Neutral"],
            values=[stats.get("positive", 0), stats.get("negative", 0), stats.get("neutral", 0)],
            hole=0.62, marker=dict(colors=[POS, NEG, NEU]),
            textinfo="percent", sort=False,
        ))
        donut.update_layout(title="Overall sentiment mix")
        _plot(_fig_base(donut, height=300), key="brief_donut")
    with c2:
        if "emotion" in df.columns:
            emo = df["emotion"].value_counts().reset_index()
            emo.columns = ["emotion", "count"]
            emap = {"love": POS, "joy": POS, "neutral": "#64748b", "fear": "#8b5cf6",
                    "sadness": INFO, "anger": NEU, "hate": NEG}
            bar = px.bar(emo, x="count", y="emotion", orientation="h",
                         color="emotion", color_discrete_map=emap)
            bar.update_layout(title="What emotion is driving the conversation", yaxis=dict(autorange="reversed"))
            _plot(_fig_base(bar, height=300, legend=False), key="brief_emo")


def _render_verbatim(df):
    c1, c2 = st.columns(2)
    neg = df[df["sentiment"] == "negative"].sort_values("engagement", ascending=False)
    pos = df[df["sentiment"] == "positive"].sort_values("engagement", ascending=False)
    with c1:
        st.markdown(f"<b style='color:{NEG}'>Loudest criticism</b>", unsafe_allow_html=True)
        if not neg.empty:
            r = neg.iloc[0]
            _card(f"<div style='font-size:0.9rem;color:var(--text-2)'>“{str(r['text'])[:220]}”</div>"
                  f"<div style='font-size:0.72rem;color:var(--text-mute);margin-top:6px'>— {r.get('author_name') or r.get('author')} · {r.get('platform')}</div>",
                  border=NEG)
        else:
            st.caption("No negative posts in this set.")
    with c2:
        st.markdown(f"<b style='color:{POS}'>Strongest support</b>", unsafe_allow_html=True)
        if not pos.empty:
            r = pos.iloc[0]
            _card(f"<div style='font-size:0.9rem;color:var(--text-2)'>“{str(r['text'])[:220]}”</div>"
                  f"<div style='font-size:0.72rem;color:var(--text-mute);margin-top:6px'>— {r.get('author_name') or r.get('author')} · {r.get('platform')}</div>",
                  border=POS)
        else:
            st.caption("No positive posts in this set.")


def _render_media_vs_public(df):
    split = split_media_vs_public(df)
    m, p, gap = split["media"], split["public"], split["gap"]

    c1, c2 = st.columns(2)
    for col, title, b, icon in [(c1, "Mainstream media", m, "📰"), (c2, "Public voice", p, "🗣️")]:
        with col:
            posv = b["positivity"]
            color = POS if (posv or 0) >= 55 else (NEG if (posv or 100) < 40 else NEU)
            _card(
                f"<div style='font-size:0.75rem;color:var(--text-mute);font-weight:700;text-transform:uppercase'>{icon} {title}</div>"
                f"<div style='font-size:1.8rem;font-weight:800;color:{color}'>{posv if posv is not None else '—'}%<span style='font-size:0.8rem;color:var(--text-mute);font-weight:600'> positivity</span></div>"
                f"<div style='font-size:0.8rem;color:var(--text-2)'>{b['total']} mentions · {b['pos_pct']}% pos / {b['neg_pct']}% neg · top emotion: <b>{b['top_emotion']}</b></div>",
                border=color,
            )

    # Grouped comparison bar.
    comp = pd.DataFrame([
        {"Source": "Media", "Sentiment": "Positive", "Pct": m["pos_pct"]},
        {"Source": "Media", "Sentiment": "Negative", "Pct": m["neg_pct"]},
        {"Source": "Media", "Sentiment": "Neutral", "Pct": m["neu_pct"]},
        {"Source": "Public", "Sentiment": "Positive", "Pct": p["pos_pct"]},
        {"Source": "Public", "Sentiment": "Negative", "Pct": p["neg_pct"]},
        {"Source": "Public", "Sentiment": "Neutral", "Pct": p["neu_pct"]},
    ])
    fig = px.bar(comp, x="Source", y="Pct", color="Sentiment", barmode="group",
                 color_discrete_map={"Positive": POS, "Negative": NEG, "Neutral": NEU},
                 text="Pct")
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
    fig.update_layout(title="Sentiment split: press vs. grassroots")
    _plot(_fig_base(fig, height=300), key="brief_mvp")

    gp = gap.get("positivity_gap")
    gcolor = INFO if gp is None else (POS if gp >= 0 else NEG)
    _card(f"<div style='color:{gcolor};font-weight:700'>Read:</div>"
          f"<div style='color:var(--text-2);font-size:0.92rem'>{split['verdict']}</div>", border=gcolor)


def _render_region_age(df, plan):
    c1, c2 = st.columns([1.15, 1])
    with c1:
        geo = aggregate_india_state_sentiments(df)
        if geo is not None and not geo.empty:
            fig = px.scatter_geo(
                geo, lat="lat", lon="lon", size="mentions", color="avg_score",
                color_continuous_scale=[[0, NEG], [0.5, NEU], [1, POS]],
                range_color=[-1, 1], hover_name="state",
                hover_data={"mentions": True, "negative_pct": True, "top_city": True,
                            "lat": False, "lon": False, "avg_score": ":.2f"},
                projection="mercator",
            )
            fig.update_geos(scope="asia", center=dict(lat=22, lon=80),
                            lataxis_range=[6, 37], lonaxis_range=[68, 98],
                            bgcolor="rgba(0,0,0,0)", showland=True,
                            landcolor="#1e293b", showcountries=True,
                            countrycolor="#334155", showcoastlines=False)
            fig.update_layout(title="Sentiment by state (bubble = volume, colour = mood)",
                              coloraxis_colorbar=dict(title="mood"))
            _plot(_fig_base(fig, height=380, legend=False), key="brief_map")
            st.caption("Content-based inference from text mentions — not GPS. Directional only.")
        else:
            st.info("No Indian-state signal detected in this set (region is inferred from post text).")
    with c2:
        if "age_group" in df.columns:
            ag = (df.groupby(["age_group", "sentiment"]).size()
                  .reset_index(name="count"))
            fig = px.bar(ag, x="age_group", y="count", color="sentiment",
                         color_discrete_map={"positive": POS, "negative": NEG, "neutral": NEU},
                         barmode="stack")
            fig.update_layout(title="Sentiment by inferred age band",
                              xaxis=dict(tickangle=-20))
            _plot(_fig_base(fig, height=380), key="brief_age")
            st.caption("Age is inferred from language/platform — not disclosed by any API.")

    # Priority callouts.
    reg, age = plan.get("region"), plan.get("age")
    cc1, cc2 = st.columns(2)
    with cc1:
        if reg:
            city = f" (esp. {reg['top_city']})" if reg.get("top_city") else ""
            _card(f"<div style='font-size:0.72rem;color:{NEG};font-weight:800;text-transform:uppercase'>Target region first</div>"
                  f"<div style='font-size:1.15rem;font-weight:800;color:#fff'>{reg['state']}{city}</div>"
                  f"<div style='font-size:0.82rem;color:var(--text-2)'>{reg['neg_pct']}% negative · {reg['mentions']} mentions · drivers: {', '.join(reg['local_drivers'][:3])}</div>",
                  border=NEG)
    with cc2:
        if age:
            _card(f"<div style='font-size:0.72rem;color:{NEG};font-weight:800;text-transform:uppercase'>Coldest audience</div>"
                  f"<div style='font-size:1.15rem;font-weight:800;color:#fff'>{age['age_group']}</div>"
                  f"<div style='font-size:0.82rem;color:var(--text-2)'>{age['neg_pct']}% negative · {age['mentions']} mentions</div>",
                  border=NEG)


def _render_similarity(df, term):
    sim = build_topic_matrix(df, search_term=term, top_k=10)
    if not sim["labels"] or len(sim["labels"]) < 2:
        st.info("Not enough recurring topics to map a narrative web yet.")
        return
    labels = sim["labels"]
    # Colour axis labels by how negative each topic is.
    heat = go.Figure(go.Heatmap(
        z=sim["matrix"], x=labels, y=labels,
        colorscale=[[0, "#0f172a"], [0.5, ACCENT], [1, "#5eead4"]],
        zmin=0, zmax=1, hoverongaps=False,
        colorbar=dict(title="link"),
    ))
    heat.update_layout(title="Topic co-occurrence (brighter = more often said together)")
    heat.update_yaxes(autorange="reversed")
    _plot(_fig_base(heat, height=420, legend=False), key="brief_sim")

    links = sim["links"][:4]
    if links:
        chips = ""
        for a, b, s in links:
            an, bn = sim["neg_pct"].get(a, 0), sim["neg_pct"].get(b, 0)
            hostile = "🔴" if max(an, bn) >= 50 else "⚪"
            chips += (f"<span style='display:inline-block;background:rgba(255,255,255,0.05);"
                      f"border:1px solid var(--border);border-radius:14px;padding:4px 10px;margin:3px;"
                      f"font-size:0.8rem'>{hostile} <b>{a}</b> ↔ <b>{b}</b> "
                      f"<span style='color:var(--text-mute)'>({s:.2f})</span></span>")
        _card(f"<div style='font-size:0.85rem;color:var(--text-2);margin-bottom:6px'>"
              f"These topics keep appearing together — that linkage is the story being built around the name "
              f"(🔴 = the pairing skews hostile):</div>{chips}", border=ACCENT)


def _render_history(term):
    hist = storage.load_history(term=term)
    if hist is None or len(hist) < 2:
        st.info("Only one scan on record for this target so far. Run scans over several days "
                "to chart how the image is shifting — each scan is saved automatically.")
        return
    hist = hist.sort_values("ts")
    c1, c2 = st.columns([1.3, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist["ts"], y=hist["positivity_ratio"], mode="lines+markers",
                                 name="Positivity %", line=dict(color=POS, width=3)))
        fig.add_trace(go.Scatter(x=hist["ts"], y=hist["avg_score"] * 100, mode="lines+markers",
                                 name="Avg score (×100)", line=dict(color=ACCENT, width=2, dash="dot")))
        fig.update_layout(title="Image trajectory across past scans")
        _plot(_fig_base(fig, height=320), key="brief_hist")
    with c2:
        st.markdown("<b>Dominant emotion, scan by scan</b>", unsafe_allow_html=True)
        emo_rows = hist[["ts", "dominant_emotion"]].tail(8).iloc[::-1]
        for _, r in emo_rows.iterrows():
            when = pd.to_datetime(r["ts"]).strftime("%b %d %H:%M")
            _card(f"<div style='display:flex;justify-content:space-between'>"
                  f"<span style='color:var(--text-mute);font-size:0.8rem'>{when}</span>"
                  f"<b style='color:#fff'>{str(r['dominant_emotion']).title()}</b></div>")


def _render_plan(plan, stats):
    st.caption("Sequenced from the data above — biggest issue first, then region, then audience, then a durable positive story.")
    phases = plan.get("phases", [])
    for ph in phases:
        steps_html = "".join(
            f"<li style='margin:3px 0;color:var(--text-2);font-size:0.88rem'>{s}</li>" for s in ph["steps"]
        )
        _card(
            f"<div style='display:flex;justify-content:space-between;align-items:center'>"
            f"<div style='font-size:0.72rem;color:{ACCENT};font-weight:800;text-transform:uppercase'>{ph['window']}</div>"
            f"<div style='font-size:0.75rem;color:var(--text-mute)'>{ph['playbook']}</div></div>"
            f"<div style='font-size:1.02rem;font-weight:700;color:#fff;margin:4px 0 8px'>{ph['goal']}</div>"
            f"<ul style='margin:0;padding-left:18px'>{steps_html}</ul>",
            border=ACCENT,
        )

    forecast = plan.get("forecast")
    if forecast and stats.get("total"):
        st.markdown("#### 📊 If these moves land — modelled forecast")
        comp = pd.DataFrame([
            {"Stage": "Now", "Sentiment": "Positive", "Count": stats.get("positive", 0)},
            {"Stage": "Now", "Sentiment": "Negative", "Count": stats.get("negative", 0)},
            {"Stage": "After plan", "Sentiment": "Positive", "Count": forecast["positive"]},
            {"Stage": "After plan", "Sentiment": "Negative", "Count": forecast["negative"]},
        ])
        fig = px.bar(comp, x="Stage", y="Count", color="Sentiment", barmode="group",
                     color_discrete_map={"Positive": POS, "Negative": NEG})
        fig.update_layout(title="Projected shift in the opinionated conversation")
        c1, c2 = st.columns([1.4, 1])
        with c1:
            _plot(_fig_base(fig, height=280), key="brief_forecast")
        with c2:
            now_p = stats.get("positivity_ratio") or 0
            proj_p = forecast.get("positivity_ratio") or 0
            delta = round(proj_p - now_p, 1)
            _card(
                f"<div style='font-size:0.75rem;color:var(--text-mute);text-transform:uppercase;font-weight:700'>Positivity index</div>"
                f"<div style='font-size:2.2rem;font-weight:800;color:{POS}'>{now_p:.0f}% → {proj_p:.0f}%</div>"
                f"<div style='font-size:0.9rem;color:{(POS if delta>=0 else NEG)};font-weight:700'>{'+' if delta>=0 else ''}{delta} pts projected</div>"
                f"<div style='font-size:0.75rem;color:var(--text-mute);margin-top:6px'>Directional model based on the selected playbooks — not a guarantee.</div>",
                border=POS,
            )
        st.info("➡️ Open **🤖 Phase 3: Crisis Remediation Desk** to run the interactive simulator and tune each action.")
