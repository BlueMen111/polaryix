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
        "Sua conta PolarYix foi criada com sucesso. Para proteger seu acesso, confirme seu e-mail pelo link abaixo:\n\n"
        f"{verify_url}\n\n"
        "Guarde seu e-mail de login com seguranca. Por protecao, o PolarYix nunca envia sua senha por e-mail.\n\n"
        "Este link expira em 24 horas. Se voce nao criou esta conta, ignore esta mensagem.\n\n"
        "Atenciosamente,\n"
        "Equipe PolarYix"
    )
    html_body = _email_layout(
        title="Conta criada com sucesso",
        intro=f"Ola, {name}. Sua conta PolarYix foi criada com sucesso.",
        sections=[
            ("Login", email),
            ("Seguranca", "Por protecao, nunca enviamos sua senha por e-mail. Guarde sua senha em local seguro."),
            ("Validade do link", "24 horas"),
        ],
        button_label="Confirmar e-mail",
        button_url=verify_url,
        footer="Se voce nao criou esta conta, ignore esta mensagem.",
    )
    _send_or_store("email_verification", email, subject, body, html_body)


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
    html_body = _email_layout(
        title="Redefinicao de senha",
        intro=f"Ola, {name}. Recebemos uma solicitacao para redefinir sua senha.",
        sections=[
            ("Login", email),
            ("Validade do link", "30 minutos"),
            ("Uso", "Este link pode ser usado apenas uma vez."),
        ],
        button_label="Redefinir senha",
        button_url=reset_url,
        footer="Se voce nao solicitou a redefinicao, ignore esta mensagem.",
    )
    _send_or_store("password_reset", email, subject, body, html_body)


def _send_or_store(kind: str, recipient: str, subject: str, body: str, html_body: str | None = None) -> None:
    entry = {
        "id": secrets.token_hex(12),
        "kind": kind,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "html_body": html_body,
        "sent": False,
        "reason": None,
        "created_at": datetime.now(UTC).isoformat(),
    }

    if _smtp_ready():
        try:
            _send_smtp(recipient, subject, body, html_body)
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


def _send_smtp(recipient: str, subject: str, body: str, html_body: str | None = None) -> None:
    message = EmailMessage()
    message["From"] = str(settings.smtp_from_email)
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(str(settings.smtp_host), int(settings.smtp_port), timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(str(settings.smtp_username), str(settings.smtp_password))
        smtp.send_message(message)


def _email_layout(
    *,
    title: str,
    intro: str,
    sections: list[tuple[str, str]],
    button_label: str,
    button_url: str,
    footer: str,
) -> str:
    logo = _logo_html()
    rows = "".join(
        f"""
        <tr>
          <td style="padding:10px 0;color:#60728e;font-size:14px;">{_escape(label)}</td>
          <td style="padding:10px 0;color:#061334;font-size:14px;font-weight:700;text-align:right;">{_escape(value)}</td>
        </tr>
        """
        for label, value in sections
    )
    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#eef7ff;font-family:Arial,Helvetica,sans-serif;color:#061334;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef7ff;padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #d8eaff;border-radius:18px;overflow:hidden;">
            <tr>
              <td style="padding:28px 28px 12px;text-align:center;">{logo}</td>
            </tr>
            <tr>
              <td style="padding:0 28px 8px;text-align:center;">
                <p style="margin:0 0 8px;color:#0874ff;font-size:12px;font-weight:900;text-transform:uppercase;">PolarYix Account</p>
                <h1 style="margin:0;color:#061334;font-size:30px;line-height:1.1;">{_escape(title)}</h1>
                <p style="margin:14px 0 0;color:#60728e;font-size:16px;line-height:1.55;">{_escape(intro)}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 28px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-top:1px solid #d8eaff;border-bottom:1px solid #d8eaff;">{rows}</table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:8px 28px 28px;">
                <a href="{_escape(button_url)}" style="display:inline-block;background:#0874ff;color:#ffffff;text-decoration:none;font-weight:800;padding:13px 22px;border-radius:10px;">{_escape(button_label)}</a>
                <p style="margin:18px 0 0;color:#60728e;font-size:13px;line-height:1.5;">{_escape(footer)}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _logo_html() -> str:
    if settings.public_logo_url:
        return f'<img src="{_escape(settings.public_logo_url)}" alt="PolarYix" width="150" style="display:inline-block;max-width:150px;height:auto;">'
    return '<div style="font-size:24px;font-weight:900;color:#0874ff;">PolarYix</div>'


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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
