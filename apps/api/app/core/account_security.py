from __future__ import annotations

import hashlib
import json
import logging
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from app.core.config.settings import settings


logger = logging.getLogger("polaryix.account_security")

TOKEN_TYPES = {"email_verification", "password_reset"}
VERIFY_TOKEN_HOURS = 24
RESET_TOKEN_MINUTES = 30


def account_tokens_path() -> Path:
    return settings.storage_path / "auth" / "account_tokens.json"


def account_email_outbox_path() -> Path:
    return settings.storage_path / "notifications" / "account_emails.json"


def create_account_token(user_id: str, email: str, token_type: str) -> tuple[str, dict]:
    if token_type not in TOKEN_TYPES:
        raise ValueError("Invalid account token type.")

    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    expires_delta = timedelta(hours=VERIFY_TOKEN_HOURS) if token_type == "email_verification" else timedelta(minutes=RESET_TOKEN_MINUTES)
    record = {
        "id": secrets.token_hex(12),
        "user_id": user_id,
        "email": email,
        "type": token_type,
        "token_hash": _hash_token(token),
        "created_at": now.isoformat(),
        "expires_at": (now + expires_delta).isoformat(),
        "used_at": None,
    }

    tokens = [
        item
        for item in _read_tokens()
        if not (item.get("user_id") == user_id and item.get("type") == token_type and not item.get("used_at"))
    ]
    tokens.append(record)
    _write_tokens(tokens)
    return token, record


def consume_account_token(token: str, token_type: str) -> dict | None:
    token_hash = _hash_token(token)
    now = datetime.now(UTC)
    tokens = _read_tokens()
    matched: dict | None = None

    for item in tokens:
        if item.get("type") != token_type or item.get("token_hash") != token_hash or item.get("used_at"):
            continue
        expires_at = _parse_datetime(item.get("expires_at"))
        if not expires_at or expires_at <= now:
            return None
        item["used_at"] = now.isoformat()
        matched = item
        break

    if matched:
        _write_tokens(tokens)
    return matched


def send_verification_email(email: str, name: str, token: str) -> None:
    verify_url = f"{str(settings.frontend_url).rstrip('/')}/verify-email?token={token}"
    subject = "PolarYix - confirme seu e-mail"
    body = (
        f"Ola, {name}.\n\n"
        "Recebemos seu cadastro no PolarYix. Para proteger sua conta, confirme seu e-mail pelo link abaixo:\n\n"
        f"{verify_url}\n\n"
        "Este link expira em 24 horas. Se voce nao criou esta conta, ignore esta mensagem.\n\n"
        "Atenciosamente,\n"
        "Equipe PolarYix"
    )
    _send_or_store("email_verification", email, subject, body)


def send_password_reset_email(email: str, name: str, token: str) -> None:
    reset_url = f"{str(settings.frontend_url).rstrip('/')}/reset-password?token={token}"
    subject = "PolarYix - redefinicao de senha"
    body = (
        f"Ola, {name}.\n\n"
        "Recebemos uma solicitacao para redefinir a senha da sua conta PolarYix. Use o link abaixo:\n\n"
        f"{reset_url}\n\n"
        "Este link expira em 30 minutos e pode ser usado apenas uma vez. Se voce nao solicitou a redefinicao, ignore esta mensagem.\n\n"
        "Atenciosamente,\n"
        "Equipe PolarYix"
    )
    _send_or_store("password_reset", email, subject, body)


def _send_or_store(kind: str, recipient: str, subject: str, body: str) -> None:
    entry = {
        "id": secrets.token_hex(12),
        "kind": kind,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "sent": False,
        "reason": None,
        "created_at": datetime.now(UTC).isoformat(),
    }

    if _smtp_ready():
        try:
            _send_smtp(recipient, subject, body)
            entry["sent"] = True
        except Exception as exc:  # pragma: no cover - depends on external SMTP.
            logger.warning("Account email could not be sent: %s", exc)
            entry["reason"] = "smtp_error"
    else:
        entry["reason"] = "smtp_not_configured"

    outbox = _read_outbox()
    outbox.append(entry)
    _write_outbox(outbox)


def _smtp_ready() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def _send_smtp(recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = str(settings.smtp_from_email)
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(str(settings.smtp_host), int(settings.smtp_port), timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(str(settings.smtp_username), str(settings.smtp_password))
        smtp.send_message(message)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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


def _read_tokens() -> list[dict]:
    path = account_tokens_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _write_tokens(data: list[dict]) -> None:
    path = account_tokens_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_outbox() -> list[dict]:
    path = account_email_outbox_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _write_outbox(data: list[dict]) -> None:
    path = account_email_outbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
