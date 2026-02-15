from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(tags=["admin"])


@router.get("/api/admin/bot-requests", response_model=list[schemas.BotRequestSubmission])
def admin_list_bot_requests(
    status: str | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    q = (
        db.query(models.BotSubmission)
        .filter(models.BotSubmission.type == "BOT_REQUEST")
        .order_by(models.BotSubmission.id.desc())
    )
    if status:
        q = q.filter(models.BotSubmission.status == status)
    return q.all()


@router.put("/api/admin/bot-requests/{submission_id}", response_model=schemas.BotRequestSubmission)
def admin_update_bot_request(
    submission_id: int,
    body: schemas.BotRequestUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    item = (
        db.query(models.BotSubmission)
        .filter(models.BotSubmission.id == submission_id, models.BotSubmission.type == "BOT_REQUEST")
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    item.status = (body.status or "").strip() or item.status
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/api/admin/dashboard-stats", response_model=schemas.AdminDashboardStats)
def admin_dashboard_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    active_bots = (
        db.query(func.count(models.User.id))
        .filter(
            models.User.role == "CANDIDATE",
            models.User.is_active == True,  # noqa: E712
            models.User.bot_token.isnot(None),
        )
        .scalar()
        or 0
    )
    total_questions = (
        db.query(func.count(models.BotSubmission.id))
        .filter(models.BotSubmission.type == "QUESTION")
        .scalar()
        or 0
    )
    total_feedback = (
        db.query(func.count(models.BotSubmission.id))
        .filter(models.BotSubmission.type == "FEEDBACK")
        .scalar()
        or 0
    )
    total_bot_requests = (
        db.query(func.count(models.BotSubmission.id))
        .filter(models.BotSubmission.type == "BOT_REQUEST")
        .scalar()
        or 0
    )
    return schemas.AdminDashboardStats(
        active_bots=active_bots,
        total_questions=total_questions,
        total_feedback=total_feedback,
        total_bot_requests=total_bot_requests,
    )


@router.get("/api/admin/candidate-stats", response_model=list[schemas.AdminCandidateStats])
def admin_candidate_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    answered_cond = (
        (models.BotSubmission.type == "QUESTION")
        & (func.upper(func.coalesce(models.BotSubmission.status, "")) == "ANSWERED")
    )
    rows = (
        db.query(
            models.BotSubmission.candidate_id.label("candidate_id"),
            func.sum(case((models.BotSubmission.type == "QUESTION", 1), else_=0)).label("total_questions"),
            func.sum(case((models.BotSubmission.type == "FEEDBACK", 1), else_=0)).label("total_feedback"),
            func.sum(case((answered_cond, 1), else_=0)).label("answered_questions"),
        )
        .group_by(models.BotSubmission.candidate_id)
        .all()
    )

    out: list[schemas.AdminCandidateStats] = []
    for r in rows:
        out.append(
            schemas.AdminCandidateStats(
                candidate_id=int(r.candidate_id),
                total_questions=int(r.total_questions or 0),
                total_feedback=int(r.total_feedback or 0),
                answered_questions=int(r.answered_questions or 0),
            )
        )
    return out
