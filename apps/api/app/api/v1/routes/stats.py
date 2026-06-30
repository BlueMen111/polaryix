from __future__ import annotations

from fastapi import APIRouter

from app.core.public_stats import get_public_stats


router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/public")
async def public_stats() -> dict:
    return get_public_stats()
