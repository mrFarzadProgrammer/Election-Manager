# schemas.py
from pydantic import BaseModel
from typing import List, Optional

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str

    class Config:
        from_attributes = True  # در نسخه‌های جدید Pydantic جایگزین orm_mode شده

# --- Plan Schemas ---
class PlanBase(BaseModel):
    title: str
    description: str

class PlanCreate(PlanBase):
    pass

class Plan(PlanBase):
    id: int
    candidate_id: int

    class Config:
        from_attributes = True

# --- Candidate Schemas ---
class CandidateBase(BaseModel):
    name: str
    slogan: Optional[str] = None
    bio: Optional[str] = None
    image_url: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class Candidate(CandidateBase):
    id: int
    vote_count: int
    plans: List[Plan] = []

    class Config:
        from_attributes = True

# --- Ticket Schemas ---
class TicketCreate(BaseModel):
    user_id: str
    candidate_id: int

class TicketUpdate(BaseModel):
    status: str

class Ticket(BaseModel):
    id: int
    user_id: str
    candidate_id: int
    status: str

    class Config:
        from_attributes = True
