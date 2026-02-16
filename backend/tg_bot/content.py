import json
import os

from .text_utils import normalize_text


def _coerce_bot_config(candidate: dict) -> dict:
    raw = candidate.get("bot_config")
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


def candidate_constituency(candidate: dict) -> str:
    constituency = normalize_text(candidate.get("constituency"))
    if constituency:
        return constituency

    bot_config = _coerce_bot_config(candidate)
    constituency = normalize_text(bot_config.get("constituency"))
    if constituency:
        return constituency

    province = normalize_text(candidate.get("province"))
    city = normalize_text(candidate.get("city"))
    if province and city:
        return f"{province} - {city}"
    return province or city


def format_structured_resume(candidate: dict) -> str:
    bot_config = _coerce_bot_config(candidate)
    structured = bot_config.get("structured_resume")
    if isinstance(structured, dict):
        parts: list[str] = []
        title = normalize_text(structured.get("title"))
        if title:
            parts.append(title)

        highlights = structured.get("highlights")
        if isinstance(highlights, list) and highlights:
            items = [f"• {normalize_text(x)}" for x in highlights if normalize_text(x)]
            if items:
                parts.append("\n".join(items))

        def _as_lines(v) -> list[str]:
            if v is None:
                return []
            if isinstance(v, list):
                return [normalize_text(x) for x in v if normalize_text(x)]
            if isinstance(v, str):
                return [s.strip() for s in v.splitlines() if s.strip()]
            return [normalize_text(v)] if normalize_text(v) else []

        education_items = _as_lines(structured.get("education"))
        if education_items:
            parts.append("\nتحصیلات:\n" + "\n".join([f"• {x}" for x in education_items]))

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

    fallback = normalize_text(candidate.get("resume"))
    return fallback or "برای این بخش هنوز اطلاعاتی ثبت نشده است."


def get_program_answer(candidate: dict, index: int) -> str:
    bot_config = _coerce_bot_config(candidate)
    programs = bot_config.get("programs")
    if isinstance(programs, list) and 0 <= index < len(programs):
        ans = normalize_text(programs[index])
        return ans or "برای این سوال هنوز پاسخی ثبت نشده است."
    if isinstance(programs, dict):
        ans = normalize_text(programs.get(str(index + 1)) or programs.get(f"q{index + 1}"))
        return ans or "برای این سوال هنوز پاسخی ثبت نشده است."

    ideas = normalize_text(candidate.get("ideas"))
    return ideas or "برای این سوال هنوز پاسخی ثبت نشده است."


def file_ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()
