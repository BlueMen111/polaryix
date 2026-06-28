from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.auth_store import (
    apply_plan_to_user,
    consume_user_credits,
    create_user,
    find_user_by_email,
    get_bearer_token,
    get_current_user,
    issue_session,
    public_user,
    read_sessions,
    read_users,
    verify_password,
    write_sessions,
    write_users,
)
from app.core.config.settings import settings
from app.core.premium import PREMIUM_PLANS, public_plan_data


router = APIRouter(prefix="/auth", tags=["Auth"])
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    terms_accepted: bool = False


class LoginPayload(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class ActivatePlanPayload(BaseModel):
    plan: str = Field(..., pattern="^(basic|pro)$")
    billing: str = Field(..., pattern="^(monthly|annual)$")


class GoogleExchangePayload(BaseModel):
    code: str = Field(..., min_length=8)
    redirect_uri: str = Field(..., min_length=8)


class AuthResponse(BaseModel):
    token: str
    user: dict


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe um e-mail válido.")

    return normalized


def _frontend_url() -> str:
    return str(settings.frontend_url).rstrip("/")


def _exchange_google_code(code: str, redirect_uri: str | None = None) -> dict:
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Login Google ainda não foi configurado no servidor.")

    final_redirect_uri = redirect_uri or settings.google_redirect_uri
    token_body = urlencode(
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": final_redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    token_request = UrlRequest(
        "https://oauth2.googleapis.com/token",
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urlopen(token_request, timeout=20) as token_response:
        token_data = json.loads(token_response.read().decode("utf-8"))

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google não retornou token de acesso.")

    profile_request = UrlRequest(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urlopen(profile_request, timeout=20) as profile_response:
        return json.loads(profile_response.read().decode("utf-8"))


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupPayload) -> AuthResponse:
    if not payload.terms_accepted:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Aceite os termos de uso para criar sua conta.")

    users = read_users()
    email = _normalize_email(payload.email)

    if find_user_by_email(users, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com esse e-mail.")

    user = create_user(payload.name, email, payload.password, terms_accepted=True)
    users.append(user)
    write_users(users)

    return AuthResponse(token=issue_session(user["id"]), user=public_user(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginPayload) -> AuthResponse:
    users = read_users()
    email = _normalize_email(payload.email)
    user = find_user_by_email(users, email)

    if user is None or not user.get("password_hash") or not verify_password(payload.password, user["password_salt"], user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")

    return AuthResponse(token=issue_session(user["id"]), user=public_user(user))


@router.get("/me")
async def me(request: Request) -> dict:
    user = get_current_user(request, required=True)
    return {"user": public_user(user)}


@router.post("/logout")
async def logout(request: Request) -> dict:
    token = get_bearer_token(request)
    if token:
        sessions = read_sessions()
        sessions.pop(token, None)
        write_sessions(sessions)
    return {"ok": True}


@router.get("/plans")
async def plans() -> dict:
    return {"plans": [public_plan_data(plan) for plan in PREMIUM_PLANS.values()]}


@router.post("/premium/activate")
async def activate_plan(request: Request, payload: ActivatePlanPayload) -> dict:
    current = get_current_user(request, required=True)
    users = read_users()
    user = next((item for item in users if item.get("id") == current["id"]), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")

    apply_plan_to_user(user, payload.plan, payload.billing)
    write_users(users)
    return {"user": public_user(user)}


@router.get("/oauth/google/start")
async def start_google_oauth() -> RedirectResponse:
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Configure GOOGLE_CLIENT_ID e GOOGLE_REDIRECT_URI no servidor.")

    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


def _login_or_create_google_user(profile: dict) -> AuthResponse:
    email = _normalize_email(str(profile.get("email", "")))
    name = str(profile.get("name") or email.split("@")[0])
    google_id = str(profile.get("sub") or "")
    picture = profile.get("picture")
    users = read_users()
    user = find_user_by_email(users, email)
    now = datetime.now(UTC).isoformat()

    if user:
        user["google_id"] = user.get("google_id") or google_id
        user["avatar_url"] = user.get("avatar_url") or picture
        user["auth_provider"] = "google" if not user.get("password_hash") else user.get("auth_provider", "email")
        user["updated_at"] = now
    else:
        user = create_user(name, email, auth_provider="google", google_id=google_id, terms_accepted=True)
        user["avatar_url"] = picture
        users.append(user)

    write_users(users)
    return AuthResponse(token=issue_session(user["id"]), user=public_user(user))


@router.post("/oauth/google/exchange", response_model=AuthResponse)
async def google_oauth_exchange(payload: GoogleExchangePayload) -> AuthResponse:
    try:
      profile = _exchange_google_code(payload.code, payload.redirect_uri)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não foi possível concluir o login com Google.") from exc

    return _login_or_create_google_user(profile)


@router.get("/oauth/google/callback")
async def google_oauth_callback(code: str | None = None, error: str | None = None) -> RedirectResponse:
    if error:
        return RedirectResponse(f"{_frontend_url()}/login?auth_error=google")
    if not code:
        return RedirectResponse(f"{_frontend_url()}/login?auth_error=missing_code")

    try:
        profile = _exchange_google_code(code)
    except Exception:
        return RedirectResponse(f"{_frontend_url()}/login?auth_error=google")
    session = _login_or_create_google_user(profile)
    return RedirectResponse(f"{_frontend_url()}/login?token={session.token}")
