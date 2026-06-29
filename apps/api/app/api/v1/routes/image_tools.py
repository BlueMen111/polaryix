from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
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
from app.core.image_tools.processing import SUPPORTED_IMAGE_FORMATS, is_premium_user, should_apply_watermark, validate_image_file
from app.core.image_tools.processing import warmup_remove_background_model
from app.core.security.file_security import FileSecurityError, validate_file_name, validate_upload_size


router = APIRouter(tags=["Image Tools"])
logger = logging.getLogger("polaryix.image_tools")

configure_job_processor("image_tool", process_image_tool)

try:
    warmup_remove_background_model()
except Exception as exc:  # pragma: no cover - startup should continue for non-remove tools
    logger.warning("Remove background model warmup failed: %s", exc)


def _is_premium(user: dict) -> bool:
    return is_premium_user(user)


async def _create_image_tool_job(
    request: Request,
    operation: str,
    file: UploadFile,
    scale: int = 2,
    keep_original_size: bool = False,
    sharpness: float | None = None,
    denoise: float | None = None,
    contrast: float | None = None,
    detail: float | None = None,
    intensity: float | None = None,
) -> dict:
    if operation == "remaster_image":
        operation = "upscale_image"
    user = get_current_user(request, required=True)
    safe_name = validate_file_name(file.filename or "image")
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use PNG, JPG, JPEG ou WEBP.")

    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O arquivo enviado precisa ser uma imagem.")

    normalized_scale = 4 if scale == 4 else 2
    cost = 10 if operation == "upscale_image" and normalized_scale == 4 else IMAGE_TOOL_COSTS[operation]
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
    is_premium = _is_premium(user)
    tool_options = {
        "scale": normalized_scale if is_premium else 2,
        "keep_original_size": keep_original_size if is_premium else False,
        "sharpness": sharpness,
        "denoise": denoise,
        "contrast": contrast,
        "detail": detail,
        "intensity": intensity,
        "alpha_threshold": 26,
        "edge_smooth": 1.25,
        "remove_small_artifacts": True,
        "preserve_details": True,
    }
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
            is_premium=is_premium,
            plan=user.get("plan"),
            role=user.get("role"),
            subscription_status=user.get("subscription_status"),
            should_apply_watermark=should_apply_watermark(user, operation),
            original_size=size_bytes,
            tool_options=tool_options,
        )
    except Exception:
        refund_user_credits(str(user["id"]), cost)
        raise

    return {
        "job_id": job["id"],
        "status": job["status"],
        "operation": operation,
        "tokens_cost": cost,
        "is_premium": is_premium,
        "queue_position": job.get("queue_position"),
        "job": job,
    }


@router.post("/image-tools/remove-background", status_code=status.HTTP_201_CREATED)
@router.post("/image/remove-background", status_code=status.HTTP_201_CREATED)
async def remove_background(request: Request, file: UploadFile = File(...)) -> dict:
    return await _create_image_tool_job(request, "remove_background", file)


@router.post("/image-tools/optimize", status_code=status.HTTP_201_CREATED)
@router.post("/image/optimize", status_code=status.HTTP_201_CREATED)
async def optimize(request: Request, file: UploadFile = File(...)) -> dict:
    return await _create_image_tool_job(request, "optimize_image", file)


@router.post("/image-tools/remaster", status_code=status.HTTP_201_CREATED)
@router.post("/image-tools/upscale", status_code=status.HTTP_201_CREATED)
@router.post("/image/upscale", status_code=status.HTTP_201_CREATED)
async def upscale(
    request: Request,
    file: UploadFile = File(...),
    scale: int = Form(2),
    keep_original_size: bool = Form(False),
    sharpness: float | None = Form(None),
    denoise: float | None = Form(None),
    contrast: float | None = Form(None),
    detail: float | None = Form(None),
    intensity: float | None = Form(None),
) -> dict:
    return await _create_image_tool_job(
        request,
        "upscale_image",
        file,
        scale,
        keep_original_size,
        sharpness,
        denoise,
        contrast,
        detail,
        intensity,
    )


@router.get("/image-tools/jobs/{job_id}")
@router.get("/image/jobs/{job_id}")
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


@router.delete("/image-tools/jobs/{job_id}")
@router.delete("/image/jobs/{job_id}")
async def cancel_image_tool_job(request: Request, job_id: str) -> dict:
    user = get_current_user(request, required=True)
    job = get_user_job(str(user["id"]), job_id)
    if job.get("job_type") != "image_tool":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de imagem nao encontrado.")
    return {"job": cancel_user_job(str(user["id"]), job_id)}


@router.get("/image-tools/jobs/{job_id}/download")
@router.get("/image/jobs/{job_id}/download")
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
