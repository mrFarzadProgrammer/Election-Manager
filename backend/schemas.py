# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- User Schemas ---
class User(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    phone: Optional[str] = None
    
    # Candidate Fields
    bot_token: Optional[str] = None
    bot_name: Optional[str] = None
    slogan: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    constituency: Optional[str] = None
    image_url: Optional[str] = None
    resume: Optional[str] = None
    ideas: Optional[str] = None
    address: Optional[str] = None
    voice_url: Optional[str] = None
    socials: Optional[dict] = None
    bot_config: Optional[dict] = None
    vote_count: int = 0
    created_at_jalali: Optional[str] = None

    class Config:
        from_attributes = True

# --- Candidate Schemas (Mapped to User) ---
# Keeping these names for compatibility with frontend, but they map to User model
class CandidateCreate(BaseModel):
    name: str # Maps to full_name
    username: str
    password: str
    phone: Optional[str] = None
    bot_name: str
    bot_token: str
    slogan: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    constituency: Optional[str] = None
    image_url: Optional[str] = None
    resume: Optional[str] = None
    ideas: Optional[str] = None
    address: Optional[str] = None
    voice_url: Optional[str] = None
    socials: Optional[dict] = None
    bot_config: Optional[dict] = None
    is_active: bool = True

class CandidateUpdate(BaseModel):
    name: Optional[str] = None # Maps to full_name
    username: Optional[str] = None
    password: Optional[str] = None # Added for password update
    phone: Optional[str] = None
    bot_name: Optional[str] = None
    bot_token: Optional[str] = None
    slogan: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    constituency: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    resume: Optional[str] = None
    ideas: Optional[str] = None
    address: Optional[str] = None
    voice_url: Optional[str] = None
    socials: Optional[dict] = None
    bot_config: Optional[dict] = None

class Candidate(BaseModel):
    id: int
    # user_id: Optional[int] = None # Removed, id is user_id
    name: Optional[str] = Field(None, alias="full_name") # Map full_name to name
    username: str
    phone: Optional[str] = None
    bot_token: Optional[str] = None
    bot_name: Optional[str] = None
    slogan: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    constituency: Optional[str] = None
    image_url: Optional[str] = None
    resume: Optional[str] = None
    ideas: Optional[str] = None
    address: Optional[str] = None
    voice_url: Optional[str] = None
    socials: Optional[dict] = None
    bot_config: Optional[dict] = None
    vote_count: int = 0
    is_active: bool = True
    created_at_jalali: Optional[str] = None
    active_plan_id: Optional[int] = None
    plan_start_date: Optional[datetime] = None
    plan_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True # Allow using alias

# --- Plan Schemas ---
class PlanCreate(BaseModel):
    title: str
    price: str
    description: Optional[str] = None
    features: Optional[List[str]] = None
    color: str = "#3b82f6"
    user_id: Optional[int] = None # Changed from candidate_id
    is_visible: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class PlanUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[str] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    color: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_visible: Optional[bool] = None

class Plan(BaseModel):
    id: int
    title: str
    price: str
    description: Optional[str] = None
    features: Optional[List[str]]
    color: str
    user_id: Optional[int] = None # Changed from candidate_id
    is_visible: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    created_at_jalali: Optional[str] = None

    class Config:
        from_attributes = True

# --- Ticket Schemas ---
class TicketMessageCreate(BaseModel):
    text: str
    sender_role: str
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None

class TicketMessage(BaseModel):
    id: int
    sender_role: str
    text: str
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TicketCreate(BaseModel):
    subject: str
    message: str # Initial message

class TicketUpdate(BaseModel):
    status: str

class Ticket(BaseModel):
    id: int
    user_id: int # Changed from candidate_id
    subject: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[TicketMessage] = []
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    password: str = Field(min_length=4)

# --- Bot Submissions (Feedback MVP) ---
class FeedbackStatus(str):
    pass


class FeedbackSubmissionUpdate(BaseModel):
    tag: Optional[str] = None
    status: Optional[str] = None  # NEW | REVIEWED


class FeedbackSubmission(BaseModel):
    id: int
    candidate_id: int
    text: str
    created_at: datetime
    constituency: Optional[str] = None
    status: str
    tag: Optional[str] = None

    class Config:
        from_attributes = True


class FeedbackTagStat(BaseModel):
    tag: str
    count: int
    percent: float


# --- Admin Dashboard (MVP) ---
class AdminDashboardStats(BaseModel):
    active_bots: int
    total_questions: int
    total_feedback: int
    total_bot_requests: int


class AdminCandidateStats(BaseModel):
    candidate_id: int
    total_questions: int
    total_feedback: int
    answered_questions: int


class FeedbackStatsResponse(BaseModel):
    days: int
    total: int
    items: List[FeedbackTagStat]

# --- Public Questions (Q&A) ---

class QuestionStatus:
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"
    REJECTED = "REJECTED"


class QuestionSubmission(BaseModel):
    id: int
    candidate_id: int
    text: str
    topic: Optional[str] = None
    constituency: Optional[str] = None
    status: str
    answer_text: Optional[str] = Field(None, alias="answer")
    answered_at: Optional[datetime] = None
    is_public: bool = False
    is_featured: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class QuestionSubmissionAnswer(BaseModel):
    answer_text: str
    topic: Optional[str] = None
    is_featured: Optional[bool] = None


class QuestionSubmissionMeta(BaseModel):
    topic: Optional[str] = None
    is_featured: Optional[bool] = None


# --- Bot Build Requests (MVP) ---

class BotRequestSubmission(BaseModel):
    id: int
    candidate_id: int
    telegram_user_id: str
    telegram_username: Optional[str] = None
    requester_full_name: Optional[str] = None
    requester_contact: Optional[str] = None
    role: Optional[str] = Field(None, alias="topic")
    constituency: Optional[str] = None
    status: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class BotRequestUpdate(BaseModel):
    status: str


class QuestionSubmissionReject(BaseModel):
    # No body required; keep schema for future extensibility
    reason: Optional[str] = None

# --- Announcement Schemas ---
class AnnouncementCreate(BaseModel):
    title: str
    content: str
    attachments: Optional[List[dict]] = None # List of {url, type}

class Announcement(BaseModel):
    id: int
    title: str
    content: str
    attachments: Optional[List[dict]] = None
    created_at: datetime
    created_at_jalali: Optional[str] = None

    class Config:
        from_attributes = True
