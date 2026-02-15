from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas

from ._common import clear_auth_cookies, rate_limit, set_auth_cookies


router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    full_name: str | None = None


@router.post("/api/auth/register", response_model=TokenResponse)
def register(request: RegisterRequest, req: Request, response: Response, db: Session = Depends(database.get_db)):
    """ثبت نام کاربر جدید.

    امنیت: این endpoint نباید نقش ADMIN بسازد. ثبت‌نام عمومی فقط کاربر CANDIDATE می‌سازد.
    """
    rate_limit(req, key="auth:register", limit=10, window_seconds=60)

    username = (request.username or "").strip()
    email = (request.email or "").strip()
    password = (request.password or "").strip()
    full_name = (request.full_name or "").strip() or None

    if not username or not password or not email:
        raise HTTPException(status_code=422, detail="نام کاربری، ایمیل و رمز عبور الزامی است")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="رمز عبور باید حداقل ۸ کاراکتر باشد")

    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="نام کاربری تکراری است")

    existing_email = db.query(models.User).filter(models.User.email == email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="ایمیل تکراری است")

    new_user = models.User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=auth.get_password_hash(password),
        role="CANDIDATE",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    tokens = auth.create_tokens(new_user.username)
    try:
        set_auth_cookies(response, access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])
    except Exception:
        pass
    return tokens


@router.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, req: Request, response: Response, db: Session = Depends(database.get_db)):
    rate_limit(req, key="auth:login", limit=20, window_seconds=60)
    user = auth.authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
        )
    tokens = auth.create_tokens(user.username)
    try:
        set_auth_cookies(response, access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])
    except Exception:
        pass
    return tokens


@router.post("/api/auth/refresh", response_model=TokenResponse)
def refresh_access_token(
    req: Request,
    response: Response,
    db: Session = Depends(database.get_db),
    request: RefreshRequest | None = Body(None),
):
    """Issue a new access token using a valid refresh token."""
    rate_limit(req, key="auth:refresh", limit=30, window_seconds=60)

    refresh_token: str | None = None
    try:
        refresh_token = request.refresh_token if request is not None else None
    except Exception:
        refresh_token = None

    if not refresh_token:
        try:
            refresh_token = (req.cookies.get("refresh_token") if req and req.cookies else None)
        except Exception:
            refresh_token = None

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    username = auth.decode_refresh_token(refresh_token)
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    tokens = auth.create_tokens(username)
    try:
        set_auth_cookies(response, access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])
    except Exception:
        pass
    return tokens


@router.post("/api/auth/logout")
def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "logged out"}


@router.get("/api/auth/me", response_model=schemas.User)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user
