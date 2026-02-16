import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load env vars from .env (repo root and/or backend cwd)
load_dotenv()
try:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")
except Exception:
    pass

FAILED_BOT_COOLDOWN = timedelta(minutes=5)

# Update processing concurrency (python-telegram-bot)
BOT_CONCURRENT_UPDATES = int((os.getenv("BOT_CONCURRENT_UPDATES") or "64").strip() or "64")
if BOT_CONCURRENT_UPDATES < 1:
    BOT_CONCURRENT_UPDATES = 1

# Telegram HTTP connection pool size for bot API calls.
TELEGRAM_CONNECTION_POOL_SIZE = int((os.getenv("TELEGRAM_CONNECTION_POOL_SIZE") or "32").strip() or "32")
if TELEGRAM_CONNECTION_POOL_SIZE < 4:
    TELEGRAM_CONNECTION_POOL_SIZE = 4

# Notify admin when a new BOT_REQUEST is submitted.
# NOTE: Telegram bots can only message users who have started that bot.
BOT_NOTIFY_ADMIN_USERNAME = (os.getenv("BOT_NOTIFY_ADMIN_USERNAME") or "mrFarzadMdi").lstrip("@").strip()
BOT_NOTIFY_ADMIN_CHAT_ID = (os.getenv("BOT_NOTIFY_ADMIN_CHAT_ID") or "").strip()
