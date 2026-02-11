"""Diagnose Telegram notification targets for question-answer announcements.

Run (from repo root):
    .venv\\Scripts\\python.exe backend\\debug_notify_targets.py

It reads the first CANDIDATE from the DB and tries to send a test message
(using the candidate bot token) to:
    - telegram_channel(_chat_id)
    - telegram_group(_chat_id)

It also checks bot membership/permissions where possible.
This is best-effort diagnostic output only.
"""

from __future__ import annotations

import re
import sys
from typing import Optional, Union

import httpx

# Ensure backend modules can be imported when running from repo root.
sys.path.insert(0, "backend")

import database  # noqa: E402
import models  # noqa: E402


ChatTarget = Union[int, str]


def extract_target(value: Optional[str]) -> Optional[ChatTarget]:
    raw = (value or "").strip()
    if not raw:
        return None

    # Numeric chat id
    if re.fullmatch(r"-?\d{5,}", raw):
        try:
            return int(raw)
        except Exception:
            return raw

    v = raw
    if v.startswith("t.me/"):
        v = "https://" + v

    if v.startswith("http://") or v.startswith("https://"):
        m = re.search(r"t\.me/([^/?#]+)", v)
        if not m:
            return None
        v = m.group(1)

    if v.startswith("+"):
        return None

    if v.startswith("@"):  # @channel
        v = v[1:]

    v = v.strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{4,}", v):
        return None

    return "@" + v


def main() -> int:
    db = database.SessionLocal()
    try:
        c = (
            db.query(models.User)
            .filter(models.User.role == "CANDIDATE")
            .order_by(models.User.id.asc())
            .first()
        )
        if not c:
            print("No candidate found")
            return 2

        token = (getattr(c, "bot_token", None) or "").strip()
        socials = getattr(c, "socials", None) or {}
        if not isinstance(socials, dict):
            socials = {}

        group_chat_id = socials.get("telegram_group_chat_id") or socials.get("telegramGroupChatId")
        channel_chat_id = socials.get("telegram_channel_chat_id") or socials.get("telegramChannelChatId")

        group_raw = socials.get("telegram_group") or socials.get("telegramGroup")
        channel_raw = socials.get("telegram_channel") or socials.get("telegramChannel")

        group_target = extract_target(str(group_chat_id) if group_chat_id is not None else None) or extract_target(
            str(group_raw) if group_raw is not None else None
        )
        channel_target = extract_target(
            str(channel_chat_id) if channel_chat_id is not None else None
        ) or extract_target(str(channel_raw) if channel_raw is not None else None)

        print("candidate_id", c.id)
        print("bot_name", getattr(c, "bot_name", None))
        print("token_set", bool(token))
        print("socials", socials)
        print("group_target", group_target)
        print("channel_target", channel_target)

        if not token:
            print("No bot token; cannot test")
            return 3

        api_base = f"https://api.telegram.org/bot{token}"
        url = f"{api_base}/sendMessage"
        with httpx.Client(timeout=20.0) as client:
            me = client.get(f"{api_base}/getMe")
            print("getMe status", me.status_code)
            print("getMe body", (me.text or "")[:800])
            bot_id = None
            try:
                if me.is_success:
                    bot_id = (me.json() or {}).get("result", {}).get("id")
            except Exception:
                bot_id = None

            if channel_target is not None:
                try:
                    ch = client.get(f"{api_base}/getChat", params={"chat_id": channel_target})
                    print("channel getChat", ch.status_code, (ch.text or "")[:500])
                    if bot_id is not None:
                        cm = client.get(
                            f"{api_base}/getChatMember",
                            params={"chat_id": channel_target, "user_id": int(bot_id)},
                        )
                        print("channel getChatMember", cm.status_code, (cm.text or "")[:500])
                except Exception as e:
                    print("channel getChat ERR", repr(e))

                r = client.post(
                    url,
                    json={
                        "chat_id": channel_target,
                        "text": "TEST: notify check (channel)",
                        "disable_web_page_preview": True,
                    },
                )
                print("channel status", r.status_code)
                print("channel body", (r.text or "")[:800])
            else:
                print("channel: no usable target")

            if group_target is not None:
                try:
                    gr = client.get(f"{api_base}/getChat", params={"chat_id": group_target})
                    print("group getChat", gr.status_code, (gr.text or "")[:500])
                    if bot_id is not None:
                        gm = client.get(
                            f"{api_base}/getChatMember",
                            params={"chat_id": group_target, "user_id": int(bot_id)},
                        )
                        print("group getChatMember", gm.status_code, (gm.text or "")[:500])
                except Exception as e:
                    print("group getChat ERR", repr(e))

                r = client.post(
                    url,
                    json={
                        "chat_id": group_target,
                        "text": "TEST: notify check (group)",
                        "disable_web_page_preview": True,
                    },
                )
                print("group status", r.status_code)
                print("group body", (r.text or "")[:800])
            else:
                print("group: no usable target")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
