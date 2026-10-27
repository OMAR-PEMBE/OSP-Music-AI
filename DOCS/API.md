# API.md — Backend endpoints used by the web app

Django REST Framework, JSON, all under `/api/` on the same domain as the web app.

## 1. Conventions

- **Auth:** Django session cookie (set by allauth). Web sends `X-CSRFToken` on every POST/PATCH/DELETE (read from the `csrftoken` cookie).
- **Every private endpoint** filters by `request.user`. Another user's ID returns **404** (not 403).
- **Money:** integers in TZS, field names end in `_tzs`.
- **Times:** ISO 8601 UTC; the frontend shows East Africa Time.
- **Pagination:** `?page=1` → `{ "results": [...], "next": 2 | null, "count": 37 }`, page size 20.
- **Errors:** always
  ```json
  { "error": { "code": "insufficient_balance", "message": "Salio halitoshi", "fields": {} } }
  ```
  `message` is in the user's language (`sw`/`en`). `fields` holds per-field validation errors.

| HTTP | code examples |
|---|---|
| 400 | `validation_error` |
| 401 | `not_authenticated` |
| 402 | `insufficient_balance` |
| 404 | `not_found` |
| 409 | `duplicate_request` |
| 429 | `rate_limited`, `lyrics_limit_reached` |
| 503 | `generation_paused`, `payment_provider_error` |

## 2. Auth (django-allauth headless, browser client)

Mounted at `/api/auth/`. Use allauth's standard headless browser endpoints:

| Action | Endpoint |
|---|---|
| Sign up | `POST /api/auth/browser/v1/auth/signup` (email, password, first_name, last_name, display_name) |
| Log in | `POST /api/auth/browser/v1/auth/login` |
| Log out | `DELETE /api/auth/browser/v1/auth/session` |
| Session check | `GET /api/auth/browser/v1/auth/session` |
| Verify email | `POST /api/auth/browser/v1/auth/email/verify` |
| Forgot password | `POST /api/auth/browser/v1/auth/password/request` |
| Reset password | `POST /api/auth/browser/v1/auth/password/reset` |

Email must be verified before Create and Wallet work (`403 email_not_verified`). Throttle login and signup: 10/min per IP.

## 3. Public

### `GET /api/config` (no login)
```json
{ "song_price_tzs": 1000, "min_topup_tzs": 1000, "max_topup_tzs": 500000,
  "topup_presets_tzs": [1000, 3000, 5000, 10000], "generation_enabled": true,
  "payment_demo": true,
  "lyrics_daily_limit": 10, "support_whatsapp": "2557XXXXXXXX",
  "genres": ["bongo_flava","rnb","afrobeats","amapiano","gospel","hiphop","other"] }
```

### `GET /api/health` → `{ "db": "ok", "redis": "ok" }`

### `GET /api/csrf`
Returns a CSRF token and sets the `csrftoken` cookie for browser clients before their first mutation.

`payment_demo` is true only in local development when `SNIPPE_FAKE_MODE` is enabled. The wallet uses it to label simulated top-ups.

## 4. Me

| Endpoint | Purpose |
|---|---|
| `GET /api/me` | `{ id, email, first_name, last_name, display_name, avatar_url, language, theme, email_verified, balance_tzs, unseen_songs }` |
| `PATCH /api/me` | update first_name, last_name, display_name, theme; language is fixed to `en` |
| `POST /api/me/avatar` | multipart, ≤ 2 MB, jpg/png/webp |
| `POST /api/me/delete` | body `{ "password": "..." }` → deletes/anonymizes per DATABASE.md §6, logs out → 204; wrong password → 400, storage deletion failure → 503 |

## 5. Lyrics

### `POST /api/lyrics`
In: `{ "idea": "...", "genre": "bongo_flava", "language": "sw" }`
Out: `{ "title": "...", "lyrics": "...", "remaining_today": 7 }`
Errors: `429 lyrics_limit_reached`, `503 generation_paused`. Free (no wallet change).

## 6. Songs

### `POST /api/songs` — create (charges wallet)
Header: `Idempotency-Key: <uuid>` (frontend creates one each time the Create form is opened/reset).
In:
```json
{ "idea": "Wimbo wa mapenzi kwa Asha", "genre": "bongo_flava", "genre_other": "",
  "language": "sw", "voice": "male", "lyrics": "" }
```
Rules: idea 3–1,000 chars; lyrics ≤ 5,000 chars (empty = auto). Same Idempotency-Key again → returns the **existing** job (200), no second charge.
Out `201`: the job object (below). Errors: `402 insufficient_balance`, `503 generation_paused`. Throttle: 6/min per user.

### Job object
```json
{ "id": "uuid", "title": "Asha", "genre": "bongo_flava", "language": "sw",
  "status": "streaming", "price_tzs": 1000, "refund_tzs": 0,
  "created_at": "...", "finished_at": null, "lyrics": "...",
  "versions": [
    { "index": 0, "status": "streaming", "stream_url": "https://...", "duration_ms": null },
    { "index": 1, "status": "pending", "stream_url": null, "duration_ms": null } ] }
```
`status` values shown to users: queued/submitting → "In queue", running → "Creating", streaming → "Creating (listen now)", ready, partial, failed.

| Endpoint | Purpose |
|---|---|
| `GET /api/songs?page=1&status=ready` | list, newest first, excludes deleted |
| `GET /api/songs/{id}` | one job (frontend polls every 3 s while not final) |
| `PATCH /api/songs/{id}` | `{ "title": "..." }` (1–120 chars) |
| `DELETE /api/songs/{id}` | soft delete + remove files → 204 |
| `GET /api/songs/{id}/versions/{index}/audio` | 302 redirect to a **10-minute signed R2 URL**; `?download=1` sets `Content-Disposition: attachment; filename="<title> - A.mp3"` |
| `POST /api/songs/mark-seen` | clears the red dot |

## 7. Wallet

| Endpoint | Purpose |
|---|---|
| `GET /api/wallet` | `{ "balance_tzs": 4000 }` |
| `GET /api/wallet/transactions?page=1` | `{ "results": [{ id, type, amount_tzs, balance_after_tzs, created_at, song_title?, payment_status? }], "next": 2 | null, "count": 37 }` (page size 20) |
| `POST /api/wallet/topups` | `{ amount_tzs, phone }` → payment object (see SNIPPE.md §2). Errors: `400`, `429`, `503 payment_provider_error` |
| `GET /api/wallet/topups/{id}` | `{ id, amount_tzs, phone_masked, status, created_at, completed_at }` |

## 8. Support

### `POST /api/support` (login optional)
`{ name, email, message }` (message 10–2,000 chars) → 201 after the message is stored and emailed to `support_email`; authenticated submissions are linked to the account. Throttle: 3/hour per IP. Returns 503 when support email delivery is unavailable; a failed delivery is logged and the stored message remains available to staff.

## 9. Webhooks (not called by the web app)

`POST /webhooks/snippe` — see SNIPPE.md §3. Outside `/api/`, CSRF-exempt, no session.

## 10. Admin

`/admin/` — Django admin, staff only. Not part of the public API. See PRD 4.9 and MILESTONES.md M8.
