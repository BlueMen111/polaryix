from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.api.v1.routes.converter import _normalize_format, _validate_conversion_or_raise
from app.core.auth_store import consume_user_credits
from app.core.auth_store import get_current_user, public_user
from app.core.conversion_jobs import create_job
from app.core.credit_costs import CONVERSION_CREDIT_COST
from app.core.image_tools import IMAGE_TOOL_COSTS
from app.core.image_tools.processing import SUPPORTED_IMAGE_FORMATS, is_premium_user, should_apply_watermark, validate_image_file
from app.core.conversion_history import (
    create_conversion_record,
    delete_user_record,
    ensure_storage_available,
    get_user_record,
    list_workspace_records,
    mark_record_downloaded,
    public_record,
    retention_hours,
    set_favorite,
    storage_limit_bytes,
    storage_used_bytes,
    update_conversion_record,
)
from app.core.config.settings import settings
from app.core.security.file_security import FileSecurityError, validate_file_name, validate_file_extension, validate_upload_size


router = APIRouter(tags=["Workspace"])


def _storage_summary(user: dict) -> dict:
    used = storage_used_bytes(str(user["id"]))
    limit = storage_limit_bytes(user)
    return {
        "used": used,
        "limit": limit,
        "percent": round((used / max(limit, 1)) * 100, 1),
        "retention_hours": retention_hours(user),
    }


def _safe_completed_record(user: dict, file_id: str) -> dict:
    record = get_user_record(str(user["id"]), file_id)
    public = public_record(record)
    if public["status"] != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Arquivo indisponivel para esta acao.")
    file_path = Path(str(record.get("output_path") or "")).resolve()
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo final nao encontrado.")
    return record


@router.get("/workspace")
async def workspace(
    request: Request,
    q: str | None = None,
    filter: str = Query("all", pattern="^(all|favorites|expired|completed|queued|processing|failed|deleted)$"),
    limit: int = 100,
) -> dict:
    user = get_current_user(request, required=True)
    favorite = True if filter == "favorites" else None
    status_filter = None if filter in {"all", "favorites"} else filter
    return {
        "files": list_workspace_records(str(user["id"]), limit=limit, favorite=favorite, search=q, status_filter=status_filter),
        "storage": _storage_summary(user),
    }


@router.get("/workspace/favorites")
async def workspace_favorites(request: Request, limit: int = 50) -> dict:
    user = get_current_user(request, required=True)
    return {"files": list_workspace_records(str(user["id"]), limit=limit, favorite=True), "storage": _storage_summary(user)}


@router.post("/workspace/upload", status_code=status.HTTP_201_CREATED)
async def upload_workspace_files(request: Request, files: list[UploadFile] = File(...)) -> dict:
    user = get_current_user(request, required=True)
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecione ao menos um arquivo.")

    saved: list[dict] = []
    upload_dir = settings.storage_path / "workspace" / str(user["id"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        try:
            safe_name = validate_file_name(file.filename or "arquivo")
            validate_file_extension(safe_name)
            size_bytes = await validate_upload_size(file)
            ensure_storage_available(user, size_bytes)
            suffix = Path(safe_name).suffix.lower() or ".bin"
            stored_path = upload_dir / f"{uuid4().hex}{suffix}"
            with stored_path.open("wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    buffer.write(chunk)
        except FileSecurityError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        extension = suffix.lstrip(".")
        record = create_conversion_record(
            user_id=str(user["id"]),
            user=user,
            original_filename=safe_name,
            original_format=extension.upper(),
            target_format=extension.upper(),
            output_path=str(stored_path),
            download_url=None,
            file_size=stored_path.stat().st_size,
            status="completed",
            operation_type="upload",
            mime_type=file.content_type,
            extension=extension,
        )
        record = update_conversion_record(str(record["id"]), download_url=f"/api/v1/workspace/{record['id']}/download") or record
        saved.append(record)

    return {"files": saved, "storage": _storage_summary(user)}


@router.post("/workspace/{file_id}/favorite")
async def favorite_workspace_file(request: Request, file_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"file": set_favorite(str(user["id"]), file_id, True)}


@router.delete("/workspace/{file_id}/favorite")
async def unfavorite_workspace_file(request: Request, file_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"file": set_favorite(str(user["id"]), file_id, False)}


@router.delete("/workspace/{file_id}")
async def delete_workspace_file(request: Request, file_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"file": delete_user_record(str(user["id"]), file_id), "storage": _storage_summary(user)}


@router.post("/workspace/{file_id}/convert", status_code=status.HTTP_201_CREATED)
async def convert_workspace_file(request: Request, file_id: str, target_format: str = Form(...)) -> dict:
    user = get_current_user(request, required=True)
    record = _safe_completed_record(user, file_id)
    input_path = Path(str(record.get("output_path"))).resolve()
    source_format = _normalize_format(str(record.get("extension") or record.get("target_format") or input_path.suffix.lstrip(".")))
    output_format = _normalize_format(target_format)
    _validate_conversion_or_raise(source_format, output_format)

    credits_cost = CONVERSION_CREDIT_COST
    consume_user_credits(str(user["id"]), credits_cost)
    priority = 10 if is_premium_user(user) else 1
    job = create_job(
        user_id=str(user["id"]),
        original_filename=str(record.get("original_filename") or input_path.name),
        input_path=str(input_path),
        input_format=source_format,
        output_format=output_format,
        priority=priority,
        credits_cost=credits_cost,
        is_premium=is_premium_user(user),
        plan=user.get("plan"),
    )
    create_conversion_record(
        id=job["id"],
        user_id=str(user["id"]),
        user=user,
        original_filename=str(record.get("original_filename") or input_path.name),
        original_format=source_format,
        target_format=output_format,
        input_path=str(input_path),
        status="queued",
        operation_type="conversion",
        is_premium_job=priority >= 10,
        priority_level=priority,
        extension=output_format.lower(),
    )
    return {"job": job}


@router.post("/workspace/{file_id}/image-tool", status_code=status.HTTP_201_CREATED)
async def process_workspace_image(
    request: Request,
    file_id: str,
    operation: str = Form(...),
    scale: int = Form(2),
) -> dict:
    user = get_current_user(request, required=True)
    record = _safe_completed_record(user, file_id)
    input_path = Path(str(record.get("output_path"))).resolve()
    suffix = input_path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta ferramenta aceita PNG, JPG, JPEG ou WEBP.")

    operation = "upscale_image" if operation == "remaster_image" else operation
    if operation not in {"remove_background", "optimize_image", "upscale_image"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ferramenta de imagem invalida.")
    validate_image_file(input_path)

    premium = is_premium_user(user)
    normalized_scale = 4 if scale == 4 else 2
    cost = 10 if operation == "upscale_image" and premium and normalized_scale == 4 else IMAGE_TOOL_COSTS[operation]
    consume_user_credits(str(user["id"]), cost)
    priority = 10 if premium else 1
    tool_options = {
        "scale": normalized_scale if premium else 2,
        "keep_original_size": False,
        "model": "u2net",
        "fallback_model": "u2net",
        "use_alpha_matting": False,
    }
    output_format = "PNG" if operation == "remove_background" else SUPPORTED_IMAGE_FORMATS[suffix]
    job = create_job(
        user_id=str(user["id"]),
        original_filename=str(record.get("original_filename") or input_path.name),
        job_type="image_tool",
        operation=operation,
        input_path=str(input_path),
        input_format=SUPPORTED_IMAGE_FORMATS[suffix],
        output_format=output_format,
        priority=priority,
        credits_cost=cost,
        is_premium=premium,
        plan=user.get("plan"),
        should_apply_watermark=should_apply_watermark(user, operation),
        original_size=input_path.stat().st_size,
        tool_options=tool_options,
    )
    create_conversion_record(
        id=job["id"],
        user_id=str(user["id"]),
        user=user,
        original_filename=str(record.get("original_filename") or input_path.name),
        original_format=SUPPORTED_IMAGE_FORMATS[suffix],
        target_format=output_format,
        input_path=str(input_path),
        status="queued",
        operation_type=operation,
        is_premium_job=premium,
        priority_level=priority,
        extension="png" if operation == "remove_background" else suffix.lstrip("."),
    )
    return {"job": job}


@router.get("/workspace/{file_id}/download")
async def download_workspace_file(request: Request, file_id: str) -> FileResponse:
    user = get_current_user(request, required=True)
    record = get_user_record(str(user["id"]), file_id)
    public = public_record(record)
    if public["status"] != "completed":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Arquivo expirado ou indisponivel.")

    file_path = Path(str(record.get("output_path") or "")).resolve()
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo final nao encontrado.")

    filename = Path(str(record.get("original_filename") or file_path.name)).stem
    extension = str(record.get("extension") or record.get("target_format") or file_path.suffix.lstrip(".")).lower()
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=f"{filename}-polaryix.{extension}",
        background=BackgroundTask(mark_record_downloaded, str(user["id"]), file_id),
    )


@router.get("/dashboard")
async def dashboard(request: Request) -> dict:
    user = get_current_user(request, required=True)
    files = list_workspace_records(str(user["id"]), limit=200)
    recent = files[:8]
    favorites = [item for item in files if item.get("is_favorite")][:6]
    active = [item for item in files if item.get("status") in {"queued", "processing"}]
    storage = _storage_summary(user)
    profile = public_user(user)
    return {
        "user": profile,
        "plan": profile["plan"],
        "credits": profile["credits_remaining"],
        "storage": storage,
        "workspace_count": len([item for item in files if item.get("status") != "deleted"]),
        "favorite_count": len(favorites),
        "active_jobs": active[:6],
        "recent_jobs": recent,
        "favorite_files": favorites,
    }
