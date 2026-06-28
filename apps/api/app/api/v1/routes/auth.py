from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config.settings import settings


router = APIRouter(prefix="/auth", tags=["Auth"])
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)


class LoginPayload(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class AuthUser(BaseModel):
    id: str
    name: str
    email: str
    is_premium: bool = False


class AuthResponse(BaseModel):
    token: str
    user: AuthUser


def _users_path() -> Path:
    return settings.storage_path / "auth" / "users.json"


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe um e-mail válido.")

    return normalized


def _read_users() -> list[dict]:
    path = _users_path()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Base de usuários inválida.") from exc

    return data if isinstance(data, list) else []


def _write_users(users: list[dict]) -> None:
    path = _users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(password_salt), 180_000)
    return password_salt, digest.hex()


def _verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, candidate_hash = _hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def _public_user(user: dict) -> AuthUser:
    return AuthUser(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        is_premium=bool(user.get("is_premium", False)),
    )


def _issue_token() -> str:
    return secrets.token_urlsafe(32)


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupPayload) -> AuthResponse:
    users = _read_users()
    email = _normalize_email(payload.email)

    if any(user["email"].lower() == email for user in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com esse e-mail.")

    salt, password_hash = _hash_password(payload.password)
    now = datetime.now(UTC).isoformat()
    user = {
        "id": str(uuid4()),
        "name": payload.name.strip(),
        "email": email,
        "password_salt": salt,
        "password_hash": password_hash,
        "is_premium": False,
        "created_at": now,
        "updated_at": now,
    }

    users.append(user)
    _write_users(users)

    return AuthResponse(token=_issue_token(), user=_public_user(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginPayload) -> AuthResponse:
    users = _read_users()
    email = _normalize_email(payload.email)
    user = next((item for item in users if item["email"].lower() == email), None)

    if user is None or not _verify_password(payload.password, user["password_salt"], user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")

    return AuthResponse(token=_issue_token(), user=_public_user(user))


@router.get("/oauth/{provider}/start")
async def start_oauth(provider: str) -> dict:
    normalized_provider = provider.lower()
    if normalized_provider not in {"google", "microsoft"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provedor não suportado.")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Login social ainda precisa das credenciais OAuth do provedor para ser ativado.",
    )
