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
BACKEND_PUBLIC_URL=http://localhost:8000
PUBLIC_LOGO_URL=http://localhost:3000/assets/polaryix-logo.png
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
```

Use `sandbox` while testing. Change to `production` only after webhook tests pass.
`FRONTEND_URL` must point to the public web app. `BACKEND_PUBLIC_URL` must point to the public API domain that receives webhooks.

## Payment Products

All final product prices must be defined on the backend, never in the frontend.

- Premium monthly: Basic and Pro monthly plans.
- Premium annual: Basic and Pro annual plans.
- Credit packages: Starter, Creator and Studio token bundles.
- Donation: one-time donation with custom amount.

The frontend may display prices for UX, but the backend catalog is the source of truth. A user changing a price in browser devtools must not affect the charged amount or the benefit granted.

## Sandbox Without Provider Credentials

If Mercado Pago or PayPal credentials are empty in development, PolarYix creates a simulated sandbox payment for backend/UI testing.

This mode is strictly for local development and QA. It must be blocked in production.

Backend enforcement:

- If `ENVIRONMENT=production` and Mercado Pago credentials are empty, the API returns an error.
- If `ENVIRONMENT=production` and PayPal credentials are empty, the API returns an error.
- The `Aprovar sandbox` endpoint rejects all requests when `ENVIRONMENT=production`.
- Simulated checkout records are not created in production.

Use this mode only to test UI, status polling and backend benefit release before adding real sandbox credentials.

## Checkout Expiration

Pending checkouts expire after 5 minutes without provider confirmation.

- The backend creates `expires_at` for every payment record.
- The payment status endpoint changes old pending records to `expired`.
- Expired payments must not release Premium, credits or donation benefits.
- The pending checkout page shows the expiration notice and countdown.
- Leaving and returning to a checkout should not reuse local payment state; the user must create a new checkout after expiration.
- For Mercado Pago PIX, PolarYix also sends the expiration timestamp to the provider when available.

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
- Shows the 5-minute expiration notice while the payment is pending.
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
- The frontend must not expose sandbox approval controls in production.
- The frontend must not keep old checkout sessions as reusable local state.
- The frontend may show `pending`, `approved` or `cancelled` status only after reading backend status.
- The frontend must never store card number, CVV, expiration date or cardholder payment data in cookies, localStorage or logs.

## Payment Emails

PolarYix sends formal payment emails when SMTP is configured.

- `pending`: payment request received and waiting for provider confirmation.
- `approved`: payment confirmed and package applied.
- `expired`: checkout expired without confirmation.

The message includes the package purchased, amount, provider and internal checkout identifier. It must never include card number, CVV, expiration date or sensitive provider payload.

If SMTP variables are empty in development, PolarYix writes a safe local outbox at `storage/notifications/payment_emails.json` so the flow can be tested without sending real emails.

## Account Emails

PolarYix also uses SMTP for account security emails:

- Email verification after signup.
- Resend verification link from `/resend-verification`.
- Password reset request from `/forgot-password`.
- Password reset confirmation flow from `/reset-password?token=<token>`.
- HTML email templates include the PolarYix logo when `PUBLIC_LOGO_URL` points to a public image.
- Never send the customer's password by email. Emails may show the login email, but passwords must remain secret.

Development fallback:

- If SMTP is empty, account emails are written to `storage/notifications/account_emails.json`.
- Verification/reset tokens are stored hashed in `storage/auth/account_tokens.json`.
- Verification links expire after 24 hours.
- Password reset links expire after 30 minutes and are single-use.

Production requirements:

- Configure a real transactional email provider or Google Workspace SMTP.
- Use `SMTP_FROM_EMAIL` from the final domain, for example `no-reply@polaryix.com`.
- Set `PUBLIC_LOGO_URL=https://polaryix.com/assets/polaryix-logo.png` or another public logo URL.
- Configure SPF, DKIM and DMARC on the domain before sending real customer emails.
- Test verification, resend verification, forgot password and reset password before launch.

## Google Login OAuth

Google OAuth is separate from SMTP email sending. Keep using OAuth for "Entrar com Google".

Google Cloud setup:

1. Open Google Cloud Console.
2. Create or select a project for PolarYix.
3. Open APIs and Services > OAuth consent screen.
4. Configure app name, support email and authorized domain.
5. Open Credentials > Create credentials > OAuth client ID.
6. Choose Web application.
7. Add authorized JavaScript origins:
   - Development: `http://localhost:3000`
   - Production: `https://polaryix.com`
8. Add authorized redirect URIs:
   - Development: `http://localhost:3000/auth/google/callback` for frontend exchange mode, or `http://localhost:8000/api/v1/auth/oauth/google/callback` for backend callback mode.
   - Production: `https://polaryix.com/auth/google/callback` for frontend exchange mode, or `https://api.polaryix.com/api/v1/auth/oauth/google/callback` for backend callback mode.
9. Copy Client ID to `GOOGLE_CLIENT_ID`.
10. Copy Client Secret to `GOOGLE_CLIENT_SECRET`.
11. Set `GOOGLE_REDIRECT_URI` to the callback mode used by the deployed app.

Current PolarYix frontend uses `/auth/google/callback` and exchanges the Google code with the backend. For that flow, set the production Google redirect URI to:

```env
GOOGLE_REDIRECT_URI=https://polaryix.com/auth/google/callback
```

If you decide to use only the backend callback endpoint instead, set:

```env
GOOGLE_REDIRECT_URI=https://api.polaryix.com/api/v1/auth/oauth/google/callback
```

## Google SMTP Option

For account/payment emails, use SMTP. Google can be used, but a transactional provider is usually better for deliverability.

Google Workspace SMTP example:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=no-reply@polaryix.com
SMTP_PASSWORD=your-google-app-password-or-smtp-password
SMTP_FROM_EMAIL=no-reply@polaryix.com
SMTP_USE_TLS=true
```

Google setup for SMTP:

1. Use Google Workspace for the final domain if possible.
2. Enable 2-Step Verification on the sending mailbox.
3. Create an App Password for SMTP, or configure an approved SMTP relay in Google Workspace Admin.
4. Put the app password or relay credential in `SMTP_PASSWORD`.
5. Test verification email, password reset email and payment email before launch.

## Production Required Checks

- HTTPS/SSL active on frontend and backend.
- Public webhook URL reachable by Mercado Pago and PayPal.
- `BACKEND_PUBLIC_URL` points to the public API domain.
- Real Mercado Pago credentials configured.
- Real PayPal credentials configured.
- `FRONTEND_URL` points to the final production domain.
- SMTP credentials configured if payment emails must be sent in production.
- SPF, DKIM and DMARC configured for account/payment emails.
- CORS allows only trusted production domains.
- Logs do not contain sensitive payment data.
- Real low-value payment tested on Mercado Pago.
- Real low-value payment tested on PayPal.
- PIX QR Code tested with Mercado Pago.
- Premium/credits are released only after backend status `approved`.
- Sandbox simulation is disabled with `ENVIRONMENT=production`.
- Checkout expiration tested after 5 minutes.
- Payment emails tested for pending and approved flows.
- Account verification and password reset emails tested.

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
- [ ] `BACKEND_PUBLIC_URL` points to the production API.
- [ ] Sandbox simulation disabled in production.
- [ ] Payment expiration after 5 minutes tested.
- [ ] Final production domain configured.
- [ ] `FRONTEND_URL` is correct.
- [ ] SMTP configured and payment emails tested.
- [ ] Email verification flow tested.
- [ ] Resend verification flow tested.
- [ ] Forgot/reset password flow tested.
- [ ] SPF, DKIM and DMARC configured.
- [ ] CORS is restricted to trusted domains.
- [ ] SSL/HTTPS active.
- [ ] Real Mercado Pago credentials configured.
- [ ] Real PayPal credentials configured.
- [ ] Low-value real payment tested.
- [ ] Logs reviewed for sensitive data.
- [ ] Premium/credits release only after `approved`.
