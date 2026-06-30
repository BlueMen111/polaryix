from __future__ import annotations

import json
import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.auth_store import refund_user_credits
from app.core.config.settings import settings
from app.core.conversion_history import storage_limit_bytes, storage_used_bytes, update_conversion_record
from app.core.public_stats import record_public_operation

logger = logging.getLogger("polaryix.conversion_jobs")

JobProcessor = Callable[[dict], dict]

_lock = threading.RLock()
_workers: list[threading.Thread] = []
_started = False
_processors: dict[str, JobProcessor] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def jobs_path() -> Path:
    return settings.storage_path / "jobs" / "conversion_jobs.json"


def read_jobs() -> list[dict]:
    path = jobs_path()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fila de conversoes invalida.") from exc

    return data if isinstance(data, list) else []


def write_jobs(jobs: list[dict]) -> None:
    path = jobs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def configure_conversion_job_processor(processor: JobProcessor) -> None:
    configure_job_processor("conversion", processor)


def configure_job_processor(job_type: str, processor: JobProcessor) -> None:
    _processors[job_type] = processor


def start_persistent_conversion_workers() -> None:
    global _started
    with _lock:
        if _started:
            return

        worker_count = max(int(getattr(settings, "max_concurrent_conversions", settings.conversion_workers)), 1)
        for index in range(worker_count):
            worker = threading.Thread(target=_worker_loop, name=f"polaryix-persistent-conversion-worker-{index + 1}", daemon=True)
            worker.start()
            _workers.append(worker)

        _started = True
        logger.info("Started %s persistent conversion workers.", worker_count)


def create_job(**values: object) -> dict:
    job = {
        "id": str(values.get("id") or uuid4()),
        "user_id": str(values.get("user_id")),
        "original_filename": values.get("original_filename") or "arquivo",
        "job_type": values.get("job_type") or "conversion",
        "operation": values.get("operation") or values.get("job_type") or "conversion",
        "input_path": values.get("input_path"),
        "output_path": values.get("output_path"),
        "input_format": values.get("input_format") or "",
        "output_format": values.get("output_format") or "",
        "status": "queued",
        "priority": int(values.get("priority") or 1),
        "credits_cost": int(values.get("credits_cost") or 1),
        "credits_charged": bool(values.get("credits_charged", True)),
        "credits_refunded": False,
        "is_premium": bool(values.get("is_premium", False)),
        "plan": values.get("plan"),
        "role": values.get("role"),
        "subscription_status": values.get("subscription_status"),
        "should_apply_watermark": bool(values.get("should_apply_watermark", False)),
        "tool_options": values.get("tool_options") or {},
        "original_size": values.get("original_size"),
        "final_size": values.get("final_size"),
        "reduction_percent": values.get("reduction_percent"),
        "message": values.get("message"),
        "error_message": None,
        "created_at": values.get("created_at") or _now(),
        "started_at": None,
        "finished_at": None,
        "cancelled_at": None,
    }

    with _lock:
        jobs = read_jobs()
        jobs.append(job)
        write_jobs(jobs)

    logger.info("Conversion job created: %s user=%s priority=%s", job["id"], job["user_id"], job["priority"])
    start_persistent_conversion_workers()
    return public_job(job)


def list_user_jobs(user_id: str, limit: int = 50) -> list[dict]:
    with _lock:
        jobs = [job for job in read_jobs() if job.get("user_id") == user_id]

    jobs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return [public_job(job) for job in jobs[: max(1, min(limit, 100))]]


def get_user_job(user_id: str, job_id: str) -> dict:
    with _lock:
        job = next((item for item in read_jobs() if item.get("id") == job_id and item.get("user_id") == user_id), None)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversao nao encontrada.")
    return job


def cancel_user_job(user_id: str, job_id: str) -> dict:
    with _lock:
        jobs = read_jobs()
        target = None
        for job in jobs:
            if job.get("id") == job_id and job.get("user_id") == user_id:
                target = job
                break

        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversao nao encontrada.")
        if target.get("status") != "queued":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Apenas conversoes na fila podem ser canceladas.")

        target["status"] = "cancelled"
        target["cancelled_at"] = _now()
        _refund_job_credits(target)
        update_conversion_record(str(target["id"]), status="cancelled", deleted_at=target["cancelled_at"], download_url=None)
        write_jobs(jobs)

    logger.info("Conversion job cancelled: %s", job_id)
    return public_job(target)


def public_job(job: dict) -> dict:
    return {
        "id": job.get("id"),
        "user_id": job.get("user_id"),
        "original_filename": job.get("original_filename"),
        "job_type": job.get("job_type"),
        "operation": job.get("operation"),
        "input_format": job.get("input_format"),
        "output_format": job.get("output_format"),
        "status": job.get("status"),
        "priority": job.get("priority"),
        "credits_cost": job.get("credits_cost"),
        "error_message": job.get("error_message"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "cancelled_at": job.get("cancelled_at"),
        "queue_position": queue_position(str(job.get("id"))) if job.get("status") == "queued" else None,
        "download_url": f"/api/v1/conversions/{job.get('id')}/download" if job.get("status") == "completed" else None,
        "is_priority": int(job.get("priority") or 0) >= 10,
        "is_premium": bool(job.get("is_premium", False)),
        "should_apply_watermark": bool(job.get("should_apply_watermark", False)),
        "original_size": job.get("original_size"),
        "final_size": job.get("final_size"),
        "reduction_percent": job.get("reduction_percent"),
        "message": job.get("message"),
        "tool_options": job.get("tool_options") or {},
    }


def queue_position(job_id: str) -> int | None:
    with _lock:
        queued = [job for job in read_jobs() if job.get("status") == "queued"]
    queued.sort(key=lambda item: (-int(item.get("priority") or 0), str(item.get("created_at") or "")))
    for index, job in enumerate(queued, start=1):
        if job.get("id") == job_id:
            return index
    return None


def _claim_next_job() -> dict | None:
    with _lock:
        jobs = read_jobs()
        queued = [job for job in jobs if job.get("status") == "queued"]
        if not queued:
            return None

        queued.sort(key=lambda item: (-int(item.get("priority") or 0), str(item.get("created_at") or "")))
        next_id = queued[0].get("id")
        for job in jobs:
            if job.get("id") == next_id and job.get("status") == "queued":
                job["status"] = "processing"
                job["started_at"] = _now()
                write_jobs(jobs)
                logger.info("Conversion job started: %s", job["id"])
                return dict(job)
    return None


def _complete_job(job_id: str, result: dict) -> None:
    with _lock:
        jobs = read_jobs()
        for job in jobs:
            if job.get("id") == job_id:
                file_size = int(result.get("file_size") or 0)
                if job.get("preserve_in_workspace"):
                    used = storage_used_bytes(str(job.get("user_id")))
                    limit = storage_limit_bytes(job)
                    if used + file_size > limit:
                        output_path = Path(str(result.get("output_path") or ""))
                        try:
                            if output_path.exists() and output_path.is_file():
                                output_path.unlink()
                        except OSError:
                            logger.warning("Failed to delete output after storage limit exceeded: %s", output_path)
                        _fail_job(job, "Voce atingiu o limite de armazenamento do seu plano.")
                        return
                job["status"] = "completed"
                job["output_path"] = result.get("output_path")
                job["finished_at"] = _now()
                job["error_message"] = None
                for field in ("original_size", "final_size", "reduction_percent", "message"):
                    if field in result:
                        job[field] = result.get(field)
                if result.get("refund_credits"):
                    _refund_job_credits(job)
                update_conversion_record(
                    str(job_id),
                    status="completed",
                    output_path=result.get("output_path"),
                    download_url=f"/api/v1/workspace/{job_id}/download",
                    file_size=result.get("file_size") or 0,
                    finished_at=job["finished_at"],
                )
                category = "image_tool" if str(job.get("job_type") or "") == "image_tool" else "conversion"
                record_public_operation(category, event_id=str(job_id), amount=1)
                break
        write_jobs(jobs)
    logger.info("Conversion job completed: %s", job_id)


def _fail_job(job: dict, error: object) -> None:
    message = str(error)
    with _lock:
        jobs = read_jobs()
        for item in jobs:
            if item.get("id") == job.get("id"):
                item["status"] = "failed"
                item["error_message"] = message
                item["finished_at"] = _now()
                _refund_job_credits(item)
                update_conversion_record(
                    str(item["id"]),
                    status="failed",
                    error_message=message,
                    finished_at=item["finished_at"],
                    download_url=None,
                )
                break
        write_jobs(jobs)
    logger.exception("Conversion job failed: %s", job.get("id"))


def _refund_job_credits(job: dict) -> None:
    if not job.get("credits_charged") or job.get("credits_refunded"):
        return

    refund_user_credits(str(job.get("user_id")), int(job.get("credits_cost") or 0))
    job["credits_refunded"] = True
    logger.info("Conversion job credits refunded: %s amount=%s", job.get("id"), job.get("credits_cost"))


def _worker_loop() -> None:
    while True:
        job = _claim_next_job()
        if not job:
            time.sleep(0.6)
            continue

        processor = _processors.get(str(job.get("job_type") or "conversion"))
        if processor is None:
            _fail_job(job, f"Worker nao configurado para {job.get('job_type')}.")
            continue

        try:
            result = processor(job)
            _complete_job(str(job["id"]), result)
        except Exception as exc:  # pragma: no cover
            _fail_job(job, exc)
