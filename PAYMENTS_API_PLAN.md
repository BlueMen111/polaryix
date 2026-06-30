# PolarYix Payments API Plan

Generated: 2026-06-29

## Goal

Sell Basic and Pro packages through two providers:

- Mercado Pago for Brazil.
- PayPal for international customers.

The frontend must never activate Premium directly. It should only create a checkout session and display payment status returned by the backend.

## Recommended Data Model

Create persistent tables or collections:

- `users`
- `plans`
- `orders`
- `payments`
- `subscriptions`
- `payment_events`

Minimum `orders` fields:

- `id`
- `user_id`
- `plan`
- `billing`
- `provider`
- `currency`
- `amount`
- `status`
- `provider_order_id`
- `provider_payment_id`
- `created_at`
- `paid_at`
- `cancelled_at`

Minimum `payment_events` fields:

- `id`
- `provider`
- `event_id`
- `event_type`
- `payload`
- `signature_valid`
- `processed_at`

## Backend Endpoints

- `POST /api/v1/billing/checkout`
  - Auth required.
  - Body: `plan`, `billing`, `provider`.
  - Creates an internal order.
  - Calls Mercado Pago or PayPal.
  - Returns provider checkout URL.

- `GET /api/v1/billing/orders/{order_id}`
  - Auth required.
  - Returns current order/payment status.

- `POST /api/v1/billing/webhooks/mercadopago`
  - Public endpoint, but validates Mercado Pago signature/secret.
  - Reads provider payment status server-side.
  - Activates Premium only after approved payment.

- `POST /api/v1/billing/webhooks/paypal`
  - Public endpoint, but validates PayPal webhook signature.
  - Reads provider capture/subscription status server-side.
  - Activates Premium only after completed/active payment.

## Provider Selection

Frontend can suggest:

- Mercado Pago when locale/country is Brazil or currency is BRL.
- PayPal when locale/country is outside Brazil.

Backend must still validate provider, plan, billing and price.

## Security Rules

- Do not trust amount, plan price or Premium status from the browser.
- Store provider secrets only in backend env vars.
- Validate every webhook signature.
- Make webhook processing idempotent by event id and provider payment id.
- Fetch payment details from provider API before activating Premium.
- Activate Premium only from backend webhook or verified backend status check.
- Keep failed, pending and cancelled orders without granting credits.
- Log provider event ids, not full card/customer sensitive data.

## Env Vars

- `MERCADOPAGO_ACCESS_TOKEN`
- `MERCADOPAGO_WEBHOOK_SECRET`
- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_WEBHOOK_ID`
- `PAYPAL_ENV=sandbox|live`

## Implementation Order

1. Move users/orders/payments to a database.
2. Create billing schemas and plan price source on backend.
3. Implement Mercado Pago checkout and webhook.
4. Implement PayPal checkout and webhook.
5. Add frontend payment provider selector.
6. Add account billing page with order status.
7. Add automated tests for webhook idempotency and Premium activation.
