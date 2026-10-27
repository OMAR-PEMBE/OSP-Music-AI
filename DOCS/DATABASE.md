# DATABASE.md — OSP Music AI (MVP)

PostgreSQL 16. All money columns are `BIGINT` TZS (whole shillings). All tables have `created_at` / `updated_at` (timestamptz) unless noted. Primary keys are UUIDs, except `AppSettings` (singleton, id=1).

Money rules live in [WALLET.md](WALLET.md). Job rules live in [MUREKA.md](MUREKA.md). Payment rules live in [SNIPPE.md](SNIPPE.md).

## 1. accounts

### User (custom, `AUTH_USER_MODEL = "accounts.User"`)
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| email | citext UNIQUE | login identifier |
| first_name | varchar(60) | required (Snippe needs it) |
| last_name | varchar(60) | required |
| display_name | citext UNIQUE | 3–30 chars, letters/numbers/_ |
| avatar | varchar(255) null | R2 key, optional |
| language | varchar(2) | `en` (English-only interface preference) |
| theme | varchar(6) | `system` (default), `light`, `dark` |
| phone_last_used | varchar(15) null | last Snippe number, for convenience |
| is_active, is_staff | bool | Django defaults |
| deleted_at | timestamptz null | set when account deleted (row anonymized) |

Email verification + password reset tables come from django-allauth.

## 2. wallet

### Wallet
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | FK User UNIQUE | one wallet per user, created on signup |
| balance_tzs | bigint | CHECK (balance_tzs >= 0) |

### LedgerEntry (append-only — never UPDATE or DELETE)
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| wallet_id | FK Wallet | index |
| type | varchar(20) | `topup`, `song_charge`, `song_refund`, `adjustment` |
| amount_tzs | bigint | + adds money, − removes money; never 0 |
| balance_after_tzs | bigint | balance right after this entry |
| idempotency_key | varchar(100) UNIQUE | see WALLET.md §3 |
| payment_id | FK Payment null | for `topup` |
| song_job_id | FK SongJob null | for `song_charge` / `song_refund` |
| note | varchar(255) | required for `adjustment` |
| created_by_id | FK User null | staff user for `adjustment` |
| created_at | timestamptz | index |

## 3. payments

### Payment
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| short_id | varchar(24) UNIQUE | e.g. `pay_7Hk2...` — used as Snippe Idempotency-Key (≤30 chars) |
| user_id | FK User | index |
| amount_tzs | bigint | requested amount |
| phone | varchar(15) | `255XXXXXXXXX` |
| status | varchar(12) | `pending`, `completed`, `failed`, `expired`, `voided` |
| snippe_reference | varchar(64) UNIQUE null | from create response |
| channel_provider | varchar(20) null | `mpesa`, `airtel`, ... |
| fee_tzs | bigint null | from settlement.fees |
| confirmed_amount_tzs | bigint null | amount Snippe confirmed |
| expires_at | timestamptz null | from Snippe |
| completed_at | timestamptz null | |
| failure_reason | varchar(255) null | |
| raw_create_response | jsonb | for debugging (no secrets) |

### WebhookEvent
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| event_id | varchar(64) UNIQUE | Snippe `id` (`evt_...`) — dedupe |
| event_type | varchar(40) | |
| reference | varchar(64) | index |
| payload | jsonb | |
| signature_valid | bool | |
| processed_at | timestamptz null | |

## 4. songs

### SongJob (one user request = one job = 2 versions)
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | FK User | index (user_id, created_at desc) |
| client_request_id | uuid | from `Idempotency-Key` header; UNIQUE (user_id, client_request_id) — stops double-tap duplicates |
| title | varchar(120) | from lyrics title or idea; user can rename |
| idea | text | ≤ 1,000 chars |
| genre | varchar(30) | |
| genre_other | varchar(30) | optional custom genre label when `genre = other` |
| language | varchar(10) | `sw`, `en`, `mixed` |
| voice | varchar(6) | `male`, `female`, `auto` |
| lyrics | text | ≤ 5,000 chars (Mureka limit) |
| lyrics_source | varchar(10) | `user`, `generated` |
| engine | varchar(20) | `mureka` or `suno` — set at submit, never changes |
| model | varchar(30) | e.g. `mureka-9` or the Suno model (snapshot from AppSettings) |
| versions_requested | smallint | 2 |
| price_tzs | bigint | snapshot of price charged |
| est_cost_usd_cents | int | snapshot of estimated provider cost |
| status | varchar(20) | `queued`, `submitting`, `running`, `streaming`, `ready`, `partial`, `failed` |
| provider_task_id | varchar(64) UNIQUE null | Mureka task id |
| provider_trace_id | varchar(64) null | Mureka trace id (from response header) |
| provider_status | varchar(20) null | raw Mureka status |
| capacity_error_since | timestamptz null | starts the two-minute wait before submit-time fallback after provider capacity errors |
| failure_reason | varchar(255) null | |
| submitted_at, finished_at | timestamptz null | |
| poll_attempts | int default 0 | |
| settled_at | timestamptz null | set once refund logic has run |
| seen_by_user | bool default false | drives the "new" red dot |
| deleted_at | timestamptz null | user deleted song (files removed) |

Index: `(status, created_at)` for dispatcher/poller.

### SongVersion
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| job_id | FK SongJob | UNIQUE (job_id, index) |
| index | smallint | 0 or 1 (shown as Version A / B) |
| provider_song_id | varchar(64) null | |
| status | varchar(12) | `pending`, `streaming`, `ready`, `failed` |
| stream_url | text null | temporary, from Mureka |
| storage_key | varchar(255) null | R2 key `songs/{user_id}/{job_id}/{index}.mp3` |
| duration_ms | int null | |
| size_bytes | bigint null | |

### LyricsRequest (for the 10/day free limit and cost tracking)
| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | FK User | index (user_id, created_at) |
| prompt | text | |
| success | bool | |

## 5. core

### AppSettings (singleton, id = 1, edited in Django admin)
| Field | Default | Notes |
|---|---|---|
| song_price_tzs | 1000 | price per request (2 versions) |
| active_engine | `mureka` | `mureka` or `suno` (SUNO.md §6) |
| fallback_engine | `none` | `none`, `mureka`, `suno` |
| mureka_model | `mureka-9` | must be one of the allowed models |
| suno_model | "" | filled from Suno docs |
| suno_cost_per_version_usd_cents | null (`numeric(6,2)`) | Suno can't be enabled while null |
| mureka_balance_usd_cents | null | last balance from Mureka account refresh; below request cost makes Mureka unavailable to the router |
| generation_enabled | true | maintenance switch |
| lyrics_daily_limit | 10 | per user |
| min_topup_tzs | 1000 | Snippe minimum is 500 |
| max_topup_tzs | 500000 | |
| usd_to_tzs | 2640 | only for cost/profit estimates |
| cost_per_version_usd_cents | 4.5 (store as `numeric(6,2)`) | estimate for reports |
| cost_per_lyrics_usd_cents | 0.9 | estimate for reports |
| mureka_low_balance_usd | 20 | warn admin below this |
| support_whatsapp | "" | e.g. `2557XXXXXXXX` |
| support_email | "" | |

Every change to AppSettings is logged with Django admin's built-in LogEntry.

### SupportMessage
| id, user_id (null), name, email, message, created_at, handled (bool) |

## 6. Deletion rules

- **Delete song:** set `SongJob.deleted_at`, delete R2 files, hide from lists. Ledger rows stay.
- **Delete account:** delete all R2 files and SongVersion/LyricsRequest rows; keep SongJob rows (the ledger points to them) but blank their `title`, `idea`, `lyrics` and set `deleted_at`; then set User: `email = deleted-{id}@deleted.local`, names blank, `display_name = deleted-{first 22 UUID hex characters}` (30 characters total, unique), `is_active = false`, `deleted_at = now()`. Wallet, LedgerEntry, Payment rows are kept (anonymized via the user row) for accounting.
- Use `on_delete=PROTECT` on all FKs pointing to User, Wallet, Payment. Nothing money-related is ever cascade-deleted.
