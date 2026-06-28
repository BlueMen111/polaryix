from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config.settings import settings
from app.core.conversion_history import cleanup_expired_files


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/cleanup-files")
async def cleanup_files(x_admin_token: str | None = Header(default=None)) -> dict:
    if settings.admin_cleanup_token and x_admin_token != settings.admin_cleanup_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token administrativo invalido.")

    if not settings.admin_cleanup_token and not settings.debug:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Configure ADMIN_CLEANUP_TOKEN para usar este endpoint.")

    return cleanup_expired_files()
