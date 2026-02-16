import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database import SessionLocal
from models import User, BotUser, BotSubmission, BotUserRegistry

logger = logging.getLogger(__name__)


async def run_db_query(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


def save_submission_sync(
    *,
    candidate_id: int,
    telegram_user_id: str,
    telegram_username: str | None,
    submission_type: str,
    text: str,
    requester_full_name: str | None = None,
    requester_contact: str | None = None,
    topic: str | None = None,
    constituency: str | None = None,
    status: str | None = None,
    is_public: bool | None = None,
) -> int:
    db = SessionLocal()
    try:
        submission = BotSubmission(
            candidate_id=candidate_id,
            telegram_user_id=str(telegram_user_id),
            telegram_username=telegram_username,
            type=submission_type,
            topic=topic,
            text=text,
            constituency=constituency,
            requester_full_name=requester_full_name,
            requester_contact=requester_contact,
        )
        if status is not None:
            submission.status = str(status).strip()
        if is_public is not None:
            submission.is_public = bool(is_public)
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission.id
    finally:
        db.close()


def get_candidate_sync(candidate_id: int):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == candidate_id, User.role == "CANDIDATE").first()
    finally:
        db.close()


def save_bot_user_sync(user_data: dict, candidate_name: str):
    db = SessionLocal()
    try:
        bot_user = db.query(BotUser).filter(BotUser.telegram_id == user_data["id"]).first()
        if not bot_user:
            bot_user = BotUser(
                telegram_id=user_data["id"],
                username=user_data.get("username"),
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                bot_name=candidate_name,
            )
            db.add(bot_user)
        else:
            bot_user.username = user_data.get("username")
            bot_user.first_name = user_data.get("first_name")
            bot_user.last_name = user_data.get("last_name")
            bot_user.bot_name = candidate_name
        db.commit()
    except Exception as e:
        logger.error(f"Error saving bot user: {e}")
    finally:
        db.close()


def save_bot_user_registry_sync(*, user_data: dict, candidate_id: int, candidate_snapshot: dict, chat_type: str | None):
    db = SessionLocal()
    try:
        row = (
            db.query(BotUserRegistry)
            .filter(BotUserRegistry.candidate_id == int(candidate_id), BotUserRegistry.telegram_user_id == str(user_data["id"]))
            .first()
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not row:
            row = BotUserRegistry(
                candidate_id=int(candidate_id),
                telegram_user_id=str(user_data["id"]),
                telegram_username=user_data.get("username"),
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                chat_type=chat_type,
                candidate_name=candidate_snapshot.get("name"),
                candidate_bot_name=candidate_snapshot.get("bot_name"),
                candidate_city=candidate_snapshot.get("city"),
                candidate_province=candidate_snapshot.get("province"),
                candidate_constituency=candidate_snapshot.get("constituency"),
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(row)
        else:
            row.telegram_username = user_data.get("username")
            row.first_name = user_data.get("first_name")
            row.last_name = user_data.get("last_name")
            row.chat_type = chat_type or row.chat_type

            row.candidate_name = candidate_snapshot.get("name")
            row.candidate_bot_name = candidate_snapshot.get("bot_name")
            row.candidate_city = candidate_snapshot.get("city")
            row.candidate_province = candidate_snapshot.get("province")
            row.candidate_constituency = candidate_snapshot.get("constituency")
            row.last_seen_at = now

        db.commit()
    except Exception as e:
        logger.error(f"Error saving bot user registry: {e}")
    finally:
        db.close()


async def save_bot_user(update, *, candidate_id: int, candidate_snapshot: dict):
    user = update.effective_user
    if not user:
        return

    user_data = {
        "id": str(user.id),
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }

    candidate_name = str(candidate_snapshot.get("bot_name") or candidate_snapshot.get("name") or "")
    chat_type = update.effective_chat.type if update.effective_chat else None

    await run_db_query(save_bot_user_sync, user_data, candidate_name)
    await run_db_query(
        save_bot_user_registry_sync,
        user_data=user_data,
        candidate_id=int(candidate_id),
        candidate_snapshot=candidate_snapshot,
        chat_type=chat_type,
    )


def looks_like_telegram_token(token: str | None) -> bool:
    if not token:
        return False
    token = token.strip()
    if not token or token.startswith("TOKEN_"):
        return False
    if ":" not in token:
        return False
    bot_id, secret = token.split(":", 1)
    return bot_id.isdigit() and len(secret) >= 20


def upload_file_path_from_localhost_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None
    prefixes = (
        "http://localhost:8000/uploads/",
        "http://127.0.0.1:8000/uploads/",
    )
    if not url.startswith(prefixes):
        return None
    filename = url.split("/uploads/", 1)[-1]
    filename = filename.split("?", 1)[0].split("#", 1)[0]
    filename = filename.replace("..", "").lstrip("/\\")
    local_path = os.path.join(os.path.dirname(__file__), "..", "uploads", filename)
    local_path = os.path.normpath(local_path)
    return local_path if os.path.exists(local_path) else None


def persist_group_chat_id_sync(candidate_id: int, chat_id_int: int) -> None:
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == int(candidate_id), User.role == "CANDIDATE").first()
        if not u:
            return
        base = u.socials if isinstance(u.socials, dict) else {}
        s = dict(base)
        if s.get("telegram_group_chat_id") != chat_id_int:
            s["telegram_group_chat_id"] = chat_id_int
        if s.get("telegramGroupChatId") != chat_id_int:
            s["telegramGroupChatId"] = chat_id_int
        u.socials = s
        db.add(u)
        db.commit()
    finally:
        db.close()
