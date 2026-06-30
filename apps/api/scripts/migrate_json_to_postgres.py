from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.core.config.settings import settings
from app.core.database import SessionLocal, create_database_schema
from app.core.db_models import AccountTokenModel, CommentModel, PaymentEventModel, PaymentModel, PublicStatEventModel, SessionModel, UserModel


def _read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback
    return data if isinstance(data, type(fallback)) else fallback


def _dt(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def migrate_users(db) -> int:
    users = _read_json(settings.storage_path / "auth" / "users.json", [])
    count = 0
    for user in users:
        row = {
            "id": str(user.get("id")),
            "email": str(user.get("email") or "").lower(),
            "name": str(user.get("name") or "Usuario"),
            "password_salt": user.get("password_salt"),
            "password_hash": user.get("password_hash"),
            "auth_provider": str(user.get("auth_provider") or "email"),
            "google_id": user.get("google_id"),
            "avatar_url": user.get("avatar_url"),
            "email_verified": bool(user.get("email_verified", user.get("auth_provider") == "google")),
            "email_verified_at": _dt(user.get("email_verified_at")),
            "terms_accepted_at": _dt(user.get("terms_accepted_at")),
            "is_premium": bool(user.get("is_premium", False)),
            "plan": str(user.get("plan") or "free"),
            "billing": str(user.get("billing") or "daily"),
            "plan_started_at": _dt(user.get("plan_started_at")),
            "plan_expires_at": _dt(user.get("plan_expires_at")),
            "monthly_credits": int(user.get("monthly_credits") or 50),
            "credits_remaining": int(user.get("credits_remaining") or 0),
            "credits_period": user.get("credits_period"),
            "max_file_size_mb": int(user.get("max_file_size_mb") or 100),
            "max_concurrent_conversions": int(user.get("max_concurrent_conversions") or 2),
            "priority_level": int(user.get("priority_level") or 0),
            "metadata_json": {},
            "created_at": _dt(user.get("created_at")) or datetime.now().astimezone(),
            "updated_at": _dt(user.get("updated_at")) or datetime.now().astimezone(),
        }
        statement = insert(UserModel).values(**row).on_conflict_do_update(
            index_elements=[UserModel.id],
            set_={key: value for key, value in row.items() if key != "id"},
        )
        db.execute(statement)
        count += 1
    return count


def migrate_sessions(db) -> int:
    sessions = _read_json(settings.storage_path / "auth" / "sessions.json", {})
    count = 0
    for token, session in sessions.items():
        row = {
            "token_hash": _token_hash(str(token)),
            "user_id": str(session.get("user_id")),
            "created_at": _dt(session.get("created_at")) or datetime.now().astimezone(),
            "expires_at": _dt(session.get("expires_at")),
            "revoked_at": None,
        }
        statement = insert(SessionModel).values(**row).on_conflict_do_update(
            index_elements=[SessionModel.token_hash],
            set_={key: value for key, value in row.items() if key != "token_hash"},
        )
        db.execute(statement)
        count += 1
    return count


def migrate_account_tokens(db) -> int:
    tokens = _read_json(settings.storage_path / "auth" / "account_tokens.json", [])
    count = 0
    for token in tokens:
        row = {
            "id": str(token.get("id")),
            "user_id": str(token.get("user_id")),
            "email": str(token.get("email") or "").lower(),
            "type": str(token.get("type") or ""),
            "token_hash": str(token.get("token_hash") or ""),
            "created_at": _dt(token.get("created_at")) or datetime.now().astimezone(),
            "expires_at": _dt(token.get("expires_at")) or datetime.now().astimezone(),
            "used_at": _dt(token.get("used_at")),
        }
        statement = insert(AccountTokenModel).values(**row).on_conflict_do_update(
            index_elements=[AccountTokenModel.id],
            set_={key: value for key, value in row.items() if key != "id"},
        )
        db.execute(statement)
        count += 1
    return count


def migrate_payments(db) -> int:
    payments = _read_json(settings.storage_path / "payments" / "payments.json", [])
    count = 0
    for payment in payments:
        row = {
            "id": str(payment.get("id")),
            "user_id": payment.get("user_id"),
            "provider": str(payment.get("provider") or ""),
            "type": str(payment.get("type") or ""),
            "amount": float(payment.get("amount") or 0),
            "currency": str(payment.get("currency") or "BRL"),
            "status": str(payment.get("status") or "pending"),
            "external_payment_id": payment.get("external_payment_id"),
            "checkout_url": payment.get("checkout_url"),
            "qr_code": payment.get("qr_code"),
            "qr_code_base64": payment.get("qr_code_base64"),
            "metadata_json": payment.get("metadata") or {},
            "benefit_applied": bool(payment.get("benefit_applied", False)),
            "created_at": _dt(payment.get("created_at")) or datetime.now().astimezone(),
            "updated_at": _dt(payment.get("updated_at")) or datetime.now().astimezone(),
            "expires_at": _dt(payment.get("expires_at")),
            "paid_at": _dt(payment.get("paid_at")),
        }
        statement = insert(PaymentModel).values(**row).on_conflict_do_update(
            index_elements=[PaymentModel.id],
            set_={key: value for key, value in row.items() if key != "id"},
        )
        db.execute(statement)
        count += 1
    return count


def migrate_payment_events(db) -> int:
    events = _read_json(settings.storage_path / "payments" / "events.json", [])
    count = 0
    for event in events:
        row = {
            "id": str(event.get("id")),
            "provider": str(event.get("provider") or ""),
            "event_id": str(event.get("event_id") or ""),
            "event_type": str(event.get("event_type") or ""),
            "payload": event.get("payload") or {},
            "signature_valid": bool(event.get("signature_valid", False)),
            "processed_at": _dt(event.get("processed_at")) or datetime.now().astimezone(),
        }
        statement = insert(PaymentEventModel).values(**row).on_conflict_do_nothing(
            index_elements=[PaymentEventModel.provider, PaymentEventModel.event_id],
        )
        db.execute(statement)
        count += 1
    return count


def migrate_comments(db) -> int:
    comments = _read_json(settings.storage_path / "comments" / "comments.json", [])
    count = 0
    for comment in comments:
        row = {
            "id": str(comment.get("id")),
            "user_id": comment.get("user_id"),
            "user_name": str(comment.get("user_name") or "Usuario Polaryix"),
            "avatar_url": comment.get("avatar_url"),
            "message": str(comment.get("message") or ""),
            "status": str(comment.get("status") or "published"),
            "created_at": _dt(comment.get("created_at")) or datetime.now().astimezone(),
            "updated_at": _dt(comment.get("updated_at")) or _dt(comment.get("created_at")) or datetime.now().astimezone(),
        }
        statement = insert(CommentModel).values(**row).on_conflict_do_update(
            index_elements=[CommentModel.id],
            set_={key: value for key, value in row.items() if key != "id"},
        )
        db.execute(statement)
        count += 1
    return count


def migrate_public_stat_events(db) -> int:
    events = _read_json(settings.storage_path / "stats" / "public_operations.json", [])
    count = 0
    for event in events:
        row = {
            "id": str(event.get("event_id") or event.get("id")),
            "operation": str(event.get("category") or "conversion"),
            "status": "completed",
            "amount": int(event.get("amount") or 1),
            "created_at": _dt(event.get("created_at")) or datetime.now().astimezone(),
            "metadata_json": {},
        }
        statement = insert(PublicStatEventModel).values(**row).on_conflict_do_update(
            index_elements=[PublicStatEventModel.id],
            set_={key: value for key, value in row.items() if key != "id"},
        )
        db.execute(statement)
        count += 1
    return count


if __name__ == "__main__":
    if SessionLocal is None:
        raise SystemExit("DATABASE_URL nao configurado.")
    create_database_schema()
    with SessionLocal() as db:
        counts = {
            "users": migrate_users(db),
            "sessions": migrate_sessions(db),
            "account_tokens": migrate_account_tokens(db),
            "payments": migrate_payments(db),
            "payment_events": migrate_payment_events(db),
            "comments": migrate_comments(db),
            "public_stat_events": migrate_public_stat_events(db),
        }
        db.commit()
    print(counts)
