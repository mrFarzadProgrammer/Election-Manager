from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


FIELD_LABELS = {
    "username": "نام کاربری",
    "phone": "شماره تماس",
    "email": "ایمیل",
    "bot_name": "نام بات",
    "bot_token": "توکن بات",
}


def raise_duplicate_field(field: str):
    label = FIELD_LABELS.get(field, field)
    raise HTTPException(
        status_code=400,
        detail={
            "code": "DUPLICATE_FIELD",
            "field": field,
            "label": label,
            "message": f"«{label}» تکراری است. لطفاً مقدار دیگری وارد کنید.",
        },
    )


def parse_integrity_error_field(e: IntegrityError) -> Optional[str]:
    msg = str(getattr(e, "orig", e))
    msg_lower = msg.lower()

    if "unique constraint failed:" in msg_lower:
        tail = msg.split("UNIQUE constraint failed:", 1)[-1].strip()
        first_part = tail.split(",")[0].strip()
        field = first_part.split(".")[-1].strip() if "." in first_part else first_part
        return field if field else None

    return None


def raise_from_integrity_error(e: IntegrityError):
    field = parse_integrity_error_field(e)
    if field:
        raise_duplicate_field(field)

    raise HTTPException(
        status_code=400,
        detail={
            "code": "DUPLICATE_FIELD",
            "message": "یکی از فیلدها تکراری است. لطفاً مقادیر را تغییر دهید.",
        },
    )
