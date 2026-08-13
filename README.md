# LUMISOCIAL — Public Figure Monitor

A free, self-hostable **social-listening command center** for tracking a public
figure or brand. Type a name (or a `@username` / `#hashtag`), and it pulls recent
public chatter from ten free, terms-compliant sources and turns it into a single
strategic read: what people think, where the criticism is loudest, how the press
narrative differs from the street, and what to do about it.

Built to run at **$0** — no paid APIs, no database server, no scraping. Optional
local AI models make it smarter (especially for Hindi and other Indian languages)
but are never required.

> **⚠️ Read `SECURITY_README.md` first.** This package ships **without** real
> credentials — the `.env`, the Telegram `.session`, and the local history DB were
> intentionally removed so the zip is safe to share. Copy `.env.example → .env`
> and add your own keys (all optional).

---

## Table of contents

1. [The 5-phase workflow](#the-5-phase-workflow)
2. [What's new in this build](#whats-new-in-this-build)
3. [Data sources](#data-sources)
4. [Quick start](#quick-start-2-minutes-no-keys)
5. [Credentials setup](#credentials-setup-all-optional)
6. [Optional AI stack](#optional-ai-stack-free-but-heavy)
7. [History & scheduled runs](#history--scheduled-runs)
8. [Deploying for 24/7 uptime](#deploying-for-247-uptime)
9. [Project structure](#project-structure)
10. [Honest limits — please read](#honest-limits--please-read)
11. [What is deliberately not included](#what-is-deliberately-not-included)
12. [Troubleshooting](#troubleshooting)

---

## The 5-phase workflow

The dashboard is organized as a top row of phases. Phase 0 is the default landing
view; the rest let you drill down.

| Phase | Name | What it's for |
|-------|------|---------------|
| **🧭 0** | **Executive Brief** | The one-screen strategic read. Problems first, each paired with a next step, ending in an action plan + forecast. |
| **📥 1** | **Ingested Feeds** | The raw, unfiltered stream of every post/article collected, with poster ID and link. |
| **📊 2** | **Sentiment & Topic Analysis** | Deep-dive charts: sentiment split, emotions, hot topics, top voices, India state/city map, per-topic crisis warnings. |
| **🤖 3** | **Crisis Remediation Desk** | Interactive simulator — pick response levers for a scenario and model the sentiment recovery. |
| **⚙️ 4** | **Command Center Administration** | Profile validation (social-analyzer), name-origin lookup, and settings. |

### The Executive Brief (Phase 0), section by section

1. **Bottom-line verdict** on the current image, in one line.
2. **⚠️ What needs attention now** — the loudest criticism surfaced first, with the
   #1 priority issue called out (topic, negativity %, reach, driving emotion,
   hottest region and audience).
3. **🧠 What people actually think** — sentiment donut, emotion breakdown, and the
   strongest verbatim criticism vs. support side by side.
4. **📰 Media image vs. 🗣️ public opinion** — splits press coverage (newspapers /
   Google News / GDELT) from grassroots voice (Reddit, Bluesky, YouTube,
   Telegram, …) and flags when the two narratives diverge.
5. **🗺️ Where & 👥 who** — a geographic map of Indian state sentiment (bubble =
   volume, colour = mood) plus a sentiment-by-age-band chart, naming the priority
   region and the coldest audience.
6. **🕸️ The narrative web** — a **topic similarity / co-occurrence matrix** (heatmap)
   showing which themes are being fused into a single story about the name.
7. **📈 Image over time** — the trajectory of positivity and dominant emotion across
   past scans, pulled from saved run history.
8. **✅ The plan** — a sequenced **Now / 30-day / 60–90-day** plan, each step mapped
   to a remediation playbook, ending with a **modelled sentiment forecast** and a
   hand-off to the Phase 3 simulator.

> **Design note.** The brief leads with problems on purpose — surfacing negative
> signal prominently is the right job for a monitoring tool — but every problem is
> paired with a concrete next step. It's an honest priority board, not engineered
> anxiety.

---

## What's new in this build

Four new modules were added on top of the existing app; the mature 1,400-line
`app.py` was **not** rewritten — only three small hooks were added to wire the new
landing phase in.

| Module | Adds |
|--------|------|
| `brief.py` | The entire Phase 0 Executive Brief view. |
| `media_analysis.py` | Press-coverage vs. grassroots-opinion split and divergence verdict. |
| `similarity.py` | The topic co-occurrence / similarity matrix (the heatmap). |
| `strategy.py` | Priority issue / region / age detection + the sequenced action plan. |

All four are **free, offline, and deterministic** — no network, no paid model.

---

## Data sources

Ten sources, all free and terms-compliant. Enable whichever you want in the sidebar.

| Source | Auth | Notes |
|--------|------|-------|
| **Bluesky** | none | Public search, works out of the box. |
| **Indian Newspapers** | none | 30+ national + regional outlet RSS feeds. |
| **Google News** | none | Multiple language editions. |
| **GDELT** | none | Real historical news archive back to 2017 — this is what makes "All Available Data" mean *all time*. |
| **Mastodon** | none | Public hashtag timeline. |
| **Hacker News** | none | Via the Algolia API. |
| **Reddit** | free key | Public subreddits/threads via PRAW (read-only). |
| **YouTube** | free key | Comments via Data API v3 (10k units/day free). |
| **Telegram** | free login | Searches public channels you list (Telethon). |
| **Twitter / X** | free-tier token | API v2 — last ~7 days only (platform limit). |

---

## Quick start (2 minutes, no keys)

```bash
cd LUMISOCIAL
pip install -r requirements.txt
streamlit run app.py
```

Bluesky needs **no setup** — tick it in the sidebar, type a name, and click **Run
Intelligence Report**. Add the other sources or the AI models as described below.

**Login:** the app opens on a gate screen; the default sandbox credentials are
shown on that screen.

> **⚠️ If you deploy this publicly (e.g. Streamlit Cloud), change the default
> admin password first.** `admin@lumisocial.com` / `admin123` is seeded
> automatically on first run and is printed on the login screen itself — on a
> public URL that's a published credential, not a secret. It's a `SUPER_ADMIN`
> account that can create/delete other users and **write real API keys to
> `.env`** from Phase 4. Log in once, go to **Phase 4 → Team Management**,
> create your own `SUPER_ADMIN` account, then delete the seeded `admin` user.

---

## Credentials setup (all optional)

Copy the template and fill in only the keys you have:

```bash
cp .env.example .env
```

Every connector **degrades gracefully** — if a key is missing, that source shows a
friendly "setup" card and is skipped; nothing crashes, and the no-auth sources keep
working. See `api_credentials_guide.md` for step-by-step provider instructions.

- **Reddit** — create a *script* app at <https://www.reddit.com/prefs/apps>, then set
  `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`.
- **YouTube** — enable *YouTube Data API v3* at <https://console.cloud.google.com/>,
  create an API key, set `YOUTUBE_API_KEY`.
- **Twitter / X** — set `TWITTER_BEARER_TOKEN` from <https://developer.x.com/>.
- **Telegram** — get `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` at
  <https://my.telegram.org>, then run the one-time login:
  ```bash
  python telegram_login.py
  ```
  This creates a `monitor.session` file (reused automatically afterwards). In the
  sidebar, list the public channels to search — Telegram has no global search, so
  you choose which public channels to monitor.

---

## Optional AI stack (free, but heavy)

The app ships with fast, free defaults (VADER for sentiment, a keyword lexicon for
emotion, TF-IDF for clustering). The AI models are **also free of money cost**, but
they're **heavier** — a one-time ~1 GB download and more RAM/CPU — and noticeably
smarter, especially for Hindi and other Indian languages that VADER can't read.

```bash
pip install -r requirements-ai.txt
```

Then set the sidebar **Sentiment engine** to **AI multilingual** (or **Ensemble**).
That one switch upgrades all three layers:

| Feature | Default (instant) | With AI stack (heavier) |
|---------|-------------------|--------------------------|
| Sentiment | VADER (English only) | `cardiffnlp/twitter-xlm-roberta-base-sentiment` — multilingual, reads Hindi, better on sarcasm |
| Emotion | keyword lexicon | `SamLowe/roberta-base-go_emotions` — 28 emotions mapped to our set |
| Narratives | TF-IDF + KMeans | `paraphrase-multilingual-MiniLM-L12-v2` embeddings + KMeans |

Models download once on first use, then cache. If the AI libraries aren't installed
or a model fails to load, the app **silently falls back** to the free defaults. The
models run entirely on your machine — nothing is sent to any paid API.

---

## History & scheduled runs

Every dashboard run auto-saves an aggregate snapshot to a local SQLite file
(`monitor_history.db`, created on first run). Re-running the same term builds a
trend line, which powers the "Image over time" section of the brief.

For automatic tracking, schedule headless runs:

```bash
python scheduled_run.py "Some Politician" --sources bluesky,reddit,news
python scheduled_run.py "#SomeTopic" --type hashtag --sources bluesky --limit 80
python scheduled_run.py "Name" --sources bluesky,telegram --tg-channels ndtv,indiatoday
```

Cron example (daily at 9am):

```cron
0 9 * * *  cd /path/to/LUMISOCIAL && /usr/bin/python scheduled_run.py "Name" --sources bluesky,reddit,news
```

Change the DB location with `export MONITOR_DB=/path/to/history.db`.

---

## Deploying for 24/7 uptime

Deployed on **Streamlit Community Cloud**, the app runs on Streamlit's servers —
reachable regardless of whether your laptop is on.

1. Push the repo to GitHub, then create an app at
   [share.streamlit.io](https://share.streamlit.io) pointing at `app.py`, branch `main`.
2. In **Settings → Secrets**, paste your keys as flat TOML (no `[section]` headers —
   Streamlit mirrors top-level secrets into `os.environ`, which every connector reads):
   ```toml
   YOUTUBE_API_KEY = "..."
   REDDIT_CLIENT_ID = "..."
   REDDIT_CLIENT_SECRET = "..."
   REDDIT_USER_AGENT = "lumisocial by u/yourusername"
   TWITTER_BEARER_TOKEN = "..."
   TELEGRAM_API_ID = "..."
   TELEGRAM_API_HASH = "..."
   ```
   Add only the keys for sources you use.
3. Save — Streamlit redeploys automatically on every push to `main`.
4. The free tier sleeps an idle app; the first visit wakes it in a few seconds
   (cold start, not downtime).
5. Telegram needs the one-time local login (`python telegram_login.py`) and its
   `monitor.session` uploaded alongside the repo, since secrets alone can't authorize it.

> **Never commit `.env` or `*.session`.** The included `.gitignore` already excludes them.

---

## Project structure

```
LUMISOCIAL/
├── app.py                    # Streamlit dashboard — the 5-phase command center
│
│   # ── new strategic layer ──
├── brief.py                  # Phase 0 Executive Brief (the strategic read)
├── media_analysis.py         # press-coverage vs. grassroots-opinion split
├── similarity.py             # topic co-occurrence / similarity matrix
├── strategy.py               # priority issue/region/age + sequenced action plan
│
│   # ── core engine ──
├── pipeline.py               # collect → normalize → score → enrich engine
├── sentiment.py              # VADER + optional multilingual AI (auto-fallback)
├── emotion.py                # keyword lexicon + optional AI GoEmotions (auto-fallback)
├── narratives.py             # theme clustering (AI embeddings / TF-IDF / keyword)
├── analysis.py               # hot topics, India state/region inference, top voices
├── demographics.py           # heuristic age-band inference from text/platform
├── keywords.py               # query expansion via rules + Wikidata aliases
├── remediation.py            # Phase 3 crisis scenarios + recovery simulator
├── storage.py                # SQLite run-history storage (trends)
├── report.py                 # downloadable HTML report builder
│
│   # ── connectors (all free/compliant) ──
├── connectors/
│   ├── bluesky.py            # public search, no auth
│   ├── indian_news.py        # 30+ Indian newspaper RSS feeds
│   ├── news.py               # Google News RSS, multi-language
│   ├── gdelt.py              # GDELT DOC 2.0 — historical archive back to 2017
│   ├── mastodon.py           # public hashtag timeline
│   ├── hackernews.py         # HN via Algolia API
│   ├── reddit.py             # PRAW read-only
│   ├── youtube.py            # comments via YouTube Data API v3
│   ├── telegram.py           # Telethon, public channels
│   └── twitter.py            # official API v2 (last ~7 days)
│
│   # ── OSINT sub-package (profile validator, Phase 4) ──
├── social-analyzer/          # bundled; imported by social_analyzer_helper.py
├── social_analyzer_helper.py # username validation + name-origin lookup (fail-safe)
│
│   # ── ops & docs ──
├── scheduled_run.py          # cron-friendly headless run → history DB
├── telegram_login.py         # one-time Telegram authorization
├── requirements.txt          # core deps ($0, always installed)
├── requirements-ai.txt       # optional AI add-ons (free but heavy)
├── .env.example              # credential template (copy to .env)
├── .gitignore                # excludes secrets, sessions, DB, caches
├── SECURITY_README.md        # what was stripped and how to handle keys
├── api_credentials_guide.md  # step-by-step provider setup
├── project_overview.md       # design notes
└── sample_report.html        # example of the exported report
```

The `social-analyzer` sub-package is optional at runtime: if it (or a heavy
dependency) is unavailable, the profile validator degrades to a clear message
instead of taking down the dashboard.

---

## Honest limits — please read

- **Geography is inference, not GPS.** Bluesky, Reddit, YouTube, Telegram, and news
  feeds don't attach location to posts. Countries and Indian states/cities are
  inferred from place names and language in the text, so many posts are "Unknown"
  and the map is **directional only**. Don't present it to your org as precise
  geography — real per-user location needs a paid data provider.
- **Age bands are inferred, not verified.** Age is a heuristic guess from language
  and platform cues, not any demographic API. Treat it as directional.
- **The forecast is a model, not a promise.** The recovery projection is a
  deterministic directional estimate of how sentiment might move if the suggested
  levers are pulled — not a guarantee.
- **Results are a sample, not the whole platform.** Each run reflects the recent
  public posts the free APIs return, not every post ever made.
- **No tool delivers "100% accurate" monitoring.** Always verify important claims at
  the original source.
- **Scope:** built for **public figures and brands**. Keep to public content and each
  platform's API terms; don't repurpose it to profile private individuals.

---

## What is deliberately not included

Some platforms have no free, terms-compliant way to search public posts about a
third party, so they're intentionally excluded rather than scraped:

- **Facebook / Instagram** — Meta's Graph API only returns *your own* pages/accounts;
  no public third-party mention search exists.
- **LinkedIn** — no third-party API for searching public posts, at any price.
- **X / Twitter** — full reading access is paid; the free-tier connector is included
  but limited to ~7 days.

If you add budget later, a paid data provider can bring these platforms in through a
single API without changing the rest of the app.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "AI models not installed — using VADER" | `pip install -r requirements-ai.txt` |
| First AI run slow / seems stuck | It's downloading models once; wait a few minutes. |
| Reddit / YouTube / Telegram error in sidebar | A credential env var is missing — recheck `.env`. |
| Telegram "session not authorized" | Run `python telegram_login.py` once. |
| Profile validator unavailable in Phase 4 | The `social-analyzer` sub-package or a dep didn't load; the rest of the app is unaffected. |
| No posts found | Try a broader term, enable **Expand search**, or add more sources. |

---

*Runs at $0 with no keys at all — keyed connectors just add Reddit, YouTube,
Telegram, and X coverage on top of the free defaults.*
