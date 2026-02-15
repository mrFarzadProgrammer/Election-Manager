from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(tags=["misc"])


@router.get("/")
async def root():
    return {"message": "Election Manager API"}


@router.get("/health")
async def health():
    return {"status": "healthy"}
