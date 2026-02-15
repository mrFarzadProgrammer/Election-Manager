from __future__ import annotations

import jdatetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(tags=["plans"])


@router.get("/api/plans")
def get_plans(db: Session = Depends(database.get_db)):
    return db.query(models.Plan).order_by(models.Plan.id.desc()).all()


@router.post("/api/plans", response_model=schemas.Plan)
def create_plan(
    plan_data: schemas.PlanCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    data = plan_data.model_dump(exclude_unset=True)
    now_jalali = jdatetime.datetime.now()
    created_at_jalali = now_jalali.strftime("%Y/%m/%d %H:%M:%S")
    new_plan = models.Plan(**data, created_at_jalali=created_at_jalali)
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan


@router.put("/api/plans/{plan_id}", response_model=schemas.Plan)
def update_plan(
    plan_id: int,
    plan_data: schemas.PlanUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="پلن یافت نشد")

    data = plan_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(plan, key, value)

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/api/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="پلن یافت نشد")

    db.delete(plan)
    db.commit()
    return {"detail": "پلن حذف شد"}
