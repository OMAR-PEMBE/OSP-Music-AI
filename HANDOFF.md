# OSP Music AI — Coding Agent Handoff

Updated: 2026-10-27

## Start here

Before making changes, read `AGENTS.md` and the current milestone in `DOCS/MILESTONES.md`. Project docs use uppercase `DOCS/` paths in this checkout. Follow the repository rules: implement one milestone at a time, keep the interface English-only, put UI copy in `web/messages/en.json`, and read `DOCS/WALLET.md` before any change that can affect balances.

## Current state

- M0 through M4b were previously implemented in the repository.
- **M5 — Web app: core screens** and **M6 — Language, theme, PWA** are implemented and verified locally.
- **M7 — Support, legal, account deletion** is implemented and approved by Omar to proceed. Legal pages remain clearly labeled drafts; qualified legal review is still required before launch.
- **M8 — Owner admin** is implemented and verified: searchable owner records, safe poll-only job re-check, and the daily admin summary are available.
- Omar explicitly approved M8 and asked to start **M9 — Deploy and launch**. M9 deployment preparation is underway; no production server has been inspected or changed.
- The user said third-party APIs will be purchased/configured later. Keep real Mureka, Suno, and Snippe calls pending unless the user explicitly asks otherwise. Local music generation defaults to `MUSIC_ENGINE=fake`; local top-ups use `SNIPPE_FAKE_MODE=true` and a clearly labeled local simulator that credits through the existing confirmation and wallet service path.
- Preserve the current M5/M6/M7/M8 worktree changes.

## M5 implementation present

- Public landing page and signup, login, email verification, forgot-password, and reset-password screens.
- Signed-in app shell with balance, theme toggle, account link, email-verification notice, and mobile navigation.
- Create screen with lyrics helper, price/balance summary, and song submission/status flow.
- My Music list and song detail pages with A/B players, download links, rename/delete, polling, and unseen-song indicator.
- Wallet screen with balance, presets/custom amount, phone input, payment status/history, and local demo top-ups.
- Profile settings screen with profile editing and avatar upload.
- English-only messages, API/CSRF helpers, responsive styling, public `/api/config`, and correct unseen-song count.
- Documentation notes the local-only fake payment mode.

## M6 implementation present

- `next-intl` serves the English-only interface; UI copy is in `web/messages/en.json`.
- Language-switch controls are removed; interface language is fixed to English while song language remains selectable. Existing account language preferences are migrated to English.
- System/light/dark theme preferences are cached locally and saved to the signed-in profile. The early bootstrap avoids a theme flash, and login/session changes reload profile preferences.
- English date formatting uses the `Africa/Dar_es_Salaam` time zone.
- Added the PWA manifest, SVG and 192/512 PNG icons, install prompt, and iOS Add to Home Screen guidance. Offline caching is intentionally not enabled.
- README documents preference persistence and PWA installation.

## M7 implementation complete

- Added the rate-limited `/api/support` endpoint, `SupportMessage` persistence/admin, and owner email delivery.
- Added public FAQ/contact pages and a floating WhatsApp link sourced from `support_whatsapp`.
- Account deletion now requires the current password, removes audio/avatar files and lyrics/version data, anonymizes retained song jobs and the user, and preserves wallet, ledger, and payment rows. Deleted jobs are skipped by generation/polling and cannot receive late song refunds.
- Terms, Privacy, and Refund drafts are published in English, visibly labeled as drafts. Omar approved these drafts to proceed with M8; legal review remains a pre-launch requirement.
- To enable contact channels, set `support_email` and `support_whatsapp` in Django admin and configure SMTP environment variables.

## M8 implementation complete

- Registered users as read-only/searchable in Django admin. Song jobs are searchable and read-only; payments, wallets, ledger entries, support messages, and application settings retain their existing admin surfaces.
- Added a Payment "needs review" filter for Snippe amount mismatches.
- Added the admin SongJob action "Re-check status"; it only polls active provider tasks and never submits or resubmits a generation.
- Added `/admin/summary/` with today's new users, confirmed top-ups, successful/partial generations, jobs with failed versions, refunds, estimated Mureka cost, estimated profit, Mureka balance/low-balance alert, and wallet-ledger integrity warnings.
- Estimated profit is today's song charges less today's refunds and estimated Mureka costs. Cost uses job cost snapshots plus today's standalone lyrics requests; amounts are shown as integer TZS.

## Verification already run

Commands and observed results:

- M5 phone-sized browser flow: signup → email verification → fake top-up → fake song generation through Ready → both MP3 downloads. Local CSRF and browser-facing MinIO download issues were fixed with regression tests.
- Backend suite after M5 fixes: `52 passed`.
- In `web/`: `npm.cmd run lint` — passed.
- In `web/`: `npx.cmd tsc --noEmit` — passed (no diagnostics).
- In `web/`: `npm.cmd run format:check` — `All matched files use Prettier code style!`
- In `web/`: `npm.cmd run build` — passed; Next.js generated all 15 routes. Configuring the next-intl time zone removed the `ENVIRONMENT_FALLBACK` warning.
- M6 browser checks: English UI and `lang=en`; `/api/me` returned the saved `language=en` and `theme=system`; emulated OS light/dark changes resolved the page theme correctly; clearing local preference cache and firing the post-login session event restored profile preferences.
- PWA checks: synthetic `beforeinstallprompt` displayed and dismissed the install action; iPhone user-agent simulation at 390×844 showed the localized Add to Home Screen instructions in the mobile-safe position. Manifest and PNG/SVG icon endpoints returned HTTP 200.
- `docker compose up -d --build web` — web image rebuilt and container started successfully.
- M7 focused backend suite (SQLite): `12 passed`.
- M7 complete backend suite (Compose PostgreSQL/MinIO): `59 passed`.
- Backend `ruff check`, `black --check`, and `manage.py makemigrations --check --dry-run` — passed.
- Final M7 web lint, format, TypeScript, and production build — passed; Next.js generated all 20 routes, including the legal draft pages.
- Applied `core.0003_supportmessage` to the local Compose database.
- `git diff --check` — no whitespace errors (Git printed line-ending conversion warnings).
- No physical-device install was performed; PWA prompt behavior was simulated in the browser. Actual credential logout/login was not repeated, but the same profile reload path is wired to the login event and verified.
- M8 targeted dashboard/admin tests on SQLite — `4 passed`.
- M8 complete backend suite on Compose PostgreSQL/MinIO — `63 passed`.
- M8 backend Ruff and Black checks, Django system check, and migration consistency check — passed.
- English-only interface update: web lint, formatting, TypeScript, and production build passed; focused account/profile tests passed (`4 passed`); Django system and migration checks passed. The local Compose web/API images were rebuilt and the account-language migrations applied.
- M9 preparation: production Compose configuration parsed successfully; focused backup/restore-command tests passed (`2 passed`); production Django settings and R2 storage checks passed with disposable test-only values; fake generation was rejected as expected; Ruff and Black checks passed. Web lint, formatting, TypeScript, standalone build, and both production Docker image builds passed.
- No production credentials were supplied or used. The production backup/upload and disposable-container restore scripts have not been run against R2, and no VPS inspection or deployment has occurred.

Earlier local-environment results, before Docker became available:

- In `backend/`: `.\.venv\Scripts\ruff.exe check .` — `All checks passed!`
- In `backend/`: `.\.venv\Scripts\black.exe --check .` — `92 files would be left unchanged.`
- In `backend/`, with `$env:DATABASE_URL='sqlite:///m5-local.sqlite3'`: `.\.venv\Scripts\python.exe -m pytest -q tests/test_health.py tests/test_payments.py::test_local_fake_topup_credits_only_through_confirmed_wallet_service` — `4 passed in 2.55s`.
- In `backend/`, with the same SQLite URL: full `pytest -q` — `45 passed, 6 failed in 77.15s`. Song storage tests could not reach MinIO at `host.docker.internal`; two concurrency tests failed with SQLite table-lock errors. These results do not establish a passing full suite on the documented Postgres/MinIO setup.

## M9 deployment preparation

- Added a separate production Compose file, production Dockerfiles, strict production settings, an Nginx site template, a production environment template, and R2 database backup/download commands with host backup and isolated restore scripts.
- Production settings reject fake music generation and missing Mureka, Snippe, R2, SMTP, HTTPS, host, or database configuration.
- Actual deployment remains blocked until the VPS is inspected for existing services, ports, memory, disk, and proxy; a production domain/DNS and securely provisioned environment values are also required.
- Do not deploy or perform paid Mureka/Snippe calls from this workspace. Suno stays disabled until `DOCS/SUNO.md` §3 has an official, implemented API contract.
- Before launch, run the documented backup and isolated restore test and complete every applicable launch-checklist item. Legal drafts still need qualified review.

## Next actions

1. Inspect the VPS using `DOCS/DEPLOYMENT.md` §1 without changing any existing system.
2. Confirm domain/DNS, the available reverse proxy, free localhost ports, and host capacity before enabling the Nginx site or starting Compose.
3. Provision production secrets directly on the VPS, then build, migrate, collect static files, start services, and verify HTTPS.
4. Configure support email/WhatsApp values and verify SMTP, real Snippe, and real Mureka only with separately approved production credentials and explicit test amounts.
5. Run the first R2 backup and isolated restore test; finish the remaining launch checklist.

## Important constraints

- Do not add dependencies, frameworks, databases, or services without asking.
- Money is integer TZS. Balance changes go only through `backend/apps/wallet/services.py` and must remain idempotent.
- Never call real Mureka, Suno, or Snippe in automated tests. Use fake engines/mocks.
- Do not automatically resubmit a paid generation. Follow only official Suno API documentation; if `DOCS/SUNO.md` §3 is empty, leave Suno as a skeleton.
- Filter private data by the authenticated user. Keep secrets in backend environment variables only.
- If two project docs conflict or a required rule is unclear, stop and ask rather than guessing.
