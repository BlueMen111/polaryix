from __future__ import annotations

import base64
import hashlib
import hmac
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.auth_store import get_current_user
from app.core.config.settings import settings
from app.core.payments_store import (
    CREDIT_PACKAGES,
    PREMIUM_PRODUCTS,
    approve_payment,
    create_payment_record,
    find_payment,
    find_payment_by_external,
    public_payment,
    record_payment_event,
    update_payment,
)


router = APIRouter(tags=["Payments"])


class PaymentCreatePayload(BaseModel):
    provider: str = Field("mercadopago", pattern="^(mercadopago|paypal)$")
    type: str = Field(..., pattern="^(donation|credits|premium)$")
    amount: float | None = Field(None, ge=1, le=10000)
    currency: str = Field("BRL", min_length=3, max_length=3)
    plan: str | None = Field(None, pattern="^(basic|pro)$")
    billing: str | None = Field(None, pattern="^(monthly|annual)$")
    credits_package: str | None = Field(None, pattern="^(starter|creator|studio)$")
    method: str | None = Field(None, pattern="^(checkout|pix)$")


def _frontend_url(path: str) -> str:
    return f"{str(settings.frontend_url).rstrip('/')}{path}"


def _current_user_id(request: Request) -> str | None:
    user = get_current_user(request, required=False)
    return str(user["id"]) if user else None


def _is_production() -> bool:
    return str(settings.environment or "").strip().lower() == "production"


def _ensure_provider_credentials_for_environment(provider: str) -> None:
    if not _is_production():
        return

    if provider == "mercadopago" and (not settings.mercadopago_access_token or not settings.mercadopago_public_key):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mercado Pago precisa estar configurado com credenciais reais em producao.",
        )

    if provider == "paypal" and (not settings.paypal_client_id or not settings.paypal_client_secret):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal precisa estar configurado com credenciais reais em producao.",
        )


def _resolve_product(payload: PaymentCreatePayload) -> tuple[float, str, dict]:
    if payload.type == "premium":
        key = (payload.plan or "basic", payload.billing or "monthly")
        product = PREMIUM_PRODUCTS.get(key)
        if not product:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Plano invalido.")
        return float(product["amount"]), str(product["currency"]), {
            "plan": key[0],
            "billing": key[1],
            "credits": product["credits"],
        }

    if payload.type == "credits":
        package = payload.credits_package or "starter"
        product = CREDIT_PACKAGES.get(package)
        if not product:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pacote invalido.")
        return float(product["amount"]), str(product["currency"]), {
            "credits_package": package,
            "credits": product["credits"],
        }

    amount = round(float(payload.amount or 10), 2)
    return amount, payload.currency.upper(), {"donation": True}


@router.post("/payments/mercadopago/create", status_code=status.HTTP_201_CREATED)
async def create_mercadopago_payment(request: Request, payload: PaymentCreatePayload) -> dict:
    payload.provider = "mercadopago"
    return await create_payment(request, payload)


@router.post("/payments/paypal/create", status_code=status.HTTP_201_CREATED)
async def create_paypal_payment(request: Request, payload: PaymentCreatePayload) -> dict:
    payload.provider = "paypal"
    return await create_payment(request, payload)


@router.post("/payments/donation/create", status_code=status.HTTP_201_CREATED)
async def create_donation_payment(request: Request, payload: PaymentCreatePayload) -> dict:
    payload.type = "donation"
    return await create_payment(request, payload)


@router.post("/payments/credits/create", status_code=status.HTTP_201_CREATED)
async def create_credits_payment(request: Request, payload: PaymentCreatePayload) -> dict:
    payload.type = "credits"
    return await create_payment(request, payload)


@router.post("/payments/premium/create", status_code=status.HTTP_201_CREATED)
async def create_premium_payment(request: Request, payload: PaymentCreatePayload) -> dict:
    payload.type = "premium"
    return await create_payment(request, payload)


@router.post("/payments/create", status_code=status.HTTP_201_CREATED)
async def create_payment(request: Request, payload: PaymentCreatePayload) -> dict:
    _ensure_provider_credentials_for_environment(payload.provider)

    user = get_current_user(request, required=False)
    user_id = str(user["id"]) if user else None
    if payload.type in {"credits", "premium"} and not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faca login para comprar creditos ou Premium.")
    if payload.provider == "mercadopago" and payload.method == "pix" and not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faca login para gerar PIX com confirmacao automatica.")

    amount, currency, metadata = _resolve_product(payload)
    metadata.update({"method": payload.method or "checkout"})
    payment = create_payment_record(
        user_id=user_id,
        provider=payload.provider,
        payment_type=payload.type,
        amount=amount,
        currency=currency,
        metadata=metadata,
    )

    if payload.provider == "mercadopago":
        payment = _create_mercadopago_checkout(payment, user)
    else:
        payment = _create_paypal_order(payment)

    return {"payment": payment}


@router.post("/payments/paypal/{payment_id}/capture")
async def capture_paypal_payment(request: Request, payment_id: str) -> dict:
    payment = find_payment(payment_id)
    if not payment or payment.get("provider") != "paypal":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento nao encontrado.")
    user_id = _current_user_id(request)
    if payment.get("user_id") and payment.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento nao encontrado.")
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pagamento sandbox deve ser aprovado pela simulacao.")

    token = _paypal_access_token()
    data = _json_request(
        f"{_paypal_base_url()}/v2/checkout/orders/{payment.get('external_payment_id')}/capture",
        "POST",
        {},
        {"Authorization": f"Bearer {token}"},
    )
    paypal_status = str(data.get("status") or "").upper()
    if paypal_status == "COMPLETED":
        return {"payment": approve_payment(payment_id, str(data.get("id") or payment.get("external_payment_id")))}
    return {"payment": update_payment(payment_id, status=_map_status(paypal_status))}


@router.get("/payments/{payment_id}/status")
async def payment_status(request: Request, payment_id: str) -> dict:
    payment = find_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento nao encontrado.")
    user_id = _current_user_id(request)
    if payment.get("user_id") and payment.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento nao encontrado.")
    return {"payment": public_payment(payment)}


@router.post("/payments/{payment_id}/sandbox/approve")
async def sandbox_approve_payment(payment_id: str) -> dict:
    if _is_production():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Simulacao indisponivel em producao.")
    payment = find_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento nao encontrado.")
    if payment.get("metadata", {}).get("sandbox_simulated") is not True:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pagamento real deve ser confirmado pelo provedor.")
    return {"payment": approve_payment(payment_id, external_payment_id=f"sandbox-{payment_id}")}


@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(request: Request, x_signature: str | None = Header(default=None), x_request_id: str | None = Header(default=None)) -> dict:
    payload = await request.json()
    signature_valid = _validate_mercadopago_signature(payload, x_signature)
    event_id = str(payload.get("id") or x_request_id or payload.get("data", {}).get("id") or "")
    if not event_id:
        event_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    _, is_new = record_payment_event("mercadopago", event_id, str(payload.get("type") or payload.get("action") or "payment"), payload, signature_valid)
    if not is_new:
        return {"ok": True, "duplicate": True}
    if settings.mercadopago_webhook_secret and not signature_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura invalida.")

    external_id = str(payload.get("data", {}).get("id") or payload.get("id") or "")
    provider_payment = _fetch_mercadopago_payment(external_id) if external_id and settings.mercadopago_access_token else None
    reference_id = str((provider_payment or {}).get("external_reference") or "")
    payment = find_payment(reference_id) if reference_id else (find_payment_by_external("mercadopago", external_id) if external_id else None)
    status_value = str((provider_payment or payload).get("status") or "").lower()

    if payment and status_value in {"approved", "accredited"}:
        approve_payment(str(payment["id"]), external_id)
    elif payment and status_value:
        update_payment(str(payment["id"]), status=_map_status(status_value))
    return {"ok": True}


@router.post("/webhooks/paypal")
async def paypal_webhook(
    request: Request,
    paypal_transmission_id: str | None = Header(default=None, alias="paypal-transmission-id"),
    paypal_transmission_time: str | None = Header(default=None, alias="paypal-transmission-time"),
    paypal_cert_url: str | None = Header(default=None, alias="paypal-cert-url"),
    paypal_auth_algo: str | None = Header(default=None, alias="paypal-auth-algo"),
    paypal_transmission_sig: str | None = Header(default=None, alias="paypal-transmission-sig"),
) -> dict:
    payload = await request.json()
    signature_valid = _validate_paypal_signature(
        payload,
        {
            "transmission_id": paypal_transmission_id,
            "transmission_time": paypal_transmission_time,
            "cert_url": paypal_cert_url,
            "auth_algo": paypal_auth_algo,
            "transmission_sig": paypal_transmission_sig,
        },
    )
    event_id = str(payload.get("id") or hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest())
    event_type = str(payload.get("event_type") or "")
    _, is_new = record_payment_event("paypal", event_id, event_type, payload, signature_valid)
    if not is_new:
        return {"ok": True, "duplicate": True}
    if settings.paypal_webhook_id and not signature_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura PayPal invalida.")

    resource = payload.get("resource") or {}
    external_id = str(resource.get("id") or resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id") or "")
    payment = find_payment_by_external("paypal", external_id) if external_id else None
    if payment and event_type in {"CHECKOUT.ORDER.APPROVED", "PAYMENT.CAPTURE.COMPLETED"}:
        approve_payment(str(payment["id"]), external_id)
    elif payment and event_type:
        update_payment(str(payment["id"]), status=_map_status(event_type))
    return {"ok": True}


def _create_mercadopago_checkout(payment: dict, user: dict | None) -> dict:
    if not settings.mercadopago_access_token:
        return _mark_sandbox_simulated(payment)

    if payment.get("metadata", {}).get("method") == "pix":
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faca login para gerar PIX.")
        pix_body = {
            "transaction_amount": float(payment["amount"]),
            "description": _payment_title(payment),
            "payment_method_id": "pix",
            "payer": {"email": user["email"]},
            "external_reference": payment["id"],
            "metadata": {"polaryix_payment_id": payment["id"]},
        }
        data = _json_request(
            "https://api.mercadopago.com/v1/payments",
            "POST",
            pix_body,
            {
                "Authorization": f"Bearer {settings.mercadopago_access_token}",
                "X-Idempotency-Key": str(payment["id"]),
            },
        )
        point = data.get("point_of_interaction", {}).get("transaction_data", {})
        return update_payment(
            str(payment["id"]),
            external_payment_id=str(data.get("id") or ""),
            checkout_url=_frontend_url(f"/payment/pending?payment_id={payment['id']}"),
            qr_code=point.get("qr_code"),
            qr_code_base64=point.get("qr_code_base64"),
        )

    body = {
        "items": [
            {
                "title": _payment_title(payment),
                "quantity": 1,
                "currency_id": payment["currency"],
                "unit_price": float(payment["amount"]),
            }
        ],
        "external_reference": payment["id"],
        "back_urls": {
            "success": _frontend_url(f"/payment/success?payment_id={payment['id']}"),
            "pending": _frontend_url(f"/payment/pending?payment_id={payment['id']}"),
            "failure": _frontend_url(f"/payment/cancelled?payment_id={payment['id']}"),
        },
        "notification_url": _frontend_url("/api/v1/webhooks/mercadopago"),
        "metadata": {"polaryix_payment_id": payment["id"]},
    }
    data = _json_request("https://api.mercadopago.com/checkout/preferences", "POST", body, {"Authorization": f"Bearer {settings.mercadopago_access_token}"})
    checkout_url = data.get("sandbox_init_point") if settings.mercadopago_env == "sandbox" else data.get("init_point")
    return update_payment(
        str(payment["id"]),
        external_payment_id=str(data.get("id") or ""),
        checkout_url=checkout_url,
        metadata={"provider_preference_id": data.get("id")},
    )


def _create_paypal_order(payment: dict) -> dict:
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        return _mark_sandbox_simulated(payment)

    token = _paypal_access_token()
    base = _paypal_base_url()
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": payment["id"],
                "amount": {"currency_code": "USD" if payment["currency"] == "BRL" else payment["currency"], "value": f"{float(payment['amount']):.2f}"},
                "description": _payment_title(payment),
            }
        ],
        "application_context": {
            "return_url": _frontend_url(f"/payment/success?payment_id={payment['id']}"),
            "cancel_url": _frontend_url(f"/payment/cancelled?payment_id={payment['id']}"),
        },
    }
    data = _json_request(f"{base}/v2/checkout/orders", "POST", body, {"Authorization": f"Bearer {token}"})
    approval_url = next((link.get("href") for link in data.get("links", []) if link.get("rel") == "approve"), None)
    return update_payment(str(payment["id"]), external_payment_id=str(data.get("id") or ""), checkout_url=approval_url)


def _mark_sandbox_simulated(payment: dict) -> dict:
    if _is_production():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout sandbox sem credenciais reais esta bloqueado em producao.",
        )

    return update_payment(
        str(payment["id"]),
        checkout_url=_frontend_url(f"/payment/pending?payment_id={payment['id']}&sandbox=1"),
        qr_code=f"POLARYIX-SANDBOX-{payment['id']}",
        qr_code_base64=None,
        metadata={"sandbox_simulated": True},
    )


def _paypal_access_token() -> str:
    raw = f"{settings.paypal_client_id}:{settings.paypal_client_secret}".encode("utf-8")
    data = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    response = _raw_request(
        f"{_paypal_base_url()}/v1/oauth2/token",
        "POST",
        data,
        {
            "Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    token = response.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="PayPal nao retornou token.")
    return str(token)


def _fetch_mercadopago_payment(external_id: str) -> dict | None:
    try:
        return _json_request(f"https://api.mercadopago.com/v1/payments/{external_id}", "GET", None, {"Authorization": f"Bearer {settings.mercadopago_access_token}"})
    except HTTPException:
        return None


def _json_request(url: str, method: str, body: dict | None, headers: dict[str, str]) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    return _raw_request(url, method, data, {"Content-Type": "application/json", **headers})


def _raw_request(url: str, method: str, data: bytes | None, headers: dict[str, str]) -> dict:
    request = UrlRequest(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=25) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:300]
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Provider error: {detail}") from exc
    return json.loads(payload or "{}")


def _paypal_base_url() -> str:
    return "https://api-m.paypal.com" if settings.paypal_env == "production" else "https://api-m.sandbox.paypal.com"


def _payment_title(payment: dict) -> str:
    if payment.get("type") == "premium":
        metadata = payment.get("metadata") or {}
        return f"PolarYix Premium {metadata.get('plan', 'basic')} {metadata.get('billing', 'monthly')}"
    if payment.get("type") == "credits":
        return "PolarYix credits package"
    return "PolarYix donation"


def _map_status(value: str) -> str:
    lowered = value.lower()
    if "approved" in lowered or "completed" in lowered or "accredited" in lowered:
        return "approved"
    if "cancel" in lowered:
        return "cancelled"
    if "refund" in lowered:
        return "refunded"
    if "reject" in lowered or "denied" in lowered:
        return "rejected"
    if "expire" in lowered:
        return "expired"
    if "fail" in lowered:
        return "failed"
    return "pending"


def _validate_mercadopago_signature(payload: dict, signature: str | None) -> bool:
    if not settings.mercadopago_webhook_secret:
        return True
    if not signature:
        return False
    digest = hmac.new(
        settings.mercadopago_webhook_secret.encode("utf-8"),
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, digest)


def _validate_paypal_signature(payload: dict, headers: dict[str, str | None]) -> bool:
    if not settings.paypal_webhook_id:
        return True
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        return False
    if any(not value for value in headers.values()):
        return False

    token = _paypal_access_token()
    verification_body = {
        "auth_algo": headers["auth_algo"],
        "cert_url": headers["cert_url"],
        "transmission_id": headers["transmission_id"],
        "transmission_sig": headers["transmission_sig"],
        "transmission_time": headers["transmission_time"],
        "webhook_id": settings.paypal_webhook_id,
        "webhook_event": payload,
    }
    result = _json_request(
        f"{_paypal_base_url()}/v1/notifications/verify-webhook-signature",
        "POST",
        verification_body,
        {"Authorization": f"Bearer {token}"},
    )
    return str(result.get("verification_status") or "").upper() == "SUCCESS"
