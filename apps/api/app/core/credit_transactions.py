from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.auth_store import find_user_by_id, read_users, refresh_user_credits, write_users
from app.core.config.settings import settings
from app.core.database import SessionLocal, is_database_enabled
from app.core.db_models import CreditTransactionModel

UTC = timezone.utc


def credit_transactions_path() -> Path:
    return settings.storage_path / "credits" / "transactions.json"


def add_user_credits_once(
    *,
    user_id: str,
    amount: int,
    reason: str,
    source: str,
    source_id: str,
    metadata: dict | None = None,
) -> tuple[dict | None, bool]:
    if amount <= 0:
        return None, False

    if _credit_transaction_exists(source, source_id):
        return _find_credit_transaction(source, source_id), False

    users = read_users()
    user = find_user_by_id(users, user_id)
    if not user:
        return None, False

    refresh_user_credits(user)
    current_balance = int(user.get("credits_remaining", 0))
    balance_after = current_balance + amount
    user["credits_remaining"] = balance_after
    user["updated_at"] = _now()
    write_users(users)

    transaction = {
        "id": str(uuid4()),
        "user_id": user_id,
        "amount": amount,
        "reason": reason,
        "source": source,
        "source_id": source_id,
        "balance_after": balance_after,
        "created_at": _now(),
        "metadata": _safe_metadata(metadata),
    }
    _write_credit_transaction(transaction)
    return transaction, True


def read_credit_transactions() -> list[dict]:
    if is_database_enabled():
        with SessionLocal() as db:
            return [_db_transaction_to_dict(item) for item in db.query(CreditTransactionModel).all()]
    path = credit_transactions_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _credit_transaction_exists(source: str, source_id: str) -> bool:
    return _find_credit_transaction(source, source_id) is not None


def _find_credit_transaction(source: str, source_id: str) -> dict | None:
    if is_database_enabled():
        with SessionLocal() as db:
            item = (
                db.query(CreditTransactionModel)
                .filter(CreditTransactionModel.source == source, CreditTransactionModel.source_id == source_id)
                .first()
            )
            return _db_transaction_to_dict(item) if item else None

    return next(
        (
            item
            for item in read_credit_transactions()
            if item.get("source") == source and str(item.get("source_id")) == str(source_id)
        ),
        None,
    )


def _write_credit_transaction(transaction: dict) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            db.merge(_dict_to_db_transaction(transaction))
            db.commit()
        return

    path = credit_transactions_path()
    data = read_credit_transactions()
    data.append(transaction)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_metadata(metadata: dict | None) -> dict:
    safe: dict = {}
    for key, value in (metadata or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)[:80]] = value
    return safe


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _db_transaction_to_dict(transaction: CreditTransactionModel) -> dict:
    return {
        "id": transaction.id,
        "user_id": transaction.user_id,
        "amount": transaction.amount,
        "reason": transaction.reason,
        "source": transaction.source,
        "source_id": transaction.source_id,
        "balance_after": transaction.balance_after,
        "created_at": transaction.created_at.isoformat(),
        "metadata": transaction.metadata_json or {},
    }


def _dict_to_db_transaction(transaction: dict) -> CreditTransactionModel:
    return CreditTransactionModel(
        id=str(transaction["id"]),
        user_id=str(transaction["user_id"]),
        amount=int(transaction["amount"]),
        reason=str(transaction["reason"]),
        source=str(transaction["source"]),
        source_id=str(transaction["source_id"]),
        balance_after=int(transaction["balance_after"]),
        created_at=_to_datetime(transaction.get("created_at")),
        metadata_json=transaction.get("metadata") or {},
    )
