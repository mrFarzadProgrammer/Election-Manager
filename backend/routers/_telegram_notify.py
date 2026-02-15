from __future__ import annotations

import logging
import re

import httpx

import database
import models


logger = logging.getLogger(__name__)


def _extract_telegram_chat_target(value: str | None) -> str | int | None:
    raw = (value or "").strip()
    if not raw:
        return None

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
    return f"@{v}"


def _candidate_bot_username(candidate: models.User) -> str | None:
    v = (getattr(candidate, "bot_name", None) or "").strip()
    if v.startswith("@"):  # tolerate @BotUsername
        v = v[1:]
    v = v.split()[0] if v else ""
    if not v:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_]{4,}", v):
        return None
    return v


def notify_question_answer_published(*, candidate: models.User, submission: models.BotSubmission) -> None:
    """Best-effort: notify candidate socials (group + channel) when a question gets answered.

    Must never fail the API request.
    """
    try:
        token = (getattr(candidate, "bot_token", None) or "").strip()
        if not token:
            return

        socials = getattr(candidate, "socials", None) or {}
        if not isinstance(socials, dict):
            socials = {}

        group_chat_id = socials.get("telegram_group_chat_id") or socials.get("telegramGroupChatId")
        channel_chat_id = socials.get("telegram_channel_chat_id") or socials.get("telegramChannelChatId")

        group_raw = socials.get("telegram_group") or socials.get("telegramGroup")
        channel_raw = socials.get("telegram_channel") or socials.get("telegramChannel")
        targets = [
            _extract_telegram_chat_target(str(group_chat_id) if group_chat_id is not None else None)
            or _extract_telegram_chat_target(str(group_raw) if group_raw is not None else None),
            _extract_telegram_chat_target(str(channel_chat_id) if channel_chat_id is not None else None)
            or _extract_telegram_chat_target(str(channel_raw) if channel_raw is not None else None),
        ]
        targets = [t for t in targets if t is not None]

        seen: set[str] = set()
        uniq: list[str | int] = []
        for t in targets:
            key = str(t)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(t)

        if not uniq:
            return

        bot_username = _candidate_bot_username(candidate)
        deep_link = f"https://t.me/{bot_username}?start=question_{int(submission.id)}" if bot_username else None

        topic = (getattr(submission, "topic", None) or "").strip()
        topic_line = f"\n🗂 دسته: {topic}" if topic else ""
        link_line = f"\n\n🔗 مشاهده در بات: {deep_link}" if deep_link else ""

        text = (
            "✅ پاسخ جدید به سؤال مردمی منتشر شد."
            f"\n🔖 کد سؤال: {int(submission.id)}"
            f"{topic_line}"
            f"{link_line}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        with httpx.Client(timeout=10.0) as client:
            for chat_id in uniq:
                try:
                    resp = client.post(
                        url,
                        json={
                            "chat_id": chat_id,
                            "text": text,
                            "disable_web_page_preview": True,
                        },
                    )
                    # If we used @username and Telegram returns a numeric chat.id, persist it.
                    try:
                        if resp.is_success and isinstance(chat_id, str) and str(chat_id).startswith("@"):  # @username
                            payload = (
                                resp.json()
                                if resp.headers.get("content-type", "").startswith("application/json")
                                else None
                            )
                            chat_obj = (payload or {}).get("result", {}).get("chat", {})
                            numeric_id = chat_obj.get("id")
                            if isinstance(numeric_id, int):
                                if str(chat_id) == str(
                                    _extract_telegram_chat_target(str(channel_raw) if channel_raw is not None else None)
                                ):
                                    db2 = database.SessionLocal()
                                    try:
                                        u2 = db2.query(models.User).filter(models.User.id == int(candidate.id)).first()
                                        if u2:
                                            base2 = u2.socials if isinstance(u2.socials, dict) else {}
                                            next2 = dict(base2)
                                            if next2.get("telegram_channel_chat_id") != numeric_id:
                                                next2["telegram_channel_chat_id"] = numeric_id
                                            if next2.get("telegramChannelChatId") != numeric_id:
                                                next2["telegramChannelChatId"] = numeric_id
                                            u2.socials = next2
                                            db2.add(u2)
                                            db2.commit()
                                    finally:
                                        db2.close()
                    except Exception:
                        logger.debug("Failed to persist numeric chat id from Telegram response")

                    if not resp.is_success:
                        logger.warning(
                            "Question notify failed: status=%s body=%s",
                            resp.status_code,
                            (resp.text or "")[:500],
                        )
                except Exception:
                    logger.exception("Question notify exception")
    except Exception:
        logger.exception("Question notify wrapper exception")
