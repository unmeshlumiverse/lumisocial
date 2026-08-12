# API Credentials & Setup Guide

This guide details all the API keys and configurations needed to fully unlock all platform integrations (Reddit, YouTube, Telegram, and Bluesky) in the **Public Figure Monitor**.

---

## 1. Reddit Integration (Reddit API)
Reddit is used to search forum discussions and comments. It uses PRAW (Python Reddit API Wrapper) in read-only mode, which is completely free.

### Credentials Needed
* `REDDIT_CLIENT_ID`
* `REDDIT_CLIENT_SECRET`
* `REDDIT_USER_AGENT` (A custom description name, e.g., `my-monitor-app by u/yourusername`)

### How to Get Them
1. Log into your Reddit account on a web browser.
2. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
3. Scroll to the bottom and click **"are you a developer? create an app..."** or **"create another app..."**.
4. Fill in the form:
   * **Name:** `public-figure-monitor` (or any name you prefer)
   * **App Type:** Select the **script** radio button (critical: choose script, not web/installed).
   * **Description:** Optional.
   * **About URL:** Optional.
   * **Redirect URI:** `http://localhost` (or any dummy URL).
5. Click **create app**.
6. Retrieve the keys:
   * **Client ID:** Located right under the app name (a random string, e.g., `aBcDe12345FgHi`).
   * **Client Secret:** Labeled as **secret** (e.g., `xYz_1234567890abcdefg`).
7. **To Set (Windows Powershell):**
   ```powershell
   $env:REDDIT_CLIENT_ID="your_client_id"
   $env:REDDIT_CLIENT_SECRET="your_client_secret"
   $env:REDDIT_USER_AGENT="monitor-app by u/your_reddit_username"
   ```

---

## 2. YouTube Comments Integration (Google Cloud API)
Used to pull comments from top YouTube videos matching your search query. It has a generous free tier (10,000 units/day) which is more than enough for regular use.

### Credentials Needed
* `YOUTUBE_API_KEY`

### How to Get It
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Open the navigation menu, go to **APIs & Services** > **Library**.
4. Search for **"YouTube Data API v3"** and click **Enable**.
5. Go to **APIs & Services** > **Credentials**.
6. Click **+ Create Credentials** at the top and select **API key**.
7. Copy the generated API key.
8. **To Set (Windows Powershell):**
   ```powershell
   $env:YOUTUBE_API_KEY="your_api_key"
   ```

---

## 3. Telegram Integration (Telethon API)
Telegram reads public channels. It runs via a client-side session using a personal account.

### Credentials Needed
* `TELEGRAM_API_ID`
* `TELEGRAM_API_HASH`

### How to Get Them
1. Log into your account at [my.telegram.org](https://my.telegram.org).
2. Go to **API development tools**.
3. Create a new application. Fill in the short form (App title and short name, e.g., `SocialMonitor`).
4. Once created, copy the **App api_id** and **App api_hash**.
5. Set the environment variables in Powershell:
   ```powershell
   $env:TELEGRAM_API_ID="12345"
   $env:TELEGRAM_API_HASH="your_api_hash"
   ```
6. Complete the one-time user authorization by running this script in your terminal:
   ```bash
   python telegram_login.py
   ```
7. Enter your phone number (including country code, e.g., `+911234567890`) and the login code Telegram sends you. This creates a persistent `monitor.session` file in the project directory, so you won't need to log in again.

---

## 4. Bluesky Integration (App Password)
Although Bluesky search has a public URL that requires no keys, it returns `403 Forbidden` errors under scraping protection rules in cloud environments. Logging in with your Bluesky account resolves this.

### Credentials Needed (Optional, but recommended)
* `BLUESKY_USERNAME` (Your handle, e.g., `username.bsky.social`)
* `BLUESKY_PASSWORD` (An App Password)

### How to Get Them
1. Log into Bluesky.
2. Go to **Settings** > **App Passwords**.
3. Click **Add App Password**.
4. Give it a name (e.g., `MonitorApp`) and copy the generated password (usually looks like `xxxx-xxxx-xxxx-xxxx`).
5. **To Set (Windows Powershell):**
   ```powershell
   $env:BLUESKY_USERNAME="yourname.bsky.social"
   $env:BLUESKY_PASSWORD="xxxx-xxxx-xxxx-xxxx"
   ```
