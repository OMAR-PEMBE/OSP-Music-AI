# OSP Music AI — Coding Agent Handoff

Updated: 2026-10-28

## Start here

Before making changes, read `AGENTS.md` and the current milestone in `DOCS/MILESTONES.md`. Project docs use uppercase `DOCS/` paths in this checkout. Follow the repository rules: implement one milestone at a time, keep Swahili as the default, put UI copy in `web/messages/sw.json` and `web/messages/en.json`, and read `DOCS/WALLET.md` before any change that can affect balances.

## Current state

- M0 through M4b were previously implemented in the repository.
- **M5 — Web app: core screens** and **M6 — Language, theme, PWA** are implemented and verified locally. M6 is the current completed milestone.
- The user said third-party APIs will be purchased/configured later. Keep real Mureka, Suno, and Snippe calls pending unless the user explicitly asks otherwise. Local music generation defaults to `MUSIC_ENGINE=fake`; local top-ups use `SNIPPE_FAKE_MODE=true` and a clearly labeled local simulator that credits through the existing confirmation and wallet service path.
- Do not start M7 until the user approves it.
- The working tree contains uncommitted M5 changes. Inspect `git status` and the existing files before editing; preserve useful work.

## M5 implementation present

- Public landing page and signup, login, email verification, forgot-password, and reset-password screens.
- Signed-in app shell with balance, locale/theme toggles, account link, email-verification notice, and mobile navigation.
- Create screen with lyrics helper, price/balance summary, and song submission/status flow.
- My Music list and song detail pages with A/B players, download links, rename/delete, polling, and unseen-song indicator.
- Wallet screen with balance, presets/custom amount, phone input, payment status/history, and local demo top-ups.
- Profile settings screen with profile editing and avatar upload.
- Swahili and English messages, API/CSRF helpers, responsive styling, public `/api/config`, and correct unseen-song count.
- Documentation notes the local-only fake payment mode.

## M6 implementation present

- `next-intl` uses Swahili by default and English as the second locale; UI copy is in both message dictionaries.
- Locale and system/light/dark theme preferences are cached locally and saved to the signed-in profile. The early bootstrap avoids a theme flash, and login/session changes reload profile preferences.
- Locale-aware dates use the `Africa/Dar_es_Salaam` time zone.
- Added the PWA manifest, SVG and 192/512 PNG icons, install prompt, and iOS Add to Home Screen guidance. Offline caching is intentionally not enabled.
- README documents preference persistence and PWA installation.

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
- `git diff --check` — no whitespace errors (Git printed line-ending conversion warnings).
- No physical-device install was performed; PWA prompt behavior was simulated in the browser. Actual credential logout/login was not repeated, but the same profile reload path is wired to the login event and verified.

Earlier local-environment results, before Docker became available:

- In `backend/`: `.\.venv\Scripts\ruff.exe check .` — `All checks passed!`
- In `backend/`: `.\.venv\Scripts\black.exe --check .` — `92 files would be left unchanged.`
- In `backend/`, with `$env:DATABASE_URL='sqlite:///m5-local.sqlite3'`: `.\.venv\Scripts\python.exe -m pytest -q tests/test_health.py tests/test_payments.py::test_local_fake_topup_credits_only_through_confirmed_wallet_service` — `4 passed in 2.55s`.
- In `backend/`, with the same SQLite URL: full `pytest -q` — `45 passed, 6 failed in 77.15s`. Song storage tests could not reach MinIO at `host.docker.internal`; two concurrency tests failed with SQLite table-lock errors. These results do not establish a passing full suite on the documented Postgres/MinIO setup.

## Next actions

1. Await approval before starting M7.
2. Do not perform real paid provider calls; Mureka, Suno, and Snippe remain in local fake/mock mode.

## Important constraints

- Do not add dependencies, frameworks, databases, or services without asking.
- Money is integer TZS. Balance changes go only through `backend/apps/wallet/services.py` and must remain idempotent.
- Never call real Mureka, Suno, or Snippe in automated tests. Use fake engines/mocks.
- Do not automatically resubmit a paid generation. Follow only official Suno API documentation; if `DOCS/SUNO.md` §3 is empty, leave Suno as a skeleton.
- Filter private data by the authenticated user. Keep secrets in backend environment variables only.
- If two project docs conflict or a required rule is unclear, stop and ask rather than guessing.
