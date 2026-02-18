"""
Diagnose bot path: checks active candidates and token validity.
"""
import os
import sys

# Avoid UnicodeEncodeError on Windows console
try:
    if getattr(sys.stdout, "reconfigure", None) and sys.stdout.encoding:
        if sys.stdout.encoding.lower() in ("cp1252", "cp850", "ascii"):
            sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# backend as cwd
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from database import SessionLocal
from models import User
from tg_bot.db_ops import looks_like_telegram_token


def mask_token(t: str | None) -> str:
    if not t or not t.strip():
        return "(empty)"
    t = t.strip()
    if t.startswith("TOKEN_"):
        return "TOKEN_... (fake - rejected)"
    if ":" in t:
        pre, post = t.split(":", 1)
        return f"{pre}:{post[:4]}... (secret len={len(post)})"
    return "(invalid format)"


def main():
    print("=" * 60)
    print("1) Candidates in DB (role=CANDIDATE, is_active=True)")
    print("=" * 60)

    db = SessionLocal()
    try:
        candidates = (
            db.query(User)
            .filter(User.role == "CANDIDATE", User.is_active == True)  # noqa: E712
            .all()
        )
    finally:
        db.close()

    if not candidates:
        print("  No active candidates. Bot runner will not start any bot.")
        print("  Fix: Add a candidate with real Telegram token from admin panel.")
        return

    print(f"  Active candidates count: {len(candidates)}\n")

    valid_count = 0
    for c in candidates:
        token_ok = looks_like_telegram_token(c.bot_token)
        if token_ok:
            valid_count += 1
        status = "OK (bot will start)" if token_ok else "INVALID (bot will NOT start)"
        raw_name = c.full_name or c.username or ""
        name = "".join(c if ord(c) < 128 else "?" for c in raw_name) or "(no name)"
        print(f"  id={c.id}  full_name={name}")
        print(f"    bot_name={getattr(c, 'bot_name', None)}")
        print(f"    bot_token={mask_token(c.bot_token)}")
        print(f"    -> {status}")
        print()

    print("=" * 60)
    print("2) Summary")
    print("=" * 60)
    print(f"  Candidates with valid token: {valid_count} of {len(candidates)}")
    if valid_count == 0:
        print()
        print("  Reason: DB tokens are empty or TOKEN_... (fake).")
        print("  Get real token from @BotFather and save in candidate panel.")
        print("  Format: digits:secret (min 20 chars), e.g. 123456789:ABCdef...")
    else:
        print()
        print("  If bot still does not respond:")
        print("  - Ensure bot_runner.py is running.")
        print("  - Send /start to the bot once.")
        print("  - Use VPN/proxy if Telegram is blocked.")


if __name__ == "__main__":
    main()
