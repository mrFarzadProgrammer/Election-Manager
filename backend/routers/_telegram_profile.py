from __future__ import annotations

import mimetypes
import re

import httpx

import models


def _telegram_post_json(token: str, method: str, payload: dict) -> tuple[bool, str | None]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        with httpx.Client(timeout=20) as client:
            res = client.post(url, json=payload)
        data = res.json() if res.content else {}
        if res.status_code >= 400 or not data.get("ok"):
            desc = data.get("description") or f"HTTP {res.status_code}"
            return False, _humanize_telegram_error(str(desc))
        return True, None
    except Exception as e:
        return False, _humanize_telegram_error(str(e))


def _telegram_get_me(token: str) -> tuple[bool, str | None]:
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with httpx.Client(timeout=20) as client:
            res = client.get(url)
        data = res.json() if res.content else {}
        if res.status_code >= 400 or not data.get("ok"):
            desc = data.get("description") or f"HTTP {res.status_code}"
            if res.status_code == 404 and str(desc).strip() == "Not Found":
                return (
                    False,
                    "توکن بات نامعتبر است (Telegram: Not Found). لطفاً Bot Token را دقیق از BotFather کپی کنید.",
                )
            return False, _humanize_telegram_error(str(desc))
        return True, None
    except Exception as e:
        return False, _humanize_telegram_error(str(e))


def _telegram_get_json(token: str, method: str) -> tuple[bool, dict | None, str | None]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        with httpx.Client(timeout=20) as client:
            res = client.get(url)
        data = res.json() if res.content else {}
        if res.status_code >= 400 or not data.get("ok"):
            desc = data.get("description") or f"HTTP {res.status_code}"
            if res.status_code == 404 and str(desc).strip() == "Not Found":
                return False, None, "پاسخ تلگرام: Not Found (احتمالاً این متد برای این نسخه/اکانت پشتیبانی نمی‌شود)."
            return False, None, _humanize_telegram_error(str(desc))
        return True, data.get("result") if isinstance(data, dict) else None, None
    except Exception as e:
        return False, None, _humanize_telegram_error(str(e))


def _humanize_telegram_error(err: str) -> str:
    msg = (err or "").strip()
    if not msg:
        return "خطای نامشخص هنگام ارتباط با تلگرام"

    lower = msg.lower()

    if msg.strip() == "Not Found" or "telegram: not found" in lower:
        return "پاسخ تلگرام: Not Found (احتمالاً متد پشتیبانی نمی‌شود یا دسترسی شما به Bot API محدود است)."
    if "unexpected_eof_while_reading" in lower or "eof occurred in violation of protocol" in lower:
        return "اتصال امن (SSL) به تلگرام قطع شد. معمولاً به خاطر اینترنت/فیلترینگ/پروکسی یا آنتی‌ویروس است."
    if "certificate_verify_failed" in lower:
        return "اعتبارسنجی گواهی SSL تلگرام ناموفق بود (CERTIFICATE_VERIFY_FAILED). تاریخ/ساعت سیستم و تنظیمات پروکسی را بررسی کنید."
    if "timed out" in lower or "timeout" in lower:
        return "ارتباط با تلگرام timeout شد. اینترنت/فیلترشکن/پروکسی را بررسی کنید."

    return msg


_BOT_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")


def _looks_like_telegram_bot_token(token: str) -> bool:
    token = (token or "").strip()
    return bool(_BOT_TOKEN_RE.match(token))


def _guess_image_content_type(filename: str) -> str:
    ct, _ = mimetypes.guess_type(filename)
    return ct or "application/octet-stream"


def apply_telegram_profile_for_candidate(candidate: models.User) -> dict:
    result: dict = {"ok": True, "applied": {}, "errors": {}, "notes": {}, "requested": {}, "telegram": {}}

    token = (candidate.bot_token or "").strip()
    if not token:
        result["ok"] = False
        result["errors"]["token"] = "توکن بات تنظیم نشده است."
        return result

    if not _looks_like_telegram_bot_token(token):
        result["ok"] = False
        result["errors"]["token"] = "فرمت توکن بات نامعتبر است. نمونه صحیح: 123456789:AA... (از BotFather کپی کنید)."
        return result

    ok, err = _telegram_get_me(token)
    result["applied"]["getMe"] = ok
    if not ok:
        result["ok"] = False
        result["errors"]["token"] = err or "بررسی توکن بات در تلگرام ناموفق بود"
        return result

    if candidate.bot_name and isinstance(candidate.bot_name, str) and candidate.bot_name.strip():
        result["requested"]["name"] = candidate.bot_name.strip()
        ok, err = _telegram_post_json(token, "setMyName", {"name": candidate.bot_name.strip()})
        result["applied"]["name"] = ok
        if not ok:
            result["ok"] = False
            result["errors"]["name"] = err

    bot_config = candidate.bot_config or {}
    telegram_profile: dict = {}
    if isinstance(bot_config, dict):
        telegram_profile = bot_config.get("telegram_profile") or bot_config.get("telegramProfile") or {}

    if isinstance(telegram_profile, dict):
        desc = telegram_profile.get("description")
        if isinstance(desc, str):
            result["requested"]["description"] = desc
            ok, err = _telegram_post_json(token, "setMyDescription", {"description": desc})
            result["applied"]["description"] = ok
            if not ok:
                result["ok"] = False
                result["errors"]["description"] = err

        short_desc = telegram_profile.get("short_description") or telegram_profile.get("shortDescription")
        if isinstance(short_desc, str):
            result["requested"]["short_description"] = short_desc
            ok, err = _telegram_post_json(token, "setMyShortDescription", {"short_description": short_desc})
            result["applied"]["short_description"] = ok
            if not ok:
                result["ok"] = False
                result["errors"]["short_description"] = err

    image_url = candidate.image_url
    if isinstance(image_url, str) and image_url.strip():
        result["applied"]["photo"] = False
        result["notes"]["photo"] = (
            "تغییر عکس پروفایل بات از طریق Telegram Bot API پشتیبانی نمی‌شود. "
            "برای تغییر آواتار، باید دستی از طریق BotFather انجام دهید (مثلاً دستور /setuserpic)."
        )

    ok_name, res_name, _ = _telegram_get_json(token, "getMyName")
    if ok_name and isinstance(res_name, dict) and isinstance(res_name.get("name"), str):
        result["telegram"]["name"] = res_name.get("name")

    ok_desc, res_desc, _ = _telegram_get_json(token, "getMyDescription")
    if ok_desc and isinstance(res_desc, dict) and isinstance(res_desc.get("description"), str):
        result["telegram"]["description"] = res_desc.get("description")

    ok_sdesc, res_sdesc, _ = _telegram_get_json(token, "getMyShortDescription")
    if ok_sdesc and isinstance(res_sdesc, dict) and isinstance(res_sdesc.get("short_description"), str):
        result["telegram"]["short_description"] = res_sdesc.get("short_description")

    return result
