from __future__ import annotations

import os
from datetime import datetime, timedelta

import jdatetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas

from ._integrity import raise_from_integrity_error
from ._telegram_profile import apply_telegram_profile_for_candidate
from .uploads import upload_file_path_from_localhost_url


router = APIRouter(tags=["candidates"])


class AssignPlanRequest(BaseModel):
    plan_id: int
    duration_days: int = 30


@router.get("/api/candidates", response_model=list[schemas.Candidate])
def get_candidates(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.role == "ADMIN":
        return (
            db.query(models.User)
            .filter(models.User.role == "CANDIDATE")
            .order_by(models.User.id.desc())
            .all()
        )

    if current_user.role == "CANDIDATE":
        return [current_user]

    raise HTTPException(status_code=403, detail="Access denied")


@router.get("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    candidate = (
        db.query(models.User)
        .filter(models.User.id == candidate_id, models.User.role == "CANDIDATE")
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    if current_user.role != "ADMIN" and candidate.id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return candidate


@router.post("/api/candidates", response_model=schemas.Candidate)
def create_candidate(
    candidate_data: schemas.CandidateCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    data = candidate_data.model_dump(exclude_unset=True)

    try:
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        phone = data.get("phone")
        full_name = (data.get("name") or "").strip()
        bot_name = (data.get("bot_name") or "").strip()
        bot_token = (data.get("bot_token") or "").strip()

        if isinstance(phone, str):
            phone = phone.strip() or None
        if isinstance(bot_name, str):
            bot_name = bot_name.strip() or None
        if isinstance(bot_token, str):
            bot_token = bot_token.strip() or None

        if not username or not password:
            raise HTTPException(status_code=422, detail={"message": "نام کاربری و رمز عبور برای ایجاد نماینده الزامی است"})

        if len(password) < 8:
            raise HTTPException(status_code=422, detail={"message": "رمز عبور باید حداقل ۸ کاراکتر باشد"})

        now_jalali = jdatetime.datetime.now()
        created_at_jalali = now_jalali.strftime("%Y/%m/%d %H:%M:%S")

        new_user = models.User(
            username=username,
            phone=phone,
            full_name=full_name,
            hashed_password=auth.get_password_hash(password),
            role="CANDIDATE",
            is_active=True,
            bot_name=bot_name,
            bot_token=bot_token,
            city=data.get("city") or None,
            province=data.get("province") or None,
            constituency=(data.get("constituency") or None),
            slogan=data.get("slogan"),
            bio=data.get("bio"),
            image_url=data.get("image_url"),
            resume=data.get("resume"),
            ideas=data.get("ideas"),
            address=data.get("address"),
            voice_url=data.get("voice_url"),
            socials=data.get("socials"),
            bot_config=data.get("bot_config"),
            created_at_jalali=created_at_jalali,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError as e:
        db.rollback()
        raise_from_integrity_error(e)
    except HTTPException:
        db.rollback()
        raise


@router.put("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate(
    candidate_id: int,
    candidate_data: schemas.CandidateUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    candidate = db.query(models.User).filter(models.User.id == candidate_id, models.User.role == "CANDIDATE").first()
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    if current_user.role != "ADMIN" and candidate.id != current_user.id:
        raise HTTPException(status_code=403, detail="شما اجازه ویرایش این کاندید را ندارید")

    data = candidate_data.model_dump(exclude_unset=True) if hasattr(candidate_data, "model_dump") else candidate_data.dict()

    try:
        previous_voice_url = candidate.voice_url

        # Normalize common string fields to reduce duplicate/dirty data.
        if isinstance(data.get("username"), str):
            data["username"] = data["username"].strip()
        if isinstance(data.get("phone"), str):
            v = data["phone"].strip()
            data["phone"] = v or None
        if isinstance(data.get("bot_name"), str):
            v = data["bot_name"].strip()
            data["bot_name"] = v or None
        if isinstance(data.get("bot_token"), str):
            v = data["bot_token"].strip()
            data["bot_token"] = v or None

        if "password" in data and data["password"]:
            new_password = (data["password"] or "").strip()
            if len(new_password) < 8:
                raise HTTPException(status_code=422, detail="رمز عبور باید حداقل ۸ کاراکتر باشد")
            candidate.hashed_password = auth.get_password_hash(new_password)
            del data["password"]

        if "name" in data:
            candidate.full_name = data["name"]
            del data["name"]

        for key, value in data.items():
            if not hasattr(candidate, key):
                continue

            if value is None:
                if key in {"voice_url"}:
                    setattr(candidate, key, None)
                continue

            if key in {"city", "province", "constituency"} and isinstance(value, str):
                value = value.strip() or None

            setattr(candidate, key, value)

        if "voice_url" in data:
            new_voice_url = candidate.voice_url
            if previous_voice_url and previous_voice_url != new_voice_url:
                try:
                    old_path = upload_file_path_from_localhost_url(previous_voice_url)
                    if old_path and os.path.exists(old_path):
                        os.remove(old_path)
                except Exception:
                    pass

        db.commit()
        db.refresh(candidate)
        return candidate
    except IntegrityError as e:
        db.rollback()
        raise_from_integrity_error(e)
    except HTTPException:
        db.rollback()
        raise


@router.post("/api/candidates/{candidate_id}/apply-telegram-profile")
def apply_telegram_profile(
    candidate_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    candidate = (
        db.query(models.User)
        .filter(models.User.id == candidate_id, models.User.role == "CANDIDATE")
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    if current_user.role != "ADMIN" and candidate.id != current_user.id:
        raise HTTPException(status_code=403, detail="شما اجازه این عملیات را ندارید")

    return apply_telegram_profile_for_candidate(candidate)


@router.delete("/api/candidates/{candidate_id}")
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    candidate = db.query(models.User).filter(models.User.id == candidate_id, models.User.role == "CANDIDATE").first()
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    db.delete(candidate)
    db.commit()
    return {"detail": "کاندید حذف شد"}


@router.post("/api/candidates/{candidate_id}/reset-password")
def reset_candidate_password(
    candidate_id: int,
    body: schemas.PasswordResetRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    candidate = db.query(models.User).filter(models.User.id == candidate_id, models.User.role == "CANDIDATE").first()
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    new_password = (body.password or "").strip()
    if len(new_password) < 8:
        raise HTTPException(status_code=422, detail="رمز عبور باید حداقل ۸ کاراکتر باشد")

    candidate.hashed_password = auth.get_password_hash(new_password)
    db.add(candidate)
    db.commit()
    return {"detail": "رمز عبور با موفقیت تغییر کرد"}


@router.post("/api/candidates/{candidate_id}/assign-plan")
def assign_plan_to_candidate(
    candidate_id: int,
    request: AssignPlanRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    candidate = db.query(models.User).filter(models.User.id == candidate_id, models.User.role == "CANDIDATE").first()
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    plan = db.query(models.Plan).filter(models.Plan.id == request.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="پلن یافت نشد")

    now = datetime.utcnow()
    candidate.active_plan_id = plan.id
    candidate.plan_start_date = now
    candidate.plan_expires_at = now + timedelta(days=request.duration_days)

    db.commit()
    return {"message": "پلن با موفقیت فعال شد"}
