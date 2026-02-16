import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func
from telegram.ext import Application

from database import SessionLocal
import models

logger = logging.getLogger(__name__)

_last_409_logged_at_by_candidate: dict[int, datetime] = {}


class Telegram409ConflictHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage() or ""
            if "terminated by other getUpdates request" not in msg and "telegram.error.Conflict" not in msg:
                return

            # The runner keeps a global running_bots dict; we import lazily to avoid cycles.
            from .runner import running_bots  # noqa: WPS433

            for cid, app in list(running_bots.items()):
                if app is None:
                    continue
                last = _last_409_logged_at_by_candidate.get(int(cid))
                now = datetime.utcnow()
                if last and (now - last) < timedelta(minutes=10):
                    continue
                _last_409_logged_at_by_candidate[int(cid)] = now

                try:
                    logger.warning(
                        "Telegram 409 Conflict for candidate_id=%s: another poller is running for this bot token. "
                        "Stop all other bot_runner instances (including on other machines).",
                        int(cid),
                    )
                except Exception:
                    pass
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
            return


def install_409_conflict_logger() -> None:
    try:
        updater_logger = logging.getLogger("telegram.ext.Updater")
        updater_logger.addHandler(Telegram409ConflictHandler())
    except Exception:
        pass


def log_ux_sync(*, candidate_id: int, telegram_user_id: str, state: str | None, action: str, expected_action: str | None = None) -> None:
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
