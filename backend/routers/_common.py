from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, Request, Response

import auth


# ---------------------------------------------------------------------------
# Runtime config (dev vs prod)
# ---------------------------------------------------------------------------

APP_ENV = (os.getenv("APP_ENV") or os.getenv("ENV") or "development").strip().lower()


def env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def client_ip(request: Request) -> str:
    # Behind reverse proxy, enable TRUST_PROXY=1 and ensure X-Forwarded-For is set.
    if env_truthy("TRUST_PROXY"):
        xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if xff:
            return xff
    try:
        return request.client.host if request.client else "unknown"
    except Exception:
        return "unknown"


# Very small in-memory rate limiter (per-process). Use Redis-based limiter for multi-worker production.
_RATE_LIMIT: dict[str, list[float]] = {}


def _rate_limit_backend() -> str:
    v = (os.getenv("RATE_LIMIT_BACKEND") or "").strip().lower()
    if v:
        return v
    # Safer default in production: shared limiter across processes on the same host.
    if APP_ENV in {"production", "prod"}:
        return "sqlite"
    return "memory"


def _rate_limit_sqlite_path() -> str:
    # Default to backend-local file so multi-worker setups share a limiter on the same host.
    p = (os.getenv("RATE_LIMIT_SQLITE_PATH") or "").strip()
    if p:
        return p
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.normpath(os.path.join(here, "..", "rate_limit.sqlite3"))


def _rate_limit_sqlite(request: Request, *, key: str, limit: int, window_seconds: int) -> None:
    now = datetime.now(timezone.utc).timestamp()
    bucket_key = f"{key}:{client_ip(request)}"
    cutoff = now - window_seconds

    path = _rate_limit_sqlite_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=2.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=2000;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_limit_events (
                bucket_key TEXT NOT NULL,
                ts REAL NOT NULL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_events_key_ts ON rate_limit_events(bucket_key, ts);")

        # Clean old
        conn.execute("DELETE FROM rate_limit_events WHERE bucket_key = ? AND ts < ?", (bucket_key, cutoff))
        cur = conn.execute(
            "SELECT COUNT(1) FROM rate_limit_events WHERE bucket_key = ? AND ts >= ?",
            (bucket_key, cutoff),
        )
        count = int(cur.fetchone()[0] or 0)
        if count >= limit:
            raise HTTPException(status_code=429, detail="تعداد درخواست‌ها زیاد است. لطفاً کمی بعد دوباره تلاش کنید.")

        conn.execute("INSERT INTO rate_limit_events(bucket_key, ts) VALUES(?, ?)", (bucket_key, now))
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def rate_limit(request: Request, *, key: str, limit: int, window_seconds: int) -> None:
    backend = _rate_limit_backend()
    if backend == "sqlite":
        return _rate_limit_sqlite(request, key=key, limit=limit, window_seconds=window_seconds)

    now = datetime.now(timezone.utc).timestamp()
    bucket_key = f"{key}:{client_ip(request)}"
    items = _RATE_LIMIT.get(bucket_key, [])
    cutoff = now - window_seconds
    items = [t for t in items if t >= cutoff]
    if len(items) >= limit:
        raise HTTPException(status_code=429, detail="تعداد درخواست‌ها زیاد است. لطفاً کمی بعد دوباره تلاش کنید.")
    items.append(now)
    _RATE_LIMIT[bucket_key] = items


def cookie_secure_flag() -> bool:
    # In production behind HTTPS (Cloudflare + reverse proxy), cookies should be Secure.
    if APP_ENV in {"production", "prod"}:
        return True
    return env_truthy("COOKIE_SECURE")


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str, csrf_token: str | None = None) -> None:
    secure = cookie_secure_flag()
    csrf = (csrf_token or uuid.uuid4().hex).strip()

    response.set_cookie(
        key="access_token",
        value=str(access_token),
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=str(refresh_token),
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/auth/refresh",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    response.set_cookie(
        key="csrf_token",
        value=str(csrf),
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def clear_auth_cookies(response: Response) -> None:
    secure = cookie_secure_flag()
    response.delete_cookie("access_token", path="/", secure=secure, samesite="lax")
    response.delete_cookie("refresh_token", path="/api/auth/refresh", secure=secure, samesite="lax")
    response.delete_cookie("csrf_token", path="/", secure=secure, samesite="lax")
