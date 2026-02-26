import asyncio
import html
import json
import re
from datetime import datetime, timezone
from typing import Any

import jdatetime
from telegram.error import NetworkError, TimedOut, RetryAfter


def normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def repair_suspicious_json_backslashes(text: str) -> str:
    """Heuristic repair for invalid JSON that commonly appears in Windows paths.

    Example: a string contains an unescaped backslash like "C:\\Users\\..." but is stored as "C:\\Users".
    Also handles invalid unicode escape prefixes like "\\uploads" which would otherwise be read as "\\u...".
    """
    if not text:
        return text
    # "\u" is valid only if followed by 4 hex digits.
    fixed = re.sub(r"\\u(?![0-9a-fA-F]{4})", r"\\\\u", text)
    # Any other backslash must start a valid JSON escape sequence.
    fixed = re.sub(r"\\(?![\"\\/bfnrtu])", r"\\\\", fixed)
    return fixed


def json_loads_loose(text: str) -> Any | None:
    """Parse JSON, attempting a best-effort repair when the input is almost-JSON.

    Returns None if parsing fails.
    """
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        try:
            return json.loads(repair_suspicious_json_backslashes(s))
        except Exception:
            return None


def normalize_button_text(value: str | None) -> str:
    v = normalize_text(value)
    # Strip common invisible/formatting characters that can appear in Telegram button labels
    # (bidi marks, zero-width chars, variation selectors). This keeps routing robust.
    for ch in (
        "\u200b",  # zero-width space
        "\u200c",  # ZWNJ
        "\u200d",  # ZWJ
        "\u200e",  # LRM
        "\u200f",  # RLM
        "\u2060",  # word joiner
        "\ufeff",  # BOM
        "\ufe0e",  # text variation selector
        "\ufe0f",  # emoji variation selector
        "\u2066",  # LRI
        "\u2067",  # RLI
        "\u2068",  # FSI
        "\u2069",  # PDI
        "\u202a",  # LRE
        "\u202b",  # RLE
        "\u202c",  # PDF
        "\u202d",  # LRO
        "\u202e",  # RLO
    ):
        v = v.replace(ch, "")
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


def format_public_feedback_answer_block(*, tag: str | None, feedback_text: str, answer: str, answered_at: datetime | None) -> str:
    t = normalize_text(tag)
    q = normalize_text(feedback_text)
    a = normalize_text(answer)
    date_line = to_jalali_date_ymd(answered_at)

    parts: list[str] = []
    if t:
        parts.append(f"🏷 {t}")
    parts.append(f"📝 {q}")
    parts.append("\n━━━━━━━━━━━━\n✅ پاسخ رسمی نماینده\n\n" + a)
    if date_line:
        parts.append(f"📅 {date_line}")
    return "\n\n".join([p for p in parts if p]).strip()


def _topic_base_and_label(topic: str) -> tuple[str, str]:
    t = normalize_text(topic)
    if not t:
        return "", ""
    if "|" in t:
        base, detail = t.split("|", 1)
        base = base.strip()
        detail = detail.strip()
        if detail:
            return base, detail
        return base, base
    return t, t


def _make_hashtag(text: str) -> str:
    t = normalize_text(text)
    if not t:
        return ""
    t = t.replace(" ", "_")
    t = re.sub(r"[^0-9A-Za-z_\u0600-\u06FF]", "", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return f"#{t}" if t else ""


def _topic_hashtags(topic: str) -> str:
    base, label = _topic_base_and_label(topic)
    tags: list[str] = []
    base_tag = _make_hashtag(base)
    if base_tag:
        tags.append(base_tag)
    # Add the custom label tag only if it's short and different.
    if label and label != base and len(label) <= 24:
        detail_tag = _make_hashtag(label)
        if detail_tag:
            tags.append(detail_tag)
    tags.append("#سؤال_از_نماینده")
    return " ".join([t for t in tags if t])


def format_public_question_answer_card_html(*, idx: int, topic: str, question: str, answer: str, answered_at: datetime | None) -> str:
    raw_topic = normalize_text(topic)
    base_topic, label_topic = _topic_base_and_label(raw_topic)
    display_topic = label_topic or base_topic or "سایر"

    q = normalize_text(question)
    a = normalize_text(answer)

    esc_q = html.escape(q)
    esc_a = html.escape(a)
    date_line = to_jalali_date_ymd(answered_at)
    num = to_fa_digits(str(idx))

    parts: list[str] = []
    parts.append(f"🟢 <b>{html.escape(display_topic)}</b>")
    parts.append("──────────────")
    parts.append(f"🧩 <b>پرسش {html.escape(num)}</b>")
    parts.append(f"«{esc_q}»")
    parts.append("")
    parts.append("✅ <b>پاسخ رسمی نماینده</b>")
    parts.append(esc_a)

    meta: list[str] = []
    tags = _topic_hashtags(raw_topic or display_topic)
    if tags:
        meta.append(f"🏷 <b>تگ‌ها:</b> {html.escape(tags)}")
    if date_line:
        meta.append(f"📅 <b>تاریخ پاسخ:</b> {html.escape(date_line)}")
    if meta:
        parts.append("")
        parts.extend(meta)

    return "\n".join([p for p in parts if p is not None]).strip()


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


async def send_question_answers_message_cards_html(*, safe_reply, update_message, items: list[dict], back_keyboard):
    # Render a richer, card-like HTML view (used for all topics).
    blocks: list[str] = []
    for idx, it in enumerate(items, start=1):
        topic = normalize_text(it.get("topic") or "")
        q = normalize_text(it.get("q") or "")
        a = normalize_text(it.get("a") or "")
        answered_at = it.get("answered_at")
        if q and a:
            blocks.append(
                format_public_question_answer_card_html(
                    idx=idx,
                    topic=topic,
                    question=q,
                    answer=a,
                    answered_at=answered_at if isinstance(answered_at, datetime) else None,
                )
            )

    if not blocks:
        await safe_reply(
            update_message,
            "فعلاً پاسخ عمومی ثبت نشده است.",
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
        await safe_reply(
            update_message,
            ch,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=rm,
        )


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
        lines.append(f"📣 <b>کانال تلگرام:</b> {html.escape(ch)}")
    if gr:
        lines.append(f"👥 <b>گروه تلگرام:</b> {html.escape(gr)}")
    return lines


def build_feedback_intro_text(feedback_intro_text: str, socials: dict) -> str:
    lines = [feedback_intro_text]
    link_lines = format_social_links_lines(socials)
    if link_lines:
        lines.append("")
        lines.append("🔗 <b>دریافت جمع‌بندی‌ها</b>")
        lines.append("برای دریافت جمع‌بندی‌ها می‌توانید از لینک‌های زیر استفاده کنید:")
        lines.extend(link_lines)
    return "\n".join(lines)


def build_feedback_confirmation_text(socials: dict) -> str:
    lines: list[str] = []
    lines.append("✅ <b>نظر / دغدغه شما ثبت شد</b>")
    lines.append("──────────────")
    lines.append("📨 پیام شما با موفقیت ثبت شد.")
    lines.append("🔎 این پیام‌ها بررسی و به نماینده منتقل می‌شوند.")
    lines.append("🙏 سپاس از همراهی شما.")

    link_lines = format_social_links_lines(socials)
    if link_lines:
        lines.append("")
        lines.append("🔗 <b>دریافت جمع‌بندی‌ها</b>")
        lines.append("در صورت تمایل می‌توانید در کانال یا گروه اطلاع‌رسانی عضو شوید:")
        lines.extend(link_lines)
    return "\n".join(lines)
