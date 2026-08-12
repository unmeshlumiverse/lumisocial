"""
Report generator (inspired by BettaFish's ReportEngine, rebuilt free & compliant).

Turns one monitoring run into a polished, standalone HTML report you can download
and share — executive summary, sentiment, emotions, hot topics, top voices, the
loudest post, and an estimated-region breakdown. No LLM, no database, no cost.
"""

import datetime as dt
import html


def _bar_row(label, value, total, color):
    pct = (100 * value / total) if total else 0
    return (
        f'<div class="bar-row"><span class="bar-label">{html.escape(str(label))}</span>'
        f'<span class="bar-track"><span class="bar-fill" style="width:{pct:.1f}%;'
        f'background:{color}"></span></span>'
        f'<span class="bar-val">{value} ({pct:.0f}%)</span></div>'
    )


def _summary_sentence(term, stats, dominant, dominant_emotion):
    if stats["total"] == 0:
        return f"No mentions of “{html.escape(term)}” were found in this run."
    pr = stats["positivity_ratio"]
    pr_txt = f"{pr:.0f}% of opinionated posts were positive" if pr is not None else "sentiment was mostly neutral"
    return (
        f"Across {stats['total']} recent posts mentioning “{html.escape(term)}”, the overall mood was "
        f"<strong>{dominant}</strong> and the most common emotion was <strong>{dominant_emotion}</strong>. "
        f"{pr_txt}, with {stats['negative']} clearly negative and {stats['positive']} clearly positive posts."
    )


def build_html_report(term, df, stats, words, tags, authors, top_posts, themes=None):
    """Return a complete standalone HTML report as a string."""
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Dominant mood + emotion
    dominant = max([("positive", stats["positive"]), ("negative", stats["negative"]),
                    ("neutral", stats["neutral"])], key=lambda x: x[1])[0]
    emo_counts = df["emotion"].value_counts()
    non_neutral = emo_counts.drop(labels=["neutral"], errors="ignore")
    dominant_emotion = (non_neutral.idxmax() if not non_neutral.empty
                        else (emo_counts.idxmax() if not emo_counts.empty else "neutral"))

    total = stats["total"]

    # Sentiment bars
    sent_html = "".join([
        _bar_row("Positive", stats["positive"], total, "#2ecc71"),
        _bar_row("Neutral", stats["neutral"], total, "#bdc3c7"),
        _bar_row("Negative", stats["negative"], total, "#e74c3c"),
    ])

    # Emotion bars
    emo_colors = {"love": "#2ecc71", "joy": "#82e0aa", "neutral": "#bdc3c7",
                  "fear": "#f39c12", "sadness": "#5dade2", "anger": "#e67e22", "hate": "#e74c3c"}
    emo_html = "".join(
        _bar_row(e, int(c), total, emo_colors.get(e, "#888"))
        for e, c in emo_counts.items()
    )

    # Platform breakdown
    plat_counts = df["platform"].value_counts()
    plat_html = "".join(_bar_row(p, int(c), total, "#3498db") for p, c in plat_counts.items())

    # Hot topics + hashtags
    topic_html = "".join(
        f'<span class="chip">{html.escape(w)} <b>{c}</b></span>' for w, c in words[:15]
    ) or "<em>Not enough text to extract topics.</em>"
    tag_html = "".join(
        f'<span class="chip tag">#{html.escape(t)} <b>{c}</b></span>' for t, c in tags[:12]
    ) or "<em>No hashtags found.</em>"

    # Region estimate
    region_counts = df["country"].value_counts()
    region_html = "".join(_bar_row(r, int(c), total, "#9b59b6") for r, c in region_counts.items())

    # Top voices table
    voices_rows = ""
    for _, r in authors.head(8).iterrows():
        voices_rows += (
            f"<tr><td>{html.escape(str(r['author']))}</td>"
            f"<td>{html.escape(str(r['platform']))}</td>"
            f"<td>{int(r['posts'])}</td>"
            f"<td>{int(r['total_engagement'])}</td>"
            f"<td>{r['avg_sentiment']:+.2f}</td></tr>"
        )

    # Top posts
    posts_html = ""
    for _, r in top_posts.head(8).iterrows():
        link = f'<a href="{html.escape(str(r["url"]))}" target="_blank">source</a>' if r["url"] else ""
        posts_html += (
            f'<div class="post"><div class="post-meta"><b>@{html.escape(str(r["author"]))}</b> '
            f'· {html.escape(str(r["platform"]))} · {html.escape(str(r["sentiment"]))} '
            f'/ {html.escape(str(r["emotion"]))} · 👍 {int(r["engagement"])} {link}</div>'
            f'<div class="post-text">{html.escape(str(r["text"])[:400])}</div></div>'
        )

    # Narratives / themes
    themes_html = ""
    if themes:
        for t in themes:
            s = t["avg_sentiment"]
            color = "#2ecc71" if s >= 0.05 else ("#e74c3c" if s <= -0.05 else "#bdc3c7")
            link = f' — <a href="{html.escape(str(t["example_url"]))}" target="_blank">source</a>' if t.get("example_url") else ""
            themes_html += (
                f'<div class="theme" style="border-left:5px solid {color}">'
                f'<div class="theme-head"><b>{html.escape(t["label"])}</b> · {t["size"]} posts · '
                f'{html.escape(t["emotion"])} · sentiment {s:+.2f} · <i>{html.escape(t["platforms"])}</i></div>'
                f'<div class="theme-ex">“{html.escape(str(t["example"]))}” — '
                f'<b>@{html.escape(str(t["example_author"]))}</b>{link}</div></div>'
            )
    themes_section = f"<h2>Main narratives</h2>{themes_html}" if themes_html else ""

    loudest = top_posts.iloc[0] if not top_posts.empty else None
    loudest_html = ""
    if loudest is not None:
        llink = f'<a href="{html.escape(str(loudest["url"]))}" target="_blank">View original →</a>' if loudest["url"] else ""
        loudest_html = (
            f'<div class="loudest"><div class="post-meta"><b>@{html.escape(str(loudest["author"]))}</b> '
            f'· {html.escape(str(loudest["platform"]))} · 👍 {int(loudest["engagement"])} engagement · '
            f'{html.escape(str(loudest["sentiment"]))} / {html.escape(str(loudest["emotion"]))}</div>'
            f'<div class="post-text">{html.escape(str(loudest["text"])[:500])}</div>{llink}</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Sentiment Report — {html.escape(term)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         color:#1a1a1a; max-width:860px; margin:0 auto; padding:40px 24px; line-height:1.55; }}
  h1 {{ font-size:26px; margin-bottom:4px; }}
  .sub {{ color:#666; font-size:13px; margin-bottom:28px; }}
  h2 {{ font-size:18px; margin-top:34px; border-bottom:2px solid #eee; padding-bottom:6px; }}
  .exec {{ background:#f7f9fc; border-left:4px solid #3498db; padding:14px 18px; border-radius:6px; }}
  .kpis {{ display:flex; gap:14px; flex-wrap:wrap; margin:18px 0; }}
  .kpi {{ flex:1; min-width:120px; background:#fff; border:1px solid #eee; border-radius:8px;
          padding:12px 14px; box-shadow:0 1px 3px rgba(0,0,0,.05); }}
  .kpi .n {{ font-size:22px; font-weight:700; }}
  .kpi .l {{ font-size:12px; color:#777; }}
  .bar-row {{ display:flex; align-items:center; gap:10px; margin:5px 0; font-size:13px; }}
  .bar-label {{ width:110px; }}
  .bar-track {{ flex:1; background:#f0f0f0; border-radius:6px; height:14px; overflow:hidden; }}
  .bar-fill {{ display:block; height:100%; }}
  .bar-val {{ width:90px; text-align:right; color:#555; }}
  .chip {{ display:inline-block; background:#eef2f7; border-radius:14px; padding:3px 10px;
           margin:3px; font-size:13px; }}
  .chip.tag {{ background:#eafaf1; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:7px 8px; border-bottom:1px solid #eee; }}
  th {{ color:#666; font-weight:600; }}
  .post {{ border:1px solid #eee; border-radius:8px; padding:10px 12px; margin:8px 0; }}
  .post-meta {{ font-size:12px; color:#666; margin-bottom:4px; }}
  .post-text {{ font-size:14px; }}
  .loudest {{ background:#fff8f0; border:1px solid #ffe0c0; border-radius:8px; padding:14px 16px; }}
  .theme {{ background:#fafbfc; border:1px solid #eee; border-radius:6px; padding:10px 14px; margin:8px 0; }}
  .theme-head {{ font-size:14px; }}
  .theme-ex {{ font-size:13px; color:#555; margin-top:4px; }}
  .warn {{ font-size:12px; color:#a94442; background:#fdf3f3; padding:8px 12px; border-radius:6px; }}
  footer {{ margin-top:40px; color:#999; font-size:12px; border-top:1px solid #eee; padding-top:12px; }}
</style></head><body>

<h1>Sentiment &amp; Public-Opinion Report</h1>
<div class="sub">Subject: <b>{html.escape(term)}</b> · Generated {now} · Sources: {', '.join(sorted(df['platform'].unique()))}</div>

<h2>Executive summary</h2>
<div class="exec">{_summary_sentence(term, stats, dominant, dominant_emotion)}</div>

<div class="kpis">
  <div class="kpi"><div class="n">{total}</div><div class="l">Total mentions</div></div>
  <div class="kpi"><div class="n">{dominant.title()}</div><div class="l">Dominant mood</div></div>
  <div class="kpi"><div class="n">{dominant_emotion.title()}</div><div class="l">Top emotion</div></div>
  <div class="kpi"><div class="n">{(str(stats['positivity_ratio'])+'%') if stats['positivity_ratio'] is not None else '—'}</div><div class="l">Positivity ratio</div></div>
</div>

<h2>Sentiment breakdown</h2>{sent_html}
<h2>Emotion breakdown</h2>{emo_html}
<h2>Mentions by platform</h2>{plat_html}

<h2>Hot topics</h2><div>{topic_html}</div>
<h2>Top hashtags</h2><div>{tag_html}</div>

{themes_section}

<h2>Loudest post</h2>{loudest_html or '<em>None.</em>'}

<h2>Most-reached voices</h2>
<table><tr><th>User</th><th>Platform</th><th>Posts</th><th>Engagement</th><th>Avg sentiment</th></tr>
{voices_rows}</table>

<h2>Top posts</h2>{posts_html}

<h2>Estimated region</h2>
<div class="warn">⚠️ Estimate only — based on language/keywords in text, not real geolocation.</div>
{region_html}

<footer>Generated by Public Figure Monitor. Sentiment via VADER; emotion &amp; region are
heuristic estimates. Figures reflect a sample of recent public posts, not the full platform.</footer>
</body></html>"""
