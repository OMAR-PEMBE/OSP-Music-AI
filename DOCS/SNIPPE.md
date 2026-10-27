# SNIPPE.md — Mobile money top-ups

Source: Snippe docs (docs.snippe.sh, API version `2026-01-25`), checked 26 Oct 2026. If the live docs differ, the live docs win — update this file.

## 1. Basics

- Base URL: `https://api.snippe.sh`
- Auth: `Authorization: Bearer $SNIPPE_API_KEY` (backend only).
- Networks: M-Pesa, Airtel Money, Mixx by Yas, Halotel (USSD push to the phone).
- Currency: **TZS only**, integer, minimum 500 (we use min 1,000 from AppSettings).
- Fee: ~2.5% (seen in `settlement.fees`). OSP absorbs it.
- Rate limit: 60 requests/minute → our sweeper must stay well below this.
- Payments expire after 4 hours if not completed.

## 2. Create top-up — `POST /api/wallet/topups`

Our API input: `{ "amount_tzs": 3000, "phone": "0712345678" }`

Steps:
1. Validate amount between `min_topup_tzs` and `max_topup_tzs`; normalize phone to `255XXXXXXXXX` (accept `07…`, `06…`, `+255…`, `255…`; 9 digits after 255).
2. Limit: max **3 pending payments per user** and max 10 top-up attempts per hour.
3. Create `Payment(status=pending, short_id=...)`.
4. Call Snippe:

```
POST /v1/payments
Authorization: Bearer <api_key>
Idempotency-Key: <payment.short_id>        # ≤ 30 chars
Content-Type: application/json

{
  "payment_type": "mobile",
  "details": { "amount": 3000, "currency": "TZS" },
  "phone_number": "255712345678",
  "customer": { "firstname": "...", "lastname": "...", "email": "..." },
  "webhook_url": "https://<domain>/webhooks/snippe",
  "metadata": { "payment_id": "<payment.id>" }
}
```

5. Response `201` → save `data.reference` → `snippe_reference`, `expires_at`. Return payment to the frontend.
6. Network error → retry up to 3× **with the same Idempotency-Key** (Snippe returns the original response, no duplicate push).
7. Still failing → mark `failed`, tell user "Imeshindikana kuanzisha malipo, jaribu tena / Couldn't start payment, try again".

Frontend then shows "Thibitisha malipo kwenye simu yako / Approve the payment on your phone" and polls `GET /api/wallet/topups/{id}` every 3 s for up to 3 minutes.

## 3. Webhook — `POST /webhooks/snippe`

Events: `payment.completed`, `payment.failed`, `payment.voided`, `payment.expired`.

Handler (Django view, CSRF-exempt, no auth):
1. Read the **raw body bytes** (never re-serialize JSON).
2. Verify signature:
   - `X-Webhook-Timestamp` is Unix seconds.
   - `message = X-Webhook-Timestamp.encode() + b"." + raw_body`
   - `expected = hmac_sha256_hex(SNIPPE_WEBHOOK_SECRET, message)`
   - compare with `X-Webhook-Signature` using `hmac.compare_digest`.
   - reject if timestamp is older than 5 minutes.
   - Invalid → store `WebhookEvent(signature_valid=False)` and return **400**.
3. Save `WebhookEvent(event_id=payload.id)`. If `event_id` already exists → return 200 (duplicate).
4. Return **200 immediately**, enqueue Celery task `process_snippe_event(event_id)`.

Note: in webhook payloads `data.amount` is an object `{ value, currency }`, not an integer.

## 4. Confirming a payment — `confirm_payment(payment)` (the only path that credits money)

Called by the webhook task **and** by the sweeper. Never trust the webhook body alone:

1. `GET /v1/payments/{snippe_reference}`
2. If `data.status == "completed"` **and** `data.amount.value == payment.amount_tzs` **and** `data.amount.currency == "TZS"`:
   - in one transaction: lock payment; if already `completed` → stop; set `completed`, `completed_at`, `confirmed_amount_tzs`, `channel_provider`, `fee_tzs` (if present); call `wallet.credit_topup(payment)`.
3. If status is `failed` / `voided` / `expired` → set that status + `failure_reason`. No money.
4. If status is `pending` → leave it.
5. If completed but amount differs → do not credit; log error `amount_mismatch`; it appears in the admin "needs review" filter.

## 5. Sweeper — `sweep_pending_payments` (Celery Beat, every 60 s)

- Payments `pending` older than 90 seconds and younger than 5 hours → `confirm_payment()` (max 30 per run, to respect the rate limit).
- Pending older than 5 hours → mark `expired` locally.

This covers missed webhooks. Money is still credited exactly once thanks to WALLET.md idempotency.

## 6. Environment variables

```
SNIPPE_API_KEY=
SNIPPE_WEBHOOK_SECRET=        # dashboard: Settings → Webhook Secret
SNIPPE_BASE_URL=https://api.snippe.sh
SNIPPE_FAKE_MODE=true        # local development only; no network calls
PUBLIC_BASE_URL=https://<domain>
```

`config.settings.dev` enables the local fake payment client by default. It completes a demo payment through the same `confirm_payment` and `wallet.credit_topup` path, but makes no network requests. Production settings always disable fake mode.


## 7. Required tests (with mocked Snippe)

1. Valid webhook + GET says completed → credited once.
2. Same webhook delivered 3 times → credited once.
3. Bad signature → 400, nothing credited.
4. Old timestamp (> 5 min) → rejected.
5. Webhook says completed but GET says pending → not credited.
6. Amount mismatch → not credited, flagged.
7. Webhook missing; sweeper confirms → credited once.
8. Webhook and sweeper run at the same moment → credited once.
9. Failed payment → status failed, balance unchanged.
10. A user cannot read another user's payment by ID.

## 8. Going live checklist

- Snippe business account verified (KYC) and **live** API key created.
- Webhook URL reachable over HTTPS from the internet.
- One real TZS 1,000 test payment on each of M-Pesa and one other network, confirmed in admin and in Wallet history.
