import asyncio
import atexit
import contextlib
import logging
import signal
import re
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import urlsplit
from typing import List
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut, RetryAfter
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from dotenv import load_dotenv
from database import SessionLocal, Base, engine
from models import User, BotUser, BotSubmission, BotUserRegistry, BotQuestionVote, BotSubmissionPublishLog, BotForumTopic, BotCommitment

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


def _get_env(name: str) -> str | None:
    """Read env var with a Windows registry fallback.

    `setx` writes to the user's environment in the registry, but already-running
    processes (VS Code / terminals) won't see it via `os.getenv()` until restarted.
    This helper makes bot_runner pick up newly `setx`'d values without restarts.
    """
    value = os.getenv(name)
    if isinstance(value, str) and value.strip():
        return value.strip()

    if os.name != "nt":
        return None

    try:
        import winreg  # type: ignore

        for hive, subkey in (
            (winreg.HKEY_CURRENT_USER, r"Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ):
            try:
                with winreg.OpenKey(hive, subkey) as k:
                    try:
                        v, _ = winreg.QueryValueEx(k, name)
                    except FileNotFoundError:
                        continue
                    if isinstance(v, str) and v.strip():
                        return v.strip()
            except OSError:
                continue
    except Exception:
        return None

    return None

FAILED_BOT_COOLDOWN = timedelta(minutes=5)

# Notify admin when a new BOT_REQUEST is submitted.
# NOTE: Telegram bots can only message users who have started that bot.
BOT_NOTIFY_ADMIN_USERNAME = (os.getenv("BOT_NOTIFY_ADMIN_USERNAME") or "mrFarzadMdi").lstrip("@").strip()
BOT_NOTIFY_ADMIN_CHAT_ID = (os.getenv("BOT_NOTIFY_ADMIN_CHAT_ID") or "").strip()


Base.metadata.create_all(bind=engine)


BTN_INTRO = "🏛 معرفی نماینده"
BTN_PROGRAMS = "✅ برنامه‌ها"
BTN_FEEDBACK = "💬 نظر / دغدغه"
BTN_FEEDBACK_LEGACY = "✍️ ارسال نظر / دغدغه"
BTN_QUESTION = "❓ سؤال از نماینده"
BTN_CONTACT = "📍 آدرس ستادها"
BTN_COMMITMENTS = "📜 تعهدات نماینده"
BTN_ABOUT_MENU = "📂 درباره نماینده"
BTN_OTHER_MENU = "⚙️ سایر امکانات"
BTN_BUILD_BOT = "🛠 ساخت بات اختصاصی"

BTN_ABOUT_BOT = "ℹ️ درباره این بات"

BTN_PROFILE_SUMMARY = "👤 سوابق"
BTN_VOICE_INTRO = "🎙 معرفی صوتی"
BTN_BACK = "🔙 بازگشت"

# Fixed categories (MVP - strict)
QUESTION_CATEGORIES: list[str] = [
    "اقتصاد",
    "اشتغال",
    "مسکن",
    "شفافیت",
    "مسائل محلی",
]

BTN_BOT_REQUEST = "✅ درخواست ساخت بات اختصاصی"

ROLE_REPRESENTATIVE = "نماینده"
ROLE_CANDIDATE = "کاندیدا"
ROLE_TEAM = "تیم"

# --- Mandatory state machine (strict) ---
STATE_IDLE = "idle"
STATE_QUESTION_CATEGORY = "question_category"
STATE_QUESTION_TEXT = "question_text"
STATE_FEEDBACK_TEXT = "feedback_text"
STATE_LEAD_ROLE = "lead_role"
STATE_LEAD_CONTACT_CHOICE = "lead_contact_choice"
STATE_DONE = "done"


def build_bot_request_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(ROLE_REPRESENTATIVE), KeyboardButton(ROLE_CANDIDATE), KeyboardButton(ROLE_TEAM)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_lead_contact_choice_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("☎️ شماره تماس"), KeyboardButton("💬 آیدی تلگرام")], [KeyboardButton(BTN_BACK)]],
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
از بخش «❓ سؤال از نماینده» استفاده کن (پاسخ‌ها عمومی منتشر می‌شوند)."""


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_QUESTION)],
            [KeyboardButton(BTN_COMMITMENTS)],
            [KeyboardButton(BTN_FEEDBACK), KeyboardButton(BTN_ABOUT_MENU)],
            [KeyboardButton(BTN_OTHER_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_about_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_INTRO), KeyboardButton(BTN_PROGRAMS)],
            [KeyboardButton(BTN_CONTACT), KeyboardButton(BTN_VOICE_INTRO)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_other_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_ABOUT_BOT)],
            [KeyboardButton(BTN_BUILD_BOT)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def _current_idle_keyboard(context: ContextTypes.DEFAULT_TYPE) -> ReplyKeyboardMarkup:
    menu = (context.user_data.get("idle_menu") or "main").strip().lower()
    if menu == "about":
        return build_about_keyboard()
    if menu == "other":
        return build_other_keyboard()
    return build_main_keyboard()


def _is_bot_admin(update: Update) -> bool:
    """Best-effort bot-admin check for write actions in the bot UI."""
    user = getattr(update, "effective_user", None)
    if user is None:
        return False
    uid = str(getattr(user, "id", "") or "").strip()
    uname = str(getattr(user, "username", "") or "").lstrip("@").strip().lower()
    if BOT_NOTIFY_ADMIN_CHAT_ID and uid and uid == str(BOT_NOTIFY_ADMIN_CHAT_ID).strip():
        return True
    if BOT_NOTIFY_ADMIN_USERNAME and uname and uname == str(BOT_NOTIFY_ADMIN_USERNAME).lstrip("@").strip().lower():
        return True
    return False


def _commitments_banner_md() -> str:
    return "🛡 *اطلاع‌رسانی عمومی*\nتمام تعهدات ثبت‌شده غیرقابل ویرایش و دائمی هستند."


def _safe_md_text(s: str) -> str:
    # Minimal escaping for classic Telegram Markdown.
    # We mostly use code blocks to avoid formatting issues.
    return (s or "").replace("*", "⋆").replace("_", "﹍").replace("[`", "[").replace("]`", "]")


def _format_commitment_pre_md(title: str, body: str, created_at: datetime | None, status: str, locked: bool) -> str:
    created_str = "-"
    if isinstance(created_at, datetime):
        created_str = created_at.strftime("%Y-%m-%d %H:%M")
    lock_icon = "🔒" if locked else ""
    safe_title = _safe_md_text((title or "").strip())
    safe_body = _safe_md_text((body or "").strip())
    safe_status = _safe_md_text((status or "").strip() or "Active")
    block = (
        f"{lock_icon} {safe_title}\n"
        f"🕒 {created_str}\n"
        f"📌 وضعیت: {safe_status}\n"
        f"\n{safe_body}"
    ).strip()
    # Prefer code block for preformatted rendering.
    block = block.replace("```", "``\u200b`")
    return f"```\n{block}\n```"


def _first_commitment_keyboard() -> InlineKeyboardMarkup:
    # Telegram doesn't support true colored buttons for callbacks; we highlight by ordering + ✅.
    options = [
        ("همین بات رسمی ✅", "official_bot"),
        ("ستادهای حضوری", "in_person"),
        ("تماس تلفنی", "phone"),
        ("شبکه‌های اجتماعی", "socials"),
        ("ترکیبی", "mixed"),
    ]
    rows = [[InlineKeyboardButton(text, callback_data=f"commit:first:{key}")] for text, key in options]
    return InlineKeyboardMarkup(rows)


def build_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True, is_persistent=True)


def build_question_category_keyboard() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    buttons = [KeyboardButton(c) for c in QUESTION_CATEGORIES]
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i : i + 2])
    rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def build_vote_inline_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("👍 این سؤال برای من مهم است", callback_data=f"vote:{int(submission_id)}")]]
    )


def _question_code(candidate_bot_config: dict, submission_id: int) -> str:
    prefix = "MA"
    if isinstance(candidate_bot_config, dict):
        v = _normalize_text(candidate_bot_config.get("question_code_prefix") or candidate_bot_config.get("questionCodePrefix"))
        if v:
            prefix = v
    return f"{prefix}-{int(submission_id):03d}"


def _vote_threshold(candidate_bot_config: dict) -> int:
    if not isinstance(candidate_bot_config, dict):
        return 10
    raw = candidate_bot_config.get("vote_threshold") or candidate_bot_config.get("voteThreshold")
    try:
        v = int(raw)
        return v if v > 0 else 10
    except Exception:
        return 10


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


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


LOCK_FILENAME = ".bot_runner.lock"


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
                return False
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
                'bot_config': c.bot_config,
            }
        finally:
            db.close()

    candidate = await run_db_query(get_candidate_data, candidate_id)
    
    if not candidate:
        msg = update.effective_message
        if msg:
            await safe_reply_text(msg, "خطا: اطلاعات کاندیدا یافت نشد.")
        return

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
                    context.user_data["state"] = STATE_IDLE
                    await safe_reply_text(msg, "این سؤال یافت نشد یا هنوز پاسخ عمومی ندارد.", reply_markup=build_main_keyboard())
                    return

                q_txt = _normalize_text(getattr(row, "text", ""))
                a_txt = _normalize_text(getattr(row, "answer", ""))
                topic = _normalize_text(getattr(row, "topic", ""))
                is_featured = bool(getattr(row, "is_featured", False))
                badge = " ⭐ منتخب" if is_featured else ""
                head = f"[{topic}] " if topic else ""
                bot_cfg = candidate.get('bot_config') if isinstance(candidate, dict) else {}
                code = _question_code(bot_cfg if isinstance(bot_cfg, dict) else {}, qid)
                block = f"❓ {head}{q_txt}\n\n✅ {a_txt}\n\n🔖 کد سؤال: {code}{badge}"

                context.user_data["state"] = STATE_IDLE
                await safe_reply_text(msg, block, reply_markup=build_vote_inline_keyboard(qid))
                await safe_reply_text(msg, "لطفاً از دکمه‌های زیر استفاده کنید 👇", reply_markup=build_main_keyboard())
                return
    except Exception:
        logger.exception("Failed to handle /start deep-link")

    # Save User Data (also logs Telegram user id -> candidate + city/province/constituency)
    await save_bot_user(update, candidate_id=candidate_id, candidate_snapshot=candidate)

    context.user_data["state"] = STATE_IDLE
    context.user_data["idle_menu"] = "main"
    context.user_data.pop("feedback_topic", None)

    welcome_text = f"سلام! من بات {candidate['name']} هستم.\n\n"

    if candidate['slogan']:
        welcome_text += f"📣 {candidate['slogan']}\n\n"
    
    welcome_text += "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
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
    text = update.message.text
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
    state = context.user_data.get("state") or STATE_IDLE

    if text == BTN_BACK:
        context.user_data["state"] = STATE_IDLE
        context.user_data["idle_menu"] = "main"
        context.user_data.pop("feedback_topic", None)
        context.user_data.pop("question_category", None)
        context.user_data.pop("lead_role", None)
        context.user_data.pop("lead_contact_method", None)
        context.user_data.pop("awaiting_contact_text", None)
        context.user_data.pop("programs_mode", None)
        await safe_reply_text(update.message, "به منوی اصلی برگشتید.", reply_markup=build_main_keyboard())
        return

    # --- Lead / bot request flow (strict: lead_role -> lead_contact_choice -> done) ---
    if state == STATE_LEAD_ROLE:
        allowed = {ROLE_REPRESENTATIVE, ROLE_CANDIDATE, ROLE_TEAM}
        if text not in allowed:
            await safe_reply_text(update.message, "لطفاً نقش خود را از دکمه‌ها انتخاب کنید.", reply_markup=build_bot_request_role_keyboard())
            return
        context.user_data["lead_role"] = text
        context.user_data["lead_contact_method"] = None
        context.user_data["awaiting_contact_text"] = False
        context.user_data["state"] = STATE_LEAD_CONTACT_CHOICE
        await safe_reply_text(update.message, "روش تماس را انتخاب کنید:", reply_markup=build_lead_contact_choice_keyboard())
        return

    if state == STATE_LEAD_CONTACT_CHOICE:
        # Step 1: user chooses contact method
        if text in {"☎️ شماره تماس", "💬 آیدی تلگرام"}:
            context.user_data["lead_contact_method"] = text
            context.user_data["awaiting_contact_text"] = True
            await safe_reply_text(update.message, "اطلاعات تماس را ارسال کنید:", reply_markup=build_back_keyboard())
            return

        # Step 2: user types the contact
        if not context.user_data.get("awaiting_contact_text"):
            await safe_reply_text(update.message, "ابتدا روش تماس را انتخاب کنید.", reply_markup=build_lead_contact_choice_keyboard())
            return

        reserved = {BTN_INTRO, BTN_PROGRAMS, BTN_FEEDBACK, BTN_FEEDBACK_LEGACY, BTN_QUESTION, BTN_CONTACT, BTN_BUILD_BOT, BTN_BACK}
        if text in reserved or not text:
            await safe_reply_text(update.message, "لطفاً اطلاعات تماس را ارسال کنید یا «بازگشت» را بزنید.")
            return

        role = _normalize_text(context.user_data.get("lead_role"))
        contact_method = _normalize_text(context.user_data.get("lead_contact_method"))
        contact = text
        constituency = _candidate_constituency(candidate)
        formatted = (f"نقش: {role}\nروش تماس: {contact_method}\nتماس: {contact}").strip()

        submission_id = await run_db_query(
            _save_submission_sync,
            candidate_id=candidate_id,
            telegram_user_id=str(update.effective_user.id) if update.effective_user else "",
            telegram_username=(update.effective_user.username if update.effective_user else None),
            submission_type="BOT_REQUEST",
            topic=(role or None),
            text=formatted,
            constituency=constituency,
            requester_full_name=None,
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
                header = f"🛠 درخواست ساخت بات اختصاصی (کد: {submission_id})"
                source = f"از بات: {cand_name} (@{cand_bot})" if cand_bot else f"از بات: {cand_name}"
                req_user = _normalize_text(update.effective_user.username if update.effective_user else "")
                req_user_line = f"یوزرنیم متقاضی: @{req_user}" if req_user else ""
                msg = "\n".join([x for x in [header, source, formatted, req_user_line] if x]).strip()
                await context.bot.send_message(chat_id=int(admin_chat_id), text=msg)
        except Exception:
            logger.exception("Failed to notify admin of BOT_REQUEST")

        context.user_data["state"] = STATE_DONE
        context.user_data.pop("lead_role", None)
        context.user_data.pop("lead_contact_method", None)
        context.user_data.pop("awaiting_contact_text", None)
        await safe_reply_text(update.message, "✅ درخواست شما ثبت شد.", reply_markup=build_main_keyboard())
        context.user_data["state"] = STATE_IDLE
        return

    # Feedback flow
    if state == STATE_FEEDBACK_TEXT:
        if text in {BTN_INTRO, BTN_PROGRAMS, BTN_FEEDBACK, BTN_FEEDBACK_LEGACY, BTN_QUESTION, BTN_CONTACT, BTN_COMMITMENTS, BTN_ABOUT_MENU, BTN_OTHER_MENU, BTN_BUILD_BOT}:
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
        context.user_data["state"] = STATE_DONE
        context.user_data.pop("feedback_topic", None)
        await safe_reply_text(update.message, _build_feedback_confirmation_text(socials), reply_markup=build_main_keyboard())
        context.user_data["state"] = STATE_IDLE
        return

    # Question flow
    if state == STATE_QUESTION_TEXT:
        if not _normalize_text(context.user_data.get("question_category")):
            context.user_data["state"] = STATE_QUESTION_CATEGORY
            await safe_reply_text(update.message, "ابتدا دسته‌بندی سؤال را انتخاب کنید:", reply_markup=build_question_category_keyboard())
            return

        if text in {BTN_INTRO, BTN_PROGRAMS, BTN_FEEDBACK, BTN_FEEDBACK_LEGACY, BTN_QUESTION, BTN_CONTACT, BTN_COMMITMENTS, BTN_ABOUT_MENU, BTN_OTHER_MENU, BTN_BUILD_BOT}:
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
            context.user_data["state"] = STATE_IDLE
            await safe_reply_text(update.message, "این سؤال قبلاً ثبت شده است.", reply_markup=build_main_keyboard())
            return

        constituency = _candidate_constituency(candidate)
        submission_id = await run_db_query(
            _save_submission_sync,
            candidate_id=candidate_id,
            telegram_user_id=str(update.effective_user.id) if update.effective_user else "",
            telegram_username=(update.effective_user.username if update.effective_user else None),
            submission_type="QUESTION",
            topic=_normalize_text(context.user_data.get("question_category")) or None,
            text=q_text,
            constituency=constituency,
            status="PENDING",
            is_public=False,
        )
        code = _question_code(bot_config, int(submission_id) if submission_id is not None else 0)
        context.user_data["state"] = STATE_DONE
        context.user_data.pop("question_category", None)
        await safe_reply_text(
            update.message,
            f"✅ سؤال شما ثبت شد.\n\n🔖 کد سؤال: {code}\n\nپاسخ‌ها به‌صورت عمومی منتشر می‌شوند (پاسخ فردی نداریم).",
            reply_markup=build_main_keyboard(),
        )
        context.user_data["state"] = STATE_IDLE
        return

    if state == STATE_QUESTION_CATEGORY:
        if text in QUESTION_CATEGORIES:
            context.user_data["question_category"] = text
            context.user_data["state"] = STATE_QUESTION_TEXT
            await safe_reply_text(update.message, "متن سؤال‌تان را تایپ کنید:", reply_markup=build_back_keyboard())
            return
        await safe_reply_text(update.message, "لطفاً یکی از دسته‌ها را انتخاب کنید 👇", reply_markup=build_question_category_keyboard())
        return

    # Programs quick selection (only allowed after entering Programs)
    if context.user_data.get("programs_mode") and text.startswith("سوال "):
        try:
            idx = int(text.replace("سوال", "").strip()) - 1
        except Exception:
            idx = -1
        if 0 <= idx < len(PROGRAM_QUESTIONS):
            q = PROGRAM_QUESTIONS[idx]
            a = _get_program_answer(candidate, idx)
            await safe_reply_text(update.message, f"{q}\n\nپاسخ نماینده:\n{a}", reply_markup=build_back_keyboard())
            return

    # Main menu
    if text == BTN_INTRO:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "about"
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
        context.user_data["state"] = STATE_IDLE
        context.user_data["programs_mode"] = True
        context.user_data["idle_menu"] = "about"
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
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "main"
        context.user_data["state"] = STATE_FEEDBACK_TEXT
        context.user_data.pop("feedback_topic", None)
        await safe_reply_text(update.message, _build_feedback_intro_text(socials), reply_markup=build_back_keyboard())
        await safe_reply_text(update.message, "متن نظر/دغدغه‌تان را ارسال کنید:", reply_markup=build_back_keyboard())
        return

    if text == BTN_QUESTION:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "main"
        context.user_data["state"] = STATE_QUESTION_CATEGORY
        await safe_reply_text(
            update.message,
            "دسته‌بندی سؤال را انتخاب کنید (پاسخ‌ها عمومی هستند و پاسخ فردی نداریم):",
            reply_markup=build_question_category_keyboard(),
        )
        return

    if text == BTN_CONTACT:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "about"
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
                await safe_reply_text(update.message, "📍 آدرس ستادها\n\n" + "\n\n".join(blocks), reply_markup=build_back_keyboard())
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

    if text == BTN_COMMITMENTS:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "main"

        def _get_commitments(cid: int) -> list[BotCommitment]:
            db = SessionLocal()
            try:
                return (
                    db.query(BotCommitment)
                    .filter(BotCommitment.candidate_id == int(cid))
                    .order_by(BotCommitment.created_at.asc(), BotCommitment.id.asc())
                    .all()
                )
            finally:
                db.close()

        rows = await run_db_query(_get_commitments, int(candidate_id))
        parts: list[str] = ["📜 *تعهدات نماینده*", "", _commitments_banner_md(), ""]

        if rows:
            parts.append("🔒 *لیست تعهدات*")
            for r in rows:
                parts.append(
                    _format_commitment_pre_md(
                        _normalize_text(getattr(r, "title", "")),
                        _normalize_text(getattr(r, "body", "")),
                        getattr(r, "created_at", None),
                        _normalize_text(getattr(r, "status", "")),
                        bool(getattr(r, "locked", True)),
                    )
                )
        else:
            parts.append("ℹ️ هنوز تعهدی ثبت نشده است.")

        await safe_reply_text(update.message, "\n".join(parts).strip(), parse_mode="Markdown", reply_markup=build_back_keyboard())

        # Mandatory first commitment prompt (admin-only)
        if not rows and _is_bot_admin(update):
            await safe_reply_text(
                update.message,
                "❓ *تعهد اول (اجباری)*\nپل ارتباطی رسمی نماینده با مردم چیست؟",
                parse_mode="Markdown",
                reply_markup=_first_commitment_keyboard(),
            )
        return

    if text == BTN_ABOUT_MENU:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "about"
        await safe_reply_text(update.message, "📂 درباره نماینده", reply_markup=build_about_keyboard())
        return

    if text == BTN_OTHER_MENU:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "other"
        await safe_reply_text(update.message, "⚙️ سایر امکانات", reply_markup=build_other_keyboard())
        return

    if text == BTN_ABOUT_BOT:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "other"
        msg = (
            "ℹ️ *درباره این بات*\n\n"
            "این بات برای اطلاع‌رسانی رسمی، ثبت سؤال و ثبت نظر/دغدغه طراحی شده است.\n"
            "پاسخ‌ها به‌صورت عمومی منتشر می‌شوند و گفتگوی مستقیم/پاسخ شخصی ندارد."
        )
        await safe_reply_text(update.message, msg, parse_mode="Markdown", reply_markup=build_other_keyboard())
        return


    if text == BTN_BUILD_BOT:
        context.user_data["programs_mode"] = False
        context.user_data["idle_menu"] = "other"
        context.user_data["state"] = STATE_LEAD_ROLE
        await safe_reply_text(
            update.message,
            "برای ساخت بات اختصاصی، چند اطلاعات کوتاه می‌گیریم.\n"
            "توجه: این بخش برای دریافت درخواست است و گفتگوی مستقیم/پاسخ شخصی ندارد.\n\n"
            "نقش شما کدام است؟",
            reply_markup=build_bot_request_role_keyboard(),
        )
        return

    # Idle behavior: ignore free text, re-render current idle menu.
    if state == STATE_IDLE:
        await safe_reply_text(update.message, "لطفاً از دکمه‌های زیر استفاده کنید 👇", reply_markup=_current_idle_keyboard(context))
        return

    # Safety fallback: keep current state unless user hits Back.
    await safe_reply_text(update.message, "لطفاً از دکمه‌ها استفاده کنید یا «بازگشت» را بزنید.")


async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    data = _normalize_text(getattr(query, "data", ""))
    m = re.fullmatch(r"vote:(\d+)", data)
    if not m:
        return
    submission_id = int(m.group(1))
    candidate_id = context.bot_data.get("candidate_id")
    user = update.effective_user
    if not candidate_id or not user:
        return

    telegram_user_id = str(user.id)

    def _can_vote_and_apply(cid: int, sid: int, tuid: str) -> tuple[bool, int, bool]:
        """Returns (voted_now, new_count, reached_threshold)."""
        db = SessionLocal()
        try:
            row = (
                db.query(BotSubmission)
                .filter(
                    BotSubmission.id == int(sid),
                    BotSubmission.candidate_id == int(cid),
                    BotSubmission.type == "QUESTION",
                    BotSubmission.status == "ANSWERED",
                    BotSubmission.is_public == True,  # noqa: E712
                )
                .first()
            )
            if not row:
                return (False, 0, False)

            exists = (
                db.query(BotQuestionVote)
                .filter(
                    BotQuestionVote.submission_id == int(sid),
                    BotQuestionVote.telegram_user_id == tuid,
                )
                .first()
            )
            if exists:
                count = (
                    db.query(func.count(BotQuestionVote.id))
                    .filter(BotQuestionVote.submission_id == int(sid))
                    .scalar()
                )
                return (False, int(count or 0), False)

            vote = BotQuestionVote(candidate_id=int(cid), submission_id=int(sid), telegram_user_id=tuid)
            db.add(vote)
            db.commit()

            count = (
                db.query(func.count(BotQuestionVote.id))
                .filter(BotQuestionVote.submission_id == int(sid))
                .scalar()
            )
            count_int = int(count or 0)

            # Threshold -> mark featured (High Priority)
            threshold = 10
            try:
                cand = db.query(User).filter(User.id == int(cid), User.role == "CANDIDATE").first()
                cfg = cand.bot_config if cand and isinstance(cand.bot_config, dict) else {}
                raw = cfg.get("vote_threshold") or cfg.get("voteThreshold")
                threshold = int(raw) if raw is not None else 10
                if threshold <= 0:
                    threshold = 10
            except Exception:
                threshold = 10

            reached = False
            if count_int >= threshold and not bool(getattr(row, "is_featured", False)):
                row.is_featured = True
                reached = True
                db.add(row)
                db.commit()

            return (True, count_int, reached)
        finally:
            db.close()

    voted_now, new_count, reached = await run_db_query(_can_vote_and_apply, int(candidate_id), submission_id, telegram_user_id)
    if new_count == 0 and not voted_now:
        await query.answer("این سؤال یافت نشد یا قابل رأی‌دادن نیست.", show_alert=True)
        return
    if not voted_now:
        await query.answer("قبلاً برای این سؤال رأی داده‌اید.")
        return
    msg = f"✅ رأی شما ثبت شد. (تعداد: {new_count})"
    if reached:
        msg += "\n⭐ این سؤال به اولویت بالا رسید."
    await query.answer(msg)


async def commitment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    data = _normalize_text(getattr(query, "data", ""))
    m = re.fullmatch(r"commit:first:([a-z_]+)", data)
    if not m:
        return

    if not _is_bot_admin(update):
        await query.answer("دسترسی ندارید.", show_alert=True)
        return

    candidate_id = context.bot_data.get("candidate_id")
    if not candidate_id:
        await query.answer("خطا: شناسه کاندیدا یافت نشد.", show_alert=True)
        return

    choice_key = m.group(1)
    option_map = {
        "official_bot": "همین بات رسمی ✅",
        "in_person": "ستادهای حضوری",
        "phone": "تماس تلفنی",
        "socials": "شبکه‌های اجتماعی",
        "mixed": "ترکیبی",
    }
    chosen = option_map.get(choice_key)
    if not chosen:
        await query.answer("گزینه نامعتبر است.", show_alert=True)
        return

    title = "پل ارتباطی رسمی نماینده با مردم چیست؟"
    body = f"پاسخ: {chosen}"

    def _insert_first_commitment(cid: int) -> bool:
        db = SessionLocal()
        try:
            exists = (
                db.query(BotCommitment)
                .filter(BotCommitment.candidate_id == int(cid), BotCommitment.key == "official_bridge")
                .first()
            )
            if exists:
                return False
            row = BotCommitment(
                candidate_id=int(cid),
                key="official_bridge",
                title=title,
                body=body,
                status="Active",
                locked=True,
            )
            db.add(row)
            db.commit()
            return True
        finally:
            db.close()

    created = await run_db_query(_insert_first_commitment, int(candidate_id))
    if not created:
        await query.answer("این تعهد قبلاً ثبت شده است.")
    else:
        await query.answer("✅ تعهد ثبت شد.")

    # Refresh the commitments view
    try:
        await query.message.reply_text("لطفاً از دکمه‌های زیر استفاده کنید 👇", reply_markup=build_main_keyboard())
    except Exception:
        pass


async def publish_loop(app: Application, *, candidate_id: int) -> None:
    """Background publisher: announces newly public answered questions into a forum topic per category."""
    while True:
        try:
            def _fetch_pending(cid: int) -> list[int]:
                db = SessionLocal()
                try:
                    subq = (
                        db.query(BotSubmission.id)
                        .filter(
                            BotSubmission.candidate_id == int(cid),
                            BotSubmission.type == "QUESTION",
                            BotSubmission.status == "ANSWERED",
                            BotSubmission.is_public == True,  # noqa: E712
                            BotSubmission.answer.isnot(None),
                        )
                        .order_by(BotSubmission.answered_at.asc().nullslast(), BotSubmission.id.asc())
                        .limit(10)
                        .all()
                    )
                    ids = [int(x[0]) for x in subq]
                    if not ids:
                        return []
                    published = (
                        db.query(BotSubmissionPublishLog.submission_id)
                        .filter(
                            BotSubmissionPublishLog.candidate_id == int(cid),
                            BotSubmissionPublishLog.submission_id.in_(ids),
                        )
                        .all()
                    )
                    published_ids = {int(x[0]) for x in published}
                    return [i for i in ids if i not in published_ids]
                finally:
                    db.close()

            pending_ids = await run_db_query(_fetch_pending, candidate_id)
            if not pending_ids:
                await asyncio.sleep(6)
                continue

            for sid in pending_ids:
                # Fetch full row + socials/bot_name
                def _get_payload(cid: int, submission_id: int):
                    db = SessionLocal()
                    try:
                        cand = db.query(User).filter(User.id == int(cid), User.role == "CANDIDATE").first()
                        sub = db.query(BotSubmission).filter(BotSubmission.id == int(submission_id), BotSubmission.candidate_id == int(cid)).first()
                        if not cand or not sub:
                            return None
                        return {
                            "bot_name": cand.bot_name,
                            "socials": cand.socials if isinstance(cand.socials, dict) else {},
                            "bot_config": cand.bot_config if isinstance(cand.bot_config, dict) else {},
                            "topic": _normalize_text(getattr(sub, "topic", "")),
                            "q": _normalize_text(getattr(sub, "text", "")),
                            "a": _normalize_text(getattr(sub, "answer", "")),
                        }
                    finally:
                        db.close()

                payload = await run_db_query(_get_payload, candidate_id, sid)
                if not payload:
                    continue

                socials = payload.get("socials") or {}
                group_chat_id = socials.get("telegram_group_chat_id") or socials.get("telegramGroupChatId")
                if not group_chat_id:
                    # Group is not configured yet; keep pending so it can be published later.
                    continue

                chat_id_int = int(group_chat_id)
                category = payload.get("topic") or "عمومی"
                bot_name = _normalize_text(payload.get("bot_name") or "").lstrip("@").strip()
                deep_link = f"https://t.me/{bot_name}?start=question_{sid}" if bot_name else ""
                code = _question_code(payload.get("bot_config") or {}, sid)

                thread_id: int | None = None
                # Reuse or create forum topic
                def _get_thread(cid: int, chat_id: str, cat: str) -> int | None:
                    db = SessionLocal()
                    try:
                        row = (
                            db.query(BotForumTopic)
                            .filter(
                                BotForumTopic.candidate_id == int(cid),
                                BotForumTopic.chat_id == str(chat_id),
                                BotForumTopic.category == cat,
                            )
                            .first()
                        )
                        return int(row.thread_id) if row else None
                    finally:
                        db.close()

                thread_id = await run_db_query(_get_thread, candidate_id, str(chat_id_int), category)
                if thread_id is None:
                    try:
                        topic = await app.bot.create_forum_topic(chat_id=chat_id_int, name=category)
                        thread_id = int(getattr(topic, "message_thread_id", None) or getattr(topic, "thread_id", None) or 0) or None
                        if thread_id is not None:
                            def _save_thread(cid: int, chat_id: str, cat: str, tid: int):
                                db = SessionLocal()
                                try:
                                    db.add(BotForumTopic(candidate_id=int(cid), chat_id=str(chat_id), category=cat, thread_id=int(tid)))
                                    db.commit()
                                finally:
                                    db.close()
                            await run_db_query(_save_thread, candidate_id, str(chat_id_int), category, thread_id)
                    except Exception:
                        thread_id = None

                text_msg = f"🔔 پاسخ جدید منتشر شد\n\n🔖 کد سؤال: {code}\n🏷 دسته: {category}\n\n❓ {payload.get('q')}\n\n✅ {payload.get('a')}"
                if deep_link:
                    text_msg += f"\n\n🔗 لینک مستقیم پاسخ: {deep_link}"

                try:
                    if thread_id is not None:
                        await app.bot.send_message(chat_id=chat_id_int, text=text_msg, message_thread_id=thread_id)
                    else:
                        await app.bot.send_message(chat_id=chat_id_int, text=text_msg)
                except Exception:
                    logger.exception("Failed to publish answered question")
                    continue

                def _mark(cid: int, submission_id: int):
                    db = SessionLocal()
                    try:
                        db.add(BotSubmissionPublishLog(candidate_id=int(cid), submission_id=int(submission_id)))
                        db.commit()
                    finally:
                        db.close()
                await run_db_query(_mark, candidate_id, sid)

        except Exception:
            logger.exception("publish_loop error")

        await asyncio.sleep(6)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


async def debug_update_logger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs minimal info about all incoming updates.

    Placed in a separate handler group so it doesn't interfere with routing.
    """
    try:
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
            or _get_env("TELEGRAM_PROXY_URL")
        )

        def _is_valid_proxy_url(value: str) -> bool:
            v = _normalize_text(value)
            if not v:
                return False
            try:
                u = urlsplit(v)
                if u.scheme not in {"http", "https", "socks5", "socks5h"}:
                    return False
                if not u.hostname:
                    return False
                # urlsplit returns None when port is missing or not numeric.
                if u.port is None:
                    return False
                return True
            except Exception:
                return False

        if explicit_proxy_url and not _is_valid_proxy_url(str(explicit_proxy_url)):
            logger.error(
                "Invalid Telegram proxy URL. Provide a full URL like http://HOST:PORT or http://USER:PASS@HOST:PORT. "
                "If you want SOCKS proxies, install httpx[socks] and use socks5://HOST:PORT."
            )
            explicit_proxy_url = None

        def _env_truthy(name: str) -> bool:
            v = (_get_env(name) or "").strip().lower()
            return v in {"1", "true", "yes", "y", "on"}

        # IMPORTANT: Many Windows environments have HTTP(S)_PROXY/ALL_PROXY set by other tools.
        # These can break Telegram connectivity. We default to trust_env=False unless explicitly enabled.
        trust_env = _env_truthy("TELEGRAM_TRUST_ENV") and not bool(explicit_proxy_url)

        if explicit_proxy_url:
            logger.info(f"Using explicit Telegram proxy for candidate_id={candidate.id}")
        else:
            if trust_env:
                logger.info("Telegram: trust_env=True (using system proxy env)")
            else:
                logger.warning(
                    "Telegram: no explicit proxy; ignoring system proxy env (trust_env=False). "
                    "If you rely on system proxy, set TELEGRAM_TRUST_ENV=1; otherwise set TELEGRAM_PROXY_URL."
                )

        request = HTTPXRequest(
            connection_pool_size=8,
            proxy_url=explicit_proxy_url or None,
            read_timeout=20,
            write_timeout=20,
            connect_timeout=20,
            pool_timeout=5,
            httpx_kwargs={"trust_env": trust_env},
        )
        
        application = Application.builder().token(candidate.bot_token).request(request).build()
        
        # Store candidate ID in bot_data for handlers to access
        application.bot_data["candidate_id"] = candidate.id

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("chatid", chatid_command))
        application.add_handler(CommandHandler("myid", myid_command))
        application.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^vote:\d+$"))
        application.add_handler(CallbackQueryHandler(commitment_callback, pattern=r"^commit:first:[a-z_]+$"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        # Logs all updates in a later group to avoid interfering with main routing.
        application.add_handler(MessageHandler(filters.ALL, debug_update_logger), group=1)
        application.add_error_handler(error_handler)

        await application.initialize()
        await application.start()
        # Don't silently drop /start messages if the bot was down.
        await application.updater.start_polling(drop_pending_updates=False)

        # Background publisher for newly answered questions.
        application.create_task(publish_loop(application, candidate_id=candidate.id))
        
        logger.info(f"Bot for {candidate.full_name} is running.")
        
        # Keep the bot running
        return application

    except Exception as e:
        logger.error(f"Failed to start bot for {candidate.full_name}: {e}")
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
        acquire_single_instance_lock(os.path.join(os.path.dirname(__file__), LOCK_FILENAME))
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
