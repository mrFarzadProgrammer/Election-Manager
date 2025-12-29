# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
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
    image_url = Column(String, nullable=True)
    resume = Column(String, nullable=True)
    ideas = Column(String, nullable=True)
    address = Column(String, nullable=True)
    voice_url = Column(String, nullable=True)
    socials = Column(JSON, nullable=True)
    bot_config = Column(JSON, nullable=True)
    vote_count = Column(Integer, default=0)
    created_at_jalali = Column(String, nullable=True)

    # Relationships
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
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

    user = relationship("User", back_populates="plans")

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

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    media_url = Column(String, nullable=True)
    media_type = Column(String, nullable=True) # IMAGE, VIDEO, VOICE, TEXT
    created_at = Column(DateTime, default=datetime.utcnow)
    created_at_jalali = Column(String, nullable=True)
