from __future__ import annotations

import io
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session
from sqlalchemy import case, func

import auth
import database
import models
import schemas

from utils.cache import cache_get_json, cache_set_json


router = APIRouter(tags=["admin-mvp"])


def _overview_counts_bulk(db: Session, *, candidate_ids: list[int]) -> tuple[schemas.MvpOverviewCounters, dict[int, schemas.MvpOverviewCounters]]:
    """Compute global + per-candidate counters using aggregated queries.

    This is intentionally query-efficient for election-day load.
    """

    active_cutoff = datetime.utcnow() - timedelta(days=7)

    # --- Users (registry) ---
    global_total_users = int(
        db.query(func.count(func.distinct(models.BotUserRegistry.telegram_user_id))).scalar() or 0
    )
    global_active_users = int(
        db.query(func.count(func.distinct(models.BotUserRegistry.telegram_user_id)))
        .filter(models.BotUserRegistry.last_seen_at >= active_cutoff)
        .scalar()
        or 0
    )

    per_user_rows = (
        db.query(
            models.BotUserRegistry.candidate_id.label("candidate_id"),
            func.count(func.distinct(models.BotUserRegistry.telegram_user_id)).label("total_users"),
            func.count(
                func.distinct(
                    case(
                        (models.BotUserRegistry.last_seen_at >= active_cutoff, models.BotUserRegistry.telegram_user_id),
                        else_=None,
                    )
                )
            ).label("active_users"),
        )
        .filter(models.BotUserRegistry.candidate_id.in_(candidate_ids) if candidate_ids else True)
        .group_by(models.BotUserRegistry.candidate_id)
        .all()
    )
    per_user: dict[int, tuple[int, int]] = {
        int(r.candidate_id): (int(r.total_users or 0), int(r.active_users or 0)) for r in per_user_rows
    }

    # --- Submissions ---
    status_upper = func.upper(func.coalesce(models.BotSubmission.status, ""))
    global_sub_row = (
        db.query(
            func.sum(case((models.BotSubmission.type == "QUESTION", 1), else_=0)).label("total_questions"),
            func.sum(
                case(
                    (
                        (models.BotSubmission.type == "QUESTION") & (status_upper == "ANSWERED"),
                        1,
                    ),
                    else_=0,
                )
            ).label("answered_questions"),
            func.sum(case((models.BotSubmission.type == "FEEDBACK", 1), else_=0)).label("total_comments"),
            func.sum(case((models.BotSubmission.type == "BOT_REQUEST", 1), else_=0)).label("total_leads"),
        )
        .one()
    )

    per_sub_rows = (
        db.query(
            models.BotSubmission.candidate_id.label("candidate_id"),
            func.sum(case((models.BotSubmission.type == "QUESTION", 1), else_=0)).label("total_questions"),
            func.sum(
                case(
                    (
                        (models.BotSubmission.type == "QUESTION") & (status_upper == "ANSWERED"),
                        1,
                    ),
                    else_=0,
                )
            ).label("answered_questions"),
            func.sum(case((models.BotSubmission.type == "FEEDBACK", 1), else_=0)).label("total_comments"),
            func.sum(case((models.BotSubmission.type == "BOT_REQUEST", 1), else_=0)).label("total_leads"),
        )
        .filter(models.BotSubmission.candidate_id.in_(candidate_ids) if candidate_ids else True)
        .group_by(models.BotSubmission.candidate_id)
        .all()
    )
    per_sub: dict[int, tuple[int, int, int, int]] = {
        int(r.candidate_id): (
            int(r.total_questions or 0),
            int(r.answered_questions or 0),
            int(r.total_comments or 0),
            int(r.total_leads or 0),
        )
        for r in per_sub_rows
    }

    # --- Commitments ---
    global_total_commitments = int(db.query(func.count(models.BotCommitment.id)).scalar() or 0)
    per_commit_rows = (
        db.query(models.BotCommitment.candidate_id.label("candidate_id"), func.count(models.BotCommitment.id).label("cnt"))
        .filter(models.BotCommitment.candidate_id.in_(candidate_ids) if candidate_ids else True)
        .group_by(models.BotCommitment.candidate_id)
        .all()
    )
    per_commit: dict[int, int] = {int(r.candidate_id): int(r.cnt or 0) for r in per_commit_rows}

    global_counters = schemas.MvpOverviewCounters(
        total_users=global_total_users,
        active_users=global_active_users,
        total_questions=int(global_sub_row.total_questions or 0),
        answered_questions=int(global_sub_row.answered_questions or 0),
        total_comments=int(global_sub_row.total_comments or 0),
        total_commitments=global_total_commitments,
        total_leads=int(global_sub_row.total_leads or 0),
    )

    per_candidate: dict[int, schemas.MvpOverviewCounters] = {}
    for cid in candidate_ids:
        tu, au = per_user.get(int(cid), (0, 0))
        tq, aq, tc, tl = per_sub.get(int(cid), (0, 0, 0, 0))
        per_candidate[int(cid)] = schemas.MvpOverviewCounters(
            total_users=int(tu),
            active_users=int(au),
            total_questions=int(tq),
            answered_questions=int(aq),
            total_comments=int(tc),
            total_commitments=int(per_commit.get(int(cid), 0)),
            total_leads=int(tl),
        )

    return global_counters, per_candidate


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        s = str(value).strip()
        if not s:
            return None
        if "T" not in s:
            return datetime.fromisoformat(s + "T00:00:00")
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _log_export_action(db: Session, *, admin_id: int, export_type: str, filters: dict | None = None) -> None:
    try:
        db.add(models.AdminExportLog(admin_id=int(admin_id), export_type=str(export_type), filters=filters or None))
        db.commit()
    except Exception:
        db.rollback()


@router.get("/api/admin/mvp/overview", response_model=schemas.MvpOverviewResponse)
def admin_mvp_overview(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    ttl_s = int((os.getenv("ADMIN_MVP_OVERVIEW_CACHE_TTL_SEC") or "5").strip() or 5)
    cache_key = "admin_mvp_overview:v2"
    if ttl_s > 0:
        cached = cache_get_json(cache_key)
        if isinstance(cached, dict) and cached:
            return cached

    candidates = (
        db.query(models.User)
        .filter(models.User.role == "CANDIDATE")
        .order_by(models.User.id.asc())
        .all()
    )

    candidate_ids = [int(c.id) for c in candidates]
    global_counters, per_candidate_counters = _overview_counts_bulk(db, candidate_ids=candidate_ids)

    per_candidate: list[schemas.MvpRepresentativeOverview] = [
        schemas.MvpRepresentativeOverview(
            candidate_id=int(c.id),
            name=getattr(c, "full_name", None) or getattr(c, "username", None),
            counters=per_candidate_counters.get(int(c.id))
            or schemas.MvpOverviewCounters(
                total_users=0,
                active_users=0,
                total_questions=0,
                answered_questions=0,
                total_comments=0,
                total_commitments=0,
                total_leads=0,
            ),
        )
        for c in candidates
    ]

    result = schemas.MvpOverviewResponse(global_counters=global_counters, per_candidate=per_candidate)
    if ttl_s > 0:
        try:
            cache_set_json(cache_key, result.model_dump(), ttl_s)
        except Exception:
            pass
    return result


@router.get("/api/admin/mvp/behavior", response_model=schemas.BehaviorStatsResponse)
def admin_mvp_behavior_stats(
    candidate_id: int | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    q = db.query(models.BotBehaviorCounter)
    if candidate_id is None:
        q = q.filter(models.BotBehaviorCounter.candidate_id.is_(None))
    else:
        q = q.filter(models.BotBehaviorCounter.candidate_id == int(candidate_id))
    rows = q.order_by(models.BotBehaviorCounter.event.asc()).all()
    items = [schemas.BehaviorCounterItem(event=r.event, count=int(r.count or 0)) for r in rows]
    return schemas.BehaviorStatsResponse(candidate_id=candidate_id, items=items)


@router.get("/api/admin/mvp/paths", response_model=schemas.FlowPathsResponse)
def admin_mvp_flow_paths(
    candidate_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    limit = max(1, min(int(limit), 200))
    q = db.query(models.BotFlowPathCounter)
    if candidate_id is None:
        q = q.filter(models.BotFlowPathCounter.candidate_id.is_(None))
    else:
        q = q.filter(models.BotFlowPathCounter.candidate_id == int(candidate_id))
    rows = q.order_by(models.BotFlowPathCounter.count.desc()).limit(limit).all()
    items = [schemas.FlowPathItem(path=r.path, count=int(r.count or 0)) for r in rows]
    return schemas.FlowPathsResponse(candidate_id=candidate_id, items=items)


@router.get("/api/admin/mvp/questions", response_model=list[schemas.QuestionLearningItem])
def admin_mvp_questions(
    candidate_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    q = db.query(models.BotSubmission).filter(models.BotSubmission.type == "QUESTION")
    if candidate_id is not None:
        q = q.filter(models.BotSubmission.candidate_id == int(candidate_id))
    if status:
        q = q.filter(func.upper(func.coalesce(models.BotSubmission.status, "")) == str(status).strip().upper())
    return q.order_by(models.BotSubmission.id.desc()).all()


@router.get("/api/admin/mvp/commitments", response_model=list[schemas.CommitmentLearningItem])
def admin_mvp_commitments(
    candidate_id: int | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    q = db.query(models.BotCommitment)
    if candidate_id is not None:
        q = q.filter(models.BotCommitment.candidate_id == int(candidate_id))
    return q.order_by(models.BotCommitment.id.desc()).all()


@router.get("/api/admin/mvp/leads", response_model=list[schemas.LeadItem])
def admin_mvp_leads(
    candidate_id: int | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    q = db.query(models.BotSubmission).filter(models.BotSubmission.type == "BOT_REQUEST")
    if candidate_id is not None:
        q = q.filter(models.BotSubmission.candidate_id == int(candidate_id))
    return q.order_by(models.BotSubmission.id.desc()).all()


@router.get("/api/admin/mvp/ux-logs", response_model=list[schemas.UxLogItem])
def admin_mvp_ux_logs(
    candidate_id: int | None = None,
    action: str | None = None,
    limit: int = 200,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    limit = max(1, min(int(limit), 2000))
    q = db.query(models.BotUxLog)
    if candidate_id is not None:
        q = q.filter(models.BotUxLog.candidate_id == int(candidate_id))
    if action:
        q = q.filter(models.BotUxLog.action == str(action).strip())
    return q.order_by(models.BotUxLog.id.desc()).limit(limit).all()


@router.get("/api/admin/mvp/global-users", response_model=list[schemas.GlobalBotUserItem])
def admin_mvp_global_users(
    representative_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    interaction_type: str | None = None,
    limit: int = 1000,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_super_admin_user),
):
    limit = max(1, min(int(limit), 5000))
    q = db.query(models.BotUserRegistry)

    if representative_id is not None:
        q = q.filter(models.BotUserRegistry.candidate_id == int(representative_id))

    sd = _parse_iso_dt(start_date)
    ed = _parse_iso_dt(end_date)
    if sd is not None:
        q = q.filter(models.BotUserRegistry.first_seen_at >= sd)
    if ed is not None:
        q = q.filter(models.BotUserRegistry.last_seen_at <= ed)

    it = (interaction_type or "").strip().lower()
    if it == "question":
        q = q.filter(models.BotUserRegistry.asked_question == True)  # noqa: E712
    elif it == "comment":
        q = q.filter(models.BotUserRegistry.left_comment == True)  # noqa: E712
    elif it == "lead":
        q = q.filter(models.BotUserRegistry.became_lead == True)  # noqa: E712

    return q.order_by(models.BotUserRegistry.last_seen_at.desc()).limit(limit).all()


@router.get("/api/admin/mvp/global-users/export.xlsx")
def admin_mvp_global_users_export_xlsx(
    representative_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    interaction_type: str | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_super_admin_user),
):
    rows = admin_mvp_global_users(
        representative_id=representative_id,
        start_date=start_date,
        end_date=end_date,
        interaction_type=interaction_type,
        limit=5000,
        db=db,
        current_user=current_user,
    )

    _log_export_action(
        db,
        admin_id=int(current_user.id),
        export_type="global_users",
        filters={
            "representative_id": representative_id,
            "start_date": start_date,
            "end_date": end_date,
            "interaction_type": interaction_type,
        },
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "users"

    headers = [
        "id",
        "user_id",
        "username",
        "first_name",
        "last_name",
        "phone",
        "platform",
        "representative_id",
        "bot_id",
        "candidate_name",
        "candidate_city",
        "candidate_province",
        "candidate_constituency",
        "chat_type",
        "first_interaction_at",
        "last_interaction_at",
        "total_interactions",
        "asked_question",
        "left_comment",
        "viewed_commitment",
        "became_lead",
        "selected_role",
    ]
    ws.append(headers)

    for r in rows:
        ws.append(
            [
                int(getattr(r, "id", 0) or 0),
                str(getattr(r, "telegram_user_id", "") or ""),
                str(getattr(r, "telegram_username", "") or ""),
                str(getattr(r, "first_name", "") or ""),
                str(getattr(r, "last_name", "") or ""),
                str(getattr(r, "phone", "") or ""),
                str(getattr(r, "platform", "TELEGRAM") or "TELEGRAM"),
                int(getattr(r, "candidate_id", 0) or 0),
                str(getattr(r, "candidate_bot_name", "") or ""),
                str(getattr(r, "candidate_name", "") or ""),
                str(getattr(r, "candidate_city", "") or ""),
                str(getattr(r, "candidate_province", "") or ""),
                str(getattr(r, "candidate_constituency", "") or ""),
                str(getattr(r, "chat_type", "") or ""),
                getattr(r, "first_seen_at", None),
                getattr(r, "last_seen_at", None),
                int(getattr(r, "total_interactions", 0) or 0),
                bool(getattr(r, "asked_question", False)),
                bool(getattr(r, "left_comment", False)),
                bool(getattr(r, "viewed_commitment", False)),
                bool(getattr(r, "became_lead", False)),
                str(getattr(r, "selected_role", "") or ""),
            ]
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"global_users_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
