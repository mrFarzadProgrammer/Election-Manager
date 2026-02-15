from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random
import statistics
import string
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Literal

import httpx


def _now_ms() -> int:
    return int(time.time() * 1000)


def _rand_slug(prefix: str) -> str:
    tail = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return f"{prefix}-{_now_ms()}-{tail}"


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


@dataclass(frozen=True)
class LoadStep:
    concurrency: int
    total: int


@dataclass
class StepResult:
    ok_2xx: int
    total: int
    elapsed_s: float
    rps: float
    status_counts: dict[str, int]
    errors: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float


@dataclass
class EndpointResult:
    method: str
    path: str
    role: str
    steps: list[dict[str, Any]]
    best: dict[str, Any] | None
    notes: list[str]


Role = Literal["none", "admin", "candidate"]


def _role_for_path(path: str, method: str) -> Role:
    if path.startswith("/api/admin/"):
        return "admin"
    if path.startswith("/api/candidates/me/"):
        return "candidate"
    if path.startswith("/api/tickets"):
        if method == "PUT" and path.endswith("/status"):
            return "admin"
        return "candidate"
    if path.startswith("/api/upload") or path.startswith("/api/uploads/"):
        return "candidate"
    if path.startswith("/api/candidates"):
        # candidate can read its own via this endpoint; admin can read too.
        if method in {"POST", "PUT", "DELETE"}:
            return "admin"
        return "candidate"
    if path.startswith("/api/plans"):
        if method == "GET":
            return "none"
        return "admin"
    if path.startswith("/api/announcements"):
        if method == "GET":
            return "none"
        return "admin"
    if path.startswith("/api/auth/"):
        if path == "/api/auth/me":
            return "candidate"
        return "none"
    return "none"


def _is_write_method(method: str) -> bool:
    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}


async def _login(client: httpx.AsyncClient, base_url: str, username: str, password: str) -> str:
    r = await client.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=20.0,
    )
    r.raise_for_status()
    data = r.json()
    token = (data.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("login returned no access_token")
    return token


async def _try_login(client: httpx.AsyncClient, base_url: str, username: str, password: str) -> str | None:
    try:
        return await _login(client, base_url, username, password)
    except Exception:
        return None


async def _ensure_candidate_tokens(
    client: httpx.AsyncClient,
    base_url: str,
    *,
    admin_token: str,
    preferred_username: str,
    preferred_password: str,
) -> tuple[str, str, str]:
    """Return (username, access_token, refresh_token).

    Tries to login using provided credentials; if that fails (e.g. the user was deleted
    by a previous destructive test run), auto-registers a fresh candidate user.
    """

    token = await _try_login(client, base_url, preferred_username, preferred_password)
    if token:
        # Fetch refresh token via login (register may not have been used)
        refresh_resp = await client.post(
            f"{base_url}/api/auth/login",
            json={"username": preferred_username, "password": preferred_password},
            timeout=20.0,
        )
        refresh_resp.raise_for_status()
        refresh_token = (refresh_resp.json().get("refresh_token") or "").strip()
        if not refresh_token:
            raise RuntimeError("login returned no refresh_token")
        return preferred_username, token, refresh_token

    # Auto-create a new candidate via admin API (not rate-limited), then login.
    username = _rand_slug("cand")
    password = "123456"
    body = {
        "name": "LoadTest Candidate",
        "username": username,
        "password": password,
        "phone": None,
        "bot_name": f"{username}_bot",
        "bot_token": f"TOKEN_{username}",
    }
    r = await client.post(
        f"{base_url}/api/candidates",
        headers=_auth_headers(admin_token),
        json=body,
        timeout=20.0,
    )
    r.raise_for_status()

    access = await _login(client, base_url, username, password)
    refresh_resp = await client.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=20.0,
    )
    refresh_resp.raise_for_status()
    refresh = (refresh_resp.json().get("refresh_token") or "").strip()
    if not refresh:
        raise RuntimeError("login returned no refresh_token")
    return username, access, refresh


def _auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


async def _seed_submissions_sqlalchemy(database_url: str, candidate_username: str) -> dict[str, int]:
    """Seed BotSubmission rows directly, because there is no public API to create them.

    Returns ids used for update endpoints.
    """

    os.environ["DATABASE_URL"] = database_url

    import database as dbmod  # local import on purpose
    import models

    db = dbmod.SessionLocal()
    try:
        candidate = (
            db.query(models.User)
            .filter(models.User.username == candidate_username, models.User.role == "CANDIDATE")
            .first()
        )
        if candidate is None:
            raise RuntimeError(f"candidate user not found for seeding: {candidate_username}")

        # Create a FEEDBACK
        feedback = models.BotSubmission(
            candidate_id=int(candidate.id),
            telegram_user_id="seed_user_1",
            telegram_username="seed",
            type="FEEDBACK",
            text="Seed feedback",
            status="NEW",
            created_at=datetime.now(UTC),
            tag=None,
        )

        # Create QUESTIONS (unanswered). We need at least two so answer/reject tests don't conflict.
        question_answer = models.BotSubmission(
            candidate_id=int(candidate.id),
            telegram_user_id="seed_user_2",
            telegram_username="seed",
            type="QUESTION",
            text="Seed question (answer)",
            status="NEW",
            created_at=datetime.now(UTC),
            topic="عمومی",
        )

        question_reject = models.BotSubmission(
            candidate_id=int(candidate.id),
            telegram_user_id="seed_user_4",
            telegram_username="seed",
            type="QUESTION",
            text="Seed question (reject)",
            status="NEW",
            created_at=datetime.now(UTC),
            topic="عمومی",
        )

        # Create a BOT_REQUEST
        botreq = models.BotSubmission(
            candidate_id=int(candidate.id),
            telegram_user_id="seed_user_3",
            telegram_username="seed",
            type="BOT_REQUEST",
            text="Seed bot request",
            status="NEW",
            created_at=datetime.now(UTC),
            requester_full_name="Seed Requester",
            requester_contact="09120000000",
        )

        db.add_all([feedback, question_answer, question_reject, botreq])
        db.commit()
        db.refresh(feedback)
        db.refresh(question_answer)
        db.refresh(question_reject)
        db.refresh(botreq)

        return {
            "feedback_id": int(feedback.id),
            "question_id_answer": int(question_answer.id),
            "question_id_reject": int(question_reject.id),
            "bot_request_id": int(botreq.id),
            "candidate_id": int(candidate.id),
        }
    finally:
        try:
            db.close()
        except Exception:
            pass


async def _create_test_ticket(client: httpx.AsyncClient, base_url: str, token: str) -> int:
    r = await client.post(
        f"{base_url}/api/tickets",
        headers=_auth_headers(token),
        json={"subject": "LoadTest", "message": "Hello"},
        timeout=20.0,
    )
    r.raise_for_status()
    return int(r.json().get("id"))


async def _create_test_candidate(client: httpx.AsyncClient, base_url: str, admin_token: str) -> int:
    u = _rand_slug("victim")
    body = {
        "name": "Victim User",
        "username": u,
        "password": "123456",
        "phone": None,
        "bot_name": f"{u}_bot",
        "bot_token": f"TOKEN_{u}",
        "city": "تهران",
        "province": "تهران",
    }
    r = await client.post(
        f"{base_url}/api/candidates",
        headers=_auth_headers(admin_token),
        json=body,
        timeout=20.0,
    )
    r.raise_for_status()
    return int(r.json().get("id"))


async def _create_test_plan(client: httpx.AsyncClient, base_url: str, token: str) -> int:
    body = {
        "title": _rand_slug("plan"),
        "price": "123",
        "description": "load test",
        "features": ["a", "b"],
        "color": "#3b82f6",
        "is_visible": True,
    }
    r = await client.post(
        f"{base_url}/api/plans",
        headers=_auth_headers(token),
        json=body,
        timeout=20.0,
    )
    r.raise_for_status()
    return int(r.json().get("id"))


async def _create_test_plan_for_delete(client: httpx.AsyncClient, base_url: str, token: str) -> int:
    # Create a separate plan so DELETE doesn't break PUT tests (method ordering is DELETE before PUT).
    return await _create_test_plan(client, base_url, token)


async def _create_private_upload(client: httpx.AsyncClient, base_url: str, token: str) -> str:
    content = b"hello" * 50
    files = {"file": ("hello.txt", content, "text/plain")}
    data = {"visibility": "private", "candidate_name": "LoadTest"}
    r = await client.post(
        f"{base_url}/api/upload",
        headers=_auth_headers(token),
        data=data,
        files=files,
        timeout=60.0,
    )
    r.raise_for_status()
    payload = r.json()
    asset_id = payload.get("id")
    if not asset_id:
        raise RuntimeError("private upload did not return id")
    return str(asset_id)


async def _ensure_commitment_flow(client: httpx.AsyncClient, base_url: str, token: str) -> int:
    # Accept terms
    r = await client.post(
        f"{base_url}/api/candidates/me/commitments/terms/accept",
        headers=_auth_headers(token),
        timeout=20.0,
    )
    r.raise_for_status()

    # Create draft
    r = await client.post(
        f"{base_url}/api/candidates/me/commitments",
        headers=_auth_headers(token),
        json={
            "title": "LoadTest commitment",
            "description": "desc",
            "category": "other",
        },
        timeout=20.0,
    )
    r.raise_for_status()
    commitment_id = int(r.json().get("id"))

    # Publish
    r = await client.post(
        f"{base_url}/api/candidates/me/commitments/{commitment_id}/publish",
        headers=_auth_headers(token),
        timeout=20.0,
    )
    r.raise_for_status()

    return commitment_id


async def _create_draft_commitment(client: httpx.AsyncClient, base_url: str, token: str) -> int:
    # Accept terms (idempotent)
    r = await client.post(
        f"{base_url}/api/candidates/me/commitments/terms/accept",
        headers=_auth_headers(token),
        timeout=20.0,
    )
    r.raise_for_status()

    r = await client.post(
        f"{base_url}/api/candidates/me/commitments",
        headers=_auth_headers(token),
        json={
            "title": _rand_slug("draft"),
            "description": "draft",
            "category": "other",
        },
        timeout=20.0,
    )
    r.raise_for_status()
    return int(r.json().get("id"))


async def _run_load(
    client: httpx.AsyncClient,
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    make_kwargs: Callable[[], dict[str, Any]],
    total: int,
    concurrency: int,
    timeout_s: float,
) -> StepResult:
    total = max(1, int(total))
    concurrency = max(1, int(concurrency))

    latencies: list[float] = []
    status_counts: dict[str, int] = {}
    errors = 0

    counter = 0
    counter_lock = asyncio.Lock()

    async def worker() -> None:
        nonlocal counter, errors
        while True:
            async with counter_lock:
                if counter >= total:
                    return
                counter += 1

            kwargs = make_kwargs() or {}
            t0 = time.perf_counter()
            try:
                resp = await client.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout_s,
                    **kwargs,
                )
                dt = time.perf_counter() - t0
                latencies.append(dt)
                key = str(int(resp.status_code))
                status_counts[key] = status_counts.get(key, 0) + 1
                try:
                    await resp.aclose()
                except Exception:
                    pass
            except Exception:
                dt = time.perf_counter() - t0
                latencies.append(dt)
                errors += 1
                status_counts["ERR"] = status_counts.get("ERR", 0) + 1

    t0 = time.perf_counter()
    await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(concurrency)])
    elapsed = time.perf_counter() - t0

    lat_sorted = sorted(latencies)
    ok_2xx = sum(v for k, v in status_counts.items() if k.startswith("2"))

    def ms(x: float) -> float:
        return float(x) * 1000.0

    rps = (total / elapsed) if elapsed > 0 else float("inf")
    return StepResult(
        ok_2xx=ok_2xx,
        total=total,
        elapsed_s=float(elapsed),
        rps=float(rps),
        status_counts=dict(sorted(status_counts.items(), key=lambda kv: kv[0])),
        errors=int(errors),
        p50_ms=ms(_percentile(lat_sorted, 50)),
        p95_ms=ms(_percentile(lat_sorted, 95)),
        p99_ms=ms(_percentile(lat_sorted, 99)),
        mean_ms=ms(statistics.mean(latencies) if latencies else float("nan")),
    )


def _default_steps_for(method: str, path: str, mode: str) -> list[LoadStep]:
    method = method.upper()
    is_write = _is_write_method(method)

    if mode == "quick":
        if method == "GET" and path == "/api/admin/mvp/overview":
            return [LoadStep(1, 10), LoadStep(2, 20), LoadStep(5, 50)]
        if path in {"/health", "/"}:
            return [LoadStep(20, 200), LoadStep(50, 500)]
        if is_write:
            return [LoadStep(1, 30), LoadStep(3, 90), LoadStep(5, 150), LoadStep(10, 300)]
        return [LoadStep(5, 200), LoadStep(10, 300), LoadStep(25, 600), LoadStep(50, 800)]

    # full
    if path in {"/health", "/"}:
        return [LoadStep(50, 1000), LoadStep(200, 5000), LoadStep(500, 10000)]
    if is_write:
        return [LoadStep(1, 200), LoadStep(5, 800), LoadStep(10, 1600), LoadStep(25, 2000)]
    return [LoadStep(10, 1000), LoadStep(50, 2000), LoadStep(100, 4000), LoadStep(200, 6000), LoadStep(400, 8000)]


def _pass_threshold(step: StepResult, *, allow_429: bool = False) -> bool:
    # OK if >=99% 2xx; or for rate-limited endpoints OK if 2xx + 429 dominate.
    success_ratio = step.ok_2xx / step.total if step.total else 0.0

    if allow_429:
        allowed = step.status_counts.get("429", 0) + step.ok_2xx
        allowed_ratio = allowed / step.total if step.total else 0.0
        if allowed_ratio < 0.99:
            return False
        # latency threshold is relaxed for auth
        return step.p95_ms <= 3000.0

    if success_ratio < 0.99:
        return False
    if step.errors > 0:
        return False
    # a simple latency guard
    return step.p95_ms <= 2000.0


def _make_endpoint_kwargs_builder(
    method: str,
    path: str,
    ctx: dict[str, Any],
) -> tuple[str, Callable[[], dict[str, Any]], list[str]]:
    """Returns resolved_path, make_kwargs() and notes."""

    notes: list[str] = []
    resolved = path

    # Path params (use separate resources per method to avoid destructive endpoint side-effects)
    if "{candidate_id}" in resolved:
        if path == "/api/candidates/{candidate_id}" and method.upper() == "GET":
            resolved = resolved.replace("{candidate_id}", str(ctx["candidate_id_self"]))
        elif path == "/api/candidates/{candidate_id}" and method.upper() == "DELETE":
            resolved = resolved.replace("{candidate_id}", str(ctx["candidate_id_delete"]))
        else:
            resolved = resolved.replace("{candidate_id}", str(ctx["candidate_id_update"]))

    if "{plan_id}" in resolved:
        if method.upper() == "DELETE":
            resolved = resolved.replace("{plan_id}", str(ctx["plan_id_delete"]))
        else:
            resolved = resolved.replace("{plan_id}", str(ctx["plan_id_update"]))
    if "{ticket_id}" in resolved:
        resolved = resolved.replace("{ticket_id}", str(ctx["ticket_id"]))
    if "{asset_id}" in resolved:
        resolved = resolved.replace("{asset_id}", str(ctx["asset_id"]))
    if "{submission_id}" in resolved:
        # disambiguate by path
        if "/feedback/" in resolved:
            resolved = resolved.replace("{submission_id}", str(ctx["feedback_id"]))
        elif "/questions/" in resolved:
            if resolved.endswith("/answer"):
                resolved = resolved.replace("{submission_id}", str(ctx["question_id_answer"]))
            elif resolved.endswith("/reject"):
                resolved = resolved.replace("{submission_id}", str(ctx["question_id_reject"]))
            else:
                # meta/list endpoints can use either
                resolved = resolved.replace("{submission_id}", str(ctx["question_id_reject"]))
        elif "/bot-requests/" in resolved:
            resolved = resolved.replace("{submission_id}", str(ctx["bot_request_id"]))
        else:
            resolved = resolved.replace("{submission_id}", str(ctx["feedback_id"]))

    if "{commitment_id}" in resolved:
        if path.endswith("/publish"):
            resolved = resolved.replace("{commitment_id}", str(ctx["commitment_id_publish"]))
        elif path == "/api/candidates/me/commitments/{commitment_id}" and method.upper() == "PUT":
            resolved = resolved.replace("{commitment_id}", str(ctx["commitment_id_update"]))
        elif path == "/api/candidates/me/commitments/{commitment_id}" and method.upper() == "DELETE":
            resolved = resolved.replace("{commitment_id}", str(ctx["commitment_id_delete"]))
        else:
            resolved = resolved.replace("{commitment_id}", str(ctx["commitment_id_published"]))

    method = method.upper()

    # Body factories
    def empty_kwargs() -> dict[str, Any]:
        return {}

    if method == "POST" and path == "/api/auth/register":
        notes.append("rate_limited")

        def kwargs() -> dict[str, Any]:
            u = _rand_slug("u")
            return {
                "json": {
                    "username": u,
                    "password": "passw0rd-123",
                    "email": f"{u}@example.com",
                    "full_name": "Load Test",
                }
            }

        return resolved, kwargs, notes

    if method == "POST" and path == "/api/auth/login":
        notes.append("rate_limited")

        def kwargs() -> dict[str, Any]:
            # Use candidate login; avoid hammering admin
            return {"json": {"username": ctx["candidate_username"], "password": ctx["candidate_password"]}}

        return resolved, kwargs, notes

    if method == "POST" and path == "/api/auth/refresh":
        notes.append("rate_limited")

        def kwargs() -> dict[str, Any]:
            return {"json": {"refresh_token": ctx["refresh_token"]}}

        return resolved, kwargs, notes

    if method == "POST" and path == "/api/plans":
        def kwargs() -> dict[str, Any]:
            return {
                "json": {
                    "title": _rand_slug("plan"),
                    "price": "1",
                    "description": "load",
                    "features": ["x"],
                    "color": "#3b82f6",
                    "is_visible": True,
                }
            }

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "PUT" and path.startswith("/api/plans/"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"description": "updated"}}

        return resolved, kwargs, notes

    if method == "DELETE" and path.startswith("/api/plans/"):
        notes.append("one_time_semantics")
        notes.append("write_heavy")
        return resolved, empty_kwargs, notes

    if method == "POST" and path == "/api/candidates":
        def kwargs() -> dict[str, Any]:
            u = _rand_slug("cand")
            return {
                "json": {
                    "name": "LoadTest User",
                    "username": u,
                    "password": "123456",
                    "phone": None,
                    "bot_name": f"{u}_bot",
                    "bot_token": f"TOKEN_{u}",
                }
            }

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "PUT" and path == "/api/candidates/{candidate_id}":
        def kwargs() -> dict[str, Any]:
            return {"json": {"name": "Updated", "city": "تهران"}}

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "DELETE" and path == "/api/candidates/{candidate_id}":
        notes.append("one_time_semantics")
        notes.append("write_heavy")
        return resolved, empty_kwargs, notes

    if method == "POST" and path == "/api/tickets":
        def kwargs() -> dict[str, Any]:
            return {"json": {"subject": "LoadTest", "message": "Hello"}}

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "POST" and "/api/tickets/" in path and path.endswith("/messages"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"text": "hi", "sender_role": "USER"}}

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "PUT" and "/api/tickets/" in path and path.endswith("/status"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"status": "CLOSED"}}

        return resolved, kwargs, notes

    if method == "POST" and path == "/api/announcements":
        def kwargs() -> dict[str, Any]:
            return {"json": {"title": _rand_slug("ann"), "content": "hello"}}

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "POST" and path == "/api/upload":
        notes.append("io_heavy")

        def kwargs() -> dict[str, Any]:
            content = b"a" * 1024
            return {
                "data": {"visibility": "public", "candidate_name": "LoadTest"},
                "files": {"file": ("a.txt", content, "text/plain")},
            }

        return resolved, kwargs, notes

    if method == "POST" and path == "/api/upload/voice-intro":
        notes.append("io_heavy")

        def kwargs() -> dict[str, Any]:
            # Not a real mp3, but has .mp3 extension and audio/mpeg content-type.
            content = b"ID3" + (b"\x00" * 1000)
            return {
                "data": {"candidate_name": "LoadTest"},
                "files": {"file": ("v.mp3", content, "audio/mpeg")},
            }

        return resolved, kwargs, notes

    if method == "PUT" and "/api/candidates/me/feedback/" in path:
        def kwargs() -> dict[str, Any]:
            return {"json": {"status": "REVIEWED", "tag": "test"}}

        return resolved, kwargs, notes

    if method == "PUT" and path.endswith("/answer"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"answer_text": "ok", "topic": "عمومی", "is_featured": False}}

        notes.append("one_time_semantics")
        return resolved, kwargs, notes

    if method == "PUT" and path.endswith("/meta"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"topic": "عمومی", "is_featured": False}}

        return resolved, kwargs, notes

    if method == "PUT" and path.endswith("/reject"):
        def kwargs() -> dict[str, Any]:
            return {"json": {}}

        notes.append("one_time_semantics")
        return resolved, kwargs, notes

    if method == "POST" and path == "/api/candidates/me/commitments":
        def kwargs() -> dict[str, Any]:
            return {
                "json": {
                    "title": _rand_slug("c"),
                    "description": "desc",
                    "category": "other",
                }
            }

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "PUT" and path == "/api/candidates/me/commitments/{commitment_id}":
        def kwargs() -> dict[str, Any]:
            return {"json": {"title": "Updated", "description": "Updated"}}

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "DELETE" and path == "/api/candidates/me/commitments/{commitment_id}":
        notes.append("one_time_semantics")
        notes.append("write_heavy")
        return resolved, empty_kwargs, notes

    if method == "POST" and path.endswith("/publish") and "/api/candidates/me/commitments/" in path:
        notes.append("one_time_semantics")
        notes.append("write_heavy")
        return resolved, empty_kwargs, notes

    if method == "POST" and path.endswith("/progress"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"note": "progress"}}

        return resolved, kwargs, notes

    if method == "POST" and path.endswith("/status") and "/commitments/" in path:
        def kwargs() -> dict[str, Any]:
            return {"json": {"status": "in_progress"}}

        return resolved, kwargs, notes

    if method == "PUT" and path.startswith("/api/admin/bot-requests/"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"status": "REVIEWED"}}

        return resolved, kwargs, notes

    if method == "POST" and path.endswith("/reset-password"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"password": "newpass-123"}}

        notes.append("write_heavy")
        return resolved, kwargs, notes

    if method == "POST" and path.endswith("/assign-plan"):
        def kwargs() -> dict[str, Any]:
            return {"json": {"plan_id": int(ctx["plan_id_update"]), "duration_days": 30}}

        notes.append("write_heavy")
        return resolved, kwargs, notes

    # Default: no body
    return resolved, empty_kwargs, notes


async def main() -> int:
    parser = argparse.ArgumentParser(description="Comprehensive per-endpoint load test suite")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--openapi", default=None, help="Override OpenAPI URL (default: {base-url}/openapi.json)")
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json-out", default="_tmp_exports/loadtest_report.json")
    parser.add_argument("--only", default=None, help="Only run endpoints whose path contains this string")

    parser.add_argument("--admin-user", default="admin")
    parser.add_argument("--admin-pass", default="admin123")
    parser.add_argument("--candidate-user", default="candidate_1")
    parser.add_argument("--candidate-pass", default="123456")

    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Database URL used for direct seeding of bot_submissions (must match the running server)",
    )

    args = parser.parse_args()

    base_url: str = str(args.base_url).rstrip("/")
    openapi_url = str(args.openapi or f"{base_url}/openapi.json")
    timeout_s = float(args.timeout)
    mode = str(args.mode)
    json_out = str(args.json_out)
    only = (str(args.only).strip() if args.only is not None else "")

    database_url = (str(args.database_url) or "").strip()
    if not database_url:
        raise SystemExit("--database-url is required (must match server DATABASE_URL)")

    setup_limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
    async with httpx.AsyncClient(limits=setup_limits, http2=False, trust_env=False) as client:
        # Auth
        admin_token = await _login(client, base_url, str(args.admin_user), str(args.admin_pass))
        candidate_username, cand_token, refresh_token = await _ensure_candidate_tokens(
            client,
            base_url,
            admin_token=admin_token,
            preferred_username=str(args.candidate_user),
            preferred_password=str(args.candidate_pass),
        )

        # Seed submissions (feedback/question/bot_request)
        seeded = await _seed_submissions_sqlalchemy(database_url, candidate_username)

        # Setup IDs for path params
        ticket_id = await _create_test_ticket(client, base_url, cand_token)
        plan_id_update = await _create_test_plan(client, base_url, admin_token)
        plan_id_delete = await _create_test_plan_for_delete(client, base_url, admin_token)
        asset_id = await _create_private_upload(client, base_url, cand_token)

        # Commitments: keep a published one for read-only endpoints and a draft one for update/delete/publish.
        commitment_id_published = await _ensure_commitment_flow(client, base_url, cand_token)
        commitment_id_update = await _create_draft_commitment(client, base_url, cand_token)
        commitment_id_delete = await _create_draft_commitment(client, base_url, cand_token)
        commitment_id_publish = await _create_draft_commitment(client, base_url, cand_token)

        # Victim candidates used for admin endpoints to prevent deleting the active candidate user.
        candidate_id_update = await _create_test_candidate(client, base_url, admin_token)
        candidate_id_delete = await _create_test_candidate(client, base_url, admin_token)

        ctx: dict[str, Any] = {
            **seeded,
            "ticket_id": int(ticket_id),
            "plan_id_update": int(plan_id_update),
            "plan_id_delete": int(plan_id_delete),
            "asset_id": str(asset_id),
            "commitment_id_published": int(commitment_id_published),
            "commitment_id_update": int(commitment_id_update),
            "commitment_id_delete": int(commitment_id_delete),
            "commitment_id_publish": int(commitment_id_publish),
            "candidate_id_self": int(seeded["candidate_id"]),
            "candidate_id_update": int(candidate_id_update),
            "candidate_id_delete": int(candidate_id_delete),
            "candidate_username": candidate_username,
            "candidate_password": str(args.candidate_pass) if candidate_username == str(args.candidate_user) else "123456",
            "refresh_token": refresh_token,
        }

        # Fetch OpenAPI
        openapi = (await client.get(openapi_url, timeout=20.0)).json()
        paths = openapi.get("paths", {})

        operations: list[tuple[str, str]] = []
        for path, methods in paths.items():
            for m in methods.keys():
                if m.lower() in {"get", "post", "put", "delete", "patch"}:
                    if only and only not in path:
                        continue
                    operations.append((m.upper(), path))
        operations.sort(key=lambda x: (x[1], x[0]))

        async def health_check() -> bool:
            # Under load the server may be temporarily slow; retry a few times
            # and only treat it as failed if it consistently cannot respond.
            for _ in range(3):
                try:
                    r = await client.get(f"{base_url}/health", timeout=5.0)
                    if r.status_code == 200:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(0.25)
            return False

        results: list[EndpointResult] = []

        for method, path in operations:
            if not await health_check():
                raise SystemExit("Server health-check failed during test run (server crashed or is overloaded)")

            # Give the server a small breather between endpoints.
            await asyncio.sleep(0.2)

            role = _role_for_path(path, method)
            token = None
            if role == "admin":
                token = admin_token
            elif role == "candidate":
                token = cand_token

            headers = {**_auth_headers(token)}

            resolved_path, make_kwargs, notes = _make_endpoint_kwargs_builder(method, path, ctx)
            url = f"{base_url}{resolved_path}"

            # If endpoint is known to have one-time semantics (e.g., answering a question), keep it very light.
            is_one_time = "one_time_semantics" in notes
            allow_429 = "rate_limited" in notes

            steps = _default_steps_for(method, path, mode)
            if is_one_time:
                steps = [LoadStep(1, 1)]

            endpoint_steps: list[dict[str, Any]] = []
            best: dict[str, Any] | None = None

            for step in steps:
                # Avoid blasting file upload endpoints too hard in quick mode
                if "io_heavy" in notes and step.concurrency > 20:
                    continue

                step_limits = httpx.Limits(
                    max_connections=max(1, int(step.concurrency)),
                    max_keepalive_connections=max(1, int(step.concurrency)),
                )

                async with httpx.AsyncClient(limits=step_limits, http2=False, trust_env=False) as step_client:
                    step_result = await _run_load(
                        step_client,
                        method=method,
                        url=url,
                        headers=headers,
                        make_kwargs=make_kwargs,
                        total=step.total,
                        concurrency=step.concurrency,
                        timeout_s=timeout_s,
                    )

                # Cool-down between steps to reduce tail latency spillover.
                await asyncio.sleep(0.15)

                row = {
                    "concurrency": step.concurrency,
                    "total": step.total,
                    "ok_2xx": step_result.ok_2xx,
                    "elapsed_s": round(step_result.elapsed_s, 3),
                    "rps": round(step_result.rps, 1),
                    "p50_ms": round(step_result.p50_ms, 2),
                    "p95_ms": round(step_result.p95_ms, 2),
                    "p99_ms": round(step_result.p99_ms, 2),
                    "mean_ms": round(step_result.mean_ms, 2),
                    "errors": step_result.errors,
                    "status_counts": step_result.status_counts,
                    "pass": _pass_threshold(step_result, allow_429=allow_429),
                }
                endpoint_steps.append(row)

                if row["pass"]:
                    best = row
                else:
                    # stop at first failure for speed
                    break

            results.append(
                EndpointResult(method=method, path=path, role=role, steps=endpoint_steps, best=best, notes=notes)
            )

        os.makedirs(os.path.dirname(json_out) or ".", exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "base_url": base_url,
                    "mode": mode,
                    "timeout_s": timeout_s,
                    "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "results": [r.__dict__ for r in results],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        # Console summary
        passed = sum(1 for r in results if r.best is not None)
        print(f"Endpoints: {len(results)}")
        print(f"Passed threshold: {passed}/{len(results)}")
        print(f"Report: {json_out}")

        # Print a compact per-endpoint line
        for r in results:
            if r.best is None:
                print(f"FAIL {r.method:6} {r.path}  role={r.role}  notes={','.join(r.notes)}")
                if r.steps:
                    last = r.steps[-1]
                    print(
                        f"     last: c={last['concurrency']} rps={last['rps']} ok2xx={last['ok_2xx']}/{last['total']} p95={last['p95_ms']}ms statuses={last['status_counts']}"
                    )
                continue
            b = r.best
            print(
                f"OK   {r.method:6} {r.path}  role={r.role}  best:c={b['concurrency']} rps={b['rps']} p95={b['p95_ms']}ms"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
