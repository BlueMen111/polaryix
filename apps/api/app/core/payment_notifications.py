from __future__ import annotations

import json
import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

from app.core.auth_store import find_user_by_id, read_users
from app.core.config.settings import settings


logger = logging.getLogger("polaryix.payment_notifications")


def payment_email_outbox_path() -> Path:
    return settings.storage_path / "notifications" / "payment_emails.json"


def send_payment_notification(payment: dict, event: str) -> None:
    recipient = _payment_recipient(payment)
    notification_id = f"{payment.get('id')}:{event}"
    outbox = _read_outbox()

    if any(item.get("notification_id") == notification_id for item in outbox):
        return

    subject, body = _message_for_event(payment, event)
    entry = {
        "notification_id": notification_id,
        "payment_id": payment.get("id"),
        "event": event,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "sent": False,
        "reason": None,
        "created_at": _now(),
    }

    if not recipient:
        entry["reason"] = "missing_recipient"
    elif _smtp_ready():
        try:
            _send_smtp(recipient, subject, body)
            entry["sent"] = True
        except Exception as exc:  # pragma: no cover - depends on external SMTP.
            logger.warning("Payment email could not be sent: %s", exc)
            entry["reason"] = "smtp_error"
    else:
        entry["reason"] = "smtp_not_configured"

    outbox.append(entry)
    _write_outbox(outbox)


def _payment_recipient(payment: dict) -> str | None:
    metadata = payment.get("metadata") or {}
    payer_email = str(metadata.get("payer_email") or "").strip()
    if payer_email:
        return payer_email

    user_id = payment.get("user_id")
    if not user_id:
        return None

    user = find_user_by_id(read_users(), str(user_id))
    if not user:
        return None
    return str(user.get("email") or "").strip() or None


def _message_for_event(payment: dict, event: str) -> tuple[str, str]:
    package = _package_label(payment)
    amount = f"{payment.get('currency', 'BRL')} {float(payment.get('amount') or 0):.2f}"

    if event == "approved":
        subject = "PolarYix - pagamento aprovado"
        status_line = "Confirmamos o pagamento e o pacote ja foi aplicado a sua conta."
    elif event == "expired":
        subject = "PolarYix - pagamento expirado"
        status_line = "O checkout expirou sem confirmacao do provedor. Para continuar, gere uma nova tentativa de pagamento."
    else:
        subject = "PolarYix - pagamento em processamento"
        status_line = "Recebemos a solicitacao de pagamento e estamos aguardando a confirmacao do provedor."

    body = (
        "Ola,\n\n"
        f"{status_line}\n\n"
        f"Pacote: {package}\n"
        f"Valor: {amount}\n"
        f"Provedor: {payment.get('provider')}\n"
        f"Identificador do checkout: {payment.get('id')}\n\n"
        "O PolarYix nunca armazena numero do cartao, CVV ou validade. A confirmacao final vem diretamente do provedor de pagamento.\n\n"
        "Atenciosamente,\n"
        "Equipe PolarYix"
    )
    return subject, body


def _package_label(payment: dict) -> str:
    metadata = payment.get("metadata") or {}
    payment_type = payment.get("type")

    if payment_type == "premium":
        plan = str(metadata.get("plan") or "basic").capitalize()
        billing = "anual" if metadata.get("billing") == "annual" else "mensal"
        return f"Premium {plan} {billing}"
    if payment_type == "credits":
        credits = int(metadata.get("credits") or 0)
        package = str(metadata.get("credits_package") or "pacote")
        return f"Pacote de creditos {package} ({credits} creditos)"
    return "Doacao PolarYix"


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


def _read_outbox() -> list[dict]:
    path = payment_email_outbox_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _write_outbox(data: list[dict]) -> None:
    path = payment_email_outbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()
