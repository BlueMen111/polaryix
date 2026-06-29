from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config.settings import settings

logger = logging.getLogger("polaryix.conversion_history")


def _now() -> datetime:
    return datetime.now(UTC)


def history_path() -> Path:
    return settings.storage_path / "history" / "conversions.json"


def read_history() -> list[dict]:
    path = history_path()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Historico de conversoes invalido.") from exc

    return data if isinstance(data, list) else []


def write_history(records: list[dict]) -> None:
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def create_conversion_record(**values: object) -> dict:
    now = _now()
    record = {
        "id": str(values.get("id") or uuid4()),
        "user_id": values.get("user_id"),
        "original_filename": values.get("original_filename") or "arquivo",
        "original_format": values.get("original_format") or "",
        "target_format": values.get("target_format") or "",
        "input_path": values.get("input_path"),
        "output_path": values.get("output_path"),
        "download_url": values.get("download_url"),
        "file_size": int(values.get("file_size") or 0),
        "status": values.get("status") or "queued",
        "error_message": values.get("error_message"),
        "quality_requested": values.get("quality_requested"),
        "quality_delivered": values.get("quality_delivered"),
        "is_premium_job": bool(values.get("is_premium_job", False)),
        "priority_level": int(values.get("priority_level") or 0),
        "created_at": values.get("created_at") or now.isoformat(),
        "started_at": values.get("started_at"),
        "finished_at": values.get("finished_at"),
        "expires_at": values.get("expires_at") or (now + timedelta(hours=settings.file_retention_hours)).isoformat(),
        "deleted_at": values.get("deleted_at"),
    }

    records = read_history()
    records.append(record)
    write_history(records)
    return public_record(record)


def update_conversion_record(record_id: str, **updates: object) -> dict | None:
    records = read_history()
    updated: dict | None = None

    for record in records:
        if record.get("id") == record_id:
            record.update(updates)
            updated = record
            break

    if updated is None:
        return None

    write_history(records)
    return public_record(updated)


def get_user_record(user_id: str, record_id: str) -> dict:
    record = next((item for item in read_history() if item.get("id") == record_id and item.get("user_id") == user_id), None)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo nao encontrado.")
    return record


def list_user_records(user_id: str, limit: int = 20) -> list[dict]:
    records = [record for record in read_history() if record.get("user_id") == user_id]
    records.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return [public_record(record) for record in records[: max(1, min(limit, 100))]]


def public_record(record: dict) -> dict:
    expires_at = str(record.get("expires_at") or "")
    deleted_at = record.get("deleted_at")
    status_value = str(record.get("status") or "queued")

    if deleted_at and status_value not in {"expired", "deleted", "cancelled", "failed"}:
        status_value = "expired"
    elif expires_at:
        try:
            if datetime.fromisoformat(expires_at) <= _now() and status_value == "completed":
                status_value = "expired"
        except ValueError:
            pass

    return {
        "id": record.get("id"),
        "original_filename": record.get("original_filename"),
        "original_format": record.get("original_format"),
        "target_format": record.get("target_format"),
        "download_url": record.get("download_url") if status_value == "completed" else None,
        "file_size": record.get("file_size"),
        "status": status_value,
        "error_message": record.get("error_message"),
        "quality_requested": record.get("quality_requested"),
        "quality_delivered": record.get("quality_delivered"),
        "is_premium_job": record.get("is_premium_job"),
        "priority_level": record.get("priority_level"),
        "created_at": record.get("created_at"),
        "started_at": record.get("started_at"),
        "finished_at": record.get("finished_at"),
        "expires_at": record.get("expires_at"),
        "deleted_at": record.get("deleted_at"),
    }


def cleanup_expired_files(now: datetime | None = None) -> dict:
    current = now or _now()
    records = read_history()
    deleted_files = 0
    marked_records = 0

    for record in records:
        if record.get("deleted_at"):
            continue

        expires_at_value = record.get("expires_at")
        try:
            expires_at = datetime.fromisoformat(str(expires_at_value)) if expires_at_value else current
        except ValueError:
            expires_at = current

        if expires_at > current:
            continue

        for field in ("input_path", "output_path"):
            value = record.get(field)
            if not value:
                continue

            path = Path(str(value)).resolve()
            try:
                storage_root = settings.storage_path.resolve()
                if storage_root not in path.parents and path != storage_root:
                    logger.warning("Skipped cleanup outside storage: %s", path)
                    continue
                if path.exists() and path.is_file():
                    path.unlink()
                    deleted_files += 1
            except OSError as exc:
                logger.warning("Failed to delete expired file %s: %s", path, exc)

        record["status"] = "expired"
        record["deleted_at"] = current.isoformat()
        record["download_url"] = None
        marked_records += 1

    write_history(records)
    logger.info("Cleanup finished: %s files deleted, %s records marked.", deleted_files, marked_records)
    return {"deleted_files": deleted_files, "marked_records": marked_records}
