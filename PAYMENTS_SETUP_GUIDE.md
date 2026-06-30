# PolarYix Payments Setup Guide

Generated: 2026-06-30

This guide configures secure payments for PolarYix using Mercado Pago and PayPal. PolarYix never captures or stores card data. Card handling happens only on Mercado Pago or PayPal checkout/tokenization pages.

## Environment Variables

Add these to `apps/api/.env` in development or to the production environment:

```env
ENVIRONMENT=development
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_PUBLIC_KEY=
MERCADOPAGO_WEBHOOK_SECRET=
MERCADOPAGO_ENV=sandbox

PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_WEBHOOK_ID=
PAYPAL_ENV=sandbox

FRONTEND_URL=http://localhost:3000
```

Use `sandbox` while testing. Change to `production` only after webhook tests pass.

## Payment Products

All final product prices must be defined on the backend, never in the frontend.

- Premium monthly: Basic and Pro monthly plans.
- Premium annual: Basic and Pro annual plans.
- Credit packages: Starter, Creator and Studio token bundles.
- Donation: one-time donation with custom amount.

The frontend may display prices for UX, but the backend catalog is the source of truth. A user changing a price in browser devtools must not affect the charged amount or the benefit granted.

## Sandbox Without Provider Credentials

If Mercado Pago or PayPal credentials are empty in development, PolarYix creates a simulated sandbox payment. The pending page shows an `Aprovar sandbox` button.

This mode is strictly for local development and QA. It must be blocked in production.

Backend enforcement:

- If `ENVIRONMENT=production` and Mercado Pago credentials are empty, the API returns an error.
- If `ENVIRONMENT=production` and PayPal credentials are empty, the API returns an error.
- The `Aprovar sandbox` endpoint rejects all requests when `ENVIRONMENT=production`.
- Simulated checkout records are not created in production.

Use this mode only to test UI, status polling and backend benefit release before adding real sandbox credentials.

## Mercado Pago Sandbox

1. Create or access a Mercado Pago account.
2. Open the Mercado Pago developer panel.
3. Create an application.
4. Copy the sandbox Public Key.
5. Copy the sandbox Access Token.
6. Set `MERCADOPAGO_ENV=sandbox`.
7. Configure webhook URL:
   - Local tunnel example: `https://your-ngrok-url/api/v1/webhooks/mercadopago`
   - Production: `https://your-api-domain/api/v1/webhooks/mercadopago`
8. Test checkout payment.
9. Test PIX payment from `/premium`, `/credits` or `/donate`.
10. Confirm the backend receives the webhook and changes the payment to `approved`.

## Mercado Pago PIX

PIX is requested through Mercado Pago with `payment_method_id=pix`.

Frontend behavior:

- Shows QR Code when `qr_code_base64` is returned.
- Shows copy-and-paste code when `qr_code` is returned.
- Polls `/api/v1/payments/{payment_id}/status`.
- Does not release Premium or credits before provider confirmation.

Validation:

1. Create a PIX checkout from `/premium`, `/credits` or `/donate`.
2. Open `/payment/pending?payment_id=<id>`.
3. Confirm QR Code or copy code appears.
4. Pay with sandbox/test flow.
5. Check `storage/payments/payments.json`; status must become `approved`.
6. Confirm credits/Premium changed only after approval.

## PayPal Sandbox

1. Create or access a PayPal Developer account.
2. Create a Sandbox REST app.
3. Copy Client ID.
4. Copy Client Secret.
5. Set `PAYPAL_ENV=sandbox`.
6. Configure webhook URL:
   - Local tunnel example: `https://your-ngrok-url/api/v1/webhooks/paypal`
   - Production: `https://your-api-domain/api/v1/webhooks/paypal`
7. Test checkout from `/premium`, `/credits` or `/donate`.
8. Return to `/payment/success?payment_id=<id>`.
9. The frontend calls the backend capture endpoint.
10. Confirm the payment is approved before credits/Premium are applied.

## Webhook Validation

- Validate provider signature when Mercado Pago or PayPal verification data is configured.
- Reject invalid signed events.
- Store suspicious/invalid event metadata for review without storing sensitive card data.
- Fetch provider payment details server-side before granting benefits whenever the provider supports it.
- Do not rely on frontend redirects as proof of payment.

## Idempotency

- Save `provider_event_id` for each webhook event.
- Process each provider event only once.
- Repeated webhook events must not duplicate credits.
- Repeated webhook events must not reapply Premium benefits.
- Store provider payment IDs and internal payment IDs together.
- Benefit application must be guarded by a backend `benefit_applied` flag or equivalent database constraint.

## Frontend Security

- The frontend only starts checkout.
- The frontend never decides whether the customer paid.
- The frontend never defines the final product price.
- The frontend never activates Premium.
- The frontend never adds credits directly.
- The frontend may show `pending`, `approved` or `cancelled` status only after reading backend status.
- The frontend must never store card number, CVV, expiration date or cardholder payment data in cookies, localStorage or logs.

## Production Required Checks

- HTTPS/SSL active on frontend and backend.
- Public webhook URL reachable by Mercado Pago and PayPal.
- Real Mercado Pago credentials configured.
- Real PayPal credentials configured.
- `FRONTEND_URL` points to the final production domain.
- CORS allows only trusted production domains.
- Logs do not contain sensitive payment data.
- Real low-value payment tested on Mercado Pago.
- Real low-value payment tested on PayPal.
- PIX QR Code tested with Mercado Pago.
- Premium/credits are released only after backend status `approved`.
- Sandbox simulation is disabled with `ENVIRONMENT=production`.

## Switching To Production

Mercado Pago:

1. Replace sandbox Access Token with production Access Token.
2. Replace sandbox Public Key with production Public Key.
3. Set `MERCADOPAGO_ENV=production`.
4. Set `ENVIRONMENT=production`.
5. Configure production webhook URL.
6. Make a real low-value payment.
7. Confirm webhook approval and benefit release.

PayPal:

1. Replace sandbox Client ID and Client Secret with Live app credentials.
2. Set `PAYPAL_ENV=production`.
3. Set `ENVIRONMENT=production`.
4. Configure Live webhook URL.
5. Make a real low-value payment.
6. Confirm capture/webhook approval and benefit release.

## Security Checklist

- Never store card number, CVV, expiration date or cardholder payment data.
- Never write provider secrets to frontend `.env`.
- Never activate Premium from frontend state.
- Always activate benefits on backend after provider confirmation.
- Validate webhook signatures when secrets/webhook IDs are configured.
- Store provider event IDs and process each event once.
- Repeated webhook events must not duplicate credits.
- Frontend amount changes must not change backend product prices.
- Keep checkout status polling read-only.
- Keep logs free of sensitive payment data.
- Use HTTPS in production.

## Local Commands

API:

```powershell
cd apps/api
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Web:

```powershell
cd apps/web
npm install
npm run dev
```

## Final Production Checklist

- [ ] Mercado Pago sandbox tested.
- [ ] PayPal sandbox tested.
- [ ] PIX QR Code tested.
- [ ] Webhook public URL tested.
- [ ] Sandbox simulation disabled in production.
- [ ] Final production domain configured.
- [ ] `FRONTEND_URL` is correct.
- [ ] CORS is restricted to trusted domains.
- [ ] SSL/HTTPS active.
- [ ] Real Mercado Pago credentials configured.
- [ ] Real PayPal credentials configured.
- [ ] Low-value real payment tested.
- [ ] Logs reviewed for sensitive data.
- [ ] Premium/credits release only after `approved`.
