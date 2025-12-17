# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models, schemas, auth, database
from database import engine

# ساخت جداول دیتابیس اگر وجود نداشته باشند
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# تنظیمات CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication Endpoints ---

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# --- Candidate Endpoints ---

@app.get("/candidates/", response_model=List[schemas.Candidate])
def read_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    candidates = db.query(models.Candidate).offset(skip).limit(limit).all()
    return candidates

@app.post("/candidates/", response_model=schemas.Candidate)
def create_candidate(candidate: schemas.CandidateCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    db_candidate = models.Candidate(**candidate.dict())
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

@app.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(candidate)
    db.commit()
    return {"message": "Candidate deleted"}

# --- Plan Endpoints ---

@app.post("/plans/", response_model=schemas.Plan)
def create_plan(plan: schemas.PlanCreate, candidate_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_plan = models.Plan(**plan.dict(), candidate_id=candidate_id)
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

# --- Ticket / Vote Endpoints ---

@app.get("/tickets/", response_model=List[schemas.Ticket])
def read_tickets(db: Session = Depends(database.get_db)):
    tickets = db.query(models.Ticket).filter(models.Ticket.status == "pending").all()
    return tickets

@app.post("/tickets/", response_model=schemas.Ticket)
def create_ticket(ticket: schemas.TicketCreate, db: Session = Depends(database.get_db)):
    db_ticket = models.Ticket(**ticket.dict())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

@app.put("/tickets/{ticket_id}/verify")
def verify_ticket(ticket_id: int, update: schemas.TicketUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = update.status
    if update.status == "approved":
        candidate = db.query(models.Candidate).filter(models.Candidate.id == ticket.candidate_id).first()
        if candidate:
            candidate.vote_count += 1
            
    db.commit()
    return {"message": "Status updated"}

# --- Seed Data ---
@app.on_event("startup")
def create_initial_data():
    db = database.SessionLocal()
    if not db.query(models.User).filter(models.User.username == "admin").first():
        admin_user = models.User(
            username="admin",
            full_name="System Admin",
            hashed_password=auth.get_password_hash("admin123"),
            role="ADMIN"
        )
        db.add(admin_user)
        db.commit()
    db.close()
