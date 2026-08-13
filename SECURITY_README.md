# 🔐 Read me first — credentials were intentionally removed

This package was built to be shareable, so **your real secrets are not in it.**
The following were stripped from the version you uploaded:

| Removed file        | Why                                                                 |
|---------------------|---------------------------------------------------------------------|
| `.env`              | Contained your **live** YouTube, Reddit, Twitter and Telegram keys. |
| `monitor.session`   | An **authenticated Telegram session** — effectively a login token.  |
| `monitor_history.db`| Your local run history (rebuilds itself as you scan).               |

### To run it with your credentials
1. Copy the template:  `cp .env.example .env`
2. Paste your keys into `.env` (or just keep using the `.env` already sitting
   in your original project folder — it's unchanged there).
3. For Telegram, run once:  `python telegram_login.py`  (recreates the session).

### Please
- **Never commit `.env` or `*.session`** to Git or paste them into a chat.
- If any of the keys that were in the old `.env` have been shared anywhere,
  rotate them (regenerate the API key/token from each provider's console).
- The included `.gitignore` already excludes these files.

Everything runs at **$0** with no keys at all — the keyed connectors just add
Reddit, YouTube, Telegram and X coverage on top of the free defaults.
