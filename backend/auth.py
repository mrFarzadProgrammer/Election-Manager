# auth.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Header, Cookie
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import models
from database import get_db

load_dotenv()

# Configuration
APP_ENV = (os.getenv("APP_ENV") or os.getenv("ENV") or "development").strip().lower()

_DEFAULT_SECRET = "your-secret-key-change-in-production"
_DEFAULT_REFRESH_SECRET = "your-refresh-secret-key-change-in-production"

SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", _DEFAULT_REFRESH_SECRET)
ALGORITHM = "HS256"


def _env_int(name: str, default: int) -> int:
    try:
        raw = (os.getenv(name) or "").strip()
        return int(raw) if raw else int(default)
    except Exception:
        return int(default)


ACCESS_TOKEN_EXPIRE_MINUTES = max(5, _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = max(1, _env_int("REFRESH_TOKEN_EXPIRE_DAYS", 7))


def _looks_unsafe_secret(value: str, *, default_value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return True
    if v == default_value:
        return True
    # Minimal length check; production should use a long random secret.
    if len(v) < 32:
        return True
    return False


if APP_ENV in {"production", "prod"}:
    if _looks_unsafe_secret(SECRET_KEY, default_value=_DEFAULT_SECRET):
        raise RuntimeError("SECRET_KEY is missing/weak. Set a strong SECRET_KEY in environment for production.")
    if _looks_unsafe_secret(REFRESH_SECRET_KEY, default_value=_DEFAULT_REFRESH_SECRET):
        raise RuntimeError(
            "REFRESH_SECRET_KEY is missing/weak. Set a strong REFRESH_SECRET_KEY in environment for production."
        )

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """رمز عبور را هش کن"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """رمز عبور را تأیید کن"""
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return False
    # چک کردن فعال بودن کاربر
    if not user.is_active:
        return False
    # چک کردن پسورد هش شده با پسورد ورودی
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_tokens(username: str):
    """Access و Refresh token ایجاد کن"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + access_token_expires
    access_payload = {
        "sub": username,
        "exp": expire,
        "type": "access"
    }
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + refresh_token_expires
    refresh_payload = {
        "sub": username,
        "exp": expire,
        "type": "refresh"
    }
    refresh_token = jwt.encode(refresh_payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def decode_refresh_token(refresh_token: str) -> str:
    """Validate refresh token and return username (sub)."""
    try:
        payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if not username or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# --- اصلاح مهم: دریافت توکن از هدر ---
def get_current_user(
    authorization: str | None = Header(None),
    access_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """کاربر جاری را دریافت کن"""
    token: str | None = None

    # Prefer explicit Authorization header for API clients.
    authz = (str(authorization).strip() if authorization is not None else "")
    # Ignore empty/bare scheme values like "Bearer" so cookie-sessions keep working.
    if authz and authz.lower() != "bearer":
        token = authz
    # Browser-safe default: allow HttpOnly cookie-based sessions.
    elif access_token is not None and str(access_token).strip():
        token = str(access_token).strip()
    else:
        raise HTTPException(status_code=401, detail="Missing credentials")
    
    try:
        # جدا کردن Bearer از توکن
        if token and " " in token:
            scheme, raw = token.split(" ", 1)
            scheme = (scheme or "").strip().lower()
            raw = (raw or "").strip()
            if scheme != "bearer" or not raw:
                raise HTTPException(status_code=401, detail="Invalid authentication scheme")
            token = raw

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token payload")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

def get_admin_user(current_user: models.User = Depends(get_current_user)):
    """تأیید کنید کاربر Admin است"""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def get_super_admin_user(current_user: models.User = Depends(get_admin_user)):
    """Restrict access to Super Admin-only endpoints.

    Config:
      SUPER_ADMIN_USERNAMES="admin1,admin2"

    If SUPER_ADMIN_USERNAMES is not set, all ADMIN users are treated as super admin
    (dev-friendly default).
    """
    raw = os.getenv("SUPER_ADMIN_USERNAMES", "").strip()
    if not raw:
        return current_user

    allowed = {u.strip().lower() for u in raw.split(",") if u.strip()}
    if (current_user.username or "").strip().lower() not in allowed:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user

# Dependency برای توکن
async def get_token_from_header(authorization: str = None):
    """توکن را از Header دریافت کن"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    return parts[1]
