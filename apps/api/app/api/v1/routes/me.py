from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.auth_store import get_current_user
from app.core.conversion_history import get_user_record, list_user_records, mark_record_downloaded, public_record


router = APIRouter(prefix="/me", tags=["Me"])


@router.get("/files")
async def my_files(request: Request, limit: int = 20) -> dict:
    user = get_current_user(request, required=True)
    return {"files": list_user_records(str(user["id"]), limit)}


@router.get("/files/{file_id}")
async def my_file_status(request: Request, file_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"file": public_record(get_user_record(str(user["id"]), file_id))}


@router.get("/files/{file_id}/download")
async def download_my_file(request: Request, file_id: str) -> FileResponse:
    user = get_current_user(request, required=True)
    record = get_user_record(str(user["id"]), file_id)
    public = public_record(record)

    if public["status"] != "completed":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Arquivo expirado ou ainda indisponivel.")

    file_path = Path(str(record.get("output_path") or ""))
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo final nao encontrado.")

    filename = Path(str(record.get("original_filename") or file_path.name)).stem
    target = str(record.get("target_format") or file_path.suffix.lstrip(".")).lower()
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=f"{filename}-polaryix.{target}",
        background=BackgroundTask(mark_record_downloaded, str(user["id"]), file_id),
    )
