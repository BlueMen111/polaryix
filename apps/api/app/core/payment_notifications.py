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

    subject, body, html_body = _message_for_event(payment, event)
    entry = {
        "notification_id": notification_id,
        "payment_id": payment.get("id"),
        "event": event,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "html_body": html_body,
        "sent": False,
        "reason": None,
        "created_at": _now(),
    }

    if not recipient:
        entry["reason"] = "missing_recipient"
    elif _smtp_ready():
        try:
            _send_smtp(recipient, subject, body, html_body)
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


def _message_for_event(payment: dict, event: str) -> tuple[str, str, str]:
    package = _package_label(payment)
    amount = f"{payment.get('currency', 'BRL')} {float(payment.get('amount') or 0):.2f}"
    provider = str(payment.get("provider") or "").capitalize()
    progress = _progress_label(event)

    if event == "approved":
        subject = "PolarYix - pagamento aprovado"
        status_line = _approved_line(payment)
    elif event == "expired":
        subject = "PolarYix - pagamento expirado"
        status_line = "O checkout expirou sem confirmacao do provedor. Para continuar, gere uma nova tentativa de pagamento."
    else:
        subject = "PolarYix - pagamento em processamento"
        status_line = "Recebemos a solicitacao de pagamento e estamos aguardando a confirmacao do provedor."

    body = (
        "Ola,\n\n"
        f"{status_line}\n\n"
        f"Status: {progress}\n"
        f"Pacote: {package}\n"
        f"Valor: {amount}\n"
        f"Provedor: {provider}\n"
        f"Identificador do checkout: {payment.get('id')}\n\n"
        "O PolarYix nunca armazena numero do cartao, CVV ou validade. A confirmacao final vem diretamente do provedor de pagamento.\n\n"
        "Atenciosamente,\n"
        "Equipe PolarYix"
    )
    html_body = _email_layout(
        title=subject.replace("PolarYix - ", ""),
        intro=status_line,
        progress=progress,
        sections=[
            ("Pacote", package),
            ("Valor", amount),
            ("Provedor", provider),
            ("Checkout", str(payment.get("id") or "")),
        ],
        footer="Compra protegida: o PolarYix nunca armazena numero do cartao, CVV ou validade.",
    )
    return subject, body, html_body


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


def _progress_label(event: str) -> str:
    if event == "approved":
        return "Confirmado"
    if event == "expired":
        return "Expirado"
    return "Processando"


def _approved_line(payment: dict) -> str:
    if payment.get("type") == "donation":
        return "Confirmamos sua doacao. Obrigado por apoiar o PolarYix."
    if payment.get("type") == "premium":
        return "Confirmamos o pagamento e seu Premium ja foi aplicado a sua conta."
    if payment.get("type") == "credits":
        return "Confirmamos o pagamento e seus creditos ja foram adicionados a sua conta."
    return "Confirmamos o pagamento e o pacote ja foi aplicado a sua conta."


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


def _email_layout(*, title: str, intro: str, progress: str, sections: list[tuple[str, str]], footer: str) -> str:
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
    progress_color = "#10a86b" if progress == "Confirmado" else "#0874ff" if progress == "Processando" else "#c2410c"
    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#eef7ff;font-family:Arial,Helvetica,sans-serif;color:#061334;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef7ff;padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:580px;background:#ffffff;border:1px solid #d8eaff;border-radius:18px;overflow:hidden;">
            <tr>
              <td style="padding:28px 28px 12px;text-align:center;">{logo}</td>
            </tr>
            <tr>
              <td style="padding:0 28px 8px;text-align:center;">
                <p style="margin:0 0 8px;color:#0874ff;font-size:12px;font-weight:900;text-transform:uppercase;">PolarYix Checkout</p>
                <h1 style="margin:0;color:#061334;font-size:30px;line-height:1.1;">{_escape(title)}</h1>
                <p style="margin:14px 0 0;color:#60728e;font-size:16px;line-height:1.55;">{_escape(intro)}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:14px 28px 4px;text-align:center;">
                <span style="display:inline-block;border:1px solid {progress_color};background:#f4fbff;color:{progress_color};font-weight:900;border-radius:999px;padding:8px 14px;">Status: {_escape(progress)}</span>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 28px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-top:1px solid #d8eaff;border-bottom:1px solid #d8eaff;">{rows}</table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:8px 28px 28px;">
                <p style="margin:0;color:#60728e;font-size:13px;line-height:1.5;">{_escape(footer)}</p>
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
