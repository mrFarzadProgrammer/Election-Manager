# models.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="USER") # مقادیر: "ADMIN" یا "USER"

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slogan = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    vote_count = Column(Integer, default=0)

    plans = relationship("Plan", back_populates="candidate", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="candidate")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))

    candidate = relationship("Candidate", back_populates="plans")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String) # شناسه کاربری که رای داده
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    status = Column(String, default="pending") # pending, approved, rejected

    candidate = relationship("Candidate", back_populates="tickets")
