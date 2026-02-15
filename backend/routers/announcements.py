from __future__ import annotations

import jdatetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(tags=["announcements"])


@router.get("/api/announcements", response_model=list[schemas.Announcement])
def get_announcements(db: Session = Depends(database.get_db)):
    return db.query(models.Announcement).order_by(models.Announcement.id.desc()).all()


@router.post("/api/announcements", response_model=schemas.Announcement)
def create_announcement(
    announcement: schemas.AnnouncementCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    now_jalali = jdatetime.datetime.now()
    created_at_jalali = now_jalali.strftime("%Y/%m/%d %H:%M:%S")

    new_announcement = models.Announcement(
        title=announcement.title,
        content=announcement.content,
        attachments=announcement.attachments,
        created_at_jalali=created_at_jalali,
    )
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    return new_announcement
