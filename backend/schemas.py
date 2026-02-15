# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CommitmentCategory(str):
    pass

class CommitmentStatus(str):
    pass

class CommitmentTermsAcceptanceOut(BaseModel):
    id: str
    representative_id: int
    accepted_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    version: str = "v1"

    class Config:
        from_attributes = True

class CommitmentProgressLogOut(BaseModel):
    id: int
    note: str
    created_at: datetime

    class Config:
        from_attributes = True

class CommitmentCreate(BaseModel):
    title: str
    description: str
    category: str

class CommitmentUpdateDraft(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None

class CommitmentUpdateStatus(BaseModel):
    status: str

class CommitmentAddProgress(BaseModel):
    note: str

class CommitmentOut(BaseModel):
    id: int
    title: str
    description: str = Field(..., alias="body")
    category: Optional[str] = None
    created_by: int = Field(..., alias="candidate_id")
    created_at: datetime
    published_at: Optional[datetime] = None
    status: str
    status_updated_at: datetime
    is_locked: bool = Field(..., alias="locked")
    progress_logs: List[CommitmentProgressLogOut] = Field(default_factory=list)

    class Config:
        from_attributes = True
        populate_by_name = True

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
    password: str = Field(min_length=8)
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
    password: Optional[str] = Field(default=None, min_length=8)  # Added for password update
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
    messages: List[TicketMessage] = Field(default_factory=list)
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    password: str = Field(min_length=8)

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


# --- Admin MVP Learning Panel ---


class MvpOverviewCounters(BaseModel):
    total_users: int
    active_users: int
    total_questions: int
    answered_questions: int
    total_comments: int
    total_commitments: int
    total_leads: int


class MvpRepresentativeOverview(BaseModel):
    candidate_id: int
    name: Optional[str] = None
    counters: MvpOverviewCounters


class MvpOverviewResponse(BaseModel):
    global_counters: MvpOverviewCounters
    per_candidate: List[MvpRepresentativeOverview]


class BehaviorCounterItem(BaseModel):
    event: str
    count: int


class BehaviorStatsResponse(BaseModel):
    candidate_id: Optional[int] = None
    items: List[BehaviorCounterItem]


class FlowPathItem(BaseModel):
    path: str
    count: int


class FlowPathsResponse(BaseModel):
    candidate_id: Optional[int] = None
    items: List[FlowPathItem]


class QuestionLearningItem(BaseModel):
    question_id: int = Field(..., alias="id")
    user_id: str = Field(..., alias="telegram_user_id")
    representative_id: int = Field(..., alias="candidate_id")
    category: Optional[str] = Field(None, alias="topic")
    question_text: str = Field(..., alias="text")
    status: str
    created_at: datetime
    answered_at: Optional[datetime] = None
    answer_views_count: int = 0
    channel_click_count: int = 0

    class Config:
        from_attributes = True
        populate_by_name = True


class CommitmentLearningItem(BaseModel):
    commitment_id: int = Field(..., alias="id")
    representative_id: int = Field(..., alias="candidate_id")
    title: str
    body: str
    created_at: datetime
    view_count: int = 0

    class Config:
        from_attributes = True
        populate_by_name = True


class LeadItem(BaseModel):
    lead_id: int = Field(..., alias="id")
    created_at: datetime
    representative_id: int = Field(..., alias="candidate_id")
    user_id: str = Field(..., alias="telegram_user_id")
    username: Optional[str] = Field(None, alias="telegram_username")
    selected_role: Optional[str] = Field(None, alias="topic")
    phone: Optional[str] = Field(None, alias="requester_contact")

    class Config:
        from_attributes = True
        populate_by_name = True


class UxLogItem(BaseModel):
    id: int
    representative_id: int = Field(..., alias="candidate_id")
    user_id: str = Field(..., alias="telegram_user_id")
    state: Optional[str] = None
    action: str
    expected_action: Optional[str] = None
    timestamp: datetime = Field(..., alias="created_at")

    class Config:
        from_attributes = True
        populate_by_name = True


class GlobalBotUserItem(BaseModel):
    # Required export/list fields
    user_id: str = Field(..., alias="telegram_user_id")
    username: Optional[str] = Field(None, alias="telegram_username")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    platform: str = "TELEGRAM"

    representative_id: int = Field(..., alias="candidate_id")
    bot_id: Optional[str] = Field(None, alias="candidate_bot_name")

    first_interaction_at: datetime = Field(..., alias="first_seen_at")
    last_interaction_at: datetime = Field(..., alias="last_seen_at")
    total_interactions: int = 0

    asked_question: bool = False
    left_comment: bool = False
    viewed_commitment: bool = False
    became_lead: bool = False
    selected_role: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


# --- Monitoring (Minimal & Learning-Focused) ---


class TechnicalErrorItem(BaseModel):
    error_id: int = Field(..., alias="id")
    timestamp: datetime = Field(..., alias="created_at")
    service_name: str
    error_type: str
    error_message: str
    user_id: Optional[str] = Field(None, alias="telegram_user_id")
    representative_id: Optional[int] = Field(None, alias="candidate_id")
    state: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class MonitoringUxLogItem(BaseModel):
    log_id: int = Field(..., alias="id")
    timestamp: datetime = Field(..., alias="created_at")
    user_id: str = Field(..., alias="telegram_user_id")
    representative_id: int = Field(..., alias="candidate_id")
    current_state: Optional[str] = Field(None, alias="state")
    action: str
    expected_action: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class HealthCheckItem(BaseModel):
    id: int
    timestamp: datetime = Field(..., alias="created_at")
    representative_id: Optional[int] = Field(None, alias="candidate_id")
    check_type: str
    status: str

    class Config:
        from_attributes = True
        populate_by_name = True


class FlowDropItem(BaseModel):
    id: int
    representative_id: Optional[int] = Field(None, alias="candidate_id")
    flow_type: str
    started_count: int
    completed_count: int
    abandoned_count: int
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

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
