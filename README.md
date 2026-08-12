# LUMISOCIAL — Public Figure Monitor

A free, cloud-hosted social-listening command center. Type a public figure's name
(or a `@username` or `#hashtag`) and see what people are saying about them across
**Indian Newspapers, Google News, GDELT historical archive, Telegram, Twitter/X,
Bluesky, Reddit, and YouTube** — with sentiment, emotions, a state-wise India
breakdown, hot topics, top voices, a shareable report, and sentiment trends over
time.

Live at: **https://lumisocial.streamlit.app/** — runs on Streamlit Community
Cloud, so it's up 24/7 regardless of whether your own laptop is on (see
**[Deploying for 24/7 uptime](#-deploying-for-247-uptime-streamlit-community-cloud)**).

Built to run at **$0** — no paid APIs, no database server, no scraping. Optional
AI models make it smarter (see **[AI setup](#-ai-setup-optional-but-recommended)**),
but the app runs fully without them.

---

## What it does

- **Search** by name / keyword, `#hashtag`, or `@username mentions`.
- **9 sources**: Indian Newspaper RSS (30+ outlets), Google News (6 language editions),
  **GDELT** (real historical news archive back to 2017 — this is what makes "All
  Available Data" actually mean all time, not just what's currently published),
  Telegram, Twitter/X, Bluesky, Reddit, YouTube comments, Mastodon, Hacker News.
- **Time range that actually filters**: Past 24h / Past Week / Past Month / All
  Available Data — results are filtered to the selected window (not cosmetic).
- **Prospect disambiguation**: 3 optional sidebar questions (state/city, org or
  role, exclude terms) rule out namesakes and rank/badge the posts that actually
  match the right person — for common names where dozens of unrelated people
  share it.
- **Sentiment**: positive / negative / neutral, dominant mood, positivity ratio.
- **Emotions**: love / joy / anger / hate / fear / sadness, colour-coded.
- **India state/city detail**: an estimated state- and city-wise sentiment
  breakdown (inferred from text mentions, not real geolocation — see caveats).
- **Hot topics & hashtags**, **most-reached voices**, and the **loudest post**
  (with poster ID + link).
- **Keyword expansion** (optional): hashtag/name variants + real Wikidata aliases
  (incl. Hindi/Marathi) to catch more mentions.
- **Shareable HTML report** you can download and send to your org.
- **History & trends**: every run is saved so you can chart sentiment over time
  for the same prospect; schedule headless runs with `scheduled_run.py`.

---

## Quick start (works in 2 minutes, no keys)

```bash
cd social_monitor
pip install -r requirements.txt
streamlit run app.py
```

Bluesky needs **no setup** - tick it in the sidebar, type a name, click **Run
Intelligence Report**. To add the other sources or the AI models, see below.

---

## ☁️ Deploying for 24/7 uptime (Streamlit Community Cloud)

The app being reachable at all times has nothing to do with your laptop being on
— once it's deployed on Streamlit Community Cloud, it runs on Streamlit's own
servers. The one thing that actually needs doing is giving that cloud instance
your API keys, because **it never reads your local `.env` file** (that file only
exists on your machine and is gitignored on purpose — it should never be
committed).

1. Go to [share.streamlit.io](https://share.streamlit.io) → your app (or **New app**
   pointing at `unmeshlumiverse/lumisocial`, file `app.py`, branch `main`).
2. Open **Settings → Secrets** and paste your keys in flat TOML (no `[section]`
   headers — Streamlit mirrors top-level string secrets into `os.environ`, which
   is what every connector in this repo reads from):
   ```toml
   YOUTUBE_API_KEY = "..."
   REDDIT_CLIENT_ID = "..."
   REDDIT_CLIENT_SECRET = "..."
   REDDIT_USER_AGENT = "lumisocial by u/yourusername"
   TWITTER_BEARER_TOKEN = "..."
   TELEGRAM_API_ID = "..."
   TELEGRAM_API_HASH = "..."
   ```
   (Only add the keys for sources you actually use — every connector degrades
   gracefully and shows a sidebar warning if its key is missing, it never crashes
   the app.)
3. Save. Streamlit redeploys automatically and the app is live at your
   `*.streamlit.app` URL for anyone with the link — no laptop required, and it
   redeploys automatically on every push to `main`.
4. Streamlit Cloud's free tier sleeps an app after ~long inactivity; the **first**
   visit after that wakes it up in a few seconds. That's a cold-start delay, not
   downtime — the app and its code are always there, just spun down to save
   resources when nobody's using it.
5. Telegram is the one source that can't be configured through secrets alone —
   it needs the one-time interactive login (`python telegram_login.py`) run
   locally first, and the resulting `monitor.session` file uploaded alongside the
   repo (or re-run whenever the cloud instance's ephemeral disk resets it).

---

## 🧠 AI setup (optional, but recommended)

The app ships with fast, free defaults (VADER for sentiment, a keyword lexicon for
emotion, TF-IDF for clustering). The **AI models are also free of cost**, but they
are **heavier** - they download once (~1 GB total across models) and need more RAM
and CPU. They make the analysis noticeably smarter, especially for **Hindi and
other Indian languages**, which the default VADER cannot read at all.

### 1. Install the AI stack

```bash
pip install -r requirements-ai.txt
```

This installs `transformers`, `torch`, and `sentence-transformers`.

### 2. Turn it on

In the sidebar, set **Sentiment engine** to **AI multilingual** (or **Ensemble**).
That single switch activates all three AI upgrades at once:

| Feature    | Default (free, instant) | With AI stack (free, heavier)                          |
|------------|-------------------------|--------------------------------------------------------|
| Sentiment  | VADER (English only)    | `cardiffnlp/twitter-xlm-roberta-base-sentiment` - multilingual, reads Hindi, better on sarcasm |
| Emotion    | keyword lexicon         | `SamLowe/roberta-base-go_emotions` - 28 fine-grained emotions mapped to our 7 |
| Narratives | TF-IDF + KMeans         | `paraphrase-multilingual-MiniLM-L12-v2` embeddings + KMeans - semantic, multilingual |

### 3. What happens on first run

The first analysis after enabling AI will **download the models** (one-time, a few
minutes). Later runs reuse the cached models. Scoring is slower than the defaults
but far more accurate.

### 4. It never breaks

If the AI libraries aren't installed, or a model fails to load, the app **silently
falls back** to VADER + lexicon + TF-IDF and shows a note. You can always run at
$0 with zero AI dependencies.

> **Tip:** the AI models run entirely on your machine - nothing is sent to any
> paid API. "Free but heavy" means disk/RAM/CPU cost, not money.

---

## Data source setup

Each source is optional; enable what you want in the sidebar.

### Bluesky - no setup
Public search needs no account or key. Just tick it.

### Reddit - free app (2 min)
1. Go to <https://www.reddit.com/prefs/apps> -> **create another app** -> type **script**.
2. Copy the **client ID** (under the app name) and the **secret**.
3. Set environment variables:
   ```bash
   export REDDIT_CLIENT_ID="your_id"
   export REDDIT_CLIENT_SECRET="your_secret"
   export REDDIT_USER_AGENT="org-monitor by u/yourusername"
   ```
   (Windows: use `set` instead of `export`.)

### YouTube - free API key
1. In <https://console.cloud.google.com/> create a project, enable **YouTube Data API v3**, make an API key.
2. ```bash
   export YOUTUBE_API_KEY="your_key"
   ```
   Free quota (10,000 units/day) is plenty. It finds top videos about your term and analyses their comments.

### Google News - no key
Tick **Google News** and pick an edition (India / US / UK). That's it.

### Telegram - user login (one-time)
1. Get `api_id` + `api_hash` free at <https://my.telegram.org>.
2. ```bash
   export TELEGRAM_API_ID="12345"
   export TELEGRAM_API_HASH="your_hash"
   ```
3. Authorize once (enter phone + the code Telegram sends):
   ```bash
   python telegram_login.py
   ```
   This creates `monitor.session`, reused automatically afterwards.
4. In the sidebar, tick **Telegram** and list the public channel usernames to
   search (one per line, e.g. `ndtv`, `indiatoday`). Telegram has no global search,
   so you choose which public channels to monitor.

> **Tip:** put the `export` lines in a `.env` you `source` before running, or in
> your shell profile, so you don't retype them.

---

## Running the dashboard

```bash
streamlit run app.py
```

Enter a term in the sidebar, choose sources and the sentiment engine, optionally
tick **Expand search**, and click **Run analysis**. Download the HTML report or CSV
from the buttons at the bottom.

---

## History & scheduled runs (trends over time)

Every dashboard run auto-saves an aggregate snapshot to a local SQLite file
(`monitor_history.db`). Run the same term again to build a trend line; the
dashboard's **History & trends** section charts sentiment, positivity, and volume
over time.

For automatic tracking, schedule headless runs:

```bash
python scheduled_run.py "Some Politician" --sources bluesky,reddit,news
python scheduled_run.py "#SomeTopic" --type hashtag --sources bluesky --limit 80
python scheduled_run.py "Name" --sources bluesky,telegram --tg-channels ndtv,indiatoday
```

Cron example (every day at 9am):

```cron
0 9 * * *  cd /path/to/social_monitor && /usr/bin/python scheduled_run.py "Name" --sources bluesky,reddit,news
```

Change the DB location with `export MONITOR_DB=/path/to/history.db`.

---

## Project structure

```
app.py               # Streamlit dashboard (the single screen)
pipeline.py          # fetch -> score -> aggregate engine
connectors/
  bluesky.py         # free public search, no auth
  reddit.py          # PRAW read-only
  youtube.py         # comments via YouTube Data API v3, relevance+date+viewCount sweep
  telegram.py        # Telethon, searches public channels
  twitter.py         # official API v2 (last ~7 days only - platform limit)
  news.py            # Google News RSS, multi-window + multi-language (no key)
  indian_news.py      # 30+ Indian newspaper RSS feeds, national + regional (no key)
  gdelt.py            # GDELT DOC 2.0 API - real historical archive back to 2017 (no key)
  mastodon.py        # public hashtag timeline (no auth)
  hackernews.py      # HN via Algolia API (no key)
sentiment.py         # VADER + optional multilingual AI (auto-fallback)
emotion.py           # keyword lexicon + optional AI GoEmotions (auto-fallback)
analysis.py          # hot topics, region/country estimate, top voices
narratives.py        # clusters posts into themes (AI embeddings / TF-IDF / keyword)
keywords.py          # query expansion: rule variants + Wikidata aliases
report.py            # builds the downloadable HTML report
storage.py           # SQLite run-history storage (trends)
scheduled_run.py     # cron-friendly headless run -> history DB
telegram_login.py    # one-time Telegram authorization
test_engine.py       # offline smoke test (no network needed)
requirements.txt     # core deps ($0, always installed)
requirements-ai.txt  # optional AI add-ons (free but heavy)
```

Test the engine without network access:
```bash
python test_engine.py
```

---

## What is NOT available for free (and why)

Some platforms have no free, terms-compliant way to search public posts about a
person, so they are **deliberately not included**:

- **Facebook / Instagram** — Meta's Graph API only returns *your own* pages/accounts;
  there is no public post/mention search for third parties. Not possible for free.
- **LinkedIn** — no third-party API for searching public posts, at any price.
- **X / Twitter** — reading is paid (per-post or enterprise), not free.

Instead, this project uses seven sources that *are* free and compliant. If you have
budget later, a paid data provider can add the platforms above through one API.

Also note: **no tool delivers "100% accurate" news.** This app aggregates recent
coverage from Google News (multiple publishers); always verify important claims at
the original source.

## Honest caveats (please read)

- **The world map is an estimate, not real geolocation.** Bluesky/Reddit/YouTube/
  Telegram/News do **not** attach location to posts. Countries are guessed from
  language and keywords in the text, so most posts show as "Unknown" and the map is
  directional only. True per-country data needs a paid data provider - there's no
  free path to real geolocation on these networks. Don't present the map to your org
  as precise geography. The India state/city breakdown is likewise inferred from place names mentioned in the text, not from where users actually are.
- **AI models are free of money cost, but heavy** (large one-time downloads, more
  RAM/CPU, slower). They're optional and off by default; the app always works
  without them.
- **Results are a sample, not the whole platform.** Each run reflects recent public
  posts the free APIs return, not every post ever made.
- **Scope:** built for monitoring **public figures / brands**. Keep to public
  content and each platform's API terms. Don't repurpose it to profile private
  individuals.

---

## Adding more sources or upgrading models

- **New platform:** add a file in `connectors/` with a `search_x(query, limit)`
  function returning the same dict shape (see `pipeline.NORMALIZED_FIELDS`), then
  add it to the `sources` dict in `app.py`. Good free candidate: Mastodon.
- **Better sentiment/emotion:** swap the model name constants in `sentiment.py` /
  `emotion.py` for any compatible Hugging Face model.

---

## Troubleshooting

- **"AI models not installed - using VADER"**: run `pip install -r requirements-ai.txt`.
- **First AI run is slow / seems stuck**: it's downloading models; wait a few minutes once.
- **Reddit/YouTube/Telegram errors in the sidebar**: a credential env var is missing - recheck the setup above.
- **Telegram "session not authorized"**: run `python telegram_login.py` once.
- **No posts found**: try a broader term, enable **Expand search**, or add more sources.
