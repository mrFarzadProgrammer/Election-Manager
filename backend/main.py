# main.py
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import List, Optional
from jose import jwt
from contextlib import asynccontextmanager
import models, database, auth, schemas
import os
import shutil
from dotenv import load_dotenv
import jdatetime
from datetime import datetime, timedelta

load_dotenv()

# ساخت جداول دیتابیس
models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application started")
    yield
    print("Application shutdown")

app = FastAPI(
    title="Election Manager",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files for uploads
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:5555"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # Sanitize filename
    filename = file.filename.replace(" ", "_")
    file_location = f"{UPLOAD_DIR}/{filename}"
    
    with open(file_location, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return URL relative to server root
    return {"url": f"http://localhost:8000/uploads/{filename}", "filename": filename}

# ============================================================================
# ✅ HELPERS برای خطاهای Duplicate Field
# ============================================================================

FIELD_LABELS = {
    "username": "نام کاربری",
    "phone": "شماره تماس",
    "email": "ایمیل",
    "bot_name": "نام بات",
    "bot_token": "توکن بات",
}

def raise_duplicate_field(field: str):
    """خطای 400 برای فیلد تکراری"""
    label = FIELD_LABELS.get(field, field)
    raise HTTPException(
        status_code=400,
        detail={
            "code": "DUPLICATE_FIELD",
            "field": field,
            "label": label,
            "message": f"«{label}» تکراری است. لطفاً مقدار دیگری وارد کنید.",
        },
    )

def parse_integrity_error_field(e: IntegrityError) -> Optional[str]:
    """SQLite error از IntegrityError فیلد را استخراج کند"""
    msg = str(getattr(e, "orig", e))
    msg_lower = msg.lower()

    if "unique constraint failed:" in msg_lower:
        tail = msg.split("UNIQUE constraint failed:", 1)[-1].strip()
        first_part = tail.split(",")[0].strip()
        field = first_part.split(".")[-1].strip() if "." in first_part else first_part
        return field if field else None

    return None

def raise_from_integrity_error(e: IntegrityError):
    """IntegrityError را به پیام کاربرپسند تبدیل کن"""
    field = parse_integrity_error_field(e)
    if field:
        raise_duplicate_field(field)

    raise HTTPException(
        status_code=400,
        detail={
            "code": "DUPLICATE_FIELD",
            "message": "یکی از فیلدها تکراری است. لطفاً مقادیر را تغییر دهید.",
        },
    )

# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordResetRequest(BaseModel):
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    full_name: Optional[str] = None

class AssignPlanRequest(BaseModel):
    plan_id: int
    duration_days: int = 30

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/api/auth/register")
def register(request: RegisterRequest, db: Session = Depends(database.get_db)):
    """ثبت نام کاربر جدید"""
    # بررسی اینکه نام کاربری منحصر به فرد است
    existing_user = db.query(models.User).filter(models.User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="نام کاربری تکراری است"
        )
    
    existing_email = db.query(models.User).filter(models.User.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="ایمیل تکراری است"
        )
    
    # ایجاد کاربر جدید
    new_user = models.User(
        username=request.username,
        email=request.email,
        full_name=request.full_name,
        hashed_password=auth.get_password_hash(request.password),
        role="ADMIN"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role
    }

@app.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(database.get_db)):
    user = auth.authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
        )
    tokens = auth.create_tokens(user.username)
    return tokens

@app.get("/api/auth/me")
def get_current_user(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    return current_user

# ============================================================================
# CANDIDATES ENDPOINTS (Now operating on Users with role=CANDIDATE)
# ============================================================================

@app.get("/api/candidates", response_model=List[schemas.Candidate])
def get_candidates(db: Session = Depends(database.get_db)):
    return db.query(models.User).filter(models.User.role == "CANDIDATE").order_by(models.User.id.desc()).all()

@app.get("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def get_candidate(candidate_id: int, db: Session = Depends(database.get_db)):
    candidate = db.query(models.User).filter(models.User.id == candidate_id, models.User.role == "CANDIDATE").first()
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")
    return candidate

@app.post("/api/candidates", response_model=schemas.Candidate)
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
            raise HTTPException(
                status_code=422,
                detail={"message": "نام کاربری و رمز عبور برای ایجاد نماینده الزامی است"},
            )

        # ✅ تاریخ شمسی
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

@app.put("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate(
    candidate_id: int,
    candidate_data: schemas.CandidateUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    candidate = db.query(models.User).filter(models.User.id == candidate_id, models.User.role == "CANDIDATE").first()
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    # Check permissions: Admin or the candidate themselves
    if current_user.role != "ADMIN":
        if candidate.id != current_user.id:
            raise HTTPException(status_code=403, detail="شما اجازه ویرایش این کاندید را ندارید")

    data = candidate_data.model_dump(exclude_unset=True) if hasattr(candidate_data, "model_dump") else candidate_data.dict()

    try:
        # Handle password update separately
        if "password" in data and data["password"]:
            candidate.hashed_password = auth.get_password_hash(data["password"])
            del data["password"]

        # Map 'name' to 'full_name'
        if "name" in data:
            candidate.full_name = data["name"]
            del data["name"]

        for key, value in data.items():
            if hasattr(candidate, key) and value is not None:
                setattr(candidate, key, value)

        db.commit()
        db.refresh(candidate)
        return candidate

    except IntegrityError as e:
        db.rollback()
        raise_from_integrity_error(e)
    except HTTPException:
        db.rollback()
        raise

@app.delete("/api/candidates/{candidate_id}")
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

@app.post("/api/candidates/{candidate_id}/reset-password")
def reset_candidate_password(
    candidate_id: int,
    body: PasswordResetRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user),
):
    candidate = db.query(models.User).filter(models.User.id == candidate_id, models.User.role == "CANDIDATE").first()
    if not candidate:
        raise HTTPException(status_code=404, detail="کاندید یافت نشد")

    candidate.hashed_password = auth.get_password_hash(body.password)
    db.add(candidate)
@app.post("/api/candidates/{candidate_id}/assign-plan")
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

    db.commit()

    return {"detail": "رمز عبور با موفقیت تغییر کرد"}

# ============================================================================
# PLANS ENDPOINTS
# ============================================================================

@app.get("/api/plans")
def get_plans(db: Session = Depends(database.get_db)):
    return db.query(models.Plan).order_by(models.Plan.id.desc()).all()

@app.post("/api/plans", response_model=schemas.Plan)
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

@app.put("/api/plans/{plan_id}", response_model=schemas.Plan)
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

@app.delete("/api/plans/{plan_id}")
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

# ============================================================================
# TICKETS ENDPOINTS
# ============================================================================

@app.get("/api/tickets", response_model=List[schemas.Ticket])
def get_tickets(db: Session = Depends(database.get_db)):
    return db.query(models.Ticket).order_by(models.Ticket.id.desc()).all()

@app.post("/api/tickets", response_model=schemas.Ticket)
def create_ticket(
    ticket_data: schemas.TicketCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # If user is candidate, they are creating ticket for themselves
    # If user is admin, they might be creating for someone else (not implemented yet, assuming self)
    
    if current_user.role == "CANDIDATE":
        user_id = current_user.id
    else:
        # Admin creating ticket? For now let's say admin creates for themselves or we need a field
        user_id = current_user.id

    new_ticket = models.Ticket(
        user_id=user_id,
        subject=ticket_data.subject,
        status="OPEN"
    )
    db.add(new_ticket)
    db.flush() # Get ID

    # Add initial message
    initial_msg = models.TicketMessage(
        ticket_id=new_ticket.id,
        sender_role=current_user.role,
        text=ticket_data.message
    )
    db.add(initial_msg)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket

@app.post("/api/tickets/{ticket_id}/messages", response_model=schemas.TicketMessage)
def add_ticket_message(
    ticket_id: int,
    message_data: schemas.TicketMessageCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    new_msg = models.TicketMessage(
        ticket_id=ticket_id,
        sender_role=message_data.sender_role,
        text=message_data.text,
        attachment_url=message_data.attachment_url,
        attachment_type=message_data.attachment_type
    )
    
    ticket.updated_at = datetime.utcnow()
    if message_data.sender_role == "ADMIN":
        ticket.status = "ANSWERED"
    else:
        ticket.status = "OPEN"

    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg

@app.put("/api/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    update: schemas.TicketUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_admin_user)
):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = update.status
    db.commit()
    return {"message": "Status updated"}

# ============================================================================
# ANNOUNCEMENTS ENDPOINTS
# ============================================================================

@app.get("/api/announcements", response_model=List[schemas.Announcement])
def get_announcements(db: Session = Depends(database.get_db)):
    return db.query(models.Announcement).order_by(models.Announcement.id.desc()).all()

@app.post("/api/announcements", response_model=schemas.Announcement)
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
        created_at_jalali=created_at_jalali
    )
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    return new_announcement

@app.get("/")
async def root():
    return {"message": "Election Manager API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
