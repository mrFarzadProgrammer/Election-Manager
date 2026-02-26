import logging
import html
import os
import re
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

import models
from database import SessionLocal
from models import BotSubmission, BotUserRegistry, User

from .config import BOT_NOTIFY_ADMIN_CHAT_ID, BOT_NOTIFY_ADMIN_USERNAME
from .content import candidate_constituency, format_structured_resume, get_program_answer
from .db_ops import persist_group_chat_id_sync, run_db_query, save_bot_user, save_submission_sync, upload_file_path_from_localhost_url
from .keyboards import (
    build_about_keyboard,
    build_back_keyboard,
    build_bot_request_contact_keyboard,
    build_bot_request_cta_keyboard,
    build_bot_request_role_keyboard,
    build_main_keyboard,
    build_other_keyboard,
    build_question_ask_entry_keyboard,
    build_question_categories_keyboard,
    build_question_entry_keyboard,
    build_question_hub_keyboard,
    build_question_view_method_keyboard,
)
from .monitoring import log_technical_error_sync, log_ux_sync, track_flow_event_sync, track_path_sync
from .text_utils import (
    btn_eq,
    btn_has,
    build_feedback_confirmation_text,
    build_feedback_intro_text,
    format_public_question_answer_block,
    format_public_feedback_answer_block,
    normalize_button_text,
    normalize_text,
    safe_reply_text,
    send_question_answers_message,
    send_question_answers_message_cards_html,
)
from .ui_constants import (
    BTN_ABOUT_BOT,
    BTN_ABOUT_INTRO,
    BTN_ABOUT_MENU,
    BTN_ASK_NEW_QUESTION,
    BTN_BACK,
    BTN_BOT_REQUEST,
    BTN_BUILD_BOT,
    BTN_COMMITMENTS,
    BTN_CONTACT,
    BTN_FEEDBACK,
    BTN_FEEDBACK_LEGACY,
    BTN_HQ_ADDRESSES,
    BTN_INTRO,
    BTN_OTHER_MENU,
    BTN_PROFILE_SUMMARY,
    BTN_PROGRAMS,
    BTN_QUESTION,
    BTN_REGISTER_QUESTION,
    BTN_SEARCH_QUESTION,
    BTN_SELECT_TOPIC,
    BTN_VIEW_BY_CATEGORY,
    BTN_VIEW_BY_SEARCH,
    BTN_VIEW_QUESTIONS,
    BTN_VOICE_INTRO,
    FEEDBACK_INTRO_TEXT,
    PROGRAM_QUESTIONS,
    QUESTION_CATEGORIES,
    ROLE_CANDIDATE,
    ROLE_REPRESENTATIVE,
    ROLE_TEAM,
    STATE_ABOUT_MENU,
    STATE_ABOUT_DETAIL,
    STATE_BOTREQ_CONTACT,
    STATE_BOTREQ_CONSTITUENCY,
    STATE_BOTREQ_NAME,
    STATE_BOTREQ_ROLE,
    STATE_COMMITMENTS_VIEW,
    STATE_FEEDBACK_TEXT,
    STATE_MAIN,
    STATE_OTHER_MENU,
    STATE_PROGRAMS,
    STATE_QUESTION_ASK_ENTRY,
    STATE_QUESTION_ASK_OTHER_TOPIC,
    STATE_QUESTION_ASK_TEXT,
    STATE_QUESTION_ASK_TOPIC,
    STATE_QUESTION_CATEGORY,
    STATE_QUESTION_ENTRY,
    STATE_QUESTION_MENU,
    STATE_QUESTION_SEARCH,
    STATE_QUESTION_TEXT,
    STATE_QUESTION_VIEW_ANSWER,
    STATE_QUESTION_VIEW_CATEGORY,
    STATE_QUESTION_VIEW_LIST,
    STATE_QUESTION_VIEW_METHOD,
    STATE_QUESTION_VIEW_RESULTS,
    STATE_QUESTION_VIEW_SEARCH_TEXT,
    flow_type_from_state,
    parse_question_list_choice,
)

logger = logging.getLogger(__name__)


def _is_back(text: str | None) -> bool:
    # Match exact + Persian keywords.
    t = normalize_button_text(text)
    return t == normalize_button_text(BTN_BACK) or ("بازگشت" in t or "برگشت" in t)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type if update.effective_chat else "unknown"
    from_user = update.effective_user.id if update.effective_user else "unknown"

    candidate_id = context.bot_data.get("candidate_id")
    logger.info("Received /start for candidate_id: %s in %s from %s", candidate_id, chat_type, from_user)
    if not candidate_id:
        msg = update.effective_message
        if msg:
            await safe_reply_text(msg, "خطا: شناسه کاندیدا یافت نشد.")
        return

    def get_candidate_data(cid):
        db = SessionLocal()
        try:
            c = db.query(User).filter(User.id == cid, User.role == "CANDIDATE").first()
            if not c:
                return None
            return {
                "name": c.full_name,
                "full_name": c.full_name,
                "bot_name": c.bot_name,
                "slogan": c.slogan,
                "city": getattr(c, "city", None),
                "province": getattr(c, "province", None),
                "constituency": getattr(c, "constituency", None),
            }
        finally:
            db.close()

    candidate = await run_db_query(get_candidate_data, candidate_id)
    if not candidate:
        msg = update.effective_message
        if msg:
            await safe_reply_text(msg, "خطا: اطلاعات کاندیدا یافت نشد.")
        return

    try:
        if update.effective_user is not None:
            log_ux_sync(
                candidate_id=int(candidate_id),
                telegram_user_id=str(update.effective_user.id),
                state=context.user_data.get("state") or STATE_MAIN,
                action="start_command",
                expected_action="tap_menu_button",
            )
    except Exception:
        pass

    # Deep-link support: https://t.me/<bot>?start=question_<id> or feedback_<id>
    try:
        args = list(getattr(context, "args", None) or [])
        if args:
            m = re.fullmatch(r"question_(\d+)", str(args[0]).strip())
            if m:
                qid = int(m.group(1))

                def _get_public_answered_by_id(cid: int, submission_id: int) -> BotSubmission | None:
                    db = SessionLocal()
                    try:
                        return (
                            db.query(BotSubmission)
                            .filter(
                                BotSubmission.id == int(submission_id),
                                BotSubmission.candidate_id == int(cid),
                                BotSubmission.type == "QUESTION",
                                BotSubmission.status == "ANSWERED",
                                BotSubmission.is_public == True,  # noqa: E712
                                BotSubmission.answer.isnot(None),
                            )
                            .first()
                        )
                    finally:
                        db.close()

                row = await run_db_query(_get_public_answered_by_id, candidate_id, qid)
                msg = update.effective_message
                if not msg:
                    return

                if not row:
                    context.user_data["state"] = STATE_MAIN
                    await safe_reply_text(msg, "این سؤال یافت نشد یا هنوز پاسخ عمومی ندارد.", reply_markup=build_main_keyboard())
                    return

                q_txt = normalize_text(getattr(row, "text", ""))
                a_txt = normalize_text(getattr(row, "answer", ""))
                topic = normalize_text(getattr(row, "topic", ""))
                is_featured = bool(getattr(row, "is_featured", False))
                badge = " ⭐ منتخب" if is_featured else ""
                answered_at = getattr(row, "answered_at", None)
                block = format_public_question_answer_block(topic=topic, question=q_txt, answer=a_txt, answered_at=answered_at)
                if badge:
                    block = block + f"\n\n{badge.strip()}"

                context.user_data["state"] = STATE_QUESTION_MENU
                await safe_reply_text(msg, block, reply_markup=build_question_hub_keyboard())
                return

            m2 = re.fullmatch(r"feedback_(\d+)", str(args[0]).strip())
            if m2:
                fid = int(m2.group(1))

                def _get_public_answered_feedback_by_id(cid: int, submission_id: int) -> BotSubmission | None:
                    db = SessionLocal()
                    try:
                        return (
                            db.query(BotSubmission)
                            .filter(
                                BotSubmission.id == int(submission_id),
                                BotSubmission.candidate_id == int(cid),
                                BotSubmission.type == "FEEDBACK",
                                BotSubmission.status == "ANSWERED",
                                BotSubmission.is_public == True,  # noqa: E712
                                BotSubmission.answer.isnot(None),
                            )
                            .first()
                        )
                    finally:
                        db.close()

                row2 = await run_db_query(_get_public_answered_feedback_by_id, candidate_id, fid)
                msg2 = update.effective_message
                if not msg2:
                    return

                if not row2:
                    context.user_data["state"] = STATE_MAIN
                    await safe_reply_text(
                        msg2,
                        "این پیام یافت نشد یا هنوز پاسخ عمومی ندارد.",
                        reply_markup=build_main_keyboard(),
                    )
                    return

                f_txt = normalize_text(getattr(row2, "text", ""))
                a_txt2 = normalize_text(getattr(row2, "answer", ""))
                tag2 = normalize_text(getattr(row2, "tag", ""))
                answered_at2 = getattr(row2, "answered_at", None)
                block2 = format_public_feedback_answer_block(
                    tag=tag2,
                    feedback_text=f_txt,
                    answer=a_txt2,
                    answered_at=answered_at2,
                )

                context.user_data["state"] = STATE_MAIN
                await safe_reply_text(msg2, block2, reply_markup=build_main_keyboard())
                return
    except Exception:
        logger.exception("Failed to handle /start deep-link")

    await save_bot_user(
        update,
        candidate_id=candidate_id,
        candidate_snapshot={
            "name": candidate.get("name"),
            "bot_name": candidate.get("bot_name"),
            "city": candidate.get("city"),
            "province": candidate.get("province"),
            "constituency": candidate.get("constituency"),
        },
    )

    context.user_data["state"] = STATE_MAIN
    context.user_data.pop("feedback_topic", None)

    cand_name = normalize_text(candidate.get("name")) or "نماینده"
    welcome_text = (
        "👋 سلام، خوشحالیم که اینجایید\n\n"
        "اینجا جاییه برای شنیده شدن صدای شما.\n"
        "این بات راه ارتباط مستقیم شما\n"
        f"با {cand_name}\n\n"
        "👇 از منوی زیر می‌تونی:\n"
        "━━━━━━━━━━━━━━\n"
        "📌 سؤال بپرسی\n"
        "📌 برنامه‌ها رو ببینی\n"
        "📌 نظر یا دغدغه‌ات رو بفرستی\n\n"
        "منتظرت هستیم 👇"
    )

    msg = update.effective_message
    if msg:
        await safe_reply_text(msg, welcome_text, reply_markup=build_main_keyboard())


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    candidate_id = context.bot_data.get("candidate_id")
    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not chat:
        return

    if not candidate_id:
        await safe_reply_text(msg, "خطا: شناسه کاندیدا یافت نشد.")
        return

    if chat.type not in ["group", "supergroup"]:
        await safe_reply_text(msg, "این دستور فقط داخل گروه قابل استفاده است.")
        return

    chat_id_int = int(chat.id)
    await run_db_query(persist_group_chat_id_sync, candidate_id, chat_id_int)
    await safe_reply_text(msg, f"✅ شناسه گروه ذخیره شد.\nchat_id: {chat_id_int}")


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not msg:
        return

    user_id = getattr(user, "id", None)
    username = getattr(user, "username", None)
    chat_id = getattr(chat, "id", None)
    chat_type = getattr(chat, "type", None)

    lines = ["🆔 اطلاعات شما:"]
    if user_id is not None:
        lines.append(f"user_id: {user_id}")
    if username:
        lines.append(f"username: @{username}")
    if chat_id is not None:
        lines.append(f"chat_id: {chat_id} ({chat_type})")
    await safe_reply_text(msg, "\n".join(lines))


async def debug_update_logger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        try:
            context.bot_data["last_update_received_at"] = datetime.now(timezone.utc)
        except Exception:
            pass

        message = getattr(update, "effective_message", None)
        chat = getattr(update, "effective_chat", None)
        user = getattr(update, "effective_user", None)

        text = None
        entities = None
        if message is not None:
            text = getattr(message, "text", None)
            entities = getattr(message, "entities", None)

        logger.info(
            "Incoming update: candidate_id=%s chat_id=%s chat_type=%s user_id=%s username=%s text=%r entities=%s",
            context.bot_data.get("candidate_id"),
            getattr(chat, "id", None),
            getattr(chat, "type", None),
            getattr(user, "id", None),
            getattr(user, "username", None),
            text,
            [(e.type, e.offset, e.length) for e in entities] if entities else None,
        )
    except Exception:
        logger.exception("Failed to log incoming update")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # --- پاسخ تستی و لاگ برای عیب‌یابی ---
    # (پیام‌های تستی حذف شد و تورفتگی اصلاح شد)
    raw_text = (update.message.text or "")
    text = normalize_button_text(raw_text)
    candidate_id = context.bot_data.get("candidate_id")
    chat_type = update.message.chat.type

    logger.info("Received message: raw=%r normalized=%r for candidate_id=%s in %s", raw_text, text, candidate_id, chat_type)

    # Legacy cached keyboard labels
    if btn_has(text, "درخواست ساخت بات") and btn_has(text, "اختصاصی"):
        text = BTN_BOT_REQUEST

    if not candidate_id:
        return

    def get_full_candidate_data(cid):
        db = SessionLocal()
        try:
            c = db.query(User).filter(User.id == cid, User.role == "CANDIDATE").first()
            if not c:
                return None
            return {
                "name": c.full_name,
                "full_name": c.full_name,
                "bot_name": c.bot_name,
                "province": getattr(c, "province", None),
                "city": getattr(c, "city", None),
                "constituency": getattr(c, "constituency", None),
                "slogan": getattr(c, "slogan", None),
                "resume": c.resume,
                "ideas": c.ideas,
                "address": c.address,
                "phone": c.phone,
                "socials": c.socials,
                "bot_config": c.bot_config,
                "image_url": getattr(c, "image_url", None),
                "voice_url": getattr(c, "voice_url", None),
            }
        finally:
            db.close()

    candidate = await run_db_query(get_full_candidate_data, candidate_id)
    if not candidate:
        return

    bot_config = candidate.get("bot_config")
    if isinstance(bot_config, str):
        try:
            parsed = json.loads(bot_config)
            bot_config = parsed if isinstance(parsed, dict) else {}
        except Exception:
            bot_config = {}
    elif not isinstance(bot_config, dict):
        bot_config = {}
    candidate["bot_config"] = bot_config

    socials = candidate.get("socials") or {}
    if isinstance(socials, dict):
        if "telegramChannel" not in socials and "telegram_channel" in socials:
            socials["telegramChannel"] = socials.get("telegram_channel")
        if "telegramGroup" not in socials and "telegram_group" in socials:
            socials["telegramGroup"] = socials.get("telegram_group")

    if isinstance(bot_config, dict):
        if "groupLockEnabled" not in bot_config and "auto_lock_enabled" in bot_config:
            bot_config["groupLockEnabled"] = bool(bot_config.get("auto_lock_enabled"))
        if "lockStartTime" not in bot_config and "lock_start_time" in bot_config:
            bot_config["lockStartTime"] = bot_config.get("lock_start_time")
        if "lockEndTime" not in bot_config and "lock_end_time" in bot_config:
            bot_config["lockEndTime"] = bot_config.get("lock_end_time")
        if "blockLinks" not in bot_config and "anti_link_enabled" in bot_config:
            bot_config["blockLinks"] = bool(bot_config.get("anti_link_enabled"))
        if "badWords" not in bot_config and "forbidden_words" in bot_config:
            raw = bot_config.get("forbidden_words")
            if isinstance(raw, str):
                bot_config["badWords"] = [w.strip() for w in raw.split(",") if w.strip()]

    await save_bot_user(
        update,
        candidate_id=candidate_id,
        candidate_snapshot={
            "name": candidate.get("name"),
            "bot_name": candidate.get("bot_name"),
            "city": candidate.get("city"),
            "province": candidate.get("province"),
            "constituency": candidate.get("constituency"),
        },
    )

    try:
        if chat_type in ["group", "supergroup"] and update.effective_chat is not None:
            chat_id_val = int(update.effective_chat.id)
            await run_db_query(persist_group_chat_id_sync, candidate_id, chat_id_val)
    except Exception:
        logger.exception("Failed to persist group chat id")

    # --- Group management ---
    if chat_type in ["group", "supergroup"]:
        if bot_config.get("groupLockEnabled"):
            start_time = bot_config.get("lockStartTime")
            end_time = bot_config.get("lockEndTime")

            if start_time and end_time:
                now = datetime.now().time()
                try:
                    start = datetime.strptime(start_time, "%H:%M").time()
                    end = datetime.strptime(end_time, "%H:%M").time()

                    is_locked = False
                    if start <= end:
                        is_locked = start <= now <= end
                    else:
                        is_locked = start <= now or now <= end

                    if is_locked:
                        try:
                            await update.message.delete()
                        except Exception as e:
                            logger.error("Failed to delete message in locked group: %s", e)
                        return
                except ValueError:
                    logger.error("Invalid time format in bot_config")

        bad_words = bot_config.get("badWords", [])
        if bad_words and isinstance(bad_words, list):
            text_lower = text.lower()
            for word in bad_words:
                if word.strip() and word.strip().lower() in text_lower:
                    try:
                        await update.message.delete()
                    except Exception as e:
                        logger.error("Failed to delete bad word message: %s", e)
                    return

        if bot_config.get("blockLinks"):
            url_pattern = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
            if url_pattern.search(text):
                try:
                    await update.message.delete()
                except Exception as e:
                    logger.error("Failed to delete link message: %s", e)
                return

    # --- Private chat MVP V1 menu logic ---

    text = (text or "").strip()
    state = context.user_data.get("state") or STATE_MAIN

    # Be tolerant to old/variant labels for Programs button.
    # Common cases: emoji moves due to RTL, ZWNJ differences, or older keyboards like "برنامه ها".
    # Do NOT remap during free-text states (feedback/questions/bot request) to avoid hijacking user input.
    if state in {STATE_MAIN, STATE_ABOUT_MENU, STATE_OTHER_MENU} and btn_has(text, "برنامه"):
        if text != BTN_PROGRAMS:
            logger.info("Mapping Programs button variant: %r -> %r (state=%s)", text, BTN_PROGRAMS, state)
        text = BTN_PROGRAMS

    def _has_existing_bot_request_sync(*, candidate_id: int, telegram_user_id: str, phone: str | None = None) -> bool:
        db = SessionLocal()
        try:
            q = (
                db.query(BotSubmission)
                .filter(
                    BotSubmission.candidate_id == int(candidate_id),
                    BotSubmission.telegram_user_id == str(telegram_user_id),
                    BotSubmission.type == "BOT_REQUEST",
                )
                .order_by(BotSubmission.created_at.desc())
            )
            if phone:
                q = q.filter(BotSubmission.requester_contact == str(phone))
            return q.first() is not None
        finally:
            db.close()

    known_states = {
        STATE_MAIN,
        STATE_ABOUT_MENU,
        STATE_ABOUT_DETAIL,
        STATE_OTHER_MENU,
        STATE_COMMITMENTS_VIEW,
        STATE_PROGRAMS,
        STATE_FEEDBACK_TEXT,
        STATE_QUESTION_TEXT,
        STATE_QUESTION_MENU,
        STATE_QUESTION_SEARCH,
        STATE_QUESTION_CATEGORY,
        STATE_QUESTION_ENTRY,
        STATE_QUESTION_VIEW_METHOD,
        STATE_QUESTION_VIEW_CATEGORY,
        STATE_QUESTION_VIEW_LIST,
        STATE_QUESTION_VIEW_ANSWER,
        STATE_QUESTION_VIEW_RESULTS,
        STATE_QUESTION_VIEW_SEARCH_TEXT,
        STATE_QUESTION_ASK_ENTRY,
        STATE_QUESTION_ASK_TOPIC,
        STATE_QUESTION_ASK_TEXT,
        STATE_BOTREQ_NAME,
        STATE_BOTREQ_ROLE,
        STATE_BOTREQ_CONSTITUENCY,
        STATE_BOTREQ_CONTACT,
    }
    if state not in known_states:
        try:
            if update.effective_user is not None:
                log_ux_sync(
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    state=str(state),
                    action="forced_return_to_main_menu",
                    expected_action="tap_menu_button",
                )
        except Exception:
            pass
        context.user_data["state"] = STATE_MAIN
        state = STATE_MAIN

    # Minimal loop detection
    try:
        last_state = context.user_data.get("_loop_last_state")
        loop_count = int(context.user_data.get("_loop_count") or 0)
        if str(state) == str(last_state):
            loop_count += 1
        else:
            loop_count = 1
        context.user_data["_loop_last_state"] = str(state)
        context.user_data["_loop_count"] = loop_count

        if loop_count >= 6 and state != STATE_MAIN:
            last_logged_state = context.user_data.get("_loop_logged_state")
            last_logged_at = context.user_data.get("_loop_logged_at")
            now = datetime.utcnow()
            should_log = True
            if last_logged_state == str(state) and isinstance(last_logged_at, datetime):
                should_log = (now - last_logged_at) > timedelta(minutes=10)
            if should_log and update.effective_user is not None:
                log_ux_sync(
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    state=str(state),
                    action="state_loop_detected",
                    expected_action="use_back_or_main_menu",
                )
                context.user_data["_loop_logged_state"] = str(state)
                context.user_data["_loop_logged_at"] = now
    except Exception:
        pass

    question_step_states = {
        STATE_QUESTION_ENTRY,
        STATE_QUESTION_VIEW_METHOD,
        STATE_QUESTION_VIEW_CATEGORY,
        STATE_QUESTION_VIEW_LIST,
        STATE_QUESTION_VIEW_ANSWER,
        STATE_QUESTION_VIEW_RESULTS,
        STATE_QUESTION_VIEW_SEARCH_TEXT,
        STATE_QUESTION_ASK_ENTRY,
        STATE_QUESTION_ASK_TOPIC,
        STATE_QUESTION_ASK_TEXT,
    }

    if _is_back(text) and state in question_step_states:
        pass
    elif _is_back(text):
        prev_state = state
        return_state = context.user_data.pop("_return_state", None)
        context.user_data["state"] = STATE_MAIN
        context.user_data.pop("feedback_topic", None)
        context.user_data.pop("botreq_full_name", None)
        context.user_data.pop("botreq_role", None)
        context.user_data.pop("botreq_constituency", None)
        context.user_data.pop("botreq_contact", None)

        try:
            if prev_state and prev_state != STATE_MAIN and update.effective_user is not None:
                ft = flow_type_from_state(prev_state)
                if ft:
                    track_flow_event_sync(candidate_id=int(candidate_id), flow_type=ft, event="flow_abandoned")
                    log_ux_sync(
                        candidate_id=int(candidate_id),
                        telegram_user_id=str(update.effective_user.id),
                        state=str(prev_state),
                        action="flow_abandoned_midway",
                        expected_action="complete_flow_or_back",
                    )
        except Exception:
            pass

        if return_state == STATE_ABOUT_MENU:
            context.user_data["state"] = STATE_ABOUT_MENU
            await safe_reply_text(update.message, "به «درباره نماینده» برگشتید.", reply_markup=build_about_keyboard())
            return
        if return_state == STATE_OTHER_MENU:
            context.user_data["state"] = STATE_OTHER_MENU
            await safe_reply_text(update.message, "به «سایر امکانات» برگشتید.", reply_markup=build_other_keyboard())
            return

        await safe_reply_text(update.message, "به منوی اصلی برگشتید.", reply_markup=build_main_keyboard())
        return

    # Build-bot request flow (legacy steps remain, but BTN_BOT_REQUEST jumps to contact directly per spec)
    if state == STATE_BOTREQ_NAME:
        reserved = {
            BTN_QUESTION,
            BTN_COMMITMENTS,
            BTN_FEEDBACK,
            BTN_FEEDBACK_LEGACY,
            BTN_ABOUT_MENU,
            BTN_OTHER_MENU,
            BTN_ABOUT_INTRO,
            BTN_PROGRAMS,
            BTN_HQ_ADDRESSES,
            BTN_VOICE_INTRO,
            BTN_BUILD_BOT,
            BTN_ABOUT_BOT,
            BTN_CONTACT,
            BTN_INTRO,
            BTN_BOT_REQUEST,
        }
        if text in reserved or not text:
            await safe_reply_text(update.message, "نام و نام خانوادگی را وارد کنید یا «بازگشت» را بزنید.")
            return
        if len(text) < 3:
            await safe_reply_text(update.message, "نام خیلی کوتاه است. لطفاً دوباره وارد کنید:")
            return
        context.user_data["botreq_full_name"] = text
        context.user_data["state"] = STATE_BOTREQ_ROLE
        await safe_reply_text(update.message, "نقش شما کدام است؟", reply_markup=build_bot_request_role_keyboard())
        return

    if state == STATE_BOTREQ_ROLE:
        allowed = {ROLE_REPRESENTATIVE, ROLE_CANDIDATE, ROLE_TEAM}
        if text not in allowed:
            await safe_reply_text(update.message, "لطفاً یکی از گزینه‌های نقش را انتخاب کنید.", reply_markup=build_bot_request_role_keyboard())
            return
        context.user_data["botreq_role"] = text
        context.user_data["state"] = STATE_BOTREQ_CONSTITUENCY
        await safe_reply_text(update.message, "حوزه انتخابیه را وارد کنید:", reply_markup=build_back_keyboard())
        return

    if state == STATE_BOTREQ_CONSTITUENCY:
        if not text:
            await safe_reply_text(update.message, "حوزه انتخابیه را وارد کنید یا «بازگشت» را بزنید.")
            return
        context.user_data["botreq_constituency"] = text
        context.user_data["state"] = STATE_BOTREQ_CONTACT
        await safe_reply_text(
            update.message,
            "لطفاً با دکمه «ارسال شماره تماس» شماره‌تان را ارسال کنید:",
            reply_markup=build_bot_request_contact_keyboard(),
        )
        return

    if state == STATE_BOTREQ_CONTACT:
        msg_obj = update.effective_message
        contact_obj = getattr(msg_obj, "contact", None) if msg_obj else None

        if not contact_obj:
            await safe_reply_text(
                update.message,
                "برای ثبت درخواست مشاوره، لطفاً با دکمه «ارسال شماره تماس» شماره‌تان را ارسال کنید.",
                reply_markup=build_bot_request_contact_keyboard(),
            )
            return

        try:
            if (
                update.effective_user is not None
                and getattr(contact_obj, "user_id", None) is not None
                and str(contact_obj.user_id) != str(update.effective_user.id)
            ):
                await safe_reply_text(
                    update.message,
                    "⚠️ لطفاً فقط شماره تماس خودتان را با دکمه «ارسال شماره تماس» ارسال کنید.",
                    reply_markup=build_bot_request_contact_keyboard(),
                )
                return
        except Exception:
            pass

        phone = normalize_text(getattr(contact_obj, "phone_number", None))

        # Guard against duplicate submissions (concurrent updates / repeated taps)
        try:
            if update.effective_user is not None and phone:
                is_dup = await run_db_query(
                    _has_existing_bot_request_sync,
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    phone=phone,
                )
                if is_dup:
                    return_state = context.user_data.pop("_return_state", None)
                    if return_state == STATE_OTHER_MENU:
                        context.user_data["state"] = STATE_OTHER_MENU
                        reply_markup = build_other_keyboard()
                    else:
                        context.user_data["state"] = STATE_MAIN
                        reply_markup = build_main_keyboard()

                    context.user_data.pop("botreq_full_name", None)
                    context.user_data.pop("botreq_role", None)
                    context.user_data.pop("botreq_constituency", None)
                    context.user_data.pop("botreq_contact", None)

                    await safe_reply_text(update.message, "✅ درخواست شما قبلاً ثبت شده است.\nتیم پشتیبانی به‌زودی با شما تماس می‌گیرد.", reply_markup=reply_markup)
                    return
        except Exception:
            pass
        collected_name = normalize_text(context.user_data.get("botreq_full_name"))
        collected_role = normalize_text(context.user_data.get("botreq_role"))
        collected_constituency = normalize_text(context.user_data.get("botreq_constituency"))

        full_name = collected_name
        if not full_name:
            full_name = " ".join(
                [
                    normalize_text(getattr(contact_obj, "first_name", None)),
                    normalize_text(getattr(contact_obj, "last_name", None)),
                ]
            ).strip()
        if not full_name and update.effective_user is not None:
            full_name = " ".join(
                [
                    normalize_text(getattr(update.effective_user, "first_name", None)),
                    normalize_text(getattr(update.effective_user, "last_name", None)),
                ]
            ).strip()

        req_username = normalize_text(update.effective_user.username if update.effective_user else "")
        tg_line = f"@{req_username}" if req_username else ""
        user_id_line = str(update.effective_user.id) if update.effective_user is not None else ""

        formatted_lines = ["📝 مشخصات متقاضی", "نوع: مشاوره"]
        if full_name:
            formatted_lines.append(f"نام: {full_name}")
        if collected_role:
            formatted_lines.append(f"نقش: {collected_role}")
        if collected_constituency:
            formatted_lines.append(f"حوزه انتخابیه: {collected_constituency}")
        if phone:
            formatted_lines.append(f"شماره تماس: {phone}")
        if tg_line:
            formatted_lines.append(f"آیدی تلگرام: {tg_line}")
        if user_id_line:
            formatted_lines.append(f"Telegram ID: {user_id_line}")
        formatted = "\n".join([x for x in formatted_lines if x]).strip()

        submission_id = await run_db_query(
            save_submission_sync,
            candidate_id=candidate_id,
            telegram_user_id=str(update.effective_user.id) if update.effective_user else "",
            telegram_username=(update.effective_user.username if update.effective_user else None),
            submission_type="BOT_REQUEST",
            topic=(collected_role or "مشاوره"),
            text=formatted,
            constituency=(collected_constituency or None),
            requester_full_name=(full_name or None),
            requester_contact=(phone or None),
            status="new_request",
        )

        try:
            def _normalize_chat_id(value: str | None) -> str | None:
                v = (str(value).strip() if value is not None else "")
                if not v:
                    return None
                if not re.fullmatch(r"-?\d+", v):
                    return None
                return v

            admin_chat_ids: list[str] = []
            fixed_id = _normalize_chat_id(BOT_NOTIFY_ADMIN_CHAT_ID)
            if fixed_id:
                admin_chat_ids.append(fixed_id)

            if BOT_NOTIFY_ADMIN_USERNAME:
                def _resolve_admin_chat_id(username: str) -> str | None:
                    uname = (username or "").lstrip("@").strip().lower()
                    if not uname:
                        return None
                    db = SessionLocal()
                    try:
                        row = (
                            db.query(BotUserRegistry)
                            .filter(
                                or_(
                                    func.lower(BotUserRegistry.telegram_username) == uname,
                                    func.lower(BotUserRegistry.telegram_username) == f"@{uname}",
                                )
                            )
                            .order_by(BotUserRegistry.last_seen_at.desc())
                            .first()
                        )
                        if not row:
                            return None
                        return str(row.telegram_user_id) if row.telegram_user_id else None
                    finally:
                        db.close()

                resolved_id = await run_db_query(_resolve_admin_chat_id, BOT_NOTIFY_ADMIN_USERNAME)
                resolved_id = _normalize_chat_id(resolved_id)
                if resolved_id and resolved_id not in admin_chat_ids:
                    admin_chat_ids.append(resolved_id)

            if admin_chat_ids:
                cand_name = normalize_text(candidate.get("full_name") or candidate.get("name") or "")
                cand_bot = normalize_text(candidate.get("bot_name") or "")
                header = f"📌 ثبت درخواست مشاوره (کد: {submission_id})"
                source = f"از بات: {cand_name} (@{cand_bot})" if cand_bot else f"از بات: {cand_name}"
                msg = "\n".join([x for x in [header, source, formatted] if x]).strip()
                for cid in admin_chat_ids:
                    # Don't echo the admin notification back into the same chat where the requester is talking to the bot.
                    if update.effective_chat and str(update.effective_chat.id) == str(cid):
                        continue
                    await context.bot.send_message(chat_id=int(cid), text=msg)
            else:
                logger.warning("BOT_REQUEST admin notify skipped: no admin chat id resolved")
        except Exception:
            logger.exception("Failed to notify admin of BOT_REQUEST")

        # After capturing contact, automatically "go back" and remove the contact-request keyboard.
        return_state = context.user_data.pop("_return_state", None)
        if return_state == STATE_OTHER_MENU:
            context.user_data["state"] = STATE_OTHER_MENU
            reply_markup = build_other_keyboard()
        else:
            context.user_data["state"] = STATE_MAIN
            reply_markup = build_main_keyboard()
        context.user_data.pop("botreq_full_name", None)
        context.user_data.pop("botreq_role", None)
        context.user_data.pop("botreq_constituency", None)
        context.user_data.pop("botreq_contact", None)
        await safe_reply_text(
            update.message,
            """⭐️ درخواست شما با موفقیت ثبت شد!

🔹 تیم پشتیبانی در کمتر از ۴۸ ساعت با شما تماس خواهد گرفت.""",
            reply_markup=reply_markup,
        )

        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="lead", event="flow_completed")
        except Exception:
            pass
        return

    if state == STATE_QUESTION_MENU:
        context.user_data["state"] = STATE_QUESTION_ENTRY
        await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
        return

    if state == STATE_FEEDBACK_TEXT:
        if text in {BTN_INTRO, BTN_PROGRAMS, BTN_FEEDBACK, BTN_FEEDBACK_LEGACY, BTN_QUESTION, BTN_CONTACT, BTN_BUILD_BOT}:
            await safe_reply_text(update.message, "برای ثبت نظر/دغدغه، لطفاً متن را ارسال کنید یا «بازگشت» را بزنید.")
            return

        constituency = candidate_constituency(candidate)
        await run_db_query(
            save_submission_sync,
            candidate_id=candidate_id,
            telegram_user_id=str(update.effective_user.id) if update.effective_user else "",
            telegram_username=(update.effective_user.username if update.effective_user else None),
            submission_type="FEEDBACK",
            topic=None,
            text=text,
            constituency=constituency,
        )
        context.user_data["state"] = STATE_MAIN
        context.user_data.pop("feedback_topic", None)
        await safe_reply_text(
            update.message,
            build_feedback_confirmation_text(socials),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_main_keyboard(),
        )

        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="comment", event="flow_completed")
        except Exception:
            pass
        return

    # SCREEN 1: entry
    if state == STATE_QUESTION_ENTRY:
        if _is_back(text):
            context.user_data["state"] = STATE_MAIN
            await safe_reply_text(update.message, "به منوی اصلی برگشتید.", reply_markup=build_main_keyboard())
            return
        if btn_eq(text, BTN_VIEW_QUESTIONS):
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return
        if btn_eq(text, BTN_ASK_NEW_QUESTION):
            context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
            await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return
        await safe_reply_text(update.message, "یکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
        return

    if state == STATE_QUESTION_VIEW_METHOD:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ENTRY
            await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
            return
        context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
        await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if state == STATE_QUESTION_VIEW_CATEGORY:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ENTRY
            await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
            return

        chosen = (text or "").replace("🗂", "").strip()
        if chosen not in QUESTION_CATEGORIES:
            await safe_reply_text(update.message, "دسته‌بندی نامعتبر است.", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        def _get_category_answered(cid: int, topic: str) -> list[BotSubmission]:
            db = SessionLocal()
            try:
                known = [c for c in QUESTION_CATEGORIES if c != "سایر"]
                if topic == "سایر":
                    q = (
                        db.query(BotSubmission)
                        .filter(
                            BotSubmission.candidate_id == int(cid),
                            BotSubmission.type == "QUESTION",
                            BotSubmission.status == "ANSWERED",
                            BotSubmission.is_public == True,  # noqa: E712
                            BotSubmission.answer.isnot(None),
                            or_(
                                BotSubmission.topic.is_(None),
                                BotSubmission.topic == "",
                                ~BotSubmission.topic.in_(known),
                            ),
                        )
                        .order_by(BotSubmission.answered_at.asc(), BotSubmission.id.asc())
                    )
                    return q.all()

                q = (
                    db.query(BotSubmission)
                    .filter(
                        BotSubmission.candidate_id == int(cid),
                        BotSubmission.type == "QUESTION",
                        BotSubmission.status == "ANSWERED",
                        BotSubmission.is_public == True,  # noqa: E712
                        BotSubmission.answer.isnot(None),
                        BotSubmission.topic == topic,
                    )
                    .order_by(BotSubmission.answered_at.asc(), BotSubmission.id.asc())
                )
                return q.all()
            finally:
                db.close()

        rows = await run_db_query(_get_category_answered, candidate_id, chosen)
        if not rows:
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(
                update.message,
                f"در دسته «{chosen}» هنوز پاسخ عمومی ثبت نشده است.\nیک دسته دیگر انتخاب کنید:",
                reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True),
            )
            return

        items: list[dict] = []
        for r in rows:
            q_txt = normalize_text(getattr(r, "text", ""))
            a_txt = normalize_text(getattr(r, "answer", ""))
            rid = getattr(r, "id", None)
            answered_at = getattr(r, "answered_at", None)
            topic_raw = normalize_text(getattr(r, "topic", ""))
            topic_for_card = topic_raw or chosen
            if q_txt and a_txt:
                items.append({"id": rid, "topic": topic_for_card, "q": q_txt, "a": a_txt, "answered_at": answered_at})

        context.user_data["view_topic"] = chosen
        context.user_data["state"] = STATE_QUESTION_VIEW_RESULTS

        await send_question_answers_message_cards_html(
            safe_reply=safe_reply_text,
            update_message=update.message,
            items=items,
            back_keyboard=build_back_keyboard(),
        )
        return

    if state == STATE_QUESTION_VIEW_RESULTS:
        if _is_back(text):
            context.user_data.pop("view_topic", None)
            context.user_data.pop("view_items", None)
            context.user_data.pop("view_choice", None)
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return
        await safe_reply_text(update.message, "برای برگشت، «بازگشت» را بزنید.", reply_markup=build_back_keyboard())
        return

    # Ask flow entry
    if state == STATE_QUESTION_ASK_ENTRY:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ENTRY
            await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
            return
        context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
        await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if state == STATE_QUESTION_ASK_TOPIC:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ENTRY
            await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
            return
        chosen = (text or "").replace("🗂", "").strip()
        if chosen not in QUESTION_CATEGORIES:
            await safe_reply_text(update.message, "موضوع نامعتبر است.", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        if chosen == "سایر":
            context.user_data["state"] = STATE_QUESTION_ASK_OTHER_TOPIC
            await safe_reply_text(
                update.message,
                "موضوع مدنظر خود را کوتاه بنویسید (مثلاً «یارانه»، «مالیات»، «کسب‌وکار»):\n(در یک پیام)",
                reply_markup=build_back_keyboard(),
            )
            return

        context.user_data["question_topic"] = chosen
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="question", event="flow_started")
        except Exception:
            pass
        context.user_data["state"] = STATE_QUESTION_ASK_TEXT
        await safe_reply_text(update.message, "سؤال‌تان را کوتاه و شفاف بنویسید.\n(در یک پیام)", reply_markup=build_back_keyboard())
        return

    if state == STATE_QUESTION_ASK_OTHER_TOPIC:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
            await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        other_topic = normalize_text(text)
        other_topic = re.sub(r"\s+", " ", other_topic).strip()
        if len(other_topic) < 2:
            await safe_reply_text(update.message, "موضوع خیلی کوتاه است. دوباره ارسال کنید:")
            return
        if len(other_topic) > 40:
            await safe_reply_text(update.message, "موضوع خیلی طولانی است (حداکثر ۴۰ کاراکتر). کوتاه‌تر کنید:")
            return

        # Store as a single string so the DB still captures the detail without schema changes.
        context.user_data["question_topic"] = f"سایر|{other_topic}"
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="question", event="flow_started")
        except Exception:
            pass
        context.user_data["state"] = STATE_QUESTION_ASK_TEXT
        await safe_reply_text(update.message, "سؤال‌تان را کوتاه و شفاف بنویسید.\n(در یک پیام)", reply_markup=build_back_keyboard())
        return

    if state == STATE_QUESTION_ASK_TEXT:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
            await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        q_text = (text or "").strip()
        if len(q_text) < 10:
            await safe_reply_text(update.message, "متن سؤال باید حداقل ۱۰ کاراکتر باشد. دوباره ارسال کنید:")
            return
        if len(q_text) > 500:
            await safe_reply_text(update.message, "متن سؤال باید حداکثر ۵۰۰ کاراکتر باشد. لطفاً کوتاه‌تر کنید:")
            return

        def _looks_duplicate(cid: int, norm: str) -> bool:
            db = SessionLocal()
            try:
                rows = (
                    db.query(BotSubmission)
                    .filter(BotSubmission.candidate_id == int(cid), BotSubmission.type == "QUESTION")
                    .order_by(BotSubmission.id.desc())
                    .limit(100)
                    .all()
                )
                for r in rows:
                    existing = normalize_text(getattr(r, "text", ""))
                    existing_norm = re.sub(r"\s+", " ", existing).strip().lower()
                    if existing_norm and existing_norm == norm:
                        return True
                return False
            finally:
                db.close()

        norm = re.sub(r"\s+", " ", q_text).strip().lower()
        is_dup = await run_db_query(_looks_duplicate, candidate_id, norm)
        if is_dup:
            context.user_data["state"] = STATE_MAIN
            context.user_data.pop("question_topic", None)
            await safe_reply_text(update.message, "این سؤال قبلاً ثبت شده است.", reply_markup=build_main_keyboard())
            return

        topic = normalize_text(context.user_data.get("question_topic")) or None
        constituency = candidate_constituency(candidate)
        await run_db_query(
            save_submission_sync,
            candidate_id=candidate_id,
            telegram_user_id=str(update.effective_user.id) if update.effective_user else "",
            telegram_username=(update.effective_user.username if update.effective_user else None),
            submission_type="QUESTION",
            topic=topic,
            text=q_text,
            constituency=constituency,
            status="PENDING",
            is_public=False,
        )

        context.user_data["state"] = STATE_MAIN
        context.user_data.pop("question_topic", None)
        await safe_reply_text(update.message, "ممنون. سؤال شما ثبت شد و به نماینده منتقل می‌شود.", reply_markup=build_main_keyboard())

        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="question", event="flow_completed")
        except Exception:
            pass
        return

    # Programs state
    if state == STATE_PROGRAMS:
        def _program_choice_index(t: str) -> int:
            tt = normalize_button_text(t)
            if tt.startswith("سوال "):
                try:
                    return int(tt.replace("سوال", "").strip()) - 1
                except Exception:
                    return -1
            m = re.match(r"^(\d{1,2})\s*\)", tt)
            if m:
                try:
                    return int(m.group(1)) - 1
                except Exception:
                    return -1
            if re.fullmatch(r"\d{1,2}", tt):
                try:
                    return int(tt) - 1
                except Exception:
                    return -1
            # Allow selecting from richer labels like "1) 🧾 شفافیت".
            m2 = re.match(r"^(\d{1,2})\D+", tt)
            if m2:
                try:
                    return int(m2.group(1)) - 1
                except Exception:
                    return -1
            return -1

        idx = _program_choice_index(text)
        if 0 <= idx < len(PROGRAM_QUESTIONS):
            rep_name = normalize_text(candidate.get("name")) or "نماینده"
            q = normalize_text(PROGRAM_QUESTIONS[idx])
            a = normalize_text(get_program_answer(candidate, idx))

            blocks: list[str] = []
            blocks.append("🟢 <b>برنامه‌ها</b>")
            blocks.append("──────────────")
            blocks.append(f"❓ {idx + 1}) {html.escape(q)}")
            blocks.append("")
            blocks.append(f"✅ <b>پاسخ {html.escape(rep_name)}</b>")
            blocks.append(html.escape(a) if a else "—")

            await safe_reply_text(
                update.message,
                "\n".join([b for b in blocks if b is not None]).strip(),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return
        await safe_reply_text(update.message, "لطفاً یکی از گزینه‌ها را انتخاب کنید یا «بازگشت» را بزنید.")
        return

    # Global handlers for step-based question UX
    if btn_eq(text, BTN_VIEW_QUESTIONS) or btn_has(text, "مشاهده سوال", "مشاهده سؤال"):
        context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
        await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if btn_eq(text, BTN_ASK_NEW_QUESTION) or btn_has(text, "ثبت سوال", "ثبت سؤال"):
        context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
        await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if btn_eq(text, BTN_VIEW_BY_CATEGORY) or btn_has(text, "دسته بندی", "دسته‌بندی"):
        context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
        await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if btn_eq(text, BTN_VIEW_BY_SEARCH) or btn_has(text, "جستجو"):
        context.user_data["state"] = STATE_QUESTION_VIEW_SEARCH_TEXT
        await safe_reply_text(update.message, "کلمه یا جمله کوتاه را بنویسید تا در سؤال‌ها جستجو کنم.", reply_markup=build_back_keyboard())
        return

    if btn_eq(text, BTN_SELECT_TOPIC) or btn_has(text, "انتخاب موضوع"):
        context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
        await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    # Main menu
    if btn_eq(text, BTN_ABOUT_MENU):
        context.user_data["state"] = STATE_ABOUT_MENU
        await safe_reply_text(update.message, "📂 درباره نماینده\n\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=build_about_keyboard())
        return

    if btn_eq(text, BTN_OTHER_MENU):
        context.user_data["state"] = STATE_OTHER_MENU
        try:
            other_image_url = None
            if isinstance(bot_config, dict):
                other_image_url = (
                    bot_config.get("other_menu_image_url")
                    or bot_config.get("otherMenuImageUrl")
                    or bot_config.get("other_image_url")
                    or bot_config.get("otherImageUrl")
                    or bot_config.get("image_url2")
                    or bot_config.get("imageUrl2")
                    or bot_config.get("image_url_2")
                    or bot_config.get("second_image_url")
                    or bot_config.get("secondImageUrl")
                )

                if not other_image_url:
                    lst = bot_config.get("menu_images") or bot_config.get("menuImages") or bot_config.get("slides") or bot_config.get("images")
                    if isinstance(lst, list) and len(lst) >= 2:
                        other_image_url = lst[1]

            other_image_url = normalize_text(other_image_url)
            if other_image_url:
                local_path = upload_file_path_from_localhost_url(other_image_url)
                if local_path:
                    with open(local_path, "rb") as f:
                        await update.message.reply_photo(photo=f)
                else:
                    await update.message.reply_photo(photo=other_image_url)
        except Exception:
            logger.exception("Failed to send OTHER menu image")

        await safe_reply_text(update.message, "⚙️ سایر امکانات\n\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=build_other_keyboard())
        return

    if btn_eq(text, BTN_COMMITMENTS):

        from sqlalchemy.orm import joinedload
        from utils.cache import cache_get_json, cache_set_json
        import models

        def _get_commitments(cid: int):
            db = SessionLocal()
            try:
                rows = (
                    db.query(models.BotCommitment)
                    .options(joinedload(models.BotCommitment.progress_logs))
                    .filter(models.BotCommitment.candidate_id == int(cid))
                    .order_by(models.BotCommitment.created_at.desc())
                    .limit(10)
                    .all()
                )
                # Serialize for cache (only needed fields)
                result = []
                for r in rows:
                    result.append({
                        "id": r.id,
                        "title": r.title,
                        "body": r.body,
                        "status": r.status,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "created_at_jalali": getattr(r, "created_at_jalali", None),
                        "progress_logs": [
                            {
                                "created_at": log.created_at.isoformat() if log.created_at else None,
                                "note": log.note,
                            }
                            for log in getattr(r, "progress_logs", [])
                        ],
                    })
                return result
            finally:
                db.close()

        context.user_data["state"] = STATE_COMMITMENTS_VIEW
        cache_key = f"commitments:{candidate_id}"
        rows = cache_get_json(cache_key)
        if rows is None:
            # Not cached, fetch and cache
            rows = await run_db_query(_get_commitments, candidate_id)
            cache_set_json(cache_key, rows, 60)  # Cache for 60 seconds

        if not rows:
            await safe_reply_text(
                update.message,
                "📜 تعهدات نماینده\n\nℹ️ تعهدات نماینده اسنادی رسمی هستند.\nپس از ثبت، متن آن‌ها غیرقابل ویرایش است.\nتنها وضعیت و گزارش پیشرفت به‌روزرسانی می‌شود.\n\n📭 هنوز تعهدی ثبت نشده است.",
                reply_markup=build_back_keyboard(),
            )
            return

        # Minimal, per-commitment cards (each commitment in a separate message)
        await safe_reply_text(
            update.message,
            "📜 تعهدات نماینده\n\nهر تعهد به‌صورت کارت مستقل نمایش داده می‌شود.",
            reply_markup=None,
        )

        from .text_utils import to_fa_digits, to_jalali_date_ymd
        import datetime

        def _status_emoji(value: str | None) -> tuple[str, str]:
            v = (value or "").strip().lower()
            if v == "completed":
                return "✅", "انجام‌شده"
            # Spec only asks for two states; treat everything else as "in progress".
            return "🟡", "در حال پیگیری"

        def _shorten_inline(text: str, max_len: int) -> str:
            s = normalize_text(text)
            s = re.sub(r"\s+", " ", s).strip()
            if not s:
                return ""
            if len(s) <= max_len:
                return s
            return (s[: max(0, max_len - 1)].rstrip() + "…")

        def _summary_3_lines(text: str, *, max_lines: int = 3, line_len: int = 46) -> str:
            s = normalize_text(text)
            s = s.replace("\r", " ").replace("\n", " ")
            s = re.sub(r"\s+", " ", s).strip()
            if not s:
                return ""
            words = s.split(" ")
            lines: list[str] = []
            cur = ""
            idx = 0
            truncated = False

            while idx < len(words) and len(lines) < max_lines:
                w = words[idx]
                candidate = (cur + " " + w).strip() if cur else w
                if len(candidate) <= line_len:
                    cur = candidate
                    idx += 1
                    continue

                if cur:
                    lines.append(cur)
                    cur = ""
                    continue

                # single very-long word
                lines.append(w[: max(1, line_len - 1)] + "…")
                idx += 1

            if cur and len(lines) < max_lines:
                lines.append(cur)

            if idx < len(words):
                truncated = True

            if truncated and lines:
                # Ensure last line ends with ellipsis.
                if not lines[-1].endswith("…"):
                    if len(lines[-1]) >= line_len:
                        lines[-1] = lines[-1][: max(1, line_len - 1)].rstrip() + "…"
                    else:
                        lines[-1] = lines[-1].rstrip() + "…"

            return "\n".join(lines[:max_lines]).strip()

        for i, r in enumerate(rows, start=1):
            emoji, status_label = _status_emoji(str(r.get("status") or ""))

            title = _shorten_inline(r.get("title", ""), 60)
            body = normalize_text(r.get("body", ""))
            summary = _summary_3_lines(body)

            created_at_jalali = normalize_text(r.get("created_at_jalali"))
            created_at = normalize_text(r.get("created_at"))
            dt = None
            if created_at:
                try:
                    dt = datetime.datetime.fromisoformat(created_at)
                except Exception:
                    dt = None
            date_label = created_at_jalali or (to_jalali_date_ymd(dt) if dt else "—")

            parts: list[str] = []
            parts.append(f"🧾 تعهد شماره {to_fa_digits(i)}")
            if title:
                parts.append(f"عنوان: {title}")
            parts.append(f"وضعیت: {emoji} {status_label}")
            if summary:
                parts.append("خلاصه:")
                parts.append(summary)
            parts.append(f"📅 تاریخ ثبت: {date_label}")

            await safe_reply_text(update.message, "\n".join([p for p in parts if p]).strip(), reply_markup=None)
        await safe_reply_text(update.message, "برای بازگشت، دکمه بازگشت را بزنید.", reply_markup=build_back_keyboard())
        return

    if state == STATE_ABOUT_MENU:
        if btn_eq(text, BTN_ABOUT_INTRO) or btn_eq(text, BTN_INTRO):
            context.user_data["_return_state"] = STATE_ABOUT_MENU
            context.user_data["state"] = STATE_ABOUT_DETAIL
            text = BTN_INTRO
        elif btn_eq(text, BTN_PROGRAMS) or btn_has(text, "برنامه"):
            context.user_data["_return_state"] = STATE_ABOUT_MENU
        elif btn_eq(text, BTN_HQ_ADDRESSES) or btn_eq(text, BTN_CONTACT):
            context.user_data["_return_state"] = STATE_ABOUT_MENU
            context.user_data["state"] = STATE_ABOUT_DETAIL
            text = BTN_CONTACT
        elif btn_eq(text, BTN_VOICE_INTRO):
            context.user_data["_return_state"] = STATE_ABOUT_MENU
            context.user_data["state"] = STATE_ABOUT_DETAIL

    if state == STATE_OTHER_MENU:
        if btn_eq(text, BTN_BUILD_BOT):
            text = BTN_BUILD_BOT
        elif btn_eq(text, BTN_ABOUT_BOT):
            await safe_reply_text(
                update.message,
                """━━ 🤖 درباره این بات ━━

این بات برای ایجاد یک پل شفاف بین مردم و نمایندگان طراحی شده است.

اینجا می‌تونی:
❓ سوال‌های واقعی مردم رو ببینی  
🗣 پاسخ‌های رسمی و ثبت‌شده نمایندگان رو بخونی  
📌 تعهداتی که اعلام می‌شن رو به‌صورت عمومی دنبال کنی  

🔒 نکته مهم:
پاسخ‌ها و تعهدات بعد از انتشار قابل ویرایش نیستند و
همه چیز با تاریخ و زمان ثبت می‌شود.

🎯 هدف ما:
شفافیت، مسئولیت‌پذیری و دسترسی ساده به اطلاعات
— بدون حاشیه، بدون تبلیغ.

━━ پایان ━━""",
                reply_markup=build_other_keyboard(),
            )
            return

    if btn_eq(text, BTN_INTRO):
        # If the user entered via the About submenu, keep back-navigation to the About menu.
        if state == STATE_ABOUT_MENU or context.user_data.get("_return_state") == STATE_ABOUT_MENU:
            context.user_data["_return_state"] = STATE_ABOUT_MENU
            context.user_data["state"] = STATE_ABOUT_DETAIL
            state = STATE_ABOUT_DETAIL

        name = normalize_text(candidate.get("name")) or "نماینده"
        constituency = normalize_text(candidate_constituency(candidate))
        slogan_raw = normalize_text(candidate.get("slogan") or (candidate.get("bot_config") or {}).get("slogan"))

        image_url = normalize_text(candidate.get("image_url"))
        if image_url:
            local_path = upload_file_path_from_localhost_url(image_url)
            try:
                if local_path:
                    with open(local_path, "rb") as f:
                        await update.message.reply_photo(photo=f, caption=name)
                else:
                    await update.message.reply_photo(photo=image_url, caption=name)
            except Exception as e:
                logger.error("Failed to send candidate photo: %s", e)

        def _parse_slogans(raw: str) -> list[str]:
            if not raw:
                return []
            s = re.sub(r"\r\n?", "\n", raw).strip()
            parts: list[str]
            if "\n" in s:
                parts = [p.strip() for p in s.split("\n")]
            elif "؛" in s:
                parts = [p.strip() for p in s.split("؛")]
            elif "،" in s:
                parts = [p.strip() for p in s.split("،")]
            elif "|" in s:
                parts = [p.strip() for p in s.split("|")]
            else:
                parts = [s]

            cleaned: list[str] = []
            for p in parts:
                p = re.sub(r"^[-•●▪▫✅🟢🔰✨\s]+", "", p).strip()
                p = re.sub(r"\s+", " ", p)
                if p:
                    cleaned.append(p)
            return cleaned[:5]

        esc_name = html.escape(name)
        esc_constituency = html.escape(constituency)
        slogans = _parse_slogans(slogan_raw)
        esc_slogans = [html.escape(s) for s in slogans]

        blocks: list[str] = []
        blocks.append(f"🟢 <b>{esc_name}</b>")
        blocks.append("──────────────")
        if esc_constituency:
            blocks.append(f"📍 <b>حوزه انتخاباتی:</b> {esc_constituency}")
        if esc_slogans:
            blocks.append("✨ <b>شعارها</b>")
            blocks.extend([f"🔰 {s}" for s in esc_slogans])

        message_html = "\n".join([b for b in blocks if b]).strip()

        await safe_reply_text(
            update.message,
            message_html,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(BTN_PROFILE_SUMMARY), KeyboardButton(BTN_BACK)]],
                resize_keyboard=True,
                is_persistent=True,
            ),
        )
        return

    if btn_eq(text, BTN_PROFILE_SUMMARY):
        # When accessed from the About flow, Back should return to the About menu.
        if state in {STATE_ABOUT_MENU, STATE_ABOUT_DETAIL} or context.user_data.get("_return_state") == STATE_ABOUT_MENU:
            context.user_data["_return_state"] = STATE_ABOUT_MENU
            context.user_data["state"] = STATE_ABOUT_DETAIL
            state = STATE_ABOUT_DETAIL

        name = normalize_text(candidate.get("name")) or "نماینده"

        def _coerce_bot_config_local(cand: dict) -> dict:
            raw = cand.get("bot_config")
            if raw is None:
                return {}
            if isinstance(raw, dict):
                return raw
            if isinstance(raw, str):
                s = raw.strip()
                if not s:
                    return {}
                try:
                    parsed = json.loads(s)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
            return {}

        def _as_lines(v) -> list[str]:
            if v is None:
                return []
            if isinstance(v, list):
                return [normalize_text(x) for x in v if normalize_text(x)]
            if isinstance(v, str):
                return [s.strip() for s in v.splitlines() if s.strip()]
            vv = normalize_text(v)
            return [vv] if vv else []

        bot_cfg = _coerce_bot_config_local(candidate)
        structured = bot_cfg.get("structured_resume") if isinstance(bot_cfg, dict) else None

        blocks: list[str] = []
        blocks.append(f"🟢 <b>{html.escape(name)}</b>")
        blocks.append("──────────────")

        # Per UX request: show only these 3 sections (no extra sections like highlights/title/experience).
        education_items: list[str] = []
        executive_items: list[str] = []
        social_items: list[str] = []
        experience_items: list[str] = []
        if isinstance(structured, dict):
            education_items = _as_lines(structured.get("education"))
            executive_items = _as_lines(structured.get("executive"))
            social_items = _as_lines(structured.get("social"))
            experience_items = _as_lines(structured.get("experience"))

        # تحصیلات
        blocks.append("🎓 <b>تحصیلات</b>")
        if education_items:
            blocks.extend([f"• {html.escape(x)}" for x in education_items[:10]])
        else:
            blocks.append("• ---")

        # سابقه اجرایی (اگر خالی بود، از experience استفاده کن تا محتوا حذف نشود)
        blocks.append("\n🏛 <b>سابقه اجرایی</b>")
        exec_items = executive_items or experience_items
        if exec_items:
            blocks.extend([f"• {html.escape(x)}" for x in exec_items[:12]])
        else:
            blocks.append("• ---")

        # سابقه اجتماعی / مردمی
        blocks.append("\n🤝 <b>سابقه اجتماعی / مردمی</b>")
        if social_items:
            blocks.extend([f"• {html.escape(x)}" for x in social_items[:12]])
        else:
            blocks.append("• ---")

        message_html = "\n".join([b for b in blocks if b]).strip()
        await safe_reply_text(
            update.message,
            message_html,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_back_keyboard(),
        )
        return

    if btn_eq(text, BTN_VOICE_INTRO):
        # If invoked from About (or its detail pages), Back returns to the About menu.
        if state in {STATE_ABOUT_MENU, STATE_ABOUT_DETAIL} or context.user_data.get("_return_state") == STATE_ABOUT_MENU:
            context.user_data["_return_state"] = STATE_ABOUT_MENU
            context.user_data["state"] = STATE_ABOUT_DETAIL
            state = STATE_ABOUT_DETAIL

        voice_url = normalize_text(candidate.get("voice_url") or (bot_config.get("voice_url") if isinstance(bot_config, dict) else None))
        if not voice_url:
            await safe_reply_text(update.message, "🎧 معرفی صوتی نماینده در حال حاضر ثبت نشده است.")
            return

        caption = "🎧 معرفی صوتی نماینده (حداکثر ۶۰ ثانیه)"
        try:
            # Telegram servers cannot fetch localhost/127.0.0.1 URLs.
            # When running locally, the uploaded file exists on disk, so send it directly.
            local_path = upload_file_path_from_localhost_url(voice_url)
            if local_path:
                ext = os.path.splitext(local_path)[1].lower()
                with open(local_path, "rb") as f:
                    if ext == ".ogg":
                        await update.message.reply_voice(voice=f, caption=caption, reply_markup=build_back_keyboard())
                    else:
                        try:
                            await update.message.reply_audio(audio=f, caption=caption, reply_markup=build_back_keyboard())
                        except Exception:
                            await update.message.reply_document(document=f, caption=caption, reply_markup=build_back_keyboard())
            else:
                try:
                    await update.message.reply_voice(voice=voice_url, caption=caption, reply_markup=build_back_keyboard())
                except Exception:
                    await update.message.reply_audio(audio=voice_url, caption=caption, reply_markup=build_back_keyboard())
        except Exception as e:
            logger.error("Failed to send voice intro: %s", e)
            await safe_reply_text(update.message, "⚠️ فایل معرفی صوتی در دسترس نیست.")
        return

    if state in {STATE_MAIN, STATE_ABOUT_MENU, STATE_OTHER_MENU} and (btn_eq(text, BTN_PROGRAMS) or btn_has(text, "برنامه")):
        context.user_data["state"] = STATE_PROGRAMS

        intro_html = (
            "🟢 <b>برنامه‌ها</b>\n"
            "──────────────\n"
            "🗳️ <b>درباره این پرسش‌ها</b>\n"
            "این پرسش‌ها به‌صورت یکسان و تکراری از همه کاندیداها پرسیده می‌شود تا کاربران بتوانند برنامه‌ها، دیدگاه‌ها و اولویت‌ها را به‌صورت شفاف، منصفانه و قابل مقایسه بررسی کنند.\n\n"
            "هدف این بخش، کمک به انتخاب آگاهانه و مقایسه واقعی برنامه‌هاست، نه تبلیغ فردی.\n\n"
            "👇 <b>یک پرسش را انتخاب کنید:</b>"
        )

        program_buttons = [
            "1) 🧾 شفافیت",
            "2) 🚦 ترافیک",
            "3) 🏠 مسکن",
            "4) 🏘 محله",
            "5) 🌫 هوا",
            "6) ⚖️ عدالت",
            "7) 🤖 هوشمند",
            "8) 🗣 مشارکت",
            "9) 🧭 پاسخگویی",
            "10) 📣 ارتباط",
        ]
        rows = [
            [KeyboardButton(program_buttons[1]), KeyboardButton(program_buttons[0])],
            [KeyboardButton(program_buttons[3]), KeyboardButton(program_buttons[2])],
            [KeyboardButton(program_buttons[5]), KeyboardButton(program_buttons[4])],
            [KeyboardButton(program_buttons[7]), KeyboardButton(program_buttons[6])],
            [KeyboardButton(program_buttons[9]), KeyboardButton(program_buttons[8])],
            [KeyboardButton(BTN_BACK)],
        ]

        await safe_reply_text(
            update.message,
            intro_html,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=ReplyKeyboardMarkup(
                rows,
                resize_keyboard=True,
                is_persistent=True,
            ),
        )
        return

    if btn_eq(text, BTN_FEEDBACK) or btn_eq(text, BTN_FEEDBACK_LEGACY):
        context.user_data["state"] = STATE_FEEDBACK_TEXT
        await safe_reply_text(
            update.message,
            build_feedback_intro_text(FEEDBACK_INTRO_TEXT, socials),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_back_keyboard(),
        )
        await safe_reply_text(
            update.message,
            "🟢 <b>ارسال نظر / دغدغه</b>\n"
            "──────────────\n"
            "👇 <b>متن پیام را ارسال کنید:</b>\n"
            "(برای بازگشت، «🔙 بازگشت» را بزنید.)",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_back_keyboard(),
        )
        return

    if btn_eq(text, BTN_QUESTION):
        context.user_data["state"] = STATE_QUESTION_ENTRY
        await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
        return

    if btn_eq(text, BTN_REGISTER_QUESTION):
        context.user_data["state"] = STATE_QUESTION_ASK_ENTRY
        await safe_reply_text(update.message, "برای ثبت سؤال جدید، مرحله بعد را انجام دهید.", reply_markup=build_question_ask_entry_keyboard())
        return

    if btn_eq(text, BTN_SEARCH_QUESTION):
        context.user_data["state"] = STATE_QUESTION_VIEW_METHOD
        await safe_reply_text(update.message, "برای مشاهده سؤال‌ها، یکی را انتخاب کنید:", reply_markup=build_question_view_method_keyboard())
        return

    if btn_eq(text, BTN_CONTACT):
        offices = (bot_config.get("offices") if isinstance(bot_config, dict) else None)
        if not isinstance(offices, list):
            offices = []
        offices = offices[:3]

        if offices:
            blocks: list[str] = []
            blocks.append("🟢 <b>ارتباط با نماینده</b>")
            blocks.append("──────────────")

            office_blocks: list[str] = []
            for office in offices:
                if not isinstance(office, dict):
                    continue
                title = normalize_text(office.get("title")) or "ستاد"
                address = normalize_text(office.get("address"))
                status = normalize_text(office.get("status"))
                manager = normalize_text(office.get("manager"))
                details = normalize_text(office.get("details")) or normalize_text(office.get("note"))
                phone = normalize_text(office.get("phone"))

                t = html.escape(title)
                a = html.escape(address) if address else ""
                s = html.escape(status) if status else ""
                m = html.escape(manager) if manager else ""
                d = html.escape(details) if details else ""
                p = html.escape(phone) if phone else ""

                lines: list[str] = []
                lines.append(f"📍 <b>{t}</b>")
                if s:
                    lines.append(f"📌 <b>وضعیت:</b> {s}")
                if m:
                    lines.append(f"👤 <b>مسئول ستاد:</b> {m}")
                if p:
                    lines.append(f"☎️ <b>شماره تماس:</b> {p}")
                if a:
                    lines.append(f"🧾 <b>آدرس:</b> {a}")
                if d:
                    lines.append(f"📝 <b>توضیحات:</b> {d}")
                office_blocks.append("\n".join(lines))

            if office_blocks:
                blocks.append("\n\n".join(office_blocks))
                message_html = "\n".join([b for b in blocks if b]).strip()
                await safe_reply_text(
                    update.message,
                    message_html,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=build_back_keyboard(),
                )
                return

        phone = normalize_text(candidate.get("phone")) or "---"
        address = normalize_text(candidate.get("address"))

        blocks: list[str] = []
        blocks.append("🟢 <b>ارتباط با نماینده</b>")
        blocks.append("──────────────")
        blocks.append(f"☎️ <b>شماره تماس:</b> {html.escape(phone)}")
        if address:
            blocks.append(f"📍 <b>آدرس ستاد:</b> {html.escape(address)}")
        if socials:
            if socials.get("telegramChannel"):
                blocks.append(f"📣 <b>کانال تلگرام:</b> {html.escape(str(socials['telegramChannel']))}")
            if socials.get("telegramGroup"):
                blocks.append(f"👥 <b>گروه تلگرام:</b> {html.escape(str(socials['telegramGroup']))}")
            if socials.get("instagram"):
                blocks.append(f"📸 <b>اینستاگرام:</b> {html.escape(str(socials['instagram']))}")

        message_html = "\n".join([b for b in blocks if b]).strip()
        await safe_reply_text(
            update.message,
            message_html,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_back_keyboard(),
        )
        return

    if btn_eq(text, BTN_BUILD_BOT):
        blocks: list[str] = []
        blocks.append("🟢 <b>ساخت بات اختصاصی</b>")
        blocks.append("──────────────")
        blocks.append("این بات نمونه‌ای از بات ارتباط مستقیم نماینده با مردم است.")
        blocks.append("")
        blocks.append("اگر شما نماینده، کاندیدا یا فعال سیاسی هستید،")
        blocks.append("می‌توانید بات اختصاصی خودتان را داشته باشید.")
        blocks.append("")
        blocks.append("✨ <b>امکانات</b>")
        blocks.extend(
            [
                "🔰 معرفی رسمی نماینده",
                "🔰 دریافت نظر و دغدغه مردم",
                "🔰 پاسخ‌گویی شفاف به سؤالات",
                "🔰 انتشار برنامه‌ها",
                "🔰 اعلان پاسخ‌ها",
                "🔰 پنل مدیریت اختصاصی",
            ]
        )

        message_html = "\n".join([b for b in blocks if b is not None]).strip()
        await safe_reply_text(
            update.message,
            message_html,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_bot_request_cta_keyboard(),
        )
        return

    if btn_eq(text, BTN_BOT_REQUEST):
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="lead", event="flow_started")
        except Exception:
            pass
        if context.user_data.get("state") == STATE_OTHER_MENU:
            context.user_data["_return_state"] = STATE_OTHER_MENU

        # Prevent re-entering the flow if user already submitted before.
        try:
            if update.effective_user is not None:
                already = await run_db_query(
                    _has_existing_bot_request_sync,
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    phone=None,
                )
                if already:
                    return_state = context.user_data.pop("_return_state", None)
                    if return_state == STATE_OTHER_MENU:
                        context.user_data["state"] = STATE_OTHER_MENU
                        reply_markup = build_other_keyboard()
                    else:
                        context.user_data["state"] = STATE_MAIN
                        reply_markup = build_main_keyboard()

                    await safe_reply_text(
                        update.message,
                        "✅ درخواست شما قبلاً ثبت شده است.\nتیم پشتیبانی به‌زودی با شما تماس می‌گیرد.",
                        reply_markup=reply_markup,
                    )
                    return
        except Exception:
            pass

        context.user_data["state"] = STATE_BOTREQ_CONTACT
        await safe_reply_text(
            update.message,
            """برای ثبت درخواست مشاوره، لطفاً شماره تماس خود را با دکمه زیر ارسال کنید.""",
            reply_markup=build_bot_request_contact_keyboard(),
        )
        return

    # Idle fallback
    if state == STATE_MAIN:
        try:
            if raw_text and raw_text != text:
                logger.info(
                    "MAIN fallback text mismatch: raw=%r normalized=%r raw_codepoints=%s normalized_codepoints=%s",
                    raw_text,
                    text,
                    [ord(c) for c in raw_text],
                    [ord(c) for c in text],
                )
        except Exception:
            pass
        context.user_data["state"] = STATE_MAIN
        await safe_reply_text(update.message, "لطفاً یکی از گزینه‌های منو را انتخاب کنید.", reply_markup=build_main_keyboard())
        return

    if state == STATE_ABOUT_MENU:
        await safe_reply_text(update.message, "لطفاً یکی از گزینه‌های «درباره نماینده» را انتخاب کنید یا «بازگشت» را بزنید.", reply_markup=build_about_keyboard())
        return

    if state == STATE_OTHER_MENU:
        await safe_reply_text(update.message, "لطفاً یکی از گزینه‌های «سایر امکانات» را انتخاب کنید یا «بازگشت» را بزنید.", reply_markup=build_other_keyboard())
        return

    await safe_reply_text(update.message, "لطفاً یکی از گزینه‌ها را انتخاب کنید یا «بازگشت» را بزنید.", reply_markup=build_back_keyboard())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


    # ثبت خطا در فایل مجزا و ارسال به تلگرام مدیر
    try:
        import os
        from datetime import datetime
        from telegram import Bot
        log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "bot_errors.log")
        error_time = datetime.now().isoformat()
        error_text = f"[{error_time}] {repr(context.error)}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(error_text)

        # ارسال پیام به آیدی تلگرام مدیر (جایگزین کنید)
        ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID") or "96763697"
        # اگر توکن ربات اصلی دارید، مقداردهی کنید
        ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN") or None
        if ADMIN_BOT_TOKEN and ADMIN_TELEGRAM_ID and ADMIN_TELEGRAM_ID != "YOUR_TELEGRAM_ID":
            try:
                bot = Bot(token=ADMIN_BOT_TOKEN)
                bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=f"❗️ خطای جدید در Election Manager:\n{error_text}")
            except Exception as notify_err:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[NOTIFY_FAIL] {notify_err}\n")
    except Exception:
        pass

    try:
        candidate_id = context.bot_data.get("candidate_id") if hasattr(context, "bot_data") else None
        telegram_user_id = None
        state = None
        if isinstance(update, Update):
            if update.effective_user is not None:
                telegram_user_id = str(update.effective_user.id)
            if update.effective_message is not None and hasattr(context, "user_data"):
                state = context.user_data.get("state")

        err = context.error
        log_technical_error_sync(
            service_name="telegram_bot",
            error_type=err.__class__.__name__ if err else "UnknownError",
            error_message=str(err) if err else "Unknown error",
            telegram_user_id=telegram_user_id,
            candidate_id=int(candidate_id) if candidate_id is not None else None,
            state=state,
        )
    except Exception:
        pass
