# models.py
import uuid

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    role = Column(String, default="CANDIDATE") # ADMIN, CANDIDATE
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    phone = Column(String, unique=True, nullable=True, index=True)
    
    # --- Candidate Specific Fields ---
    bot_token = Column(String, nullable=True)
    bot_name = Column(String, nullable=True)
    slogan = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    city = Column(String, nullable=True)
    province = Column(String, nullable=True)
    constituency = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    resume = Column(String, nullable=True)
    ideas = Column(String, nullable=True)
    address = Column(String, nullable=True)
    voice_url = Column(String, nullable=True)
    socials = Column(JSON, nullable=True)
    bot_config = Column(JSON, nullable=True)
    vote_count = Column(Integer, default=0)
    created_at_jalali = Column(String, nullable=True)

    # Subscription Fields
    active_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    plan_start_date = Column(DateTime, nullable=True)
    plan_expires_at = Column(DateTime, nullable=True)

    # Relationships
    plans = relationship("Plan", back_populates="user", foreign_keys="[Plan.user_id]", cascade="all, delete-orphan")
    active_plan = relationship("Plan", foreign_keys=[active_plan_id])
    tickets = relationship("Ticket", back_populates="user")
    
    class Config:
        from_attributes = True

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    price = Column(String, nullable=True)
    description = Column(String)
    features = Column(JSON, nullable=True)
    color = Column(String, default="#3b82f6")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Changed from candidate_id
    is_visible = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_at_jalali = Column(String, nullable=True)

    user = relationship("User", back_populates="plans", foreign_keys=[user_id])

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Changed from candidate_id, and type to Integer
    subject = Column(String, nullable=False)
    status = Column(String, default="OPEN") # OPEN, CLOSED, ANSWERED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")

    @property
    def user_name(self):
        return self.user.username if self.user else None

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    sender_role = Column(String) # ADMIN, CANDIDATE
    text = Column(String)
    attachment_url = Column(String, nullable=True)
    attachment_type = Column(String, nullable=True) # image, voice, file
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="messages")

class BotUser(Base):
    __tablename__ = "bot_users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, index=True)

    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    bot_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BotUserRegistry(Base):
    __tablename__ = "bot_user_registry"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    telegram_user_id = Column(String, index=True, nullable=False)
    telegram_username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    chat_type = Column(String, nullable=True)

    candidate_name = Column(String, nullable=True)
    candidate_bot_name = Column(String, nullable=True)
    candidate_city = Column(String, nullable=True)
    candidate_province = Column(String, nullable=True)
    candidate_constituency = Column(String, nullable=True)

    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # MVP behavior/export fields
    platform = Column(String, default="TELEGRAM", nullable=False)
    total_interactions = Column(Integer, default=0, nullable=False)
    asked_question = Column(Boolean, default=False, nullable=False)
    left_comment = Column(Boolean, default=False, nullable=False)
    viewed_commitment = Column(Boolean, default=False, nullable=False)
    became_lead = Column(Boolean, default=False, nullable=False)
    selected_role = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("candidate_id", "telegram_user_id", name="uq_bot_user_registry_candidate_telegram"),
    )


class BotSubmission(Base):
    __tablename__ = "bot_submissions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    telegram_user_id = Column(String, index=True, nullable=False)
    telegram_username = Column(String, nullable=True)

    # FEEDBACK | QUESTION | BOT_REQUEST
    type = Column(String, index=True, nullable=False)
    topic = Column(String, nullable=True)

    # Snapshot of candidate constituency at submission time (for reporting)
    constituency = Column(String, nullable=True)

    # BOT_REQUEST structured fields (MVP)
    requester_full_name = Column(String, nullable=True)
    requester_contact = Column(String, nullable=True)

    # Manual tag set by candidate/admin for analysis (nullable)
    tag = Column(String, nullable=True)

    text = Column(Text, nullable=False)
    status = Column(String, default="NEW", index=True)
    answer = Column(Text, nullable=True)

    # Question publishing workflow
    answered_at = Column(DateTime, nullable=True)
    is_public = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)

    # Learning counters (MVP)
    answer_views_count = Column(Integer, default=0, nullable=False)
    channel_click_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class BotQuestionVote(Base):
    __tablename__ = "bot_question_votes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bot_submissions.id"), index=True, nullable=False)
    telegram_user_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("submission_id", "telegram_user_id", name="uq_bot_question_vote_submission_user"),
    )


class BotSubmissionPublishLog(Base):
    __tablename__ = "bot_submission_publish_log"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bot_submissions.id"), index=True, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "submission_id", name="uq_bot_publishlog_candidate_submission"),
    )


class BotForumTopic(Base):
    __tablename__ = "bot_forum_topics"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    chat_id = Column(String, index=True, nullable=False)
    category = Column(String, nullable=False)
    thread_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "chat_id", "category", name="uq_bot_forumtopic_candidate_chat_category"),
    )


class BotCommitment(Base):
    __tablename__ = "bot_commitments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # Optional stable key for special commitments (e.g., mandatory first commitment)
    key = Column(String, nullable=True)

    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)

    # Contract fields (Commitments v1)
    category = Column(String, nullable=True)

    # Publication/locking rules:
    # - draft: published_at=NULL, locked=False
    # - published: published_at!=NULL, locked=True
    published_at = Column(DateTime, nullable=True)

    # draft | active | in_progress | completed | failed
    status = Column(String, default="draft", nullable=False)
    status_updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    locked = Column(Boolean, default=False, nullable=False)

    view_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UploadAsset(Base):
    __tablename__ = "upload_assets"

    # Use UUID primary key to prevent enumeration.
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # public | private
    visibility = Column(String, default="private", nullable=False)

    stored_filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    content_type = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User")

    progress_logs = relationship(
        "CommitmentProgressLog",
        back_populates="commitment",
        cascade="all, delete-orphan",
        order_by="CommitmentProgressLog.created_at.asc()",
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "key", name="uq_bot_commitment_candidate_key"),
    )


class CommitmentTermsAcceptance(Base):
    __tablename__ = "commitment_terms_acceptances"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    representative_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False, unique=True)
    accepted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    version = Column(String, default="v1", nullable=False)


class CommitmentProgressLog(Base):
    __tablename__ = "bot_commitment_progress_logs"

    id = Column(Integer, primary_key=True, index=True)
    commitment_id = Column(Integer, ForeignKey("bot_commitments.id"), index=True, nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    commitment = relationship("BotCommitment", back_populates="progress_logs")

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    attachments = Column(JSON, nullable=True) # List of {url, type}
    created_at = Column(DateTime, default=datetime.utcnow)
    created_at_jalali = Column(String, nullable=True)


class BotBehaviorCounter(Base):
    __tablename__ = "bot_behavior_counters"

    id = Column(Integer, primary_key=True, index=True)
    # candidate_id can be NULL to represent global counters
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    event = Column(String, index=True, nullable=False)
    count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "event", name="uq_bot_behavior_candidate_event"),
    )


class BotFlowPathCounter(Base):
    __tablename__ = "bot_flow_path_counters"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    path = Column(String, nullable=False)
    count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "path", name="uq_bot_flowpath_candidate_path"),
    )


class BotUxLog(Base):
    __tablename__ = "bot_ux_logs"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    telegram_user_id = Column(String, index=True, nullable=False)
    state = Column(String, nullable=True)
    action = Column(String, index=True, nullable=False)
    expected_action = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BotUserSession(Base):
    __tablename__ = "bot_user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    telegram_user_id = Column(String, index=True, nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_event_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(String, nullable=True)  # flow_timeout | manual

    has_interaction = Column(Boolean, default=False, nullable=False)
    path = Column(String, nullable=False, default="start")

    # Per-session flags to drive aggregated counters (start -> X)
    saw_ask_question = Column(Boolean, default=False, nullable=False)
    saw_view_commitments = Column(Boolean, default=False, nullable=False)
    saw_about_representative = Column(Boolean, default=False, nullable=False)
    saw_other_features = Column(Boolean, default=False, nullable=False)
    saw_lead_request = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "telegram_user_id", "closed_at", name="uq_bot_session_open_by_user"),
    )


class AdminExportLog(Base):
    __tablename__ = "admin_export_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    export_type = Column(String, nullable=True)
    filters = Column(JSON, nullable=True)


class TechnicalErrorLog(Base):
    __tablename__ = "technical_error_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    service_name = Column(String, nullable=False, index=True)
    error_type = Column(String, nullable=False, index=True)
    error_message = Column(Text, nullable=False)

    telegram_user_id = Column(String, index=True, nullable=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    state = Column(String, nullable=True)


class BotHealthCheck(Base):
    __tablename__ = "bot_health_checks"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    check_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)  # ok | failed


class BotFlowDropCounter(Base):
    __tablename__ = "bot_flow_drop_counters"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    flow_type = Column(String, nullable=False, index=True)  # question | lead | comment
    started_count = Column(Integer, default=0, nullable=False)
    completed_count = Column(Integer, default=0, nullable=False)
    abandoned_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "flow_type", name="uq_bot_flowdrop_candidate_flow"),
    )
