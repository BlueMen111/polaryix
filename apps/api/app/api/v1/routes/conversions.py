from __future__ import annotations

import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.v1.routes.converter import (
    _convert_stored_file,
    _normalize_format,
    _request_account,
    _save_upload,
    _validate_conversion_or_raise,
)
from app.core.auth_store import consume_user_credits, get_current_user, refund_user_credits
from app.core.config.settings import settings
from app.core.conversion_history import create_conversion_record, ensure_storage_available, update_conversion_record
from app.core.credit_costs import CONVERSION_CREDIT_COST
from app.core.conversion_jobs import (
    cancel_user_job,
    configure_conversion_job_processor,
    create_job,
    get_user_job,
    list_user_jobs,
    public_job,
)
from app.core.security.file_security import FileSecurityError


router = APIRouter(prefix="/conversions", tags=["Conversions"])
logger = logging.getLogger("polaryix.conversions")


def is_premium_user(user: dict) -> bool:
    return bool(user.get("is_premium")) and str(user.get("plan") or "free") != "free"


def _process_conversion_job(job: dict) -> dict:
    input_path = Path(str(job["input_path"]))
    if not input_path.exists() or input_path.stat().st_size == 0:
        raise RuntimeError("Arquivo original nao encontrado para conversao.")

    output_dir = settings.processed_path / "conversions"
    output_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = settings.storage_path / "jobs" / "work" / str(job["id"])
    temp_dir.mkdir(parents=True, exist_ok=True)

    output_path, output_name = _convert_stored_file(
        input_path=input_path,
        original_name=str(job["original_filename"]),
        source_format=str(job["input_format"]),
        target_format=str(job["output_format"]),
        workdir=temp_dir,
    )

    final_path = output_dir / f"{uuid4().hex}-{output_name}"
    shutil.copyfile(output_path, final_path)
    update_conversion_record(str(job["id"]), output_path=str(final_path), file_size=final_path.stat().st_size)
    return {"output_path": str(final_path), "file_size": final_path.stat().st_size}


configure_conversion_job_processor(_process_conversion_job)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversion(
    request: Request,
    file: UploadFile = File(...),
    from_format: str | None = Form(None),
    to_format: str | None = Form(None),
    output_format: str | None = Form(None),
) -> dict:
    user = get_current_user(request, required=True)
    target_value = output_format or to_format
    if not target_value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o formato de saida.")

    source_format = _normalize_format(from_format or Path(file.filename or "").suffix.lstrip("."))
    target_format = _normalize_format(target_value)
    _validate_conversion_or_raise(source_format, target_format)

    account = _request_account(request)
    priority = 10 if is_premium_user(user) else 1
    credits_cost = CONVERSION_CREDIT_COST

    upload_dir = settings.storage_path / "jobs" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = upload_dir / f"{uuid4().hex}.{source_format.lower()}"

    try:
        safe_name = await _save_upload(file, input_path, source_format, account)
        ensure_storage_available(user, input_path.stat().st_size)
        consume_user_credits(str(user["id"]), credits_cost)
        logger.info("Conversion credits debited: user=%s amount=%s", user["id"], credits_cost)
    except FileSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        job = create_job(
            user_id=str(user["id"]),
            original_filename=safe_name,
            input_path=str(input_path),
            input_format=source_format,
            output_format=target_format,
            priority=priority,
            credits_cost=credits_cost,
        )
        create_conversion_record(
            id=job["id"],
            user_id=str(user["id"]),
            original_filename=safe_name,
            original_format=source_format,
            target_format=target_format,
            input_path=str(input_path),
            status="queued",
            is_premium_job=priority >= 10,
            priority_level=priority,
            user=user,
            operation_type="conversion",
            extension=target_format.lower(),
        )
    except Exception:
        refund_user_credits(str(user["id"]), credits_cost)
        logger.info("Conversion credits refunded after create failure: user=%s amount=%s", user["id"], credits_cost)
        raise

    return {"job": job}


@router.get("")
async def list_conversions(request: Request, limit: int = 50) -> dict:
    user = get_current_user(request, required=True)
    return {"jobs": list_user_jobs(str(user["id"]), limit)}


@router.get("/{job_id}")
async def get_conversion(request: Request, job_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"job": public_job(get_user_job(str(user["id"]), job_id))}


@router.delete("/{job_id}")
async def cancel_conversion(request: Request, job_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"job": cancel_user_job(str(user["id"]), job_id)}


@router.get("/{job_id}/download")
async def download_conversion(request: Request, job_id: str) -> FileResponse:
    user = get_current_user(request, required=True)
    job = get_user_job(str(user["id"]), job_id)

    if job.get("status") != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversao ainda nao concluida.")

    file_path = Path(str(job.get("output_path") or ""))
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo convertido nao encontrado.")

    filename = Path(str(job.get("original_filename") or file_path.name)).stem
    target = str(job.get("output_format") or file_path.suffix.lstrip(".")).lower()
    return FileResponse(file_path, media_type="application/octet-stream", filename=f"{filename}-polaryix.{target}")
