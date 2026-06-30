from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.core.auth_store import apply_plan_to_user, find_user_by_id, read_users, write_users
from app.core.config.settings import settings
from app.core.database import SessionLocal, is_database_enabled
from app.core.db_models import PaymentEventModel, PaymentModel
from app.core.payment_notifications import send_payment_notification


logger = logging.getLogger("polaryix.payments")

PAYMENT_STATUSES = {"pending", "approved", "rejected", "cancelled", "expired", "refunded", "failed"}
PAYMENT_TYPES = {"donation", "credits", "premium"}
PAYMENT_PROVIDERS = {"mercadopago", "paypal"}
PAYMENT_EXPIRATION_MINUTES = 5

PREMIUM_PRODUCTS = {
    ("basic", "monthly"): {"amount": 9.99, "currency": "BRL", "credits": 1000},
    ("basic", "annual"): {"amount": 59.88, "currency": "BRL", "credits": 1000},
    ("pro", "monthly"): {"amount": 18.99, "currency": "BRL", "credits": 3000},
    ("pro", "annual"): {"amount": 155.88, "currency": "BRL", "credits": 3000},
}

CREDIT_PACKAGES = {
    "starter": {"amount": 6.90, "currency": "BRL", "credits": 250},
    "creator": {"amount": 14.90, "currency": "BRL", "credits": 750},
    "studio": {"amount": 29.90, "currency": "BRL", "credits": 1800},
}


def payments_path() -> Path:
    return settings.storage_path / "payments" / "payments.json"


def payment_events_path() -> Path:
    return settings.storage_path / "payments" / "events.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _expires_at() -> str:
    return (datetime.now(UTC) + timedelta(minutes=PAYMENT_EXPIRATION_MINUTES)).isoformat()


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Invalid payment storage JSON: %s", path)
        return fallback
    return data if isinstance(data, type(fallback)) else fallback


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_payments() -> list[dict]:
    if is_database_enabled():
        with SessionLocal() as db:
            return [_db_payment_to_dict(payment) for payment in db.query(PaymentModel).all()]
    return _read_json(payments_path(), [])


def write_payments(payments: list[dict]) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            for payment in payments:
                db.merge(_dict_to_db_payment(payment))
            db.commit()
        return
    _write_json(payments_path(), payments)


def read_payment_events() -> list[dict]:
    if is_database_enabled():
        with SessionLocal() as db:
            return [_db_event_to_dict(event) for event in db.query(PaymentEventModel).all()]
    return _read_json(payment_events_path(), [])


def write_payment_events(events: list[dict]) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            for event in events:
                db.merge(_dict_to_db_event(event))
            db.commit()
        return
    _write_json(payment_events_path(), events)


def sanitize_metadata(metadata: dict | None) -> dict:
    safe: dict = {}
    for key, value in (metadata or {}).items():
        normalized_key = str(key).lower()
        if any(forbidden in normalized_key for forbidden in ("card", "cvv", "cvc", "number", "pan", "expiry")):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)[:80]] = value
    return safe


def create_payment_record(
    *,
    user_id: str | None,
    provider: str,
    payment_type: str,
    amount: float,
    currency: str,
    metadata: dict | None = None,
) -> dict:
    if provider not in PAYMENT_PROVIDERS:
        raise ValueError("Invalid payment provider.")
    if payment_type not in PAYMENT_TYPES:
        raise ValueError("Invalid payment type.")

    payment = {
        "id": str(uuid4()),
        "user_id": user_id,
        "provider": provider,
        "type": payment_type,
        "amount": round(float(amount), 2),
        "currency": currency.upper(),
        "status": "pending",
        "external_payment_id": None,
        "checkout_url": None,
        "qr_code": None,
        "qr_code_base64": None,
        "created_at": _now(),
        "updated_at": _now(),
        "expires_at": _expires_at(),
        "paid_at": None,
        "metadata": sanitize_metadata(metadata),
        "benefit_applied": False,
    }
    payments = read_payments()
    payments.append(payment)
    write_payments(payments)
    return public_payment(payment)


def update_payment(payment_id: str, **updates: object) -> dict:
    payments = read_payments()
    updated: dict | None = None
    for payment in payments:
        if payment.get("id") == payment_id:
            for key, value in updates.items():
                if key == "metadata" and isinstance(value, dict):
                    payment[key] = {**payment.get("metadata", {}), **sanitize_metadata(value)}
                elif key in {
                    "status",
                    "external_payment_id",
                    "checkout_url",
                    "qr_code",
                    "qr_code_base64",
                    "expires_at",
                    "paid_at",
                    "benefit_applied",
                }:
                    payment[key] = value
            payment["updated_at"] = _now()
            updated = payment
            break
    if updated is None:
        raise KeyError("Payment not found.")
    write_payments(payments)
    return public_payment(updated)


def find_payment(payment_id: str) -> dict | None:
    return next((payment for payment in read_payments() if payment.get("id") == payment_id), None)


def find_payment_by_external(provider: str, external_payment_id: str) -> dict | None:
    return next(
        (
            payment
            for payment in read_payments()
            if payment.get("provider") == provider and str(payment.get("external_payment_id")) == str(external_payment_id)
        ),
        None,
    )


def expire_pending_payment(payment_id: str) -> dict | None:
    payment = find_payment(payment_id)
    if not payment or payment.get("status") != "pending":
        return payment

    expires_at = _parse_datetime(payment.get("expires_at"))
    if not expires_at or expires_at > datetime.now(UTC):
        return payment

    expired = update_payment(payment_id, status="expired")
    send_payment_notification(expired, "expired")
    return find_payment(payment_id)


def record_payment_event(provider: str, event_id: str, event_type: str, payload: dict, signature_valid: bool) -> tuple[dict, bool]:
    events = read_payment_events()
    existing = next((event for event in events if event.get("provider") == provider and event.get("event_id") == event_id), None)
    if existing:
        return existing, False
    event = {
        "id": str(uuid4()),
        "provider": provider,
        "event_id": event_id,
        "event_type": event_type,
        "payload": _safe_event_payload(payload),
        "signature_valid": signature_valid,
        "processed_at": _now(),
    }
    events.append(event)
    write_payment_events(events)
    return event, True


def approve_payment(payment_id: str, external_payment_id: str | None = None) -> dict:
    payment = expire_pending_payment(payment_id)
    if not payment:
        raise KeyError("Payment not found.")
    if payment.get("status") == "expired":
        return public_payment(payment)
    if payment.get("status") != "approved":
        update_payment(
            payment_id,
            status="approved",
            external_payment_id=external_payment_id or payment.get("external_payment_id"),
            paid_at=_now(),
        )
    apply_payment_benefit(payment_id)
    approved = find_payment(payment_id) or payment
    send_payment_notification(approved, "approved")
    return public_payment(approved)


def apply_payment_benefit(payment_id: str) -> None:
    payments = read_payments()
    payment = next((item for item in payments if item.get("id") == payment_id), None)
    if not payment or payment.get("benefit_applied") or payment.get("status") != "approved":
        return
    user_id = payment.get("user_id")
    if not user_id:
        payment["benefit_applied"] = True
        payment["updated_at"] = _now()
        write_payments(payments)
        return

    users = read_users()
    user = find_user_by_id(users, str(user_id))
    if not user:
        return

    metadata = payment.get("metadata") or {}
    if payment.get("type") == "premium":
        plan = str(metadata.get("plan") or "basic")
        billing = str(metadata.get("billing") or "monthly")
        apply_plan_to_user(user, plan, billing)
    elif payment.get("type") == "credits":
        credits = int(metadata.get("credits") or 0)
        user["credits_remaining"] = int(user.get("credits_remaining", 0)) + max(credits, 0)
        user["monthly_credits"] = max(int(user.get("monthly_credits", 0)), int(user.get("credits_remaining", 0)))
        user["updated_at"] = _now()

    payment["benefit_applied"] = True
    payment["updated_at"] = _now()
    write_users(users)
    write_payments(payments)


def public_payment(payment: dict) -> dict:
    return {
        "id": payment.get("id"),
        "user_id": payment.get("user_id"),
        "provider": payment.get("provider"),
        "type": payment.get("type"),
        "amount": payment.get("amount"),
        "currency": payment.get("currency"),
        "status": payment.get("status"),
        "external_payment_id": payment.get("external_payment_id"),
        "checkout_url": payment.get("checkout_url"),
        "qr_code": payment.get("qr_code"),
        "qr_code_base64": payment.get("qr_code_base64"),
        "created_at": payment.get("created_at"),
        "updated_at": payment.get("updated_at"),
        "expires_at": payment.get("expires_at"),
        "paid_at": payment.get("paid_at"),
        "metadata": payment.get("metadata") or {},
    }


def _safe_event_payload(payload: dict) -> dict:
    safe: dict = {}
    for key, value in payload.items():
        normalized_key = str(key).lower()
        if any(forbidden in normalized_key for forbidden in ("card", "cvv", "cvc", "number", "pan")):
            continue
        if isinstance(value, dict):
            safe[key] = _safe_event_payload(value)
        elif isinstance(value, list):
            safe[key] = value[:10]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
    return safe


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _db_payment_to_dict(payment: PaymentModel) -> dict:
    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "provider": payment.provider,
        "type": payment.type,
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
        "external_payment_id": payment.external_payment_id,
        "checkout_url": payment.checkout_url,
        "qr_code": payment.qr_code,
        "qr_code_base64": payment.qr_code_base64,
        "created_at": _to_iso(payment.created_at),
        "updated_at": _to_iso(payment.updated_at),
        "expires_at": _to_iso(payment.expires_at),
        "paid_at": _to_iso(payment.paid_at),
        "metadata": payment.metadata_json or {},
        "benefit_applied": payment.benefit_applied,
    }


def _dict_to_db_payment(payment: dict) -> PaymentModel:
    return PaymentModel(
        id=str(payment["id"]),
        user_id=payment.get("user_id"),
        provider=str(payment.get("provider") or ""),
        type=str(payment.get("type") or ""),
        amount=float(payment.get("amount") or 0),
        currency=str(payment.get("currency") or "BRL"),
        status=str(payment.get("status") or "pending"),
        external_payment_id=payment.get("external_payment_id"),
        checkout_url=payment.get("checkout_url"),
        qr_code=payment.get("qr_code"),
        qr_code_base64=payment.get("qr_code_base64"),
        metadata_json=payment.get("metadata") or {},
        benefit_applied=bool(payment.get("benefit_applied", False)),
        created_at=_parse_datetime(payment.get("created_at")) or datetime.now(UTC),
        updated_at=_parse_datetime(payment.get("updated_at")) or datetime.now(UTC),
        expires_at=_parse_datetime(payment.get("expires_at")),
        paid_at=_parse_datetime(payment.get("paid_at")),
    )


def _db_event_to_dict(event: PaymentEventModel) -> dict:
    return {
        "id": event.id,
        "provider": event.provider,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "payload": event.payload or {},
        "signature_valid": event.signature_valid,
        "processed_at": _to_iso(event.processed_at),
    }


def _dict_to_db_event(event: dict) -> PaymentEventModel:
    return PaymentEventModel(
        id=str(event["id"]),
        provider=str(event.get("provider") or ""),
        event_id=str(event.get("event_id") or ""),
        event_type=str(event.get("event_type") or ""),
        payload=event.get("payload") or {},
        signature_valid=bool(event.get("signature_valid", False)),
        processed_at=_parse_datetime(event.get("processed_at")) or datetime.now(UTC),
    )
