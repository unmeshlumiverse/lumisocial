"""
Run ONCE to authorize Telegram:  python telegram_login.py

It will prompt for your phone number and the login code Telegram sends you,
then create a `monitor.session` file that the dashboard reuses automatically.

Requires TELEGRAM_API_ID and TELEGRAM_API_HASH env vars (from my.telegram.org).
"""

import os
from dotenv import load_dotenv

load_dotenv()

from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")

if not api_id or not api_hash:
    raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH first "
                     "(get them at https://my.telegram.org).")

with TelegramClient("monitor", int(api_id), api_hash) as client:
    me = client.get_me()
    print(f"✅ Authorized as: {me.username or me.first_name}")
    print("Session file 'monitor.session' created — the dashboard will use it.")
    print("\nOptional: to use a portable string session instead of the file,")
    print("set TELEGRAM_SESSION to the value below:")
    print(StringSession.save(client.session))
