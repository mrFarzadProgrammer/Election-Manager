from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response as StarletteResponse
from starlette.types import Scope

import database
import models
from db_maintenance import ensure_indexes
from routers._common import APP_ENV
from routers import (
    admin as admin_router,
    admin_mvp as admin_mvp_router,
    announcements as announcements_router,
    auth as auth_router,
    candidate_mvp as candidate_mvp_router,
    candidates as candidates_router,
    misc as misc_router,
    monitoring as monitoring_router,
    plans as plans_router,
    tickets as tickets_router,
    uploads as uploads_router,
)


load_dotenv()

logger = logging.getLogger(__name__)


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _frontend_dist_dir() -> Path | None:
    raw = (os.getenv("FRONTEND_DIST_DIR") or "").strip()
    if raw:
        try:
            p = Path(raw).expanduser().resolve()
            return p if p.is_dir() else None
        except Exception:
            return None

    # Default: repo_root/frontend/dist
    try:
        repo_root = Path(__file__).resolve().parent.parent
        p = (repo_root / "frontend" / "dist").resolve()
        return p if p.is_dir() else None
    except Exception:
        return None


_FRONTEND_DIST_DIR = None
if _env_truthy("SERVE_FRONTEND") or APP_ENV in {"production", "prod"}:
    _FRONTEND_DIST_DIR = _frontend_dist_dir()

SERVE_FRONTEND = _FRONTEND_DIST_DIR is not None


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> StarletteResponse:
        response = await super().get_response(path, scope)
        if response.status_code != 404:
            return response

        # SPA fallback: unknown routes should serve index.html.
        # Keep API/static mounts untouched.
        try:
            request_path = (scope.get("path") or "").strip()
        except Exception:
            request_path = ""
        if request_path.startswith("/api") or request_path.startswith("/uploads"):
            return response

        return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application started")
    try:
        # Ensure tables exist (best-effort). For long-lived production, prefer Alembic migrations.
        models.Base.metadata.create_all(bind=database.engine)
    except Exception:
        logger.exception("DB create_all failed")
    try:
        ensure_indexes(database.engine)
    except Exception:
        # Best-effort: indexes are an optimization, not a boot blocker.
        pass
    yield
    logger.info("Application shutdown")


_enable_docs = True
if APP_ENV in {"production", "prod"} and not _env_truthy("ENABLE_DOCS"):
    _enable_docs = False

app = FastAPI(
    title="Election Manager",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=("/docs" if _enable_docs else None),
    redoc_url=("/redoc" if _enable_docs else None),
    openapi_url=("/openapi.json" if _enable_docs else None),
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = (request.headers.get("x-request-id") or "").strip() or uuid.uuid4().hex
    request.state.request_id = rid
    response = await call_next(request)
    if "x-request-id" not in response.headers:
        response.headers["X-Request-ID"] = rid
    return response


@app.middleware("http")
async def monitoring_error_logging_middleware(request: Request, call_next):
    """Minimal technical error logging (MVP)."""
    try:
        response = await call_next(request)
        if getattr(response, "status_code", 200) >= 500:
            try:
                rid = getattr(getattr(request, "state", None), "request_id", None)
                db = database.SessionLocal()
                db.add(
                    models.TechnicalErrorLog(
                        service_name="api",
                        error_type="HTTP_5XX",
                        error_message=f"[rid={rid}] {request.method} {request.url.path} -> {response.status_code}",
                        telegram_user_id=None,
                        candidate_id=None,
                        state=None,
                    )
                )
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        return response
    except Exception as e:
        try:
            rid = getattr(getattr(request, "state", None), "request_id", None)
            db = database.SessionLocal()
            db.add(
                models.TechnicalErrorLog(
                    service_name="api",
                    error_type=e.__class__.__name__,
                    error_message=f"[rid={rid}] {request.method} {request.url.path} :: {str(e)}"[:8000],
                    telegram_user_id=None,
                    candidate_id=None,
                    state=None,
                )
            )
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass
        raise


# Static mounts
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

UPLOAD_PRIVATE_DIR = "uploads_private"
os.makedirs(UPLOAD_PRIVATE_DIR, exist_ok=True)


# CORS
_cors_allow_origins: list[str]
_cors_allow_origin_regex: str | None

if APP_ENV in {"production", "prod"}:
    _cors_allow_origins = [o.strip() for o in (os.getenv("CORS_ALLOW_ORIGINS") or "").split(",") if o.strip()]
    _cors_allow_origin_regex = None
else:
    _cors_allow_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:5555",
        "http://127.0.0.1:5555",
    ]
    _extra_dev_origins = [
        o.strip() for o in (os.getenv("CORS_ALLOW_ORIGINS") or "").split(",") if o.strip()
    ]
    for _o in _extra_dev_origins:
        if _o not in _cors_allow_origins:
            _cors_allow_origins.append(_o)
    _cors_allow_origin_regex = r"^http://(localhost|127\\.0\\.0\\.1):5\\d{3}$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_origin_regex=_cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    if "x-content-type-options" not in response.headers:
        response.headers["X-Content-Type-Options"] = "nosniff"
    if "x-frame-options" not in response.headers:
        response.headers["X-Frame-Options"] = "DENY"
    if "referrer-policy" not in response.headers:
        response.headers["Referrer-Policy"] = "no-referrer"
    if "permissions-policy" not in response.headers:
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Extra hardening (mostly relevant in production / browsers)
    if "cross-origin-opener-policy" not in response.headers:
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if "cross-origin-resource-policy" not in response.headers:
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    if "x-permitted-cross-domain-policies" not in response.headers:
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

    # Only emit HSTS when we are effectively on HTTPS.
    try:
        is_https = (request.url.scheme == "https") if request.url else False
    except Exception:
        is_https = False

    # Behind reverse proxy, we may need to trust forwarded proto.
    try:
        if not is_https and _env_truthy("TRUST_PROXY"):
            xfproto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
            if xfproto == "https":
                is_https = True
    except Exception:
        pass
    if APP_ENV in {"production", "prod"} and (is_https or (os.getenv("FORCE_HTTPS") or "").strip() in {"1", "true", "yes", "on"}):
        if "strict-transport-security" not in response.headers:
            response.headers["Strict-Transport-Security"] = "max-age=15552000; includeSubDomains"

    # Add a safe CSP for non-doc endpoints (Swagger UI needs inline scripts/styles).
    try:
        path = request.url.path if request.url else ""
    except Exception:
        path = ""
    if (
        "content-security-policy" not in response.headers
        and not path.startswith("/docs")
        and not path.startswith("/redoc")
        and not path.startswith("/openapi.json")
    ):
        is_api_like = (
            path.startswith("/api")
            or path.startswith("/uploads")
        )
        if SERVE_FRONTEND and not is_api_like:
            # Frontend needs scripts/styles; keep it same-origin and deny framing.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response


@app.middleware("http")
async def csrf_cookie_middleware(request: Request, call_next):
    """CSRF protection for cookie-authenticated browser sessions."""
    try:
        method = (request.method or "").upper()
        if method in {"GET", "HEAD", "OPTIONS"}:
            return await call_next(request)

        path = request.url.path if request.url else ""
        if path.startswith("/api/auth/"):
            return await call_next(request)

        has_authz = bool((request.headers.get("authorization") or "").strip())
        has_cookie_session = bool((request.cookies.get("access_token") or "").strip())
        if has_authz or not has_cookie_session:
            return await call_next(request)

        csrf_cookie = (request.cookies.get("csrf_token") or "").strip()
        csrf_header = (request.headers.get("x-csrf-token") or "").strip()
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            return Response(
                content="{\"detail\":\"CSRF token missing/invalid\"}",
                status_code=403,
                media_type="application/json",
            )
    except Exception:
        return Response(
            content="{\"detail\":\"CSRF middleware error\"}",
            status_code=500,
            media_type="application/json",
        )

    return await call_next(request)


# Routers
app.include_router(auth_router.router)
app.include_router(uploads_router.router)
app.include_router(candidates_router.router)
app.include_router(plans_router.router)
app.include_router(tickets_router.router)
app.include_router(announcements_router.router)
app.include_router(candidate_mvp_router.router)
app.include_router(admin_router.router)
app.include_router(admin_mvp_router.router)
app.include_router(monitoring_router.router)
app.include_router(misc_router.router)


if SERVE_FRONTEND:
    # Mount AFTER API routes so /api keeps working.
    app.mount(
        "/",
        SpaStaticFiles(directory=str(_FRONTEND_DIST_DIR), html=True),
        name="frontend",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
