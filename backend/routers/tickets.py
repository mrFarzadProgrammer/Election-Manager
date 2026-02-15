from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(tags=["tickets"])


@router.get("/api/tickets", response_model=list[schemas.Ticket])
def get_tickets(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.Ticket).order_by(models.Ticket.id.desc())
    if current_user.role == "ADMIN":
        return q.all()
    return q.filter(models.Ticket.user_id == current_user.id).all()


@router.post("/api/tickets", response_model=schemas.Ticket)
def create_ticket(
    ticket_data: schemas.TicketCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    user_id = current_user.id
    new_ticket = models.Ticket(user_id=user_id, subject=ticket_data.subject, status="OPEN")
    db.add(new_ticket)
    db.flush()

    initial_msg = models.TicketMessage(
        ticket_id=new_ticket.id,
        sender_role=current_user.role,
        text=ticket_data.message,
    )
    db.add(initial_msg)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket


@router.post("/api/tickets/{ticket_id}/messages", response_model=schemas.TicketMessage)
def add_ticket_message(
    ticket_id: int,
    message_data: schemas.TicketMessageCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role != "ADMIN" and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    new_msg = models.TicketMessage(
        ticket_id=ticket_id,
        sender_role=current_user.role,
        text=message_data.text,
        attachment_url=message_data.attachment_url,
        attachment_type=message_data.attachment_type,
    )

    ticket.updated_at = datetime.utcnow()
    ticket.status = "ANSWERED" if current_user.role == "ADMIN" else "OPEN"

    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg


@router.put("/api/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    update: schemas.TicketUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = update.status
    db.commit()
    return {"message": "Status updated"}
