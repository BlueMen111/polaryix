from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import logging

from app.core.config.settings import settings
from app.core.database import SessionLocal, is_database_enabled
from app.core.db_models import AnalyticsEventModel

UTC = timezone.utc
logger = logging.getLogger("polaryix.analytics")

ALLOWED_EVENT_TYPES = {
    "page_view",
    "signup",
    "login",
    "premium_checkout_started",
    "premium_purchase_approved",
    "credits_used",
}


def analytics_events_path() -> Path:
    return settings.storage_path / "analytics" / "events.json"


def record_analytics_event(
    *,
    event_type: str,
    path: str | None,
    referrer: str | None,
    user_agent: str | None,
    ip_address: str | None,
    user_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    normalized_event_type = event_type if event_type in ALLOWED_EVENT_TYPES else "page_view"
    event = {
        "id": str(uuid4()),
        "event_type": normalized_event_type,
        "path": _clean_text(path, 512),
        "referrer": _clean_text(referrer, 512),
        "user_agent": _clean_text(user_agent, 256),
        "visitor_hash": _visitor_hash(ip_address, user_agent),
        "user_id": _clean_text(user_id, 64),
        "created_at": datetime.now(UTC).isoformat(),
        "metadata": _safe_metadata(metadata),
    }
    try:
        _write_event(event)
    except Exception as exc:  # pragma: no cover - analytics must not break product flows.
        logger.warning("Analytics event could not be recorded: %s", exc)
    return event


def get_analytics_summary() -> dict:
    events = read_analytics_events()
    visitors = {event.get("visitor_hash") for event in events if event.get("visitor_hash")}
    pages = Counter(str(event.get("path") or "") for event in events if event.get("event_type") == "page_view" and event.get("path"))
    event_types = Counter(str(event.get("event_type") or "unknown") for event in events)
    latest = max((str(event.get("created_at") or "") for event in events), default=None)
    return {
        "total_events": len(events),
        "total_visits": event_types.get("page_view", 0),
        "unique_visitors": len(visitors),
        "top_pages": [{"path": path, "views": views} for path, views in pages.most_common(20)],
        "events_by_type": dict(event_types),
        "updated_at": latest,
    }


def read_analytics_events() -> list[dict]:
    if is_database_enabled():
        with SessionLocal() as db:
            return [_db_event_to_dict(event) for event in db.query(AnalyticsEventModel).all()]

    path = analytics_events_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _write_event(event: dict) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            db.merge(_dict_to_db_event(event))
            db.commit()
        return

    path = analytics_events_path()
    events = read_analytics_events()
    events.append(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def _visitor_hash(ip_address: str | None, user_agent: str | None) -> str | None:
    if not ip_address and not user_agent:
        return None
    salt = settings.admin_cleanup_token or settings.app_name
    raw = f"{salt}:{ip_address or ''}:{user_agent or ''}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _safe_metadata(metadata: dict | None) -> dict:
    safe: dict = {}
    for key, value in (metadata or {}).items():
        normalized = str(key).lower()
        if any(forbidden in normalized for forbidden in ("email", "password", "token", "secret", "card", "cvv")):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)[:80]] = _clean_text(value, 256) if isinstance(value, str) else value
    return safe


def _clean_text(value: object, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:max_length] if text else None


def _to_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _db_event_to_dict(event: AnalyticsEventModel) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "path": event.path,
        "referrer": event.referrer,
        "user_agent": event.user_agent,
        "visitor_hash": event.visitor_hash,
        "user_id": event.user_id,
        "created_at": event.created_at.isoformat(),
        "metadata": event.metadata_json or {},
    }


def _dict_to_db_event(event: dict) -> AnalyticsEventModel:
    return AnalyticsEventModel(
        id=str(event["id"]),
        event_type=str(event["event_type"]),
        path=event.get("path"),
        referrer=event.get("referrer"),
        user_agent=event.get("user_agent"),
        visitor_hash=event.get("visitor_hash"),
        user_id=event.get("user_id"),
        created_at=_to_datetime(event.get("created_at")),
        metadata_json=event.get("metadata") or {},
    )
