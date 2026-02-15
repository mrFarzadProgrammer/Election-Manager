from __future__ import annotations

import mimetypes
import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import auth
import database
import models


router = APIRouter(tags=["uploads"])


UPLOAD_DIR = "uploads"
UPLOAD_PRIVATE_DIR = "uploads_private"


def upload_file_path_from_localhost_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None
    prefixes = (
        "http://localhost:8000/uploads/",
        "http://127.0.0.1:8000/uploads/",
    )
    if not url.startswith(prefixes):
        return None
    filename = url.split("/uploads/", 1)[-1]
    filename = filename.split("?", 1)[0].split("#", 1)[0]
    filename = filename.replace("..", "").lstrip("/\\")
    local_path = os.path.join(os.path.dirname(__file__), "..", UPLOAD_DIR, filename)
    local_path = os.path.normpath(local_path)
    return local_path if os.path.exists(local_path) else None


@router.post("/api/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    candidate_name: str | None = Form(None),
    visibility: str | None = Form(None),
    current_user: models.User = Depends(auth.get_current_user),
):
    def _safe_part(value: str) -> str:
        v = (value or "").strip()
        v = re.sub(r"\s+", "_", v)
        v = re.sub(r"[^\w\-\.]+", "", v, flags=re.UNICODE)
        v = v.strip("._-")
        return (v[:80] or "file")

    v = (visibility or os.getenv("UPLOAD_DEFAULT_VISIBILITY") or "public").strip().lower()
    if v not in {"public", "private"}:
        raise HTTPException(status_code=422, detail={"message": "visibility باید public یا private باشد."})

    original_name = (file.filename or "").strip()
    original_ext = os.path.splitext(original_name)[1].lower()
    if not original_ext or len(original_ext) > 10:
        guessed = mimetypes.guess_extension(file.content_type or "") or ""
        original_ext = guessed if guessed.startswith(".") else ""
    ext = original_ext or ".bin"

    content_type = (file.content_type or "").strip().lower()

    denied_exts = {
        ".html",
        ".htm",
        ".js",
        ".mjs",
        ".cjs",
        ".svg",
        ".xml",
        ".php",
        ".py",
        ".sh",
        ".bat",
        ".ps1",
        ".exe",
        ".dll",
        ".msi",
        ".jar",
    }
    if ext in denied_exts:
        raise HTTPException(status_code=422, detail={"message": "این نوع فایل مجاز نیست."})

    # For public uploads, use a conservative allow-list.
    if v == "public":
        default_allowed_exts = {
            ".txt",
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".gif",
            ".mp3",
            ".ogg",
        }
        raw_allowed = (os.getenv("UPLOAD_PUBLIC_ALLOW_EXTS") or "").strip()
        allowed_exts = (
            {e.strip().lower() for e in raw_allowed.split(",") if e.strip()}
            if raw_allowed
            else default_allowed_exts
        )
        if ext not in allowed_exts:
            raise HTTPException(status_code=422, detail={"message": "این نوع فایل برای آپلود عمومی مجاز نیست."})

        allowed_ct_prefixes = ("image/", "audio/")
        allowed_ct_exact = {"application/pdf", "text/plain", "application/ogg"}
        if content_type and not (content_type.startswith(allowed_ct_prefixes) or content_type in allowed_ct_exact):
            raise HTTPException(status_code=422, detail={"message": "نوع فایل معتبر نیست."})

    prefix = "معرفی-صوتی"
    who = _safe_part(candidate_name or "")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    base = f"{prefix}-{who}" if who else prefix
    filename = f"{base}-{ts}-{suffix}{ext}"

    MAX_BYTES = 10 * 1024 * 1024
    try:
        env_max = int((os.getenv("UPLOAD_MAX_BYTES") or "").strip() or "0")
        if env_max > 0:
            MAX_BYTES = env_max
    except Exception:
        pass

    target_dir = UPLOAD_DIR if v == "public" else UPLOAD_PRIVATE_DIR
    os.makedirs(target_dir, exist_ok=True)
    file_location = os.path.join(target_dir, filename)
    written = 0
    try:
        with open(file_location, "wb+") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_BYTES:
                    raise HTTPException(status_code=413, detail={"message": "حجم فایل بیش از حد مجاز است."})
                buffer.write(chunk)
    except HTTPException:
        try:
            if os.path.exists(file_location):
                os.remove(file_location)
        except Exception:
            pass
        raise
    finally:
        try:
            await file.close()
        except Exception:
            pass

    if v == "public":
        base_url = ""
        try:
            if request is not None and request.base_url:
                base_url = str(request.base_url).rstrip("/")
        except Exception:
            base_url = ""
        url = f"{base_url}/uploads/{filename}" if base_url else f"/uploads/{filename}"
        return {"url": url, "filename": filename, "visibility": "public"}

    asset = models.UploadAsset(
        owner_user_id=int(current_user.id),
        visibility="private",
        stored_filename=filename,
        original_filename=(original_name or None),
        content_type=(file.content_type or None),
    )
    db = database.SessionLocal()
    try:
        db.add(asset)
        db.commit()
        db.refresh(asset)
    finally:
        db.close()

    base_url = ""
    try:
        if request is not None and request.base_url:
            base_url = str(request.base_url).rstrip("/")
    except Exception:
        base_url = ""
    url = f"{base_url}/api/uploads/private/{asset.id}" if base_url else f"/api/uploads/private/{asset.id}"
    return {"url": url, "id": asset.id, "filename": filename, "visibility": "private"}


@router.get("/api/uploads/private/{asset_id}")
def download_private_upload(
    asset_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    asset = db.query(models.UploadAsset).filter(models.UploadAsset.id == str(asset_id)).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="File not found")

    if current_user.role != "ADMIN" and int(asset.owner_user_id) != int(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    filename = (asset.stored_filename or "").replace("..", "").lstrip("/\\")
    path = os.path.join(UPLOAD_PRIVATE_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    headers = {"Cache-Control": "no-store"}
    media_type = (asset.content_type or "application/octet-stream").strip() or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        filename=asset.original_filename or asset.stored_filename,
        headers=headers,
    )


@router.post("/api/upload/voice-intro")
async def upload_voice_intro(
    request: Request,
    file: UploadFile = File(...),
    candidate_name: str | None = Form(None),
    current_user: models.User = Depends(auth.get_current_user),
):
    MAX_BYTES = 2 * 1024 * 1024
    allowed_exts = {".mp3", ".ogg"}
    allowed_ct_prefixes = ("audio/",)
    allowed_ct_exact = {"application/ogg"}

    original_name = (file.filename or "").strip()
    ext = os.path.splitext(original_name)[1].lower()
    content_type = (file.content_type or "").strip().lower()

    if ext not in allowed_exts:
        raise HTTPException(status_code=422, detail={"message": "فرمت فایل صوتی باید mp3 یا ogg باشد."})
    if content_type and not (content_type.startswith(allowed_ct_prefixes) or content_type in allowed_ct_exact):
        raise HTTPException(status_code=422, detail={"message": "نوع فایل معتبر نیست. فقط فایل صوتی مجاز است."})

    def _safe_part(value: str) -> str:
        v = (value or "").strip()
        v = re.sub(r"\s+", "_", v)
        v = re.sub(r"[^\w\-\.]+", "", v, flags=re.UNICODE)
        v = v.strip("._-")
        return (v[:80] or "file")

    prefix = "معرفی-صوتی"
    who = _safe_part(candidate_name or "")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    base = f"{prefix}-{who}" if who else prefix
    filename = f"{base}-{ts}-{suffix}{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_location = os.path.join(UPLOAD_DIR, filename)

    written = 0
    try:
        with open(file_location, "wb+") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_BYTES:
                    raise HTTPException(status_code=413, detail={"message": "حجم فایل صوتی باید حداکثر ۲ مگابایت باشد."})
                buffer.write(chunk)
    except HTTPException:
        try:
            if os.path.exists(file_location):
                os.remove(file_location)
        except Exception:
            pass
        raise
    finally:
        try:
            await file.close()
        except Exception:
            pass

    base_url = ""
    try:
        if request is not None and request.base_url:
            base_url = str(request.base_url).rstrip("/")
    except Exception:
        base_url = ""
    url = f"{base_url}/uploads/{filename}" if base_url else f"/uploads/{filename}"
    return {"url": url, "filename": filename}
