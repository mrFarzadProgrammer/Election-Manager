import asyncio
import re
from datetime import datetime, timezone

import jdatetime
from telegram.error import NetworkError, TimedOut, RetryAfter


def normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_button_text(value: str | None) -> str:
    v = normalize_text(value)
    v = v.replace("\u200c", "").replace("\u200f", "").replace("\ufeff", "")
    v = re.sub(r"\s+", " ", v).strip()
    return v


def btn_eq(user_text: str | None, target: str) -> bool:
    return normalize_button_text(user_text) == normalize_button_text(target)


def btn_has(user_text: str | None, *needles: str) -> bool:
    t = normalize_button_text(user_text)
    for n in needles:
        nn = normalize_button_text(n)
        if nn and nn in t:
            return True
    return False


def is_back(user_text: str | None, *, back_button_text: str) -> bool:
    return btn_eq(user_text, back_button_text) or btn_has(user_text, "بازگشت", "برگشت")


async def safe_reply_text(message, text: str, **kwargs):
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


def to_fa_digits(value: str) -> str:
    trans = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(value).translate(trans)


def to_jalali_date_ymd(dt: datetime | None) -> str:
    if not dt:
        return ""
    try:
        if isinstance(dt, datetime):
            if getattr(dt, "tzinfo", None) is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        jd = jdatetime.date.fromgregorian(date=dt.date())
        return to_fa_digits(jd.strftime("%Y/%m/%d"))
    except Exception:
        try:
            return to_fa_digits(dt.strftime("%Y/%m/%d"))
        except Exception:
            return ""


def format_public_question_answer_block(*, topic: str | None, question: str, answer: str, answered_at: datetime | None) -> str:
    t = normalize_text(topic)
    q = normalize_text(question)
    a = normalize_text(answer)
    date_line = to_jalali_date_ymd(answered_at)

    parts: list[str] = []
    if t:
        parts.append(f"🏷 {t}")
    parts.append(f"❓ {q}")
    parts.append("\n━━━━━━━━━━━━\n✅ پاسخ رسمی نماینده\n\n" + a)
    if date_line:
        parts.append(f"📅 {date_line}")
    return "\n\n".join([p for p in parts if p]).strip()


async def send_question_list_message(*, safe_reply, update_message, topic: str, items: list[dict], back_keyboard):
    header = f"🗂 {topic}\n\nتمام سؤال‌های این بخش (شماره را ارسال کنید):\n"
    lines: list[str] = []
    for idx, it in enumerate(items, start=1):
        q = normalize_text(it.get("q") or "")
        q = re.sub(r"\s+", " ", q).strip()
        lines.append(f"{idx}) {q}" if q else f"{idx})")

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
        rm = back_keyboard if i == len(chunks) - 1 else None
        await safe_reply(update_message, ch, reply_markup=rm)


async def send_question_answers_message(*, safe_reply, update_message, topic: str, items: list[dict], back_keyboard):
    blocks: list[str] = []
    for it in items:
        q = normalize_text(it.get("q") or "")
        a = normalize_text(it.get("a") or "")
        answered_at = it.get("answered_at")
        if q and a:
            blocks.append(
                format_public_question_answer_block(
                    topic=topic,
                    question=q,
                    answer=a,
                    answered_at=answered_at if isinstance(answered_at, datetime) else None,
                )
            )

    if not blocks:
        await safe_reply(
            update_message,
            f"🗂 {topic}\n\nفعلاً پاسخ عمومی برای این دسته ثبت نشده است.",
            reply_markup=back_keyboard,
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
        rm = back_keyboard if i == len(chunks) - 1 else None
        await safe_reply(update_message, ch, reply_markup=rm)


def normalize_telegram_link(value: str) -> str:
    v = normalize_text(value)
    if not v:
        return ""
    if v.startswith("@"):  # @channel
        return f"https://t.me/{v[1:]}"
    if v.startswith("t.me/"):
        return "https://" + v
    if v.startswith("http://") or v.startswith("https://"):
        return v
    if re.fullmatch(r"[A-Za-z0-9_]{4,}", v):
        return f"https://t.me/{v}"
    return v


def format_social_links_lines(socials: dict) -> list[str]:
    if not isinstance(socials, dict):
        return []

    lines: list[str] = []
    ch = normalize_telegram_link(str(socials.get("telegramChannel") or socials.get("telegram_channel") or ""))
    gr = normalize_telegram_link(str(socials.get("telegramGroup") or socials.get("telegram_group") or ""))
    if ch:
        lines.append(f"📣 کانال تلگرام: {ch}")
    if gr:
        lines.append(f"👥 گروه تلگرام: {gr}")
    return lines


def build_feedback_intro_text(feedback_intro_text: str, socials: dict) -> str:
    lines = [feedback_intro_text]
    link_lines = format_social_links_lines(socials)
    if link_lines:
        lines.append("\nبرای دریافت جمع‌بندی‌ها می‌توانید از لینک‌های زیر استفاده کنید:")
        lines.extend(link_lines)
    return "\n".join(lines)


def build_feedback_confirmation_text(socials: dict) -> str:
    base = (
        "✅ نظر / دغدغه شما با موفقیت ثبت شد.\n"
        "این پیام‌ها بررسی و به نماینده منتقل می‌شوند.\n\n"
        "در صورت تمایل می‌توانید برای دریافت جمع‌بندی‌ها\n"
        "در کانال یا گروه اطلاع‌رسانی عضو شوید."
    ).strip()
    lines = [base]
    link_lines = format_social_links_lines(socials)
    if link_lines:
        lines.append("")
        lines.extend(link_lines)
    return "\n".join(lines)
