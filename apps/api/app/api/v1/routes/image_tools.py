from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.core.auth_store import consume_user_credits, get_current_user, refund_user_credits
from app.core.config.settings import settings
from app.core.conversion_jobs import (
    cancel_user_job,
    configure_job_processor,
    create_job,
    get_user_job,
    public_job,
)
from app.core.image_tools import IMAGE_TOOL_COSTS, process_image_tool
from app.core.image_tools.processing import SUPPORTED_IMAGE_FORMATS, validate_image_file
from app.core.security.file_security import FileSecurityError, validate_file_name, validate_upload_size


router = APIRouter(prefix="/image-tools", tags=["Image Tools"])
logger = logging.getLogger("polaryix.image_tools")

configure_job_processor("image_tool", process_image_tool)


def _is_premium(user: dict) -> bool:
    return bool(user.get("is_premium")) and str(user.get("plan") or "free") != "free"


async def _create_image_tool_job(request: Request, operation: str, file: UploadFile) -> dict:
    user = get_current_user(request, required=True)
    safe_name = validate_file_name(file.filename or "image")
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use PNG, JPG, JPEG ou WEBP.")

    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O arquivo enviado precisa ser uma imagem.")

    cost = IMAGE_TOOL_COSTS[operation]
    upload_dir = settings.storage_path / "jobs" / "image_tools"
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = upload_dir / f"{uuid4().hex}{suffix}"

    try:
        size_bytes = await validate_upload_size(file)
        max_bytes = int(user.get("max_file_size_mb", settings.max_free_file_size_mb)) * 1024 * 1024
        if size_bytes > max_bytes:
            raise FileSecurityError(f"Arquivo grande demais para seu plano. Limite atual: {user.get('max_file_size_mb')} MB.")

        with input_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
        validate_image_file(input_path)
        consume_user_credits(str(user["id"]), cost)
        logger.info("Image tool credits debited: user=%s operation=%s amount=%s", user["id"], operation, cost)
    except FileSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    priority = 10 if _is_premium(user) else 1
    try:
        job = create_job(
            user_id=str(user["id"]),
            original_filename=safe_name,
            job_type="image_tool",
            operation=operation,
            input_path=str(input_path),
            input_format=SUPPORTED_IMAGE_FORMATS[suffix],
            output_format="PNG" if operation == "remove_background" else SUPPORTED_IMAGE_FORMATS[suffix],
            priority=priority,
            credits_cost=cost,
            is_premium=_is_premium(user),
        )
    except Exception:
        refund_user_credits(str(user["id"]), cost)
        raise

    return {
        "job_id": job["id"],
        "status": job["status"],
        "operation": operation,
        "tokens_cost": cost,
        "is_premium": _is_premium(user),
        "queue_position": job.get("queue_position"),
        "job": job,
    }


@router.post("/remove-background", status_code=status.HTTP_201_CREATED)
async def remove_background(request: Request, file: UploadFile = File(...)) -> dict:
    return await _create_image_tool_job(request, "remove_background", file)


@router.post("/optimize", status_code=status.HTTP_201_CREATED)
async def optimize(request: Request, file: UploadFile = File(...)) -> dict:
    return await _create_image_tool_job(request, "optimize_image", file)


@router.post("/remaster", status_code=status.HTTP_201_CREATED)
async def remaster(request: Request, file: UploadFile = File(...)) -> dict:
    return await _create_image_tool_job(request, "remaster_image", file)


@router.get("/jobs/{job_id}")
async def get_image_tool_job(request: Request, job_id: str) -> dict:
    user = get_current_user(request, required=True)
    job = get_user_job(str(user["id"]), job_id)
    if job.get("job_type") != "image_tool":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de imagem nao encontrado.")
    public = public_job(job)
    return {
        "job_id": public["id"],
        "operation": public["operation"],
        "status": public["status"],
        "queue_position": public["queue_position"],
        "created_at": public["created_at"],
        "started_at": public["started_at"],
        "finished_at": public["finished_at"],
        "error_message": public["error_message"],
        "download_url": f"/api/v1/image-tools/jobs/{job_id}/download" if public["status"] == "completed" else None,
        "job": public,
    }


@router.delete("/jobs/{job_id}")
async def cancel_image_tool_job(request: Request, job_id: str) -> dict:
    user = get_current_user(request, required=True)
    job = get_user_job(str(user["id"]), job_id)
    if job.get("job_type") != "image_tool":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de imagem nao encontrado.")
    return {"job": cancel_user_job(str(user["id"]), job_id)}


@router.get("/jobs/{job_id}/download")
async def download_image_tool_job(request: Request, job_id: str) -> FileResponse:
    user = get_current_user(request, required=True)
    job = get_user_job(str(user["id"]), job_id)
    if job.get("job_type") != "image_tool":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de imagem nao encontrado.")
    if job.get("status") != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Processamento ainda nao concluido.")

    file_path = Path(str(job.get("output_path") or ""))
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo final nao encontrado.")

    return FileResponse(file_path, media_type="application/octet-stream", filename=file_path.name)
