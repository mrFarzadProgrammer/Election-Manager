import asyncio
import atexit
import contextlib
import logging
import signal
import re
from datetime import datetime, timedelta, timezone
import os
import tempfile
from urllib.parse import urlparse
from typing import List
from pathlib import Path
import jdatetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut, RetryAfter
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from dotenv import load_dotenv
from database import SessionLocal, Base, engine
import models
from models import User, BotUser, BotSubmission, BotUserRegistry

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Avoid leaking Telegram bot token via HTTP request logs (URLs contain /bot<token>/...)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Load env vars from .env (repo root and/or backend cwd)
load_dotenv()
try:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

FAILED_BOT_COOLDOWN = timedelta(minutes=5)

# Update processing concurrency (python-telegram-bot)
#
# Polling cannot be horizontally scaled for a single bot token (Telegram 409 Conflict),
# so the main lever for handling high message volume is *concurrent update processing*
# inside one runner process.
#
# Set BOT_CONCURRENT_UPDATES to control max concurrent updates per bot.
# Example: 64, 128, 256 (depends on CPU/DB/network).
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


Base.metadata.create_all(bind=engine)


# --- Telegram polling conflict (409) admin logging ---

_last_409_logged_at_by_candidate: dict[int, datetime] = {}


class _Telegram409ConflictHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage() or ""
            if "terminated by other getUpdates request" not in msg and "telegram.error.Conflict" not in msg:
                return

            # Best-effort: apply to the current running candidate(s). In this runner we typically have a single
            # candidate active locally, but we still rate-limit by candidate_id.
            for cid, app in list(running_bots.items()):
                if app is None:
                    continue
                last = _last_409_logged_at_by_candidate.get(int(cid))
                now = datetime.utcnow()
                if last and (now - last) < timedelta(minutes=10):
                    continue
                _last_409_logged_at_by_candidate[int(cid)] = now
                log_technical_error_sync(
                    service_name="telegram_bot",
                    error_type="Conflict409",
                    error_message=(
                        "Telegram getUpdates 409 Conflict: another poller is running for this bot token. "
                        "Stop other bot_runner instances and ensure only one machine/service polls this token."
                    ),
                    candidate_id=int(cid),
                    telegram_user_id=None,
                    state=None,
                )
        except Exception:
            # Never break logging
            return


try:
    _updater_logger = logging.getLogger("telegram.ext.Updater")
    _updater_logger.addHandler(_Telegram409ConflictHandler())
except Exception:
    pass


# --- Monitoring MVP helpers (DB-backed) ---

def log_ux_sync(
    *,
    candidate_id: int,
    telegram_user_id: str,
    state: str | None,
    action: str,
    expected_action: str | None = None,
) -> None:
    """Best-effort UX/state-machine log."""
    db: Session = SessionLocal()
    try:
        db.add(
            models.BotUxLog(
                candidate_id=int(candidate_id),
                telegram_user_id=str(telegram_user_id),
                state=state,
                action=str(action),
                expected_action=expected_action,
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def track_path_sync(*, candidate_id: int, path: str) -> None:
    """Increment a Top-Paths counter for both candidate and global scopes."""

    def _inc(db: Session, cid: int | None, p: str) -> None:
        row = (
            db.query(models.BotFlowPathCounter)
            .filter(models.BotFlowPathCounter.candidate_id.is_(None) if cid is None else models.BotFlowPathCounter.candidate_id == int(cid))
            .filter(models.BotFlowPathCounter.path == str(p))
            .first()
        )
        if row is None:
            row = models.BotFlowPathCounter(candidate_id=cid, path=str(p), count=0, updated_at=datetime.utcnow())
            db.add(row)
        row.count = int(row.count or 0) + 1
        row.updated_at = datetime.utcnow()

    db = SessionLocal()
    try:
        _inc(db, int(candidate_id), path)
        _inc(db, None, path)
        db.commit()
    finally:
        db.close()


def log_technical_error_sync(
    *,
    service_name: str,
    error_type: str,
    error_message: str,
    telegram_user_id: str | None = None,
    candidate_id: int | None = None,
    state: str | None = None,
) -> None:
    """Best-effort technical error log."""
    db: Session = SessionLocal()
    try:
        db.add(
            models.TechnicalErrorLog(
                service_name=str(service_name),
                error_type=str(error_type),
                error_message=str(error_message)[:4000],
                telegram_user_id=str(telegram_user_id) if telegram_user_id is not None else None,
                candidate_id=int(candidate_id) if candidate_id is not None else None,
                state=state,
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def track_flow_event_sync(*, candidate_id: int, flow_type: str, event: str) -> None:
    """Increment flow drop counters (started/completed/abandoned)."""
    event = str(event).strip().lower()
    if event not in {"flow_started", "flow_completed", "flow_abandoned"}:
        return

    db: Session = SessionLocal()
    try:
        row = (
            db.query(models.BotFlowDropCounter)
            .filter(models.BotFlowDropCounter.candidate_id == int(candidate_id))
            .filter(models.BotFlowDropCounter.flow_type == str(flow_type))
            .first()
        )
        if row is None:
            row = models.BotFlowDropCounter(
                candidate_id=int(candidate_id),
                flow_type=str(flow_type),
                started_count=0,
                completed_count=0,
                abandoned_count=0,
                updated_at=datetime.utcnow(),
            )
            db.add(row)

        if event == "flow_started":
            row.started_count = int(row.started_count or 0) + 1
        elif event == "flow_completed":
            row.completed_count = int(row.completed_count or 0) + 1
        else:
            row.abandoned_count = int(row.abandoned_count or 0) + 1

        row.updated_at = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


async def health_check_loop(application: Application, *, candidate_id: int) -> None:
    """Periodic lightweight health checks (1–5 min).

    Stored historically in BotHealthCheck.
    """

    def _clamp(v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, v))

    raw = (os.getenv("MONITOR_HEALTH_INTERVAL_SEC") or "").strip()
    try:
        interval = int(raw) if raw else 60
    except Exception:
        interval = 60
    interval = _clamp(interval, 60, 300)

    chat_id_raw = (os.getenv("HEALTHCHECK_CHAT_ID") or "").strip()
    health_chat_id: int | None = None
    if chat_id_raw:
        try:
            health_chat_id = int(chat_id_raw)
        except Exception:
            health_chat_id = None

    while True:
        now = datetime.now(timezone.utc)

        # 1) DB reachable
        db: Session = SessionLocal()
        try:
            ok = True
            try:
                db.execute(func.now())
            except Exception:
                ok = False

            db.add(
                models.BotHealthCheck(
                    candidate_id=int(candidate_id),
                    check_type="database_reachable",
                    status="ok" if ok else "failed",
                    created_at=datetime.utcnow(),
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        # 2) Can receive updates (heuristic): have we observed updates recently?
        try:
            last = application.bot_data.get("last_update_received_at")
            threshold_sec = max(interval * 2, 180)
            recv_ok = bool(last and isinstance(last, datetime) and (now - last.replace(tzinfo=timezone.utc)).total_seconds() <= threshold_sec)

            db2: Session = SessionLocal()
            try:
                db2.add(
                    models.BotHealthCheck(
                        candidate_id=int(candidate_id),
                        check_type="bot_can_receive_updates",
                        status="ok" if recv_ok else "failed",
                        created_at=datetime.utcnow(),
                    )
                )
                db2.commit()
            except Exception:
                db2.rollback()
            finally:
                db2.close()
        except Exception:
            pass

        # 3) Can send message (optional): only if HEALTHCHECK_CHAT_ID configured.
        if health_chat_id is not None:
            send_ok = True
            try:
                await application.bot.send_chat_action(chat_id=health_chat_id, action="typing")
            except Exception:
                send_ok = False

            db3: Session = SessionLocal()
            try:
                db3.add(
                    models.BotHealthCheck(
                        candidate_id=int(candidate_id),
                        check_type="bot_can_send_message",
                        status="ok" if send_ok else "failed",
                        created_at=datetime.utcnow(),
                    )
                )
                db3.commit()
            except Exception:
                db3.rollback()
            finally:
                db3.close()

        await asyncio.sleep(interval)


BTN_INTRO = "🤖 معرفی نماینده"
BTN_PROGRAMS = "✅ برنامه‌ها"
BTN_FEEDBACK = "💬 نظر / دغدغه"
BTN_FEEDBACK_LEGACY = "✍️ ارسال نظر / دغدغه"
BTN_QUESTION = "❓ سؤال از نماینده"
BTN_CONTACT = "☎️ ارتباط با نماینده"

# UX-first main menu (max 5 buttons)
BTN_COMMITMENTS = "📜 تعهدات نماینده"
BTN_ABOUT_MENU = "📂 درباره نماینده"
BTN_OTHER_MENU = "⚙️ سایر امکانات"

# Submenus
BTN_ABOUT_INTRO = "🏛 معرفی نماینده"
BTN_HQ_ADDRESSES = "📍 آدرس ستادها"
BTN_VOICE_INTRO = "🎙 معرفی صوتی نماینده"

BTN_BUILD_BOT = "🛠 ساخت بات اختصاصی"
BTN_ABOUT_BOT = "🤖 درباره این بات"

BTN_PROFILE_SUMMARY = "👤 سوابق"
BTN_BACK = "🔙 بازگشت"

BTN_REGISTER_QUESTION = "✅ ثبت سؤال"
BTN_SEARCH_QUESTION = "🔍 جستجو در پرسش‌ها"

# Strict step-based question UX (MVP)
BTN_VIEW_QUESTIONS = "👀 مشاهده سؤال‌ها"
BTN_ASK_NEW_QUESTION = "✍️ ثبت سؤال جدید"
BTN_VIEW_BY_CATEGORY = "📂 دسته‌بندی‌ها"
BTN_VIEW_BY_SEARCH = "🔎 جستجو"
BTN_SELECT_TOPIC = "▶️ انتخاب موضوع"

# Fixed categories (MVP)
QUESTION_CATEGORIES: list[str] = [
    "اشتغال",
    "اقتصاد و معیشت",
    "شفافیت",
    "مسکن",
]

BTN_BOT_REQUEST = "✅ درخواست ساخت بات اختصاصی"

ROLE_REPRESENTATIVE = "نماینده"
ROLE_CANDIDATE = "کاندیدا"
ROLE_TEAM = "تیم"

STATE_MAIN = "MAIN"
STATE_ABOUT_MENU = "ABOUT_MENU"
STATE_OTHER_MENU = "OTHER_MENU"
STATE_COMMITMENTS_VIEW = "COMMITMENTS_VIEW"
STATE_PROGRAMS = "PROGRAMS"
STATE_FEEDBACK_TEXT = "FEEDBACK_TEXT"
STATE_QUESTION_TEXT = "QUESTION_TEXT"
STATE_QUESTION_MENU = "QUESTION_MENU"
STATE_QUESTION_SEARCH = "QUESTION_SEARCH"
STATE_QUESTION_CATEGORY = "QUESTION_CATEGORY"

# Strict step-based states (preferred)
STATE_QUESTION_ENTRY = "QUESTION_ENTRY"
STATE_QUESTION_VIEW_METHOD = "QUESTION_VIEW_METHOD"
STATE_QUESTION_VIEW_CATEGORY = "QUESTION_VIEW_CATEGORY"
STATE_QUESTION_VIEW_LIST = "QUESTION_VIEW_LIST"
STATE_QUESTION_VIEW_ANSWER = "QUESTION_VIEW_ANSWER"
STATE_QUESTION_VIEW_RESULTS = "QUESTION_VIEW_RESULTS"
STATE_QUESTION_VIEW_SEARCH_TEXT = "QUESTION_VIEW_SEARCH_TEXT"
STATE_QUESTION_ASK_ENTRY = "QUESTION_ASK_ENTRY"
STATE_QUESTION_ASK_TOPIC = "QUESTION_ASK_TOPIC"
STATE_QUESTION_ASK_TEXT = "QUESTION_ASK_TEXT"

STATE_BOTREQ_NAME = "BOTREQ_NAME"
STATE_BOTREQ_ROLE = "BOTREQ_ROLE"
STATE_BOTREQ_CONSTITUENCY = "BOTREQ_CONSTITUENCY"
STATE_BOTREQ_CONTACT = "BOTREQ_CONTACT"


def _flow_type_from_state(state: str | None) -> str | None:
    s = (state or "").strip()
    if s in {STATE_FEEDBACK_TEXT}:
        return "comment"
    if s in {
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
    }:
        return "question"
    if s in {STATE_BOTREQ_NAME, STATE_BOTREQ_ROLE, STATE_BOTREQ_CONSTITUENCY, STATE_BOTREQ_CONTACT}:
        return "lead"
    return None


def build_bot_request_cta_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_BOT_REQUEST)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_bot_request_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(ROLE_REPRESENTATIVE), KeyboardButton(ROLE_CANDIDATE), KeyboardButton(ROLE_TEAM)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )

PROGRAM_QUESTIONS = [
    "1) اولویت اول شما در مجلس برای این حوزه چیست؟",
    "2) مهم‌ترین مشکل فعلی مردم این حوزه از نگاه شما چیست؟",
    "3) برای اشتغال و اقتصاد منطقه چه برنامه‌ای دارید؟",
    "4) درباره شفافیت، پاسخگویی و گزارش‌دهی به مردم چه تعهدی می‌دهید؟",
    "5) برنامه شما برای پیگیری مطالبات محلی (زیرساخت، بهداشت، آموزش) چیست؟",
]

FEEDBACK_INTRO_TEXT = """نظر یا دغدغه‌ات اینجا ثبت می‌شود و به نماینده منتقل خواهد شد.
این بخش برای شنیدن صدای مردم و شناسایی دغدغه‌های پرتکرار است.

پاسخ‌ها به‌صورت کلی و عمومی ارائه می‌شود، نه فردی.
اگر سؤال مشخصی داری که انتظار پاسخ مستقیم داری،
از بخش «❓ سؤال از نماینده» استفاده کن."""


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            # Swap order to match expected right-to-left visual placement in Telegram.
            [KeyboardButton(BTN_COMMITMENTS), KeyboardButton(BTN_QUESTION)],
            [KeyboardButton(BTN_ABOUT_MENU), KeyboardButton(BTN_FEEDBACK)],
            [KeyboardButton(BTN_OTHER_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_about_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_PROGRAMS), KeyboardButton(BTN_ABOUT_INTRO)],
            [KeyboardButton(BTN_VOICE_INTRO), KeyboardButton(BTN_HQ_ADDRESSES)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_other_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_BUILD_BOT)],
            [KeyboardButton(BTN_ABOUT_BOT)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True, is_persistent=True)


def build_question_hub_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for browsing featured/category/search + registering a new question."""
    rows: list[list[KeyboardButton]] = []
    # Categories as two-column buttons
    cat_buttons = [KeyboardButton(f"🗂 {c}") for c in QUESTION_CATEGORIES]
    for i in range(0, len(cat_buttons), 2):
        rows.append(cat_buttons[i : i + 2])
    rows.append([KeyboardButton(BTN_SEARCH_QUESTION), KeyboardButton(BTN_REGISTER_QUESTION)])
    rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def build_question_entry_keyboard() -> ReplyKeyboardMarkup:
    """Question entry screen."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_VIEW_QUESTIONS)], [KeyboardButton(BTN_ASK_NEW_QUESTION)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_question_view_method_keyboard() -> ReplyKeyboardMarkup:
    """SCREEN 2A: View flow entry (method choice)."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_VIEW_BY_CATEGORY), KeyboardButton(BTN_VIEW_BY_SEARCH)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_question_ask_entry_keyboard() -> ReplyKeyboardMarkup:
    """SCREEN 2B: Ask flow entry (go to topic selection)."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_SELECT_TOPIC)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_question_categories_keyboard(*, prefix_icon: bool, include_back: bool) -> ReplyKeyboardMarkup:
    """SCREEN 3 (Ask) and View-by-category selector.

    - Ask flow: prefix_icon=True (uses 🗂 prefix)
    - View flow: prefix_icon=True (uses 🗂 prefix)
    """
    rows: list[list[KeyboardButton]] = []
    if prefix_icon:
        buttons = [KeyboardButton(f"🗂 {c}") for c in QUESTION_CATEGORIES]
    else:
        buttons = [KeyboardButton(c) for c in QUESTION_CATEGORIES]

    for i in range(0, len(buttons), 2):
        rows.append(buttons[i : i + 2])
    if include_back:
        rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def build_question_list_keyboard(items: list[dict]) -> ReplyKeyboardMarkup:
    """Build a keyboard of questions for a chosen category.

    Each button starts with `N)` so we can parse it reliably.
    """
    rows: list[list[KeyboardButton]] = []
    buttons: list[KeyboardButton] = []
    for idx, it in enumerate(items, start=1):
        q = _normalize_text(it.get("q") or "")
        q = re.sub(r"\s+", " ", q).strip()
        if len(q) > 48:
            q = q[:47] + "…"
        buttons.append(KeyboardButton(f"{idx}) {q}" if q else f"{idx})"))

    for i in range(0, len(buttons), 2):
        rows.append(buttons[i : i + 2])
    rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def _parse_question_list_choice(user_text: str | None) -> int | None:
    t = _normalize_button_text(user_text)
    m = re.match(r"^(\d{1,2})\)", t)
    if not m:
        # also accept plain number input
        if re.fullmatch(r"\d{1,3}", t):
            try:
                return int(t)
            except Exception:
                return None
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _to_fa_digits(value: str) -> str:
    trans = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(value).translate(trans)


def _to_jalali_date_ymd(dt: datetime | None) -> str:
    if not dt:
        return ""
    try:
        if isinstance(dt, datetime):
            # Normalize tz-aware -> naive
            if getattr(dt, "tzinfo", None) is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        jd = jdatetime.date.fromgregorian(date=dt.date())
        return _to_fa_digits(jd.strftime("%Y/%m/%d"))
    except Exception:
        try:
            return _to_fa_digits(dt.strftime("%Y/%m/%d"))
        except Exception:
            return ""


def _format_public_question_answer_block(*, topic: str | None, question: str, answer: str, answered_at: datetime | None) -> str:
    t = _normalize_text(topic)
    q = _normalize_text(question)
    a = _normalize_text(answer)
    date_line = _to_jalali_date_ymd(answered_at)

    parts: list[str] = []
    if t:
        parts.append(f"🏷 {t}")
    parts.append(f"❓ {q}")
    parts.append("\n━━━━━━━━━━━━\n✅ پاسخ رسمی نماینده\n\n" + a)
    if date_line:
        parts.append(f"📅 {date_line}")
    return "\n\n".join([p for p in parts if p]).strip()


async def _send_question_list_message(*, update_message, topic: str, items: list[dict]):
    """Send all questions for a topic as numbered text (chunked) + Back keyboard.

    This avoids Telegram reply-keyboard limits when a category has many questions.
    """
    header = f"🗂 {topic}\n\nتمام سؤال‌های این بخش (شماره را ارسال کنید):\n"
    lines: list[str] = []
    for idx, it in enumerate(items, start=1):
        q = _normalize_text(it.get("q") or "")
        q = re.sub(r"\s+", " ", q).strip()
        if q:
            lines.append(f"{idx}) {q}")
        else:
            lines.append(f"{idx})")

    # Telegram message text has a practical limit; chunk safely.
    max_len = 3500
    chunks: list[str] = []
    current = header
    for ln in lines:
        candidate = (current + "\n" + ln) if current else ln
        if len(candidate) > max_len and current:
            chunks.append(current)
            current = ln
        else:
            current = candidate
    if current:
        chunks.append(current)

    for i, ch in enumerate(chunks):
        rm = build_back_keyboard() if i == len(chunks) - 1 else None
        await safe_reply_text(update_message, ch, reply_markup=rm)


async def _send_question_answers_message(*, update_message, topic: str, items: list[dict]):
    """Send all Q&A for a topic as text (chunked) + Back keyboard."""
    blocks: list[str] = []
    for it in items:
        q = _normalize_text(it.get("q") or "")
        a = _normalize_text(it.get("a") or "")
        answered_at = it.get("answered_at")
        if q and a:
            blocks.append(
                _format_public_question_answer_block(
                    topic=topic,
                    question=q,
                    answer=a,
                    answered_at=answered_at if isinstance(answered_at, datetime) else None,
                )
            )

    if not blocks:
        await safe_reply_text(
            update_message,
            f"🗂 {topic}\n\nفعلاً پاسخ عمومی برای این دسته ثبت نشده است.",
            reply_markup=build_back_keyboard(),
        )
        return

    max_len = 3500
    chunks: list[str] = []
    current = ""
    for blk in blocks:
        candidate = (current + "\n\n" + blk) if current else blk
        if len(candidate) > max_len and current:
            chunks.append(current)
            current = blk
        else:
            current = candidate
    if current:
        chunks.append(current)

    for i, ch in enumerate(chunks):
        rm = build_back_keyboard() if i == len(chunks) - 1 else None
        await safe_reply_text(update_message, ch, reply_markup=rm)


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_button_text(value: str | None) -> str:
    """Normalize Telegram button text for robust comparisons.

    Telegram (and Persian keyboards) can introduce ZWNJ (\u200c) and subtle whitespace.
    We normalize those so button routing doesn't break after restarts.
    """
    v = _normalize_text(value)
    v = v.replace("\u200c", "").replace("\u200f", "").replace("\ufeff", "")
    v = re.sub(r"\s+", " ", v).strip()
    return v


def _btn_eq(user_text: str | None, target: str) -> bool:
    return _normalize_button_text(user_text) == _normalize_button_text(target)


def _btn_has(user_text: str | None, *needles: str) -> bool:
    t = _normalize_button_text(user_text)
    for n in needles:
        nn = _normalize_button_text(n)
        if nn and nn in t:
            return True
    return False


def _is_back(user_text: str | None) -> bool:
    # Some Telegram clients may alter emoji presentation; match by both exact
    # button value and common Persian keywords.
    return _btn_eq(user_text, BTN_BACK) or _btn_has(user_text, "بازگشت", "برگشت")


async def safe_reply_text(message, text: str, **kwargs):
    """Reply with retries for better reliability.

    Under proxy/TLS hiccups, a single NetworkError can make the bot appear 'stopped'.
    """
    if message is None:
        return None

    for attempt in range(3):
        try:
            return await message.reply_text(text, **kwargs)
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 1.0)) + 0.5)
        except (TimedOut, NetworkError):
            if attempt >= 2:
                raise
            await asyncio.sleep(0.75 * (attempt + 1))


def _normalize_telegram_link(value: str) -> str:
    v = _normalize_text(value)
    if not v:
        return ""
    if v.startswith("@"):  # @channel
        return f"https://t.me/{v[1:]}"
    if v.startswith("t.me/"):
        return "https://" + v
    if v.startswith("http://") or v.startswith("https://"):
        return v
    # Plain username
    if re.fullmatch(r"[A-Za-z0-9_]{4,}", v):
        return f"https://t.me/{v}"
    return v


def _format_social_links_lines(socials: dict) -> list[str]:
    if not isinstance(socials, dict):
        return []

    lines: list[str] = []
    ch = _normalize_telegram_link(str(socials.get('telegramChannel') or socials.get('telegram_channel') or ''))
    gr = _normalize_telegram_link(str(socials.get('telegramGroup') or socials.get('telegram_group') or ''))
    if ch:
        lines.append(f"📣 کانال تلگرام: {ch}")
    if gr:
        lines.append(f"👥 گروه تلگرام: {gr}")
    return lines


def _build_feedback_intro_text(socials: dict) -> str:
    lines = [FEEDBACK_INTRO_TEXT]
    link_lines = _format_social_links_lines(socials)
    if link_lines:
        lines.append("\nبرای دریافت جمع‌بندی‌ها می‌توانید از لینک‌های زیر استفاده کنید:")
        lines.extend(link_lines)
    return "\n".join(lines)


def _build_feedback_confirmation_text(socials: dict) -> str:
    base = """✅ نظر / دغدغه شما با موفقیت ثبت شد.
این پیام‌ها بررسی و به نماینده منتقل می‌شوند.

در صورت تمایل می‌توانید برای دریافت جمع‌بندی‌ها
در کانال یا گروه اطلاع‌رسانی عضو شوید.""".strip()
    lines = [base]
    link_lines = _format_social_links_lines(socials)
    if link_lines:
        lines.append("")
        lines.extend(link_lines)
    return "\n".join(lines)


def _candidate_constituency(candidate: dict) -> str:
    constituency = _normalize_text(candidate.get("constituency"))
    if constituency:
        return constituency

    bot_config = candidate.get("bot_config") or {}
    constituency = _normalize_text(bot_config.get("constituency"))
    if constituency:
        return constituency

    province = _normalize_text(candidate.get("province"))
    city = _normalize_text(candidate.get("city"))
    if province and city:
        return f"{province} - {city}"
    return province or city


def _format_structured_resume(candidate: dict) -> str:
    bot_config = candidate.get("bot_config") or {}
    structured = bot_config.get("structured_resume")
    if isinstance(structured, dict):
        parts: list[str] = []
        title = _normalize_text(structured.get("title"))
        if title:
            parts.append(title)

        highlights = structured.get("highlights")
        if isinstance(highlights, list) and highlights:
            items = [f"• {_normalize_text(x)}" for x in highlights if _normalize_text(x)]
            if items:
                parts.append("\n".join(items))

        def _as_lines(v) -> list[str]:
            if v is None:
                return []
            if isinstance(v, list):
                return [_normalize_text(x) for x in v if _normalize_text(x)]
            if isinstance(v, str):
                return [s.strip() for s in v.splitlines() if s.strip()]
            return [_normalize_text(v)] if _normalize_text(v) else []

        education_items = _as_lines(structured.get("education"))
        if education_items:
            parts.append("\nتحصیلات:\n" + "\n".join([f"• {x}" for x in education_items]))

        # Compatibility keys: `experience` (older), `executive` + `social` (V1 panel)
        experience_items = _as_lines(structured.get("experience"))
        if experience_items:
            parts.append("\nسوابق:\n" + "\n".join([f"• {x}" for x in experience_items]))

        executive_items = _as_lines(structured.get("executive"))
        if executive_items:
            parts.append("\nسابقه اجرایی:\n" + "\n".join([f"• {x}" for x in executive_items]))

        social_items = _as_lines(structured.get("social"))
        if social_items:
            parts.append("\nسابقه اجتماعی / مردمی:\n" + "\n".join([f"• {x}" for x in social_items]))

        if parts:
            return "\n\n".join(parts).strip()

    fallback = _normalize_text(candidate.get("resume"))
    return fallback or "برای این بخش هنوز اطلاعاتی ثبت نشده است."


def _get_program_answer(candidate: dict, index: int) -> str:
    bot_config = candidate.get("bot_config") or {}
    programs = bot_config.get("programs")
    if isinstance(programs, list) and 0 <= index < len(programs):
        ans = _normalize_text(programs[index])
        return ans or "برای این سوال هنوز پاسخی ثبت نشده است."
    if isinstance(programs, dict):
        ans = _normalize_text(programs.get(str(index + 1)) or programs.get(f"q{index + 1}"))
        return ans or "برای این سوال هنوز پاسخی ثبت نشده است."

    # Backward compatibility: single text field
    ideas = _normalize_text(candidate.get("ideas"))
    return ideas or "برای این سوال هنوز پاسخی ثبت نشده است."


def _save_submission_sync(
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


LOCK_FILENAME = "election_manager_bot_runner.lock"

_WIN_MUTEX_HANDLE = None
_WIN_LOCK_FILE = None


def _env_truthy(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


_AUTO_TRUST_ENV_DECISION: bool | None = None


def _auto_decide_trust_env_for_telegram() -> bool:
    """Best-effort selection for httpx trust_env.

    Some environments can reach Telegram directly (no proxy needed) but also have
    system proxy env vars that are flaky for long polling. Others require the system
    proxy to reach Telegram at all.

    If TELEGRAM_TRUST_ENV is explicitly set, we honor it elsewhere.
    """
    global _AUTO_TRUST_ENV_DECISION
    if _AUTO_TRUST_ENV_DECISION is not None:
        return _AUTO_TRUST_ENV_DECISION

    try:
        import httpx

        with httpx.Client(trust_env=False, timeout=5.0, follow_redirects=True) as client:
            client.get("https://api.telegram.org")

        # Direct connectivity works; avoid system proxies by default.
        _AUTO_TRUST_ENV_DECISION = False
    except Exception:
        # Direct connectivity failed; fall back to system proxy env.
        _AUTO_TRUST_ENV_DECISION = True

    return _AUTO_TRUST_ENV_DECISION


def _default_lock_path() -> str:
    # Use a stable, machine-wide lock path so multiple repo copies don't spawn multiple pollers.
    # On Windows this resolves to something like: C:\Users\<user>\AppData\Local\Temp\...
    return os.path.join(tempfile.gettempdir(), LOCK_FILENAME)


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False

    # Cross-platform best-effort check.
    # NOTE: `os.kill(pid, 0)` is reliable on Unix, but can be unreliable on Windows.
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            OpenProcess = kernel32.OpenProcess
            OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            OpenProcess.restype = wintypes.HANDLE

            GetExitCodeProcess = kernel32.GetExitCodeProcess
            GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            GetExitCodeProcess.restype = wintypes.BOOL

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not h:
                # If we cannot open the process due to permissions, assume it is running.
                # This avoids incorrectly treating the lock as stale and starting a second poller.
                try:
                    err = int(ctypes.get_last_error())
                except Exception:
                    err = 0

                ERROR_INVALID_PARAMETER = 87  # typically means PID does not exist
                ERROR_ACCESS_DENIED = 5
                if err == ERROR_INVALID_PARAMETER:
                    return False
                if err == ERROR_ACCESS_DENIED:
                    return True
                return True
            try:
                code = wintypes.DWORD(0)
                ok = GetExitCodeProcess(h, ctypes.byref(code))
                if not ok:
                    return False
                return int(code.value) == STILL_ACTIVE
            finally:
                CloseHandle(h)
        except Exception:
            # Fall back to the Unix-style check as a last resort.
            pass

    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    else:
        return True


def acquire_single_instance_lock(lock_path: str) -> None:
    """Prevent multiple bot_runner processes on the same machine.

    Multiple pollers for the same Telegram token cause 409 Conflict and make the bot appear 'inactive'.
    """
    # Windows: use an actual OS-level file lock to avoid unreliable PID checks and
    # cross-session permission issues.
    if os.name == "nt":
        # First line of defense: a named mutex (works even if TEMP differs per process).
        # Multiple pollers for the same Telegram token cause 409 Conflict.
        try:
            import atexit
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            CreateMutexW = kernel32.CreateMutexW
            CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            CreateMutexW.restype = wintypes.HANDLE

            WaitForSingleObject = kernel32.WaitForSingleObject
            WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            WaitForSingleObject.restype = wintypes.DWORD

            ReleaseMutex = kernel32.ReleaseMutex
            ReleaseMutex.argtypes = [wintypes.HANDLE]
            ReleaseMutex.restype = wintypes.BOOL

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            WAIT_OBJECT_0 = 0
            WAIT_TIMEOUT = 258
            WAIT_ABANDONED = 0x80

            def _try_acquire_mutex(name: str):
                h = CreateMutexW(None, False, name)
                if not h:
                    return None, False

                res = int(WaitForSingleObject(h, 0))
                if res == WAIT_TIMEOUT:
                    try:
                        CloseHandle(h)
                    except Exception:
                        pass
                    return None, False

                if res not in {WAIT_OBJECT_0, WAIT_ABANDONED}:
                    try:
                        CloseHandle(h)
                    except Exception:
                        pass
                    return None, False

                return h, True

            h, ok = _try_acquire_mutex("Global\\ElectionManagerBotRunner")
            if not ok:
                h, ok = _try_acquire_mutex("Local\\ElectionManagerBotRunner")

            if not ok:
                raise SystemExit("bot_runner already running (Windows mutex)")

            if h is not None and ok:
                global _WIN_MUTEX_HANDLE
                _WIN_MUTEX_HANDLE = h

                def _cleanup_mutex() -> None:
                    try:
                        if _WIN_MUTEX_HANDLE:
                            try:
                                ReleaseMutex(_WIN_MUTEX_HANDLE)
                            except Exception:
                                pass
                            try:
                                CloseHandle(_WIN_MUTEX_HANDLE)
                            except Exception:
                                pass
                    except Exception:
                        pass

                atexit.register(_cleanup_mutex)
        except SystemExit:
            raise
        except Exception:
            # If mutex creation fails for any reason, fall back to file lock.
            pass

        try:
            import msvcrt

            lock_dir = os.path.dirname(lock_path)
            if lock_dir:
                os.makedirs(lock_dir, exist_ok=True)

            f = open(lock_path, "a+", encoding="utf-8")
            try:
                # Non-blocking exclusive lock of 1 byte.
                # NOTE: msvcrt.locking locks relative to the current file pointer.
                # Lock byte 0 so all processes contend for the same region.
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

                pid_text = f"{os.getpid()}\n"
                f.seek(0)
                f.write(pid_text)
                f.flush()
                # Keep the file length >= 1 byte while the lock is held.
                # Truncating to 0 can invalidate the locked region.
                try:
                    f.truncate(max(len(pid_text), 1))
                except Exception:
                    pass
            except OSError:
                try:
                    f.close()
                except Exception:
                    pass
                raise SystemExit("bot_runner already running (Windows file lock)")

            global _WIN_LOCK_FILE
            _WIN_LOCK_FILE = f

            def _cleanup_file_lock() -> None:
                try:
                    if _WIN_LOCK_FILE:
                        try:
                            _WIN_LOCK_FILE.seek(0)
                            msvcrt.locking(_WIN_LOCK_FILE.fileno(), msvcrt.LK_UNLCK, 1)
                        except Exception:
                            pass
                        try:
                            _WIN_LOCK_FILE.close()
                        except Exception:
                            pass
                except Exception:
                    pass

            atexit.register(_cleanup_file_lock)
            logger.info(f"Acquired bot_runner Windows file lock: {lock_path} (pid={os.getpid()})")
            return
        except SystemExit:
            raise
        except Exception:
            # Fall back to mutex+pid file logic below if anything unexpected happens.
            pass

    lock_dir = os.path.dirname(lock_path)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)

    pid = os.getpid()

    for _ in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(str(pid))

            def _cleanup() -> None:
                try:
                    if os.path.exists(lock_path):
                        with open(lock_path, "r", encoding="utf-8") as rf:
                            existing = (rf.read() or "").strip()
                        if existing == str(pid):
                            os.remove(lock_path)
                except Exception:
                    pass

            atexit.register(_cleanup)
            logger.info(f"Acquired bot_runner lock: {lock_path} (pid={pid})")
            return
        except FileExistsError:
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    existing_pid_raw = (f.read() or "").strip()
                existing_pid = int(existing_pid_raw) if existing_pid_raw else -1
            except Exception:
                existing_pid = -1

            if existing_pid > 0 and _is_pid_running(existing_pid):
                raise SystemExit(
                    f"bot_runner already running (pid={existing_pid}). "
                    f"Stop the other process before starting a new one. lock={lock_path}"
                )

            # Stale lock, remove it and try again.
            try:
                os.remove(lock_path)
            except Exception:
                pass

    raise SystemExit(f"Could not acquire bot_runner lock: {lock_path}")


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
    local_path = os.path.join(os.path.dirname(__file__), "uploads", filename)
    return local_path if os.path.exists(local_path) else None

# --- Helper for Non-Blocking DB Access ---
async def run_db_query(func, *args, **kwargs):
    """Runs a synchronous DB function in a separate thread."""
    return await asyncio.to_thread(func, *args, **kwargs)

def get_candidate_sync(candidate_id: int):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == candidate_id, User.role == "CANDIDATE").first()
    finally:
        db.close()

def save_bot_user_sync(user_data: dict, candidate_name: str):
    db = SessionLocal()
    try:
        bot_user = db.query(BotUser).filter(BotUser.telegram_id == user_data['id']).first()
        if not bot_user:
            bot_user = BotUser(
                telegram_id=user_data['id'],
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                bot_name=candidate_name
            )
            db.add(bot_user)
        else:
            bot_user.username = user_data.get('username')
            bot_user.first_name = user_data.get('first_name')
            bot_user.last_name = user_data.get('last_name')
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
            .filter(BotUserRegistry.candidate_id == int(candidate_id), BotUserRegistry.telegram_user_id == str(user_data['id']))
            .first()
        )
        # Store naive UTC timestamp (SQLite-friendly) while avoiding deprecated utcnow().
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not row:
            row = BotUserRegistry(
                candidate_id=int(candidate_id),
                telegram_user_id=str(user_data['id']),
                telegram_username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                chat_type=chat_type,
                candidate_name=candidate_snapshot.get('name'),
                candidate_bot_name=candidate_snapshot.get('bot_name'),
                candidate_city=candidate_snapshot.get('city'),
                candidate_province=candidate_snapshot.get('province'),
                candidate_constituency=candidate_snapshot.get('constituency'),
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(row)
        else:
            row.telegram_username = user_data.get('username')
            row.first_name = user_data.get('first_name')
            row.last_name = user_data.get('last_name')
            row.chat_type = chat_type or row.chat_type

            # Refresh candidate snapshot (in case candidate updated profile)
            row.candidate_name = candidate_snapshot.get('name')
            row.candidate_bot_name = candidate_snapshot.get('bot_name')
            row.candidate_city = candidate_snapshot.get('city')
            row.candidate_province = candidate_snapshot.get('province')
            row.candidate_constituency = candidate_snapshot.get('constituency')
            row.last_seen_at = now

        db.commit()
    except Exception as e:
        logger.error(f"Error saving bot user registry: {e}")
    finally:
        db.close()

async def save_bot_user(update: Update, *, candidate_id: int, candidate_snapshot: dict):
    user = update.effective_user
    if not user:
        return
    
    user_data = {
        'id': str(user.id),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }

    candidate_name = str(candidate_snapshot.get('bot_name') or candidate_snapshot.get('name') or '')
    chat_type = update.effective_chat.type if update.effective_chat else None

    await run_db_query(save_bot_user_sync, user_data, candidate_name)
    await run_db_query(
        save_bot_user_registry_sync,
        user_data=user_data,
        candidate_id=int(candidate_id),
        candidate_snapshot=candidate_snapshot,
        chat_type=chat_type,
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    chat_type = update.effective_chat.type if update.effective_chat else "unknown"
    from_user = update.effective_user.id if update.effective_user else "unknown"

    candidate_id = context.bot_data.get("candidate_id")
    logger.info(f"Received /start for candidate_id: {candidate_id} in {chat_type} from {from_user}")
    if not candidate_id:
        msg = update.effective_message
        if msg:
            await safe_reply_text(msg, "خطا: شناسه کاندیدا یافت نشد.")
        return

    # Use non-blocking DB call
    # Note: We need to fetch all needed data because session closes
    def get_candidate_data(cid):
        db = SessionLocal()
        try:
            c = db.query(User).filter(User.id == cid, User.role == "CANDIDATE").first()
            if not c: return None
            return {
                'name': c.full_name,
                'bot_name': c.bot_name,
                'slogan': c.slogan,
                'city': getattr(c, 'city', None),
                'province': getattr(c, 'province', None),
                'constituency': getattr(c, 'constituency', None),
            }
        finally:
            db.close()

    candidate = await run_db_query(get_candidate_data, candidate_id)
    
    if not candidate:
        msg = update.effective_message
        if msg:
            await safe_reply_text(msg, "خطا: اطلاعات کاندیدا یافت نشد.")
        return

    # Monitoring: record /start
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

    # Deep-link support: https://t.me/<bot>?start=question_<id>
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

                q_txt = _normalize_text(getattr(row, "text", ""))
                a_txt = _normalize_text(getattr(row, "answer", ""))
                topic = _normalize_text(getattr(row, "topic", ""))
                is_featured = bool(getattr(row, "is_featured", False))
                badge = " ⭐ منتخب" if is_featured else ""
                answered_at = getattr(row, "answered_at", None)
                block = _format_public_question_answer_block(topic=topic, question=q_txt, answer=a_txt, answered_at=answered_at)
                if badge:
                    block = block + f"\n\n{badge.strip()}"

                context.user_data["state"] = STATE_QUESTION_MENU
                await safe_reply_text(msg, block, reply_markup=build_question_hub_keyboard())
                return
    except Exception:
        logger.exception("Failed to handle /start deep-link")

    # Save User Data (also logs Telegram user id -> candidate + city/province/constituency)
    await save_bot_user(update, candidate_id=candidate_id, candidate_snapshot=candidate)

    context.user_data["state"] = STATE_MAIN
    context.user_data.pop("feedback_topic", None)

    cand_name = _normalize_text(candidate.get('name')) or "نماینده"
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
    reply_markup = build_main_keyboard()

    msg = update.effective_message
    if msg:
        await safe_reply_text(msg, welcome_text, reply_markup=reply_markup)


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Persist current group chat_id for notifications.

    Useful because private groups don't have an @username and invite links (t.me/+...) can't be
    used as chat_id in Bot API.
    """
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

    def _persist_group_chat_id(cid: int, chat_id_val: int):
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.id == int(cid), User.role == "CANDIDATE").first()
            if not u:
                return False
            base = u.socials if isinstance(u.socials, dict) else {}
            next_socials = dict(base)
            next_socials["telegram_group_chat_id"] = int(chat_id_val)
            next_socials["telegramGroupChatId"] = int(chat_id_val)
            u.socials = next_socials
            db.add(u)
            db.commit()
            return True
        finally:
            db.close()

    ok = await run_db_query(_persist_group_chat_id, candidate_id, chat_id_int)
    if ok:
        await safe_reply_text(msg, f"✅ شناسه گروه ذخیره شد.\nchat_id: {chat_id_int}")
    else:
        await safe_reply_text(msg, "⚠️ ذخیره‌سازی انجام نشد.")


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user_id and chat_id.

    Helpful for configuring BOT_NOTIFY_ADMIN_CHAT_ID.
    """
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu messages and group management."""
    text = (update.message.text or "")
    candidate_id = context.bot_data.get("candidate_id")
    chat_type = update.message.chat.type
    
    logger.info(f"Received message: '{text}' for candidate_id: {candidate_id} in {chat_type}")

    if not candidate_id:
        return

    def get_full_candidate_data(cid):
        db = SessionLocal()
        try:
            c = db.query(User).filter(User.id == cid, User.role == "CANDIDATE").first()
            if not c: return None
            return {
                'name': c.full_name,
                'bot_name': c.bot_name,
                'province': getattr(c, 'province', None),
                'city': getattr(c, 'city', None),
                'constituency': getattr(c, 'constituency', None),
                'slogan': getattr(c, 'slogan', None),
                'resume': c.resume,
                'ideas': c.ideas,
                'address': c.address,
                'phone': c.phone,
                'socials': c.socials,
                'bot_config': c.bot_config,
                'image_url': getattr(c, 'image_url', None),
                'voice_url': getattr(c, 'voice_url', None),
            }
        finally:
            db.close()

    candidate = await run_db_query(get_full_candidate_data, candidate_id)

    if not candidate:
        return

    bot_config = candidate.get('bot_config') or {}

    socials = candidate.get('socials') or {}
    if isinstance(socials, dict):
        # Normalize socials keys between snake_case (frontend) and camelCase (bot expectations)
        if 'telegramChannel' not in socials and 'telegram_channel' in socials:
            socials['telegramChannel'] = socials.get('telegram_channel')
        if 'telegramGroup' not in socials and 'telegram_group' in socials:
            socials['telegramGroup'] = socials.get('telegram_group')
        # instagram key is already same in both, but keep for completeness
        if 'instagram' not in socials and 'instagram' in socials:
            socials['instagram'] = socials.get('instagram')

    # Backward/forward compatibility between frontend and bot expectations
    # Frontend currently stores keys like:
    #   auto_lock_enabled, lock_start_time, lock_end_time, anti_link_enabled, forbidden_words
    # Bot runner historically reads:
    #   groupLockEnabled, lockStartTime, lockEndTime, blockLinks, badWords
    if isinstance(bot_config, dict):
        if 'groupLockEnabled' not in bot_config and 'auto_lock_enabled' in bot_config:
            bot_config['groupLockEnabled'] = bool(bot_config.get('auto_lock_enabled'))
        if 'lockStartTime' not in bot_config and 'lock_start_time' in bot_config:
            bot_config['lockStartTime'] = bot_config.get('lock_start_time')
        if 'lockEndTime' not in bot_config and 'lock_end_time' in bot_config:
            bot_config['lockEndTime'] = bot_config.get('lock_end_time')
        if 'blockLinks' not in bot_config and 'anti_link_enabled' in bot_config:
            bot_config['blockLinks'] = bool(bot_config.get('anti_link_enabled'))
        if 'badWords' not in bot_config and 'forbidden_words' in bot_config:
            raw = bot_config.get('forbidden_words')
            if isinstance(raw, str):
                bot_config['badWords'] = [w.strip() for w in raw.split(',') if w.strip()]

    # Always log bot users (even if message gets deleted by group moderation)
    await save_bot_user(
        update,
        candidate_id=candidate_id,
        candidate_snapshot={
            'name': candidate.get('name'),
            'bot_name': candidate.get('bot_name'),
            'city': candidate.get('city'),
            'province': candidate.get('province'),
            'constituency': candidate.get('constituency'),
        },
    )

    # Capture group chat_id for notification (private groups don't have @username).
    try:
        if chat_type in ['group', 'supergroup'] and update.effective_chat is not None:
            chat_id_val = int(update.effective_chat.id)

            def _persist_group_chat_id(cid: int, chat_id_int: int):
                db = SessionLocal()
                try:
                    u = db.query(User).filter(User.id == int(cid), User.role == 'CANDIDATE').first()
                    if not u:
                        return
                    base = u.socials if isinstance(u.socials, dict) else {}
                    s = dict(base)
                    # Keep both snake_case and camelCase variants for compatibility.
                    if s.get('telegram_group_chat_id') != chat_id_int:
                        s['telegram_group_chat_id'] = chat_id_int
                    if s.get('telegramGroupChatId') != chat_id_int:
                        s['telegramGroupChatId'] = chat_id_int
                    u.socials = s
                    db.add(u)
                    db.commit()
                finally:
                    db.close()

            await run_db_query(_persist_group_chat_id, candidate_id, chat_id_val)
    except Exception:
        logger.exception('Failed to persist group chat id')


    # --- Group Management Logic ---
    if chat_type in ['group', 'supergroup']:
        # 1. Check Group Lock
        if bot_config.get('groupLockEnabled'):
            start_time = bot_config.get('lockStartTime')
            end_time = bot_config.get('lockEndTime')
            
            if start_time and end_time:
                now = datetime.now().time()
                try:
                    start = datetime.strptime(start_time, "%H:%M").time()
                    end = datetime.strptime(end_time, "%H:%M").time()
                    
                    is_locked = False
                    if start <= end:
                        is_locked = start <= now <= end
                    else: # Crosses midnight
                        is_locked = start <= now or now <= end
                    
                    if is_locked:
                        try:
                            await update.message.delete()
                            # Optional: Send warning message (can be spammy)
                            # await update.message.reply_text("⛔ گروه در ساعات مشخص شده قفل است.")
                        except Exception as e:
                            logger.error(f"Failed to delete message in locked group: {e}")
                        return
                except ValueError:
                    logger.error("Invalid time format in bot_config")

        # 2. Check Bad Words
        bad_words = bot_config.get('badWords', [])
        if bad_words and isinstance(bad_words, list):
            text_lower = text.lower()
            for word in bad_words:
                if word.strip() and word.strip().lower() in text_lower:
                    try:
                        await update.message.delete()
                        # await update.message.reply_text("⛔ پیام شما حاوی کلمات نامناسب بود و حذف شد.")
                    except Exception as e:
                        logger.error(f"Failed to delete bad word message: {e}")
                    return

        # 3. Check Links
        if bot_config.get('blockLinks'):
            url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            if url_pattern.search(text):
                try:
                    await update.message.delete()
                    # await update.message.reply_text("⛔ ارسال لینک در این گروه ممنوع است.")
                except Exception as e:
                    logger.error(f"Failed to delete link message: {e}")
                return

    # --- Private Chat MVP V1 Menu Logic ---

    text = (text or "").strip()
    state = context.user_data.get("state") or STATE_MAIN

    # If state ever gets corrupted, reset safely (rare) and log.
    known_states = {
        STATE_MAIN,
        STATE_ABOUT_MENU,
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

    # Minimal loop detection: user keeps landing in same non-main state repeatedly.
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
                # rate-limit to avoid spam
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

    # Important: in the step-based question flow, BACK must be "one step" within the wizard.
    # So we defer BACK handling to per-state blocks below.
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
        # Monitoring: flow abandoned mid-way
        try:
            if prev_state and prev_state != STATE_MAIN and update.effective_user is not None:
                ft = _flow_type_from_state(prev_state)
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

        # If a flow was started from a submenu, return there instead of jumping to main.
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

    # Build-bot request flow
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
            try:
                if update.effective_user is not None:
                    log_ux_sync(
                        candidate_id=int(candidate_id),
                        telegram_user_id=str(update.effective_user.id),
                        state=state,
                        action="unexpected_text_input",
                        expected_action="enter_full_name",
                    )
            except Exception:
                pass
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
            try:
                if update.effective_user is not None:
                    log_ux_sync(
                        candidate_id=int(candidate_id),
                        telegram_user_id=str(update.effective_user.id),
                        state=state,
                        action="invalid_button_click",
                        expected_action="select_role_button",
                    )
            except Exception:
                pass
            await safe_reply_text(update.message, "لطفاً یکی از گزینه‌های نقش را انتخاب کنید.", reply_markup=build_bot_request_role_keyboard())
            return
        context.user_data["botreq_role"] = text
        context.user_data["state"] = STATE_BOTREQ_CONSTITUENCY
        await safe_reply_text(update.message, "حوزه انتخابیه را وارد کنید:", reply_markup=build_back_keyboard())
        return

    if state == STATE_BOTREQ_CONSTITUENCY:
        reserved = {
            BTN_INTRO,
            BTN_PROGRAMS,
            BTN_FEEDBACK,
            BTN_FEEDBACK_LEGACY,
            BTN_QUESTION,
            BTN_CONTACT,
            BTN_BUILD_BOT,
            BTN_BOT_REQUEST,
            ROLE_REPRESENTATIVE,
            ROLE_CANDIDATE,
            ROLE_TEAM,
        }
        if text in reserved or not text:
            try:
                if update.effective_user is not None:
                    log_ux_sync(
                        candidate_id=int(candidate_id),
                        telegram_user_id=str(update.effective_user.id),
                        state=state,
                        action="unexpected_text_input",
                        expected_action="enter_constituency",
                    )
            except Exception:
                pass
            await safe_reply_text(update.message, "حوزه انتخابیه را وارد کنید یا «بازگشت» را بزنید.")
            return
        context.user_data["botreq_constituency"] = text
        context.user_data["state"] = STATE_BOTREQ_CONTACT
        await safe_reply_text(update.message, "شماره تماس یا آی‌دی تلگرام را وارد کنید:", reply_markup=build_back_keyboard())
        return

    if state == STATE_BOTREQ_CONTACT:
        reserved = {
            BTN_INTRO,
            BTN_PROGRAMS,
            BTN_FEEDBACK,
            BTN_FEEDBACK_LEGACY,
            BTN_QUESTION,
            BTN_CONTACT,
            BTN_BUILD_BOT,
            BTN_BOT_REQUEST,
            ROLE_REPRESENTATIVE,
            ROLE_CANDIDATE,
            ROLE_TEAM,
        }
        if text in reserved or not text:
            try:
                if update.effective_user is not None:
                    log_ux_sync(
                        candidate_id=int(candidate_id),
                        telegram_user_id=str(update.effective_user.id),
                        state=state,
                        action="unexpected_text_input",
                        expected_action="enter_contact",
                    )
            except Exception:
                pass
            await safe_reply_text(update.message, "شماره تماس یا آی‌دی تلگرام را وارد کنید یا «بازگشت» را بزنید.")
            return

        full_name = _normalize_text(context.user_data.get("botreq_full_name"))
        role = _normalize_text(context.user_data.get("botreq_role"))
        constituency = _normalize_text(context.user_data.get("botreq_constituency"))
        contact = text

        formatted = (
            f"نام و نام خانوادگی: {full_name}\n"
            f"نقش: {role}\n"
            f"حوزه انتخابیه: {constituency}\n"
            f"تماس: {contact}"
        ).strip()

        submission_id = await run_db_query(
            _save_submission_sync,
            candidate_id=candidate_id,
            telegram_user_id=str(update.effective_user.id) if update.effective_user else "",
            telegram_username=(update.effective_user.username if update.effective_user else None),
            submission_type="BOT_REQUEST",
            topic=(role or None),
            text=formatted,
            constituency=(constituency or None),
            requester_full_name=(full_name or None),
            requester_contact=(contact or None),
            status="new_request",
        )

        # Best-effort: notify admin Telegram account.
        try:
            admin_chat_id = BOT_NOTIFY_ADMIN_CHAT_ID
            if not admin_chat_id and BOT_NOTIFY_ADMIN_USERNAME:
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

                admin_chat_id = await run_db_query(_resolve_admin_chat_id, BOT_NOTIFY_ADMIN_USERNAME)

            if admin_chat_id:
                cand_name = _normalize_text(candidate.get("full_name") or candidate.get("name") or "")
                cand_bot = _normalize_text(candidate.get("bot_name") or "")
                header = f"📌 درخواست ساخت بات اختصاصی (کد: {submission_id})"
                source = f"از بات: {cand_name} (@{cand_bot})" if cand_bot else f"از بات: {cand_name}"
                req_user = _normalize_text(update.effective_user.username if update.effective_user else "")
                req_user_line = f"یوزرنیم متقاضی: @{req_user}" if req_user else ""
                msg = "\n".join([x for x in [header, source, formatted, req_user_line] if x]).strip()
                await context.bot.send_message(chat_id=int(admin_chat_id), text=msg)
            else:
                logger.warning("BOT_REQUEST admin notify skipped: no admin chat id resolved")
        except Exception:
            logger.exception("Failed to notify admin of BOT_REQUEST")

        context.user_data["state"] = STATE_MAIN
        context.user_data.pop("botreq_full_name", None)
        context.user_data.pop("botreq_role", None)
        context.user_data.pop("botreq_constituency", None)
        context.user_data.pop("botreq_contact", None)
        await safe_reply_text(
            update.message,
            "درخواست شما ثبت شد.\nتیم ما به‌زودی با شما تماس می‌گیرد.",
            reply_markup=build_main_keyboard(),
        )

        # Flow completed: lead
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="lead", event="flow_completed")
        except Exception:
            pass
        return

    # Legacy overload state: keep safe behavior but try to route users to the new step-based flow.
    if state == STATE_QUESTION_MENU:
        context.user_data["state"] = STATE_QUESTION_ENTRY
        await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
        return

    # Feedback flow
    if state == STATE_FEEDBACK_TEXT:
        if text in {BTN_INTRO, BTN_PROGRAMS, BTN_FEEDBACK, BTN_FEEDBACK_LEGACY, BTN_QUESTION, BTN_CONTACT, BTN_BUILD_BOT}:
            await safe_reply_text(update.message, "برای ثبت نظر/دغدغه، لطفاً متن را ارسال کنید یا «بازگشت» را بزنید.")
            return

        constituency = _candidate_constituency(candidate)
        submission_id = await run_db_query(
            _save_submission_sync,
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
        await safe_reply_text(update.message, _build_feedback_confirmation_text(socials), reply_markup=build_main_keyboard())

        # Flow completed: comment
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="comment", event="flow_completed")
        except Exception:
            pass
        return

    # --- Strict step-based question flow (preferred) ---

    # SCREEN 1: entry with exactly two buttons
    if state == STATE_QUESTION_ENTRY:
        if _is_back(text):
            context.user_data["state"] = STATE_MAIN
            await safe_reply_text(update.message, "به منوی اصلی برگشتید.", reply_markup=build_main_keyboard())
            return
        if _btn_eq(text, BTN_VIEW_QUESTIONS):
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return
        if _btn_eq(text, BTN_ASK_NEW_QUESTION):
            context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
            await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        await safe_reply_text(update.message, "یکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
        return

    # SCREEN 2A: View flow method
    # Backward compatibility: older versions had an intermediate view-method screen.
    # We no longer show that menu; always go directly to categories.
    if state == STATE_QUESTION_VIEW_METHOD:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ENTRY
            await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
            return
        context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
        await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    # View flow: category selection
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
                    .order_by(BotSubmission.answered_at.desc(), BotSubmission.id.desc())
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
            q_txt = _normalize_text(getattr(r, "text", ""))
            a_txt = _normalize_text(getattr(r, "answer", ""))
            rid = getattr(r, "id", None)
            answered_at = getattr(r, "answered_at", None)
            if q_txt and a_txt:
                items.append({"id": rid, "q": q_txt, "a": a_txt, "answered_at": answered_at})

        # Simplest behavior: show ALL Q&A immediately (no extra steps)
        context.user_data["view_topic"] = chosen
        context.user_data["state"] = STATE_QUESTION_VIEW_RESULTS
        await _send_question_answers_message(update_message=update.message, topic=chosen, items=items)
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

    # View flow: list of questions for chosen category
    if state == STATE_QUESTION_VIEW_LIST:
        if _is_back(text):
            context.user_data.pop("view_topic", None)
            context.user_data.pop("view_items", None)
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        items = context.user_data.get("view_items")
        topic = context.user_data.get("view_topic")
        if not isinstance(items, list) or not topic:
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        choice = _parse_question_list_choice(text)
        if not choice or choice < 1 or choice > len(items):
            await safe_reply_text(update.message, "شمارهٔ سؤال را ارسال کنید (مثلاً 1) یا «بازگشت» را بزنید.", reply_markup=build_back_keyboard())
            return

        selected = items[choice - 1]
        q_txt = _normalize_text(selected.get("q") or "")
        a_txt = _normalize_text(selected.get("a") or "")
        answered_at = selected.get("answered_at")
        context.user_data["state"] = STATE_QUESTION_VIEW_ANSWER
        context.user_data["view_choice"] = int(choice)
        await safe_reply_text(
            update.message,
            _format_public_question_answer_block(
                topic=str(topic),
                question=q_txt,
                answer=a_txt,
                answered_at=answered_at if isinstance(answered_at, datetime) else None,
            ),
            reply_markup=build_back_keyboard(),
        )
        return

    # View flow: show answer, BACK returns to the list (one step)
    if state == STATE_QUESTION_VIEW_ANSWER:
        if _is_back(text):
            items = context.user_data.get("view_items")
            topic = context.user_data.get("view_topic")
            if isinstance(items, list) and topic:
                context.user_data["state"] = STATE_QUESTION_VIEW_LIST
                await _send_question_list_message(update_message=update.message, topic=str(topic), items=list(items))
                return
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        await safe_reply_text(update.message, "برای برگشت، «بازگشت» را بزنید.", reply_markup=build_back_keyboard())
        return

    # View flow: search text
    if state == STATE_QUESTION_VIEW_SEARCH_TEXT:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
            await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        q = (text or "").strip()
        if len(q) < 2:
            await safe_reply_text(update.message, "عبارت جستجو خیلی کوتاه است. دوباره تلاش کنید:")
            return

        def _search_public_answered(cid: int, query: str) -> list[BotSubmission]:
            db = SessionLocal()
            try:
                qq = (
                    db.query(BotSubmission)
                    .filter(
                        BotSubmission.candidate_id == int(cid),
                        BotSubmission.type == "QUESTION",
                        BotSubmission.status == "ANSWERED",
                        BotSubmission.is_public == True,  # noqa: E712
                        BotSubmission.answer.isnot(None),
                        or_(
                            BotSubmission.text.contains(query),
                            BotSubmission.answer.contains(query),
                        ),
                    )
                    .order_by(BotSubmission.answered_at.desc(), BotSubmission.id.desc())
                    .limit(10)
                )
                return qq.all()
            finally:
                db.close()

        rows = await run_db_query(_search_public_answered, candidate_id, q)
        if not rows:
            await safe_reply_text(update.message, "نتیجه‌ای پیدا نشد. عبارت دیگری امتحان کنید یا «بازگشت» را بزنید.")
            return

        blocks: list[str] = []
        for r in rows:
            q_txt = _normalize_text(getattr(r, "text", ""))
            a_txt = _normalize_text(getattr(r, "answer", ""))
            topic = _normalize_text(getattr(r, "topic", ""))
            answered_at = getattr(r, "answered_at", None)
            if q_txt and a_txt:
                blocks.append(_format_public_question_answer_block(topic=topic, question=q_txt, answer=a_txt, answered_at=answered_at))

        context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
        await safe_reply_text(
            update.message,
            "🔍 نتایج جستجو\n\n" + "\n\n".join(blocks),
            reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True),
        )
        return

    # SCREEN 2B: Ask flow entry
    if state == STATE_QUESTION_ASK_ENTRY:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ENTRY
            await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
            return

        # No intermediate steps: go directly to mandatory topic selection
        context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
        await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    # SCREEN 3: Ask flow topic selection
    if state == STATE_QUESTION_ASK_TOPIC:
        if _is_back(text):
            context.user_data["state"] = STATE_QUESTION_ENTRY
            await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
            return

        chosen = (text or "").replace("🗂", "").strip()
        if chosen not in QUESTION_CATEGORIES:
            await safe_reply_text(update.message, "موضوع نامعتبر است.", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
            return

        context.user_data["question_topic"] = chosen
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="question", event="flow_started")
        except Exception:
            pass
        context.user_data["state"] = STATE_QUESTION_ASK_TEXT
        await safe_reply_text(update.message, "سؤال‌تان را کوتاه و شفاف بنویسید.\n(در یک پیام)", reply_markup=build_back_keyboard())
        return

    # Ask flow: receive question text
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
                    existing = _normalize_text(getattr(r, "text", ""))
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

        topic = _normalize_text(context.user_data.get("question_topic")) or None
        constituency = _candidate_constituency(candidate)
        await run_db_query(
            _save_submission_sync,
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
        await safe_reply_text(
            update.message,
            "ممنون. سؤال شما ثبت شد و به نماینده منتقل می‌شود.",
            reply_markup=build_main_keyboard(),
        )

        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="question", event="flow_completed")
        except Exception:
            pass
        return

    # --- Legacy question flow (kept for compatibility) ---
    if state == STATE_QUESTION_TEXT:
        if text in {BTN_INTRO, BTN_PROGRAMS, BTN_FEEDBACK, BTN_FEEDBACK_LEGACY, BTN_QUESTION, BTN_CONTACT, BTN_BUILD_BOT, BTN_REGISTER_QUESTION}:
            await safe_reply_text(update.message, "برای ثبت سؤال، لطفاً متن سؤال را ارسال کنید یا «بازگشت» را بزنید.")
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
                    existing = _normalize_text(getattr(r, "text", ""))
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
            await safe_reply_text(update.message, "این سؤال قبلاً ثبت شده است.", reply_markup=build_main_keyboard())
            return

        constituency = _candidate_constituency(candidate)
        await run_db_query(
            _save_submission_sync,
            candidate_id=candidate_id,
            telegram_user_id=str(update.effective_user.id) if update.effective_user else "",
            telegram_username=(update.effective_user.username if update.effective_user else None),
            submission_type="QUESTION",
            text=q_text,
            constituency=constituency,
            status="PENDING",
            is_public=False,
        )
        context.user_data["state"] = STATE_MAIN
        await safe_reply_text(
            update.message,
            "سؤال شما ثبت شد.\nدر صورت پاسخ‌گویی، پاسخ به‌صورت عمومی در همین بخش منتشر خواهد شد.",
            reply_markup=build_main_keyboard(),
        )

        # Flow completed: question
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="question", event="flow_completed")
        except Exception:
            pass
        return

    if state == STATE_QUESTION_SEARCH:
        reserved = {
            BTN_INTRO,
            BTN_PROGRAMS,
            BTN_FEEDBACK,
            BTN_FEEDBACK_LEGACY,
            BTN_QUESTION,
            BTN_CONTACT,
            BTN_BUILD_BOT,
            BTN_REGISTER_QUESTION,
            BTN_SEARCH_QUESTION,
            BTN_BACK,
        }
        if text in reserved:
            await safe_reply_text(update.message, "برای جستجو، یک عبارت کوتاه وارد کنید (مثلاً «مسکن»).")
            return

        q = (text or "").strip()
        if len(q) < 2:
            await safe_reply_text(update.message, "عبارت جستجو خیلی کوتاه است. دوباره تلاش کنید:")
            return

        def _search_public_answered(cid: int, query: str) -> list[BotSubmission]:
            db = SessionLocal()
            try:
                qq = (
                    db.query(BotSubmission)
                    .filter(
                        BotSubmission.candidate_id == int(cid),
                        BotSubmission.type == "QUESTION",
                        BotSubmission.status == "ANSWERED",
                        BotSubmission.is_public == True,  # noqa: E712
                        BotSubmission.answer.isnot(None),
                        or_(
                            BotSubmission.text.contains(query),
                            BotSubmission.answer.contains(query),
                        ),
                    )
                    .order_by(BotSubmission.answered_at.desc(), BotSubmission.id.desc())
                    .limit(10)
                )
                return qq.all()
            finally:
                db.close()

        rows = await run_db_query(_search_public_answered, candidate_id, q)
        if not rows:
            await safe_reply_text(update.message, "نتیجه‌ای پیدا نشد. عبارت دیگری امتحان کنید یا «بازگشت» را بزنید.")
            return

        blocks: list[str] = []
        for r in rows:
            q_txt = _normalize_text(getattr(r, "text", ""))
            a_txt = _normalize_text(getattr(r, "answer", ""))
            topic = _normalize_text(getattr(r, "topic", ""))
            head = f"[{topic}] " if topic else ""
            if q_txt and a_txt:
                rid = getattr(r, "id", None)
                is_featured = bool(getattr(r, "is_featured", False))
                badge = " ⭐" if is_featured else ""
                code_line = f"\n🔖 کد سؤال: {rid}{badge}" if rid is not None else ""
                blocks.append(f"❓ {head}{q_txt}\n✅ {a_txt}{code_line}")
        await safe_reply_text(update.message, "🔍 نتایج جستجو\n\n" + "\n\n".join(blocks), reply_markup=build_question_hub_keyboard())
        return

    if state == STATE_QUESTION_CATEGORY:
        # Legacy category state - route back to the new flow.
        context.user_data["state"] = STATE_QUESTION_ENTRY
        await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
        return

    # Programs state
    if state == STATE_PROGRAMS:
        if text.startswith("سوال "):
            try:
                idx = int(text.replace("سوال", "").strip()) - 1
            except Exception:
                idx = -1
            if 0 <= idx < len(PROGRAM_QUESTIONS):
                q = PROGRAM_QUESTIONS[idx]
                a = _get_program_answer(candidate, idx)
                await safe_reply_text(update.message, f"{q}\n\nپاسخ نماینده:\n{a}")
                return
        await safe_reply_text(update.message, "لطفاً یکی از گزینه‌ها را انتخاب کنید یا «بازگشت» را بزنید.")
        return

    # --- Global handlers for step-based Question UX ---
    # Users can press old keyboards after a bot restart (context.user_data state lost).
    # Treat these as top-level intents to avoid bouncing back to MAIN.
    if _btn_eq(text, BTN_VIEW_QUESTIONS) or _btn_has(text, "مشاهده سوال", "مشاهده سؤال"):
        context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
        await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if _btn_eq(text, BTN_ASK_NEW_QUESTION) or _btn_has(text, "ثبت سوال", "ثبت سؤال"):
        context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
        await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if _btn_eq(text, BTN_VIEW_BY_CATEGORY) or _btn_has(text, "دسته بندی", "دسته‌بندی"):
        context.user_data["state"] = STATE_QUESTION_VIEW_CATEGORY
        await safe_reply_text(update.message, "موضوع موردنظرتان چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    if _btn_eq(text, BTN_VIEW_BY_SEARCH) or _btn_has(text, "جستجو"):
        context.user_data["state"] = STATE_QUESTION_VIEW_SEARCH_TEXT
        await safe_reply_text(update.message, "کلمه یا جمله کوتاه را بنویسید تا در سؤال‌ها جستجو کنم.", reply_markup=build_back_keyboard())
        return

    if _btn_eq(text, BTN_SELECT_TOPIC) or _btn_has(text, "انتخاب موضوع"):
        context.user_data["state"] = STATE_QUESTION_ASK_TOPIC
        await safe_reply_text(update.message, "موضوع سؤال شما چیست؟", reply_markup=build_question_categories_keyboard(prefix_icon=True, include_back=True))
        return

    # Main menu
    if text == BTN_ABOUT_MENU:
        context.user_data["state"] = STATE_ABOUT_MENU
        await safe_reply_text(update.message, "📂 درباره نماینده\n\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=build_about_keyboard())
        return

    if text == BTN_OTHER_MENU:
        context.user_data["state"] = STATE_OTHER_MENU
        await safe_reply_text(update.message, "⚙️ سایر امکانات\n\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=build_other_keyboard())
        return

    if text == BTN_COMMITMENTS:
        try:
            if update.effective_user is not None:
                log_ux_sync(
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    state=STATE_MAIN,
                    action="tap_commitments",
                    expected_action="browse_commitments",
                )
                track_path_sync(candidate_id=int(candidate_id), path="main->commitments")
        except Exception:
            pass

        def _get_commitments(cid: int):
            db = SessionLocal()
            try:
                return (
                    db.query(models.BotCommitment)
                    .filter(models.BotCommitment.candidate_id == int(cid))
                    .order_by(models.BotCommitment.created_at.desc())
                    .limit(10)
                    .all()
                )
            finally:
                db.close()

        rows = await run_db_query(_get_commitments, candidate_id)
        if not rows:
            context.user_data["state"] = STATE_COMMITMENTS_VIEW
            await safe_reply_text(update.message, "📜 تعهدات\n\nفعلاً تعهدی ثبت نشده است.", reply_markup=build_back_keyboard())
            return

        blocks: list[str] = []
        for i, r in enumerate(rows, start=1):
            title = _normalize_text(getattr(r, "title", ""))
            body = _normalize_text(getattr(r, "body", ""))
            if not title and not body:
                continue
            if len(body) > 500:
                body = body[:500].rstrip() + "…"
            if title:
                blocks.append(f"{i}) {title}\n{body}" if body else f"{i}) {title}")
            else:
                blocks.append(f"{i}) {body}")

        context.user_data["state"] = STATE_COMMITMENTS_VIEW
        await safe_reply_text(update.message, "📜 تعهدات نماینده\n\n" + "\n\n".join(blocks), reply_markup=build_back_keyboard())
        return

    # ABOUT submenu
    if state == STATE_ABOUT_MENU:
        if text in {BTN_ABOUT_INTRO, BTN_INTRO}:
            # Reuse intro handler
            text = BTN_INTRO
        elif text == BTN_PROGRAMS:
            # Programs is its own state; return to About on back
            context.user_data["_return_state"] = STATE_ABOUT_MENU
        elif text in {BTN_HQ_ADDRESSES, BTN_CONTACT}:
            text = BTN_CONTACT
        elif text == BTN_VOICE_INTRO:
            # keep as-is
            pass
        else:
            try:
                if update.effective_user is not None:
                    log_ux_sync(
                        candidate_id=int(candidate_id),
                        telegram_user_id=str(update.effective_user.id),
                        state=STATE_ABOUT_MENU,
                        action="invalid_button_click",
                        expected_action="select_about_menu_button",
                    )
            except Exception:
                pass
            await safe_reply_text(update.message, "لطفاً یکی از گزینه‌های «درباره نماینده» را انتخاب کنید یا «بازگشت» را بزنید.", reply_markup=build_about_keyboard())
            return

    # OTHER submenu
    if state == STATE_OTHER_MENU:
        if text == BTN_BUILD_BOT:
            # Show info and CTA; lead flow starts only on BTN_BOT_REQUEST
            text = BTN_BUILD_BOT
        elif text == BTN_ABOUT_BOT:
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
        else:
            try:
                if update.effective_user is not None:
                    log_ux_sync(
                        candidate_id=int(candidate_id),
                        telegram_user_id=str(update.effective_user.id),
                        state=STATE_OTHER_MENU,
                        action="invalid_button_click",
                        expected_action="select_other_menu_button",
                    )
            except Exception:
                pass
            await safe_reply_text(update.message, "لطفاً یکی از گزینه‌های «سایر امکانات» را انتخاب کنید یا «بازگشت» را بزنید.", reply_markup=build_other_keyboard())
            return

    if text == BTN_INTRO:
        try:
            if update.effective_user is not None:
                log_ux_sync(
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    state=STATE_MAIN,
                    action="tap_intro",
                    expected_action="browse_intro_tabs",
                )
        except Exception:
            pass
        name = _normalize_text(candidate.get('name')) or "نماینده"
        constituency = _candidate_constituency(candidate)
        slogan = _normalize_text(candidate.get('slogan') or (candidate.get('bot_config') or {}).get('slogan'))

        image_url = _normalize_text(candidate.get('image_url'))
        if image_url:
            local_path = upload_file_path_from_localhost_url(image_url)
            try:
                if local_path:
                    with open(local_path, 'rb') as f:
                        await update.message.reply_photo(photo=f, caption=name)
                else:
                    await update.message.reply_photo(photo=image_url, caption=name)
            except Exception as e:
                logger.error(f"Failed to send candidate photo: {e}")

        lines = [name]
        if constituency:
            lines.append(f"حوزه انتخابیه: {constituency}")
        if slogan:
            lines.append(f"📣 {slogan}")
        await safe_reply_text(
            update.message,
            "\n".join(lines),
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(BTN_PROFILE_SUMMARY), KeyboardButton(BTN_VOICE_INTRO)], [KeyboardButton(BTN_BACK)]],
                resize_keyboard=True,
                is_persistent=True,
            ),
        )
        return

    if text == BTN_PROFILE_SUMMARY:
        resume_text = _format_structured_resume(candidate)
        await safe_reply_text(update.message, f"👤 سوابق\n\n{resume_text}", reply_markup=build_back_keyboard())
        return

    if text == BTN_VOICE_INTRO:
        voice_url = _normalize_text(candidate.get('voice_url') or (candidate.get('bot_config') or {}).get('voice_url'))
        if not voice_url:
            await safe_reply_text(update.message, "🎧 معرفی صوتی نماینده در حال حاضر ثبت نشده است.")
            return
        rep_name = _normalize_text(candidate.get('name'))
        caption = "🎧 معرفی صوتی نماینده (حداکثر ۶۰ ثانیه)"
        try:
            # Telegram servers cannot fetch localhost/127.0.0.1 URLs.
            # When running locally, the uploaded file exists on disk, so send it directly.
            local_path = upload_file_path_from_localhost_url(voice_url)
            if local_path:
                ext = os.path.splitext(local_path)[1].lower()
                with open(local_path, 'rb') as f:
                    if ext == '.ogg':
                        await update.message.reply_voice(voice=f, caption=caption)
                    else:
                        try:
                            await update.message.reply_audio(audio=f, caption=caption)
                        except Exception:
                            # As a last resort, send as a generic file.
                            await update.message.reply_document(document=f, caption=caption)
            else:
                try:
                    await update.message.reply_voice(voice=voice_url, caption=caption)
                except Exception:
                    await update.message.reply_audio(audio=voice_url, caption=caption)
        except Exception as e:
            logger.error(f"Failed to send voice intro: {e}")
            await safe_reply_text(update.message, "⚠️ فایل معرفی صوتی در دسترس نیست.")
        return

    if text == BTN_PROGRAMS:
        try:
            if update.effective_user is not None:
                log_ux_sync(
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    state=STATE_MAIN,
                    action="tap_programs",
                    expected_action="select_program_question",
                )
        except Exception:
            pass
        context.user_data["state"] = STATE_PROGRAMS
        await safe_reply_text(
            update.message,
            "✅ برنامه‌های نماینده\n\nیکی از سوال‌های زیر را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [KeyboardButton("سوال 1"), KeyboardButton("سوال 2")],
                    [KeyboardButton("سوال 3"), KeyboardButton("سوال 4")],
                    [KeyboardButton("سوال 5"), KeyboardButton(BTN_BACK)],
                ],
                resize_keyboard=True,
                is_persistent=True,
            ),
        )
        return

    if text == BTN_FEEDBACK or text == BTN_FEEDBACK_LEGACY:
        try:
            if update.effective_user is not None:
                log_ux_sync(
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    state=STATE_MAIN,
                    action="tap_feedback",
                    expected_action="enter_feedback_text",
                )
                track_path_sync(candidate_id=int(candidate_id), path="main->comment")
        except Exception:
            pass
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="comment", event="flow_started")
        except Exception:
            pass
        context.user_data["state"] = STATE_FEEDBACK_TEXT
        context.user_data.pop("feedback_topic", None)
        await safe_reply_text(update.message, _build_feedback_intro_text(socials), reply_markup=build_back_keyboard())
        await safe_reply_text(update.message, "متن نظر/دغدغه‌تان را ارسال کنید:", reply_markup=build_back_keyboard())
        return

    if text == BTN_QUESTION:
        try:
            if update.effective_user is not None:
                log_ux_sync(
                    candidate_id=int(candidate_id),
                    telegram_user_id=str(update.effective_user.id),
                    state=STATE_MAIN,
                    action="tap_question",
                    expected_action="choose_view_or_ask",
                )
                track_path_sync(candidate_id=int(candidate_id), path="main->question")
        except Exception:
            pass
        # Strict flow SCREEN 1 (exactly two buttons)
        context.user_data["state"] = STATE_QUESTION_ENTRY
        await safe_reply_text(update.message, "سؤال از نماینده\nیکی را انتخاب کنید:", reply_markup=build_question_entry_keyboard())
        return

    # Legacy buttons: route into strict flow safely
    if text == BTN_REGISTER_QUESTION:
        context.user_data["state"] = STATE_QUESTION_ASK_ENTRY
        await safe_reply_text(update.message, "برای ثبت سؤال جدید، مرحله بعد را انجام دهید.", reply_markup=build_question_ask_entry_keyboard())
        return
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="question", event="flow_started")
        except Exception:
            pass
        context.user_data["state"] = STATE_QUESTION_TEXT
        await safe_reply_text(update.message, "متن سؤال‌تان را ارسال کنید (۱۰ تا ۵۰۰ کاراکتر):", reply_markup=build_back_keyboard())
        return

    if text == BTN_SEARCH_QUESTION:
        context.user_data["state"] = STATE_QUESTION_VIEW_METHOD
        await safe_reply_text(update.message, "برای مشاهده سؤال‌ها، یکی را انتخاب کنید:", reply_markup=build_question_view_method_keyboard())
        return

    # Category selection (legacy handler). Avoid hijacking when user is not in a question flow.
    if text.startswith("🗂") and state in {STATE_QUESTION_MENU, STATE_QUESTION_CATEGORY, STATE_QUESTION_VIEW_CATEGORY}:
        chosen = (text.replace("🗂", "").strip() or "")
        if chosen not in QUESTION_CATEGORIES:
            await safe_reply_text(update.message, "دسته‌بندی نامعتبر است.", reply_markup=build_question_hub_keyboard())
            return

        def _get_category_answered(cid: int, topic: str) -> list[BotSubmission]:
            db = SessionLocal()
            try:
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
                    .order_by(BotSubmission.answered_at.desc(), BotSubmission.id.desc())
                    .limit(10)
                )
                return q.all()
            finally:
                db.close()

        rows = await run_db_query(_get_category_answered, candidate_id, chosen)
        if not rows:
            context.user_data["state"] = STATE_QUESTION_MENU
            await safe_reply_text(update.message, f"در دسته «{chosen}» هنوز پاسخ عمومی ثبت نشده است.", reply_markup=build_question_hub_keyboard())
            return

        blocks: list[str] = []
        for r in rows:
            q_txt = _normalize_text(getattr(r, "text", ""))
            a_txt = _normalize_text(getattr(r, "answer", ""))
            if q_txt and a_txt:
                rid = getattr(r, "id", None)
                is_featured = bool(getattr(r, "is_featured", False))
                badge = " ⭐" if is_featured else ""
                code_line = f"\n🔖 کد سؤال: {rid}{badge}" if rid is not None else ""
                blocks.append(f"❓ {q_txt}\n✅ {a_txt}{code_line}")
        context.user_data["state"] = STATE_QUESTION_MENU
        await safe_reply_text(update.message, f"🗂 {chosen}\n\n" + "\n\n".join(blocks), reply_markup=build_question_hub_keyboard())
        return

    if text == BTN_CONTACT:
        bot_config = candidate.get('bot_config') or {}
        offices = bot_config.get('offices')
        if not isinstance(offices, list):
            offices = []
        offices = offices[:3]

        if offices:
            blocks = []
            for office in offices:
                if not isinstance(office, dict):
                    continue
                title = _normalize_text(office.get('title')) or "ستاد"
                address = _normalize_text(office.get('address'))
                note = _normalize_text(office.get('note'))
                phone = _normalize_text(office.get('phone'))
                lines = [f"📍 {title}"]
                if address:
                    lines.append(address)
                if note:
                    lines.append(f"🕒 {note}")
                if phone:
                    lines.append(f"☎️ {phone}")
                blocks.append("\n".join(lines))
            if blocks:
                await safe_reply_text(update.message, "☎️ ارتباط با نماینده\n\n" + "\n\n".join(blocks), reply_markup=build_back_keyboard())
                return

        response = f"شماره تماس: {candidate.get('phone') or '---'}\n"
        address = _normalize_text(candidate.get('address'))
        if address:
            response += f"\n📍 آدرس ستاد:\n{address}\n"
        if socials:
            if socials.get('telegramChannel'):
                response += f"\nکانال تلگرام: {socials['telegramChannel']}"
            if socials.get('telegramGroup'):
                response += f"\nگروه تلگرام: {socials['telegramGroup']}"
            if socials.get('instagram'):
                response += f"\nاینستاگرام: {socials['instagram']}"
        await safe_reply_text(update.message, response.strip(), reply_markup=build_back_keyboard())
        return

    if text == BTN_BUILD_BOT:
        await safe_reply_text(
            update.message,
            "این بات نمونه‌ای از بات ارتباط مستقیم نماینده با مردم است.\n\n"
            "اگر شما نماینده، کاندیدا یا فعال سیاسی هستید،\n"
            "می‌توانید بات اختصاصی خودتان را داشته باشید.\n\n"
            "- معرفی رسمی نماینده\n"
            "- دریافت نظر و دغدغه مردم\n"
            "- پاسخ‌گویی شفاف به سؤالات\n"
            "- انتشار برنامه‌ها\n"
            "- اعلان پاسخ‌ها\n"
            "- پنل مدیریت اختصاصی",
            reply_markup=build_bot_request_cta_keyboard(),
        )
        return

    if text == BTN_BOT_REQUEST:
        try:
            track_flow_event_sync(candidate_id=int(candidate_id), flow_type="lead", event="flow_started")
        except Exception:
            pass
        # If lead flow starts from Other menu, return there on back.
        if context.user_data.get("state") == STATE_OTHER_MENU:
            context.user_data["_return_state"] = STATE_OTHER_MENU
        context.user_data["state"] = STATE_BOTREQ_NAME
        await safe_reply_text(update.message, "نام و نام خانوادگی را وارد کنید:", reply_markup=build_back_keyboard())
        return

    # No free chat in MVP V1
    try:
        if update.effective_user is not None:
            log_ux_sync(
                candidate_id=int(candidate_id),
                telegram_user_id=str(update.effective_user.id),
                state=state,
                action="text_sent_in_idle_state" if state == STATE_MAIN else "unexpected_text_input",
                expected_action="tap_menu_button" if state == STATE_MAIN else "use_flow_buttons",
            )
    except Exception:
        pass

    # IMPORTANT: Do NOT auto-return to main menu during active flows.
    if state == STATE_MAIN:
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
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

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


async def debug_update_logger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs minimal info about all incoming updates.

    Placed in a separate handler group so it doesn't interfere with routing.
    """
    try:
        # Monitoring heuristic: update receive timestamp
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

async def run_bot(candidate: User):
    """Runs a single bot instance."""
    try:
        if not candidate.bot_token:
            logger.warning(f"Candidate {candidate.full_name} has no bot token.")
            return

        if not looks_like_telegram_token(candidate.bot_token):
            logger.warning(
                f"Candidate {candidate.full_name} has an invalid bot token format. Skipping start."
            )
            return

        logger.info(f"Starting bot for {candidate.full_name} (@{candidate.bot_name})...")
        
        # Configure Telegram HTTP client.
        # In some networks Telegram is only reachable via proxy. Relying on system env proxy can be flaky,
        # so we prefer an explicit proxy URL if provided.
        bot_config = getattr(candidate, "bot_config", None) or {}
        explicit_proxy_url = (
            (bot_config.get("telegram_proxy_url") if isinstance(bot_config, dict) else None)
            or (bot_config.get("telegramProxyUrl") if isinstance(bot_config, dict) else None)
            or (bot_config.get("proxy_url") if isinstance(bot_config, dict) else None)
            or (bot_config.get("proxyUrl") if isinstance(bot_config, dict) else None)
            or os.getenv("TELEGRAM_PROXY_URL")
        )

        # Normalize/guard proxy settings.
        # We have seen environments where TELEGRAM_PROXY_URL is set globally to a local port
        # (e.g. 127.0.0.1:10808) but the local proxy is flaky, causing the bot to receive
        # updates but fail to send replies intermittently.
        explicit_proxy_url = (str(explicit_proxy_url).strip() if explicit_proxy_url is not None else "") or None

        if explicit_proxy_url and not _env_truthy("TELEGRAM_ALLOW_LOCAL_PROXY"):
            try:
                parsed = urlparse(explicit_proxy_url)
                host = (parsed.hostname or "").lower()
                port = int(parsed.port) if parsed.port is not None else None
                if host in {"127.0.0.1", "localhost"} and port in {10808}:
                    # Only ignore local proxy when direct connectivity works.
                    # In restricted networks, direct connectivity can fail and the local proxy is required.
                    if _auto_decide_trust_env_for_telegram():
                        logger.warning(
                            "Using TELEGRAM_PROXY_URL local proxy (%s:%s) because direct connectivity failed. "
                            "Set TELEGRAM_ALLOW_LOCAL_PROXY=1 to force/quiet this warning.",
                            host,
                            port,
                        )
                    else:
                        logger.warning(
                            "Ignoring TELEGRAM_PROXY_URL pointing to a local proxy (%s:%s). "
                            "Set TELEGRAM_ALLOW_LOCAL_PROXY=1 to force using it.",
                            host,
                            port,
                        )
                        explicit_proxy_url = None
            except Exception:
                # If parsing fails, keep the value as-is.
                pass

        # IMPORTANT: Many environments have HTTP(S)_PROXY/ALL_PROXY set by other tools.
        # Some networks require these proxies for Telegram; others work better without them.
        # If TELEGRAM_TRUST_ENV is explicitly set, honor it. Otherwise auto-detect once.
        trust_env_raw = (os.getenv("TELEGRAM_TRUST_ENV") or "").strip()
        if trust_env_raw:
            trust_env = _env_truthy("TELEGRAM_TRUST_ENV") and not bool(explicit_proxy_url)
        else:
            trust_env = (not bool(explicit_proxy_url)) and _auto_decide_trust_env_for_telegram()

        if explicit_proxy_url:
            logger.info(f"Using explicit Telegram proxy for candidate_id={candidate.id}")
        else:
            if trust_env:
                logger.info("Telegram: trust_env=True (using system proxy env)")
            else:
                logger.info("Telegram: trust_env=False (direct connection; ignoring system proxy env)")

        request_kwargs = dict(
            connection_pool_size=TELEGRAM_CONNECTION_POOL_SIZE,
            # Long polling can legitimately hold the connection for >20s.
            # Keep read_timeout comfortably above Telegram's getUpdates long-poll duration
            # to avoid treating normal polling as a fatal timeout.
            read_timeout=90,
            write_timeout=20,
            connect_timeout=20,
            pool_timeout=5,
            httpx_kwargs={"trust_env": trust_env},
        )
        if explicit_proxy_url:
            # PTB v20.7+ prefers `proxy` over `proxy_url`.
            request_kwargs["proxy"] = explicit_proxy_url

        try:
            request = HTTPXRequest(**request_kwargs)
        except TypeError:
            # Backward compatibility with older PTB that still expects `proxy_url`.
            if "proxy" in request_kwargs:
                request_kwargs["proxy_url"] = request_kwargs.pop("proxy")
            request = HTTPXRequest(**request_kwargs)
        
        builder = Application.builder().token(candidate.bot_token).request(request)
        try:
            # PTB v20+ supports concurrent update processing.
            if BOT_CONCURRENT_UPDATES > 1:
                builder = builder.concurrent_updates(BOT_CONCURRENT_UPDATES)
        except Exception:
            # Best-effort: don't break startup on older PTB versions.
            pass

        application = builder.build()
        
        # Store candidate ID in bot_data for handlers to access
        application.bot_data["candidate_id"] = candidate.id

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("chatid", chatid_command))
        application.add_handler(CommandHandler("myid", myid_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        # Logs all updates in a later group to avoid interfering with main routing.
        application.add_handler(MessageHandler(filters.ALL, debug_update_logger), group=1)
        application.add_error_handler(error_handler)

        await application.initialize()
        await application.start()

        # Ensure polling mode works: if a webhook is set, Telegram can reject getUpdates.
        # This is safe for an MVP polling runner.
        try:
            await application.bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            pass

        # Don't silently drop /start messages if the bot was down.
        await application.updater.start_polling(drop_pending_updates=False)

        # Background minimal health checks (monitoring MVP).
        application.create_task(health_check_loop(application, candidate_id=candidate.id))
        
        logger.info(f"Bot for {candidate.full_name} is running.")
        
        # Keep the bot running
        return application

    except Exception as e:
        logger.exception(f"Failed to start bot for {candidate.full_name}")
        try:
            log_technical_error_sync(
                service_name="telegram_bot",
                error_type="StartFailed",
                error_message=f"Failed to start polling for candidate_id={getattr(candidate, 'id', None)}: {e}",
                telegram_user_id=None,
                candidate_id=int(getattr(candidate, "id", 0) or 0) or None,
                state=None,
            )
        except Exception:
            pass
        return None

# Global dictionary to track running bots: candidate_id -> Application
running_bots = {}

# candidate_id -> last failure UTC time
failed_bots = {}


async def stop_application(app: Application, *, candidate_id: int, reason: str) -> None:
    logger.info(f"Stopping bot for candidate_id={candidate_id}. reason={reason}")
    try:
        updater = getattr(app, "updater", None)
        if updater is not None and getattr(updater, "running", False):
            await updater.stop()
    except Exception as e:
        logger.warning(f"Failed stopping updater for candidate_id={candidate_id}: {e}")

    try:
        if getattr(app, "running", False):
            await app.stop()
    except Exception as e:
        logger.warning(f"Failed stopping app for candidate_id={candidate_id}: {e}")

    try:
        await app.shutdown()
    except Exception as e:
        logger.warning(f"Failed shutting down app for candidate_id={candidate_id}: {e}")

async def check_for_new_candidates():
    """Periodically checks for new active candidates and starts their bots."""
    while True:
        try:
            def get_active_candidates():
                db = SessionLocal()
                try:
                    return db.query(User).filter(User.role == "CANDIDATE", User.is_active == True).all()
                finally:
                    db.close()

            candidates = await run_db_query(get_active_candidates)
            
            active_ids = set()

            # Health-check currently running bots. If polling died (e.g., network/proxy issues, 409 conflict),
            # remove & restart on next loop.
            for cid, app in list(running_bots.items()):
                try:
                    updater = getattr(app, "updater", None)
                    updater_running = bool(updater and getattr(updater, "running", False))
                    app_running = bool(getattr(app, "running", False))
                    if not updater_running or not app_running:
                        running_bots.pop(cid, None)
                        await stop_application(app, candidate_id=cid, reason="healthcheck: updater/app not running")
                        failed_bots[cid] = datetime.now(timezone.utc)
                except Exception as e:
                    logger.warning(f"Healthcheck failed for candidate_id={cid}: {e}")
            
            for candidate in candidates:
                active_ids.add(candidate.id)
                
                # If candidate is active but bot is not running, start it
                if candidate.id not in running_bots:
                    last_failed_at = failed_bots.get(candidate.id)
                    if last_failed_at and (datetime.now(timezone.utc) - last_failed_at) < FAILED_BOT_COOLDOWN:
                        continue

                    if candidate.bot_token:
                        logger.info(f"Found new active candidate: {candidate.full_name}. Starting bot...")
                        app = await run_bot(candidate)
                        if app:
                            running_bots[candidate.id] = app
                            failed_bots.pop(candidate.id, None)
                        else:
                            failed_bots[candidate.id] = datetime.now(timezone.utc)

            # Stop bots for candidates that are no longer active
            ids_to_stop = [cid for cid in running_bots.keys() if cid not in active_ids]
            for cid in ids_to_stop:
                app = running_bots.pop(cid, None)
                if app is None:
                    continue
                await stop_application(app, candidate_id=cid, reason="candidate deactivated")
                failed_bots.pop(cid, None)
            
        except Exception as e:
            logger.error(f"Error in candidate check loop: {e}")
        
        # Wait 10 seconds before next check
        await asyncio.sleep(10)

async def main():
    """Main entry point to run all candidate bots."""
    logger.info("Starting Bot Runner Service...")
    
    # Start the update checker loop as a background task
    checker_task = asyncio.create_task(check_for_new_candidates())
    
    # Keep the script running indefinitely
    stop_signal = asyncio.Event()
    try:
        await stop_signal.wait()
    except KeyboardInterrupt:
        logger.info("Stopping bots...")
        stop_signal.set()
        checker_task.cancel()
        
        for app in running_bots.values():
            if app.updater.running:
                await app.updater.stop()
            if app.running:
                await app.stop()
                await app.shutdown()

if __name__ == "__main__":
    try:
        # Prevent multiple bot_runner processes on the same machine.
        acquire_single_instance_lock(_default_lock_path())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
