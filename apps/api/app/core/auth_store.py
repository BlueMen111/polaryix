from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request, status

from app.core.config.settings import settings
from app.core.database import SessionLocal, is_database_enabled
from app.core.db_models import SessionModel, UserModel
from app.core.premium import FREE_PLAN, get_plan_limits, normalize_billing, normalize_plan


def users_path() -> Path:
    return settings.storage_path / "auth" / "users.json"


def sessions_path() -> Path:
    return settings.storage_path / "auth" / "sessions.json"


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Base de autenticação inválida.") from exc

    return data


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_users() -> list[dict]:
    if is_database_enabled():
        with SessionLocal() as db:
            return [_db_user_to_dict(user) for user in db.query(UserModel).all()]
    data = read_json(users_path(), [])
    return data if isinstance(data, list) else []


def write_users(users: list[dict]) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            for user in users:
                db.merge(_dict_to_db_user(user))
            db.commit()
        return
    write_json(users_path(), users)


def read_sessions() -> dict:
    if is_database_enabled():
        return {}
    data = read_json(sessions_path(), {})
    return data if isinstance(data, dict) else {}


def write_sessions(sessions: dict) -> None:
    if is_database_enabled():
        return
    write_json(sessions_path(), sessions)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(password_salt), 220_000)
    return password_salt, digest.hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, candidate_hash = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def find_user_by_email(users: list[dict], email: str) -> dict | None:
    return next((user for user in users if str(user.get("email", "")).lower() == email.lower()), None)


def find_user_by_id(users: list[dict], user_id: str) -> dict | None:
    return next((user for user in users if user.get("id") == user_id), None)


def ensure_user_defaults(user: dict) -> dict:
    now = datetime.now(UTC).isoformat()
    user.setdefault("plan", "free")
    user.setdefault("billing", "daily")
    user.setdefault("is_premium", False)
    user.setdefault("monthly_credits", FREE_PLAN.monthly_credits)
    user.setdefault("credits_remaining", FREE_PLAN.monthly_credits)
    user.setdefault("credits_period", datetime.now(UTC).strftime("%Y-%m-%d"))
    user.setdefault("max_file_size_mb", FREE_PLAN.max_file_size_mb)
    user.setdefault("max_concurrent_conversions", FREE_PLAN.max_concurrent_conversions)
    user.setdefault("priority_level", FREE_PLAN.priority_level)
    user.setdefault("auth_provider", "email")
    user.setdefault("email_verified", user.get("auth_provider") == "google")
    user.setdefault("email_verified_at", now if user.get("auth_provider") == "google" else None)
    user.setdefault("terms_accepted_at", None)
    user.setdefault("updated_at", now)
    return user


def apply_plan_to_user(user: dict, plan: str, billing: str) -> dict:
    now = datetime.now(UTC)
    normalized_plan = normalize_plan(plan)
    normalized_billing = normalize_billing(billing)
    limits = get_plan_limits(normalized_plan, normalized_billing, normalized_plan != "free")
    expires_at = now + (timedelta(days=365) if normalized_billing == "annual" else timedelta(days=30))

    user.update(
        {
            "plan": limits.plan,
            "billing": limits.billing,
            "is_premium": limits.is_premium,
            "plan_started_at": now.isoformat(),
            "plan_expires_at": expires_at.isoformat() if limits.is_premium else None,
            "monthly_credits": limits.monthly_credits,
            "credits_remaining": limits.monthly_credits,
            "credits_period": now.strftime("%Y-%m"),
            "max_file_size_mb": limits.max_file_size_mb,
            "max_concurrent_conversions": limits.max_concurrent_conversions,
            "priority_level": limits.priority_level,
            "updated_at": now.isoformat(),
        }
    )
    return user


def refresh_user_credits(user: dict) -> dict:
    ensure_user_defaults(user)
    now = datetime.now(UTC)
    plan = normalize_plan(user.get("plan"))
    is_premium = bool(user.get("is_premium")) and plan != "free"

    if is_premium and user.get("plan_expires_at"):
        try:
            expires_at = datetime.fromisoformat(str(user["plan_expires_at"]))
        except ValueError:
            expires_at = now
        if expires_at <= now:
            apply_plan_to_user(user, "free", "daily")
            is_premium = False

    if is_premium:
        limits = get_plan_limits(user.get("plan"), user.get("billing"), True)
        period = now.strftime("%Y-%m")
    else:
        limits = FREE_PLAN
        period = now.strftime("%Y-%m-%d")

    if user.get("credits_period") != period:
        user["credits_remaining"] = limits.monthly_credits
        user["credits_period"] = period

    user["monthly_credits"] = limits.monthly_credits
    user["max_file_size_mb"] = limits.max_file_size_mb
    user["max_concurrent_conversions"] = limits.max_concurrent_conversions
    user["priority_level"] = limits.priority_level
    user["is_premium"] = limits.is_premium
    user["plan"] = limits.plan
    user["billing"] = limits.billing
    return user


def issue_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    if is_database_enabled():
        with SessionLocal() as db:
            db.merge(
                SessionModel(
                    token_hash=_session_token_hash(token),
                    user_id=user_id,
                    created_at=datetime.now(UTC),
                    expires_at=None,
                    revoked_at=None,
                )
            )
            db.commit()
        return token
    sessions = read_sessions()
    sessions[token] = {"user_id": user_id, "created_at": datetime.now(UTC).isoformat()}
    write_sessions(sessions)
    return token


def get_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def get_current_user(request: Request, required: bool = False) -> dict | None:
    token = get_bearer_token(request)
    if not token:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faça login para continuar.")
        return None

    sessions = read_sessions()
    session = sessions.get(token)
    if not session:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada. Entre novamente.")
        return None

    users = read_users()
    user = find_user_by_id(users, str(session.get("user_id")))
    if not user:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
        return None

    refresh_user_credits(user)
    write_users(users)
    return user


def get_current_user(request: Request, required: bool = False) -> dict | None:
    token = get_bearer_token(request)
    if not token:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faca login para continuar.")
        return None

    if is_database_enabled():
        with SessionLocal() as db:
            session = db.get(SessionModel, _session_token_hash(token))
            if not session or session.revoked_at is not None:
                if required:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao expirada. Entre novamente.")
                return None
            if session.expires_at and session.expires_at <= datetime.now(UTC):
                if required:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao expirada. Entre novamente.")
                return None
            db_user = db.get(UserModel, session.user_id)
            if not db_user:
                if required:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao encontrado.")
                return None
            user = _db_user_to_dict(db_user)
            refresh_user_credits(user)
            db.merge(_dict_to_db_user(user))
            db.commit()
            return user

    sessions = read_sessions()
    session = sessions.get(token)
    if not session:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao expirada. Entre novamente.")
        return None

    users = read_users()
    user = find_user_by_id(users, str(session.get("user_id")))
    if not user:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao encontrado.")
        return None

    refresh_user_credits(user)
    write_users(users)
    return user


def public_user(user: dict) -> dict:
    refresh_user_credits(user)
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "is_premium": bool(user.get("is_premium", False)),
        "plan": user.get("plan", "free"),
        "billing": user.get("billing", "daily"),
        "plan_started_at": user.get("plan_started_at"),
        "plan_expires_at": user.get("plan_expires_at"),
        "credits_remaining": max(int(user.get("credits_remaining", 0)), 0),
        "monthly_credits": int(user.get("monthly_credits", 0)),
        "max_file_size_mb": int(user.get("max_file_size_mb", FREE_PLAN.max_file_size_mb)),
        "max_concurrent_conversions": int(user.get("max_concurrent_conversions", FREE_PLAN.max_concurrent_conversions)),
        "priority_level": int(user.get("priority_level", FREE_PLAN.priority_level)),
        "auth_provider": user.get("auth_provider", "email"),
        "avatar_url": user.get("avatar_url"),
        "terms_accepted_at": user.get("terms_accepted_at"),
        "email_verified": bool(user.get("email_verified", False)),
        "email_verified_at": user.get("email_verified_at"),
    }


def create_user(name: str, email: str, password: str | None = None, auth_provider: str = "email", google_id: str | None = None, terms_accepted: bool = False) -> dict:
    now = datetime.now(UTC).isoformat()
    user = {
        "id": str(uuid4()),
        "name": name.strip(),
        "email": email.strip().lower(),
        "is_premium": False,
        "auth_provider": auth_provider,
        "google_id": google_id,
        "email_verified": auth_provider == "google",
        "email_verified_at": now if auth_provider == "google" else None,
        "terms_accepted_at": now if terms_accepted else None,
        "created_at": now,
        "updated_at": now,
    }

    if password is not None:
        salt, password_hash = hash_password(password)
        user["password_salt"] = salt
        user["password_hash"] = password_hash

    apply_plan_to_user(user, "free", "daily")
    return user


def consume_user_credits(user_id: str, amount: int) -> dict:
    if amount <= 0:
        return {}

    users = read_users()
    user = find_user_by_id(users, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")

    refresh_user_credits(user)
    remaining = int(user.get("credits_remaining", 0))
    if remaining < amount:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Seus créditos acabaram. Faça upgrade para Premium ou aguarde a renovação do seu saldo.",
        )

    user["credits_remaining"] = remaining - amount
    user["updated_at"] = datetime.now(UTC).isoformat()
    write_users(users)
    return user


def refund_user_credits(user_id: str, amount: int) -> dict:
    if amount <= 0:
        return {}

    users = read_users()
    user = find_user_by_id(users, user_id)
    if not user:
        return {}

    refresh_user_credits(user)
    limit = int(user.get("monthly_credits", FREE_PLAN.monthly_credits))
    current = int(user.get("credits_remaining", 0))
    user["credits_remaining"] = min(current + amount, limit)
    user["updated_at"] = datetime.now(UTC).isoformat()
    write_users(users)
    return user


def revoke_session(token: str) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            session = db.get(SessionModel, _session_token_hash(token))
            if session:
                session.revoked_at = datetime.now(UTC)
                db.commit()
        return
    sessions = read_sessions()
    sessions.pop(token, None)
    write_sessions(sessions)


def revoke_user_sessions(user_id: str) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            db.query(SessionModel).filter(SessionModel.user_id == user_id, SessionModel.revoked_at.is_(None)).update(
                {SessionModel.revoked_at: datetime.now(UTC)},
                synchronize_session=False,
            )
            db.commit()
        return
    sessions = read_sessions()
    filtered = {token: session for token, session in sessions.items() if str(session.get("user_id")) != user_id}
    write_sessions(filtered)


def _session_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _to_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _db_user_to_dict(user: UserModel) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "password_salt": user.password_salt,
        "password_hash": user.password_hash,
        "auth_provider": user.auth_provider,
        "google_id": user.google_id,
        "avatar_url": user.avatar_url,
        "email_verified": user.email_verified,
        "email_verified_at": _to_iso(user.email_verified_at),
        "terms_accepted_at": _to_iso(user.terms_accepted_at),
        "is_premium": user.is_premium,
        "plan": user.plan,
        "billing": user.billing,
        "plan_started_at": _to_iso(user.plan_started_at),
        "plan_expires_at": _to_iso(user.plan_expires_at),
        "monthly_credits": user.monthly_credits,
        "credits_remaining": user.credits_remaining,
        "credits_period": user.credits_period,
        "max_file_size_mb": user.max_file_size_mb,
        "max_concurrent_conversions": user.max_concurrent_conversions,
        "priority_level": user.priority_level,
        "created_at": _to_iso(user.created_at),
        "updated_at": _to_iso(user.updated_at),
    }


def _dict_to_db_user(user: dict) -> UserModel:
    ensure_user_defaults(user)
    now = datetime.now(UTC)
    return UserModel(
        id=str(user["id"]),
        email=str(user.get("email") or "").lower(),
        name=str(user.get("name") or "Usuario"),
        password_salt=user.get("password_salt"),
        password_hash=user.get("password_hash"),
        auth_provider=str(user.get("auth_provider") or "email"),
        google_id=user.get("google_id"),
        avatar_url=user.get("avatar_url"),
        email_verified=bool(user.get("email_verified", False)),
        email_verified_at=_to_datetime(user.get("email_verified_at")),
        terms_accepted_at=_to_datetime(user.get("terms_accepted_at")),
        is_premium=bool(user.get("is_premium", False)),
        plan=str(user.get("plan") or "free"),
        billing=str(user.get("billing") or "daily"),
        plan_started_at=_to_datetime(user.get("plan_started_at")),
        plan_expires_at=_to_datetime(user.get("plan_expires_at")),
        monthly_credits=int(user.get("monthly_credits") or FREE_PLAN.monthly_credits),
        credits_remaining=int(user.get("credits_remaining") or 0),
        credits_period=user.get("credits_period"),
        max_file_size_mb=int(user.get("max_file_size_mb") or FREE_PLAN.max_file_size_mb),
        max_concurrent_conversions=int(user.get("max_concurrent_conversions") or FREE_PLAN.max_concurrent_conversions),
        priority_level=int(user.get("priority_level") or FREE_PLAN.priority_level),
        metadata_json={},
        created_at=_to_datetime(user.get("created_at")) or now,
        updated_at=_to_datetime(user.get("updated_at")) or now,
    )
