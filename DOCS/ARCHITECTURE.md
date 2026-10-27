# ARCHITECTURE.md — OSP Music AI (MVP)

What we build is defined in [PRD.md](PRD.md). This file defines **how the pieces fit**.

## 1. Big picture

```
 Browser (phone / laptop)
        │ HTTPS
        ▼
 Reverse proxy (nginx or Caddy on the VPS)
   ├── /            → web   (Next.js)
   ├── /api/*       → api   (Django + DRF)
   ├── /admin/*     → api   (Django admin)
   └── /webhooks/*  → api   (Snippe webhooks)

 api ──► PostgreSQL   (source of truth: users, wallet, jobs, payments)
 api ──► Redis        (Celery queue only — never money)
 worker (Celery) ──► Mureka API   (lyrics + songs, default engine)
                 ──► Suno API     (songs, second engine / fallback)
 worker          ──► Cloudflare R2 (store MP3s)
 worker / api    ──► Snippe API   (mobile money)
 beat (Celery Beat) → runs scheduled tasks (dispatch jobs, poll jobs, sweep payments)
```

**Same domain for web and API** (e.g. `music.osp.co.tz` and `music.osp.co.tz/api`). This lets us use simple, secure **cookie sessions** with no tokens in the browser.

## 2. Stack (fixed — do not swap)

| Layer | Choice |
|---|---|
| Web | Next.js 15 (App Router), React, TypeScript, Tailwind CSS |
| Web libraries | TanStack Query (API data), next-intl (sw/en), next-themes (light/dark) |
| Backend | Python 3.12, Django 5, Django REST Framework |
| Auth | django-allauth (headless mode, browser sessions): signup, email verification, password reset |
| Database | PostgreSQL 16 |
| Jobs | Celery 5 + Redis 7, Celery Beat for schedules |
| Audio storage | Cloudflare R2 (S3-compatible) via `boto3` / `django-storages` |
| Email | Any SMTP provider (e.g. Brevo / Resend free tier) via Django SMTP |
| Deploy | Docker Compose on the Contabo VPS (see [DEPLOYMENT.md](DEPLOYMENT.md)) |

Not used in MVP: microservices, GraphQL, Kubernetes, WebSockets, a mobile app, a custom admin frontend.

## 3. Repository layout

```
osp-music-ai/
├── AGENTS.md
├── docs/                      # all *.md specs
├── docker-compose.yml         # local dev
├── docker-compose.prod.yml    # VPS
├── .env.example
├── backend/
│   ├── manage.py
│   ├── pyproject.toml
│   ├── config/                # settings/, urls.py, celery.py
│   ├── apps/
│   │   ├── accounts/          # user model, profile, delete account
│   │   ├── wallet/            # Wallet, LedgerEntry, wallet service  (WALLET.md)
│   │   ├── payments/          # Payment, Snippe webhooks, sweeper   (SNIPPE.md)
│   │   ├── songs/             # SongJob, SongVersion, lyrics, tasks  (MUREKA.md)
│   │   ├── core/              # AppSettings, support form, health check
│   │   └── dashboard/         # admin daily summary view
│   ├── engines/
│   │   ├── base.py            # MusicEngine interface
│   │   ├── mureka.py          # MurekaEngine (default)
│   │   ├── suno.py            # SunoEngine (second engine, SUNO.md)
│   │   ├── router.py          # picks active/fallback engine from AppSettings
│   │   └── fake.py            # FakeEngine for tests/dev (no cost)
│   └── tests/
└── web/
    ├── app/[locale]/          # pages: /, /login, /signup, /create, /music, /wallet, /settings, /support, /legal/*
    ├── components/
    ├── lib/api.ts             # typed API client
    ├── messages/sw.json       # Swahili strings
    ├── messages/en.json       # English strings
    └── public/manifest.json   # PWA
```

## 4. Music engine abstraction

All AI calls go through one interface, so Mureka and Suno are interchangeable and wallet/jobs code never knows which engine ran.

```python
class MusicEngine(Protocol):
    name: str
    def generate_lyrics(self, prompt: str) -> LyricsResult: ...           # title, lyrics
    def submit_song(self, req: SongRequest) -> str: ...                    # returns provider task_id
    def get_status(self, task_id: str) -> SongStatus: ...                  # normalized status + versions
    def get_capacity(self) -> int: ...                                     # max concurrent tasks
```

- `MurekaEngine` — default engine. Details: [MUREKA.md](MUREKA.md).
- `SunoEngine` — second engine via the **official** Suno API only. Details: [SUNO.md](SUNO.md).
- `router.py` — `get_engine_for_new_job()` returns the active engine, or the fallback engine when the active one is unavailable (SUNO.md §6). Polling always uses the engine saved on the job.
- `FakeEngine` returns canned results; used by tests and when `MUSIC_ENGINE=fake`.

## 5. Key flows (summary)

**Create song** (details: MUREKA.md + WALLET.md)
1. `POST /api/songs` → validate → **charge wallet** (one DB transaction) → `SongJob(status=queued)`.
2. Beat task `dispatch_jobs` (every 5 s) submits queued jobs to the chosen engine while that engine has capacity.
3. Beat task `poll_jobs` (every 5 s) checks running jobs; saves `stream_url` when streaming.
4. On success, worker copies MP3s to R2 → versions `ready`.
5. **Settle**: refund for failed versions (once, idempotent).

**Top up** (details: SNIPPE.md + WALLET.md)
1. `POST /api/wallet/topups` → `Payment(pending)` → Snippe USSD push.
2. Snippe webhook (verified signature) **or** sweeper task → confirm via `GET /v1/payments/{reference}` → credit wallet once.

## 6. Non-negotiable rules

1. PostgreSQL is the only source of truth for money and job state. Redis can be wiped at any time without losing money.
2. All money is **integer TZS**. No floats anywhere in money code.
3. Every wallet change goes through `wallet.services` (see WALLET.md). No other code touches balances.
4. API keys (Mureka, Snippe, R2) live only in backend env vars. Never in `web/`, never in logs.
5. Every private object (song, payment, transaction) is filtered by `request.user` in the queryset.
6. Celery tasks must be safe to run twice (idempotent).
7. Never automatically resubmit a paid generation to any engine (Mureka or Suno).

## 7. Observability (minimal)

- Structured JSON logs with `job_id`, `payment_id`, `mureka_task_id`, `mureka_trace_id`, `snippe_reference`.
- `GET /api/health` → checks DB + Redis.
- Errors to Sentry (free tier) if `SENTRY_DSN` is set.
- Admin daily summary + low Mureka balance warning (see PRD 4.9).
