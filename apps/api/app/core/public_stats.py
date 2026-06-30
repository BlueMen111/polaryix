from __future__ import annotations

from datetime import UTC, datetime

from app.core.conversion_history import read_history
from app.core.conversion_jobs import read_jobs


SUCCESS_STATUSES = {"completed", "expired", "deleted"}
IMAGE_OPERATIONS = {"remove_background", "optimize_image", "upscale_image", "remaster_image"}


def get_public_stats() -> dict:
    totals = {
        "total_conversions": 0,
        "total_image_tools": 0,
        "total_downloads": 0,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    seen_ids: set[str] = set()

    for record in read_history():
        if not _is_successful_record(record):
            continue

        record_id = str(record.get("id") or "")
        if record_id:
            seen_ids.add(record_id)
        _add_record_to_totals(totals, record)

    for job in read_jobs():
        job_id = str(job.get("id") or "")
        if job_id and job_id in seen_ids:
            continue
        if not _is_successful_job(job):
            continue
        _add_job_to_totals(totals, job)

    return totals


def _is_successful_record(record: dict) -> bool:
    status = str(record.get("status") or "").lower()
    if status not in SUCCESS_STATUSES:
        return False
    if record.get("error_message"):
        return False
    return bool(record.get("finished_at") or record.get("output_path") or record.get("download_url"))


def _is_successful_job(job: dict) -> bool:
    return str(job.get("status") or "").lower() == "completed" and not job.get("error_message")


def _add_record_to_totals(totals: dict, record: dict) -> None:
    operation = str(record.get("operation_type") or "").lower()
    original_format = str(record.get("original_format") or "").upper()

    if operation.startswith("download_") or original_format == "LINK":
        totals["total_downloads"] += 1
    elif operation in IMAGE_OPERATIONS:
        totals["total_image_tools"] += 1
    else:
        totals["total_conversions"] += 1


def _add_job_to_totals(totals: dict, job: dict) -> None:
    job_type = str(job.get("job_type") or "").lower()
    operation = str(job.get("operation") or "").lower()

    if job_type == "image_tool" or operation in IMAGE_OPERATIONS:
        totals["total_image_tools"] += 1
    else:
        totals["total_conversions"] += 1
