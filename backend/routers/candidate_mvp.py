from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

import auth
import database
import models
import schemas

from ._common import client_ip
from ._telegram_notify import notify_question_answer_published


router = APIRouter(tags=["candidate-mvp"])


def _require_candidate(current_user: models.User) -> None:
    if current_user.role != "CANDIDATE":
        raise HTTPException(status_code=403, detail="Access denied")


# ============================================================================
# FEEDBACK (BOT SUBMISSIONS) ENDPOINTS (MVP)
# ============================================================================


@router.get("/api/candidates/me/feedback", response_model=list[schemas.FeedbackSubmission])
def get_my_feedback_submissions(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)
    return (
        db.query(models.BotSubmission)
        .filter(
            models.BotSubmission.candidate_id == current_user.id,
            models.BotSubmission.type == "FEEDBACK",
        )
        .order_by(models.BotSubmission.id.desc())
        .all()
    )


@router.put(
    "/api/candidates/me/feedback/{submission_id}",
    response_model=schemas.FeedbackSubmission,
)
def update_my_feedback_submission(
    submission_id: int,
    payload: schemas.FeedbackSubmissionUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    submission = (
        db.query(models.BotSubmission)
        .filter(
            models.BotSubmission.id == submission_id,
            models.BotSubmission.candidate_id == current_user.id,
            models.BotSubmission.type == "FEEDBACK",
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    data = payload.model_dump(exclude_unset=True)

    if "tag" in data:
        raw = data.get("tag")
        if raw is None:
            submission.tag = None
        else:
            trimmed = str(raw).strip()
            submission.tag = trimmed or None

    if "status" in data:
        raw_status = (data.get("status") or "").strip().upper()
        if raw_status not in {"NEW", "REVIEWED"}:
            raise HTTPException(status_code=422, detail={"message": "Invalid status"})
        submission.status = raw_status

    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/api/candidates/me/feedback/stats", response_model=schemas.FeedbackStatsResponse)
def get_my_feedback_stats(
    days: int = 7,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    if days not in {7, 30}:
        raise HTTPException(status_code=422, detail={"message": "days must be 7 or 30"})

    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(models.BotSubmission)
        .filter(
            models.BotSubmission.candidate_id == current_user.id,
            models.BotSubmission.type == "FEEDBACK",
            models.BotSubmission.created_at >= since,
        )
        .all()
    )

    total = len(rows)
    counts: dict[str, int] = {}
    for r in rows:
        tag = (r.tag or "").strip() or "سایر"
        counts[tag] = counts.get(tag, 0) + 1

    items = []
    for tag, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        percent = round((count / total * 100.0), 2) if total else 0.0
        items.append({"tag": tag, "count": int(count), "percent": float(percent)})

    return {"days": days, "total": total, "items": items}


# ============================================================================
# QUESTIONS (PUBLIC Q&A) ENDPOINTS (MVP)
# ============================================================================


@router.get("/api/candidates/me/questions", response_model=list[schemas.QuestionSubmission])
def get_my_question_submissions(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)
    return (
        db.query(models.BotSubmission)
        .filter(
            models.BotSubmission.candidate_id == current_user.id,
            models.BotSubmission.type == "QUESTION",
        )
        .order_by(models.BotSubmission.id.desc())
        .all()
    )


@router.put(
    "/api/candidates/me/questions/{submission_id}/answer",
    response_model=schemas.QuestionSubmission,
)
def answer_my_question_submission(
    submission_id: int,
    payload: schemas.QuestionSubmissionAnswer,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    submission = (
        db.query(models.BotSubmission)
        .filter(
            models.BotSubmission.id == submission_id,
            models.BotSubmission.candidate_id == current_user.id,
            models.BotSubmission.type == "QUESTION",
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if (submission.status or "").upper() == "ANSWERED":
        raise HTTPException(status_code=409, detail={"message": "Answer is immutable"})

    answer_text = (payload.answer_text or "").strip()
    if not answer_text:
        raise HTTPException(status_code=422, detail={"message": "answer_text is required"})
    if len(answer_text) > 2000:
        raise HTTPException(status_code=422, detail={"message": "answer_text is too long"})

    submission.answer = answer_text
    submission.status = "ANSWERED"
    submission.is_public = True
    submission.answered_at = datetime.utcnow()

    if getattr(payload, "topic", None) is not None:
        submission.topic = (payload.topic or "").strip() or None
    if getattr(payload, "is_featured", None) is not None:
        submission.is_featured = bool(payload.is_featured)

    db.add(submission)
    db.commit()
    db.refresh(submission)

    notify_question_answer_published(candidate=current_user, submission=submission)
    return submission


@router.put(
    "/api/candidates/me/questions/{submission_id}/meta",
    response_model=schemas.QuestionSubmission,
)
def update_my_question_submission_meta(
    submission_id: int,
    payload: schemas.QuestionSubmissionMeta,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    submission = (
        db.query(models.BotSubmission)
        .filter(
            models.BotSubmission.id == submission_id,
            models.BotSubmission.candidate_id == current_user.id,
            models.BotSubmission.type == "QUESTION",
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if payload.topic is not None:
        submission.topic = (payload.topic or "").strip() or None
    if payload.is_featured is not None:
        submission.is_featured = bool(payload.is_featured)

    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.put(
    "/api/candidates/me/questions/{submission_id}/reject",
    response_model=schemas.QuestionSubmission,
)
def reject_my_question_submission(
    submission_id: int,
    _payload: schemas.QuestionSubmissionReject | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    submission = (
        db.query(models.BotSubmission)
        .filter(
            models.BotSubmission.id == submission_id,
            models.BotSubmission.candidate_id == current_user.id,
            models.BotSubmission.type == "QUESTION",
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if (submission.status or "").upper() == "ANSWERED":
        raise HTTPException(status_code=409, detail={"message": "Answer is immutable"})

    submission.status = "REJECTED"
    submission.is_public = False

    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


# ============================================================================
# COMMITMENTS (PUBLIC DIGITAL CONTRACTS) ENDPOINTS (STRICT)
# ============================================================================


COMMITMENT_TERMS_VERSION = "v1"
ALLOWED_COMMITMENT_STATUS_AFTER_PUBLISH = {"active", "in_progress", "completed", "failed"}
ALLOWED_COMMITMENT_CATEGORIES = {"economy", "housing", "transparency", "employment", "other"}


def _log_commitment_security_event(*, db: Session, representative_id: int, error_type: str, message: str) -> None:
    try:
        db.add(
            models.TechnicalErrorLog(
                service_name="api",
                error_type=str(error_type),
                error_message=str(message)[:8000],
                telegram_user_id=None,
                candidate_id=int(representative_id),
                state="commitments",
            )
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def _normalize_commitment_status(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def _validate_commitment_category(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v not in ALLOWED_COMMITMENT_CATEGORIES:
        raise HTTPException(status_code=422, detail={"message": "Invalid category"})
    return v


def _validate_commitment_status_after_publish(value: str | None) -> str:
    v = _normalize_commitment_status(value)
    if v not in ALLOWED_COMMITMENT_STATUS_AFTER_PUBLISH:
        raise HTTPException(status_code=422, detail={"message": "Invalid status"})
    return v


@router.get(
    "/api/candidates/me/commitments/terms/acceptance",
    response_model=schemas.CommitmentTermsAcceptanceOut | None,
)
def get_commitment_terms_acceptance(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)
    return (
        db.query(models.CommitmentTermsAcceptance)
        .filter(models.CommitmentTermsAcceptance.representative_id == int(current_user.id))
        .first()
    )


@router.post(
    "/api/candidates/me/commitments/terms/accept",
    response_model=schemas.CommitmentTermsAcceptanceOut,
)
def accept_commitment_terms(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    existing = (
        db.query(models.CommitmentTermsAcceptance)
        .filter(models.CommitmentTermsAcceptance.representative_id == int(current_user.id))
        .first()
    )
    if existing is not None:
        return existing

    ip_address = None
    try:
        ip_address = client_ip(request)
    except Exception:
        ip_address = None
    user_agent = (request.headers.get("user-agent") or "").strip() or None

    row = models.CommitmentTermsAcceptance(
        representative_id=int(current_user.id),
        accepted_at=datetime.utcnow(),
        ip_address=ip_address,
        user_agent=user_agent,
        version=COMMITMENT_TERMS_VERSION,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/api/candidates/me/commitments", response_model=list[schemas.CommitmentOut])
def list_my_commitments(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    rows = (
        db.query(models.BotCommitment)
        .options(joinedload(models.BotCommitment.progress_logs))
        .filter(models.BotCommitment.candidate_id == int(current_user.id))
        .order_by(models.BotCommitment.id.desc())
        .all()
    )

    touched = False
    now = datetime.utcnow()
    for r in rows:
        if getattr(r, "status_updated_at", None) is None:
            r.status_updated_at = getattr(r, "published_at", None) or getattr(r, "created_at", None) or now
            touched = True
    if touched:
        db.commit()

    return rows


@router.post("/api/candidates/me/commitments", response_model=schemas.CommitmentOut)
def create_commitment_draft(
    payload: schemas.CommitmentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    accepted = (
        db.query(models.CommitmentTermsAcceptance)
        .filter(models.CommitmentTermsAcceptance.representative_id == int(current_user.id))
        .first()
    )
    if accepted is None:
        raise HTTPException(status_code=403, detail={"message": "Commitment terms not accepted"})

    title = (payload.title or "").strip()
    description = (payload.description or "").strip()
    category = _validate_commitment_category(payload.category)

    if not title:
        raise HTTPException(status_code=422, detail={"message": "title is required"})
    if len(title) > 120:
        raise HTTPException(status_code=422, detail={"message": "title is too long"})
    if not description:
        raise HTTPException(status_code=422, detail={"message": "description is required"})
    if len(description) > 5000:
        raise HTTPException(status_code=422, detail={"message": "description is too long"})

    row = models.BotCommitment(
        candidate_id=int(current_user.id),
        title=title,
        body=description,
        category=category,
        status="draft",
        status_updated_at=datetime.utcnow(),
        locked=False,
        published_at=None,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/api/candidates/me/commitments/{commitment_id}", response_model=schemas.CommitmentOut)
def update_commitment_draft(
    commitment_id: int,
    payload: schemas.CommitmentUpdateDraft,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    row = (
        db.query(models.BotCommitment)
        .options(joinedload(models.BotCommitment.progress_logs))
        .filter(models.BotCommitment.id == int(commitment_id), models.BotCommitment.candidate_id == int(current_user.id))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Commitment not found")

    is_published = bool(getattr(row, "published_at", None)) or bool(getattr(row, "locked", False))
    if is_published or _normalize_commitment_status(getattr(row, "status", None)) != "draft":
        _log_commitment_security_event(
            db=db,
            representative_id=int(current_user.id),
            error_type="CommitmentImmutableViolation",
            message=f"Attempted to edit commitment fields after publish. commitment_id={commitment_id}",
        )
        raise HTTPException(status_code=403, detail={"message": "Commitment is immutable after publish"})

    data = payload.model_dump(exclude_unset=True)
    if "title" in data:
        v = (data.get("title") or "").strip()
        if not v:
            raise HTTPException(status_code=422, detail={"message": "title is required"})
        if len(v) > 120:
            raise HTTPException(status_code=422, detail={"message": "title is too long"})
        row.title = v

    if "description" in data:
        v = (data.get("description") or "").strip()
        if not v:
            raise HTTPException(status_code=422, detail={"message": "description is required"})
        if len(v) > 5000:
            raise HTTPException(status_code=422, detail={"message": "description is too long"})
        row.body = v

    if "category" in data:
        row.category = _validate_commitment_category(data.get("category"))

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/api/candidates/me/commitments/{commitment_id}/publish", response_model=schemas.CommitmentOut)
def publish_commitment(
    commitment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    row = (
        db.query(models.BotCommitment)
        .options(joinedload(models.BotCommitment.progress_logs))
        .filter(models.BotCommitment.id == int(commitment_id), models.BotCommitment.candidate_id == int(current_user.id))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Commitment not found")

    if getattr(row, "published_at", None) is not None or bool(getattr(row, "locked", False)):
        raise HTTPException(status_code=409, detail={"message": "Commitment already published"})
    if _normalize_commitment_status(getattr(row, "status", None)) != "draft":
        raise HTTPException(status_code=409, detail={"message": "Only draft commitments can be published"})
    if not (getattr(row, "title", None) or "").strip() or not (getattr(row, "body", None) or "").strip():
        raise HTTPException(status_code=422, detail={"message": "title and description are required"})
    if not (getattr(row, "category", None) or "").strip():
        raise HTTPException(status_code=422, detail={"message": "category is required"})

    now = datetime.utcnow()
    row.published_at = now
    row.locked = True
    row.status = "active"
    row.status_updated_at = now

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/api/candidates/me/commitments/{commitment_id}/status", response_model=schemas.CommitmentOut)
def update_commitment_status(
    commitment_id: int,
    payload: schemas.CommitmentUpdateStatus,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    row = (
        db.query(models.BotCommitment)
        .options(joinedload(models.BotCommitment.progress_logs))
        .filter(models.BotCommitment.id == int(commitment_id), models.BotCommitment.candidate_id == int(current_user.id))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Commitment not found")

    if getattr(row, "published_at", None) is None or not bool(getattr(row, "locked", False)):
        raise HTTPException(status_code=403, detail={"message": "Only published commitments can change status"})

    next_status = _validate_commitment_status_after_publish(payload.status)
    now = datetime.utcnow()
    row.status = next_status
    row.status_updated_at = now

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/api/candidates/me/commitments/{commitment_id}/progress", response_model=schemas.CommitmentOut)
def add_commitment_progress_log(
    commitment_id: int,
    payload: schemas.CommitmentAddProgress,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    row = (
        db.query(models.BotCommitment)
        .options(joinedload(models.BotCommitment.progress_logs))
        .filter(models.BotCommitment.id == int(commitment_id), models.BotCommitment.candidate_id == int(current_user.id))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Commitment not found")

    if getattr(row, "published_at", None) is None or not bool(getattr(row, "locked", False)):
        raise HTTPException(status_code=403, detail={"message": "Progress logs are only allowed after publish"})

    note = (payload.note or "").strip()
    if not note:
        raise HTTPException(status_code=422, detail={"message": "note is required"})
    if len(note) > 1000:
        raise HTTPException(status_code=422, detail={"message": "note is too long"})

    log_row = models.CommitmentProgressLog(commitment_id=int(row.id), note=note, created_at=datetime.utcnow())
    db.add(log_row)
    db.commit()

    row = (
        db.query(models.BotCommitment)
        .options(joinedload(models.BotCommitment.progress_logs))
        .filter(models.BotCommitment.id == int(commitment_id), models.BotCommitment.candidate_id == int(current_user.id))
        .first()
    )
    return row


@router.delete("/api/candidates/me/commitments/{commitment_id}")
def delete_commitment_draft(
    commitment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _require_candidate(current_user)

    row = (
        db.query(models.BotCommitment)
        .filter(models.BotCommitment.id == int(commitment_id), models.BotCommitment.candidate_id == int(current_user.id))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Commitment not found")

    if getattr(row, "published_at", None) is not None or bool(getattr(row, "locked", False)):
        _log_commitment_security_event(
            db=db,
            representative_id=int(current_user.id),
            error_type="CommitmentDeleteForbidden",
            message=f"Attempted to delete commitment after publish. commitment_id={commitment_id}",
        )
        raise HTTPException(status_code=403, detail={"message": "Published commitments cannot be deleted"})

    if _normalize_commitment_status(getattr(row, "status", None)) != "draft":
        raise HTTPException(status_code=403, detail={"message": "Only draft commitments can be deleted"})

    db.delete(row)
    db.commit()
    return {"message": "deleted"}
