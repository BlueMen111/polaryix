from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config.settings import settings
from app.core.conversion_history import read_history
from app.core.database import SessionLocal, is_database_enabled
from app.core.db_models import PublicStatEventModel


SUCCESS_STATUSES = {"completed", "expired", "deleted"}
IMAGE_OPERATIONS = {"remove_background", "optimize_image", "upscale_image", "remaster_image"}
STAT_CATEGORIES = {"conversion", "image_tool", "download"}


def public_stats_events_path() -> Path:
    return settings.storage_path / "stats" / "public_operations.json"


def read_public_stat_events() -> list[dict]:
    if is_database_enabled():
        with SessionLocal() as db:
            return [_db_event_to_dict(event) for event in db.query(PublicStatEventModel).all()]
    path = public_stats_events_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def write_public_stat_events(events: list[dict]) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            for event in events:
                db.merge(_dict_to_db_event(event))
            db.commit()
        return
    path = public_stats_events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def record_public_operation(category: str, event_id: str | None = None, amount: int = 1) -> None:
    normalized = category if category in STAT_CATEGORIES else "conversion"
    safe_amount = max(int(amount), 0)
    if safe_amount <= 0:
        return

    events = read_public_stat_events()
    unique_id = event_id or f"{normalized}:{uuid4()}"
    if any(event.get("event_id") == unique_id for event in events):
        return

    events.append(
        {
            "event_id": unique_id,
            "category": normalized,
            "amount": safe_amount,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    write_public_stat_events(events)


def get_public_stats() -> dict:
    totals = {
        "total_conversions": 0,
        "total_image_tools": 0,
        "total_downloads": 0,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    seen_ids: set[str] = set()

    for event in read_public_stat_events():
        event_id = str(event.get("event_id") or "")
        if event_id:
            seen_ids.add(event_id)
        _add_category_to_totals(totals, str(event.get("category") or ""), int(event.get("amount") or 0))

    for record in read_history():
        record_id = str(record.get("id") or "")
        if record_id and record_id in seen_ids:
            continue
        if not _is_successful_record(record):
            continue

        if record_id:
            seen_ids.add(record_id)
        _add_record_to_totals(totals, record)

    from app.core.conversion_jobs import read_jobs

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


def _add_category_to_totals(totals: dict, category: str, amount: int) -> None:
    if amount <= 0:
        return
    if category == "download":
        totals["total_downloads"] += amount
    elif category == "image_tool":
        totals["total_image_tools"] += amount
    else:
        totals["total_conversions"] += amount


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _db_event_to_dict(event: PublicStatEventModel) -> dict:
    return {
        "event_id": event.id,
        "category": event.operation,
        "amount": event.amount,
        "created_at": event.created_at.isoformat(),
    }


def _dict_to_db_event(event: dict) -> PublicStatEventModel:
    return PublicStatEventModel(
        id=str(event.get("event_id") or uuid4()),
        operation=str(event.get("category") or "conversion"),
        status="completed",
        amount=int(event.get("amount") or 1),
        created_at=_parse_datetime(event.get("created_at")),
        metadata_json={},
    )
