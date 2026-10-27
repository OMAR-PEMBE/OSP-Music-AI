# MILESTONES.md — Build order

Build in this order. **One milestone per coding-agent session.** Finish a milestone (tests passing, Omar has checked it) before starting the next. Each milestone lists which docs the agent must read.

Prompt template for the agent:
> Read AGENTS.md, then the docs listed for milestone **Mx** in docs/MILESTONES.md. Implement only Mx. Run the tests. Report what you built, test results, and anything unclear.

---

### M0 — Project skeleton
**Read:** ARCHITECTURE.md, DEPLOYMENT.md §2, §4
- Repo layout from ARCHITECTURE §3; `.gitignore`, `.env.example`, `README.md` (how to run locally).
- `docker-compose.yml` for local dev: db, redis, api, worker, beat, web.
- Django project with custom `User` model (before the first migration!), DRF, Celery wired, `GET /api/health`.
- Next.js app with Tailwind, a placeholder home page, calling `/api/health`.
- Linting: ruff + black (backend), eslint + prettier (web). pytest set up.
- **Done when:** `docker compose up` runs everything; health page shows "db ok, redis ok"; `pytest` passes.

### M1 — Accounts
**Read:** PRD 4.1, DATABASE §1, API §2, §4
- allauth headless (email login, verification, password reset), signup with first/last/display name.
- Wallet row auto-created on signup (balance 0).
- `/api/me` GET/PATCH, avatar upload, `POST /api/me/delete` (deletion logic can be finished in M7).
- Local dev email goes to console / Mailpit.
- **Done when:** tests cover signup, verify, login, reset, unique display name, and user A cannot read user B.

### M2 — Wallet core (no payment processing yet)
**Read:** WALLET.md (all), DATABASE §2–4
- Wallet + LedgerEntry models, `wallet/services.py`, admin "Adjust balance" action, daily integrity task.
- Minimal Payment and SongJob/SongVersion fields needed for LedgerEntry foreign keys and wallet settlement tests; no payment creation, Snippe calls, or song-generation workflows.
- `GET /api/wallet`, `GET /api/wallet/transactions`.
- **Done when:** all 10 tests in WALLET §7 pass on real Postgres.

### M3 — Snippe top-ups
**Read:** SNIPPE.md (all), WALLET §5, API §7, DATABASE §3
- Payment + WebhookEvent models, create top-up, webhook with signature check, `confirm_payment`, sweeper.
- Complete the Payment fields/model scaffold introduced for wallet ledger references in M2.
- Snippe client in `apps/payments/snippe_client.py` with mocked tests.
- **Done when:** all 10 tests in SNIPPE §7 pass. Optional: one real sandbox/small payment via ngrok.

### M4 — Songs engine (FakeEngine first)
**Read:** MUREKA.md (all), WALLET §4, DATABASE §4–5, API §5–6
- AppSettings singleton in admin.
- SongJob, SongVersion, LyricsRequest models; `MusicEngine` interface; `FakeEngine`; `MurekaEngine`.
- Complete the SongJob/SongVersion fields/model scaffolds introduced for wallet settlement in M2.
- `POST /api/lyrics`, `POST /api/songs` (charge + Idempotency-Key), dispatcher, poller, `store_version`, settlement.
- R2 upload (use MinIO in local docker for dev), signed audio URLs, list/detail/rename/delete, mark-seen.
- **Done when:** with `MUSIC_ENGINE=fake`: a normal request ends `ready` and charged 1,000; `#fail1` → partial + refund 500; `#fail2` → failed + refund 1,000; `#timeout` → failed after 20 min (use a shortened timeout in tests); double-tap returns same job. Then ONE manual real Mureka test with Omar's key.

### M4b — Suno engine + engine router
**Read:** SUNO.md (all), MUREKA.md §6, ARCHITECTURE §4
- `engines/router.py` (active + fallback engine, margin guard), AppSettings engine fields, per-engine capacity in the dispatcher.
- `SunoEngine` skeleton; full implementation only if Omar has filled SUNO.md §3 from the official docs.
- **Done when:** with FakeEngine registered as both engines, switching `active_engine` and the fallback path both work and settle correctly; Suno can't be activated without a key and a cost. Then ONE manual real Suno test with Omar's key.

### M5 — Web app: core screens
**Read:** PRD 4.2–4.5, 4.8, API (all)
- Pages: landing, signup, login, verify email, forgot/reset password.
- App shell: header (balance, theme, account), bottom nav on mobile (Create, My Music, Wallet, Settings).
- Create screen (lyrics helper, price + balance, Generate → status card with live player for `stream_url`).
- My Music (list, detail, play A/B, download, rename, delete, red dot).
- Wallet (balance, presets + custom, phone input, "approve on your phone" state, history).
- **Done when:** the whole flow works in a phone-sized browser: sign up → top up (mocked) → create → listen → download.

### M6 — English interface, theme, PWA
**Read:** PRD §3, ARCHITECTURE §3 (web)
- English-only interface using `messages/en.json`; generated song language remains independently selectable.
- Light/dark/system theme saved to profile, no flash on load.
- PWA manifest + icons + install prompt.
- **Done when:** the English interface and theme work on every screen and persist after logout/login.

### M7 — Support, legal, account deletion
**Read:** PRD 4.6–4.7, DATABASE §6, API §4, §8
- Floating WhatsApp button (from `support_whatsapp`), contact form, FAQ page.
- Terms, Privacy, Refund pages (English; Omar supplies/approves final text).
- Full account deletion per DATABASE §6 with password confirmation and warning about balance.
- **Done when:** deleting an account removes songs/files, blocks login, and keeps anonymized ledger/payments.

### M8 — Owner admin
**Read:** PRD 4.9, MUREKA §7
- Django admin for Users, SongJobs (filters: status, date), Payments (filter "needs review"), LedgerEntries (read-only), SupportMessages, AppSettings.
- "Re-check status" admin action for stuck jobs (poll only — never resubmit).
- Daily summary page `/admin/summary/`: new users, top-ups TZS, songs, failures, refunds, est. Mureka cost (TZS), est. profit, Mureka balance, integrity warnings.
- **Done when:** Omar can answer "how much did we make today?" in one page.

### M9 — Deploy and launch
**Read:** DEPLOYMENT.md (all)
- `docker-compose.prod.yml`, proxy config, HTTPS, backups, restore test.
- Run the full launch checklist (DEPLOYMENT §8).
- **Done when:** every checklist box is ticked. 🚀

---

**After launch (Phase 2, separate docs later):** Artist Studio + subscriptions → users choose engine (Sauti A / B) → Android app → iOS app → public community.
