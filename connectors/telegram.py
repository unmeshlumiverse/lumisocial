"""
Telegram connector (MTProto via Telethon).

Telegram has no free global search across all channels. Instead, this logs in
as a USER (one-time phone login) and searches a LIST of public channels you
choose — news channels, the person's own channel, topic channels, etc.

Setup:
  1. Get api_id + api_hash from https://my.telegram.org (free).
  2. Set env vars:
        TELEGRAM_API_ID
        TELEGRAM_API_HASH
        TELEGRAM_SESSION   (optional; defaults to a file session named "monitor")
  3. Run `python telegram_login.py` ONCE to authorize (enter phone + code).
     This creates a monitor.session file the dashboard reuses non-interactively.
"""

import os
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession


# Curated default set of PUBLIC Indian news/current-affairs channels.
# Telegram has no global search, so when the user doesn't specify channels we
# search this list — which makes "search a name" work out of the box. All are
# public broadcast channels; add/remove freely.
DEFAULT_INDIA_CHANNELS = [
    "ndtv", "indiatoday", "IndiaToday", "the_hindu", "TOIIndiaNews",
    "hindustantimes", "IndianExpress", "News18", "zeenews", "wionews",
    "republic", "ANI_News", "PTI_News", "thewire_in", "ThePrintIndia",
    "scroll_in", "livemint", "EconomicTimes", "moneycontrolcom",
    "businessstandard", "aajtak", "abpnews", "TV9Bharatvarsh", "opindia",
    "swarajyamag", "dbpost", "amarujala", "jagran",
]


def _make_client():
    api_id = (os.environ.get("TELEGRAM_API_ID") or "").strip()
    api_hash = (os.environ.get("TELEGRAM_API_HASH") or "").strip()
    session = os.environ.get("TELEGRAM_SESSION", "monitor")

    if not api_id or not api_hash or not api_id.isdigit():
        raise RuntimeError(
            "Telegram credentials invalid or missing. Set numeric TELEGRAM_API_ID and "
            "TELEGRAM_API_HASH in .env (get free at https://my.telegram.org)."
        )

    # A long value is treated as a portable StringSession; otherwise a file name.
    if session and len(session) > 40:
        return TelegramClient(StringSession(session), int(api_id), api_hash)
    return TelegramClient(session, int(api_id), api_hash)


async def _search(query, limit, channels):
    client = _make_client()
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telegram session not authorized. Run `python telegram_login.py` once."
            )

        posts = []
        per_channel = max(1, limit // max(1, len(channels)))
        for raw in channels:
            ch = raw.strip().lstrip("@")
            if not ch:
                continue
            try:
                entity = await client.get_entity(ch)
                title = getattr(entity, "title", ch)
                async for msg in client.iter_messages(entity, search=query, limit=per_channel):
                    if not msg.message:
                        continue
                    reactions = 0
                    if msg.reactions and msg.reactions.results:
                        reactions = sum(r.count for r in msg.reactions.results)
                    posts.append(
                        {
                            "platform": "telegram",
                            "id": f"{ch}:{msg.id}",
                            "author": ch,
                            "author_name": title,
                            "text": msg.message,
                            "created_at": msg.date.isoformat() if msg.date else None,
                            "likes": reactions,
                            "shares": msg.forwards or 0,
                            "replies": (msg.replies.replies if msg.replies else 0) or 0,
                            "url": f"https://t.me/{ch}/{msg.id}",
                        }
                    )
            except Exception:
                # One bad/private channel shouldn't kill the whole search.
                continue
        return posts
    finally:
        await client.disconnect()


def search_telegram(query, limit=50, channels=None):
    """
    Search public channels for `query`. If no channels are given, fall back to a
    curated list of major Indian news channels so name search works out of the box.
    Returns normalized posts.
    """
    channels = channels or DEFAULT_INDIA_CHANNELS
    if not channels:
        return []
    try:
        return asyncio.run(_search(query, limit, channels))
    except RuntimeError as e:
        # Handle "event loop already running" edge cases gracefully.
        if "event loop" in str(e).lower():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_search(query, limit, channels))
            finally:
                loop.close()
        raise

