# OSP Music AI — Coding Agent Handoff

Updated: 2026-10-27

## Start here

Before making changes, read `AGENTS.md` and the current milestone in `DOCS/MILESTONES.md`. Project docs use uppercase `DOCS/` paths in this checkout. Follow the repository rules: implement one milestone at a time, keep Swahili as the default, put UI copy in `web/messages/sw.json` and `web/messages/en.json`, and read `DOCS/WALLET.md` before any change that can affect balances.

## Current state

- M0 through M4b were previously implemented in the repository.
- The current work is **M5 — Web app: core screens**. M5 implementation is present but its documented end-to-end completion check is still outstanding.
- The user said third-party APIs will be purchased/configured later. Keep real Mureka, Suno, and Snippe calls pending unless the user explicitly asks otherwise. Local music generation defaults to `MUSIC_ENGINE=fake`; local top-ups use `SNIPPE_FAKE_MODE=true` and a clearly labeled local simulator that credits through the existing confirmation and wallet service path.
- Do not start M6 until M5’s phone-sized local flow has been verified and the user has checked the milestone, per `DOCS/MILESTONES.md`.
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

## Verification already run

Commands and observed results from the previous session:

- In `web/`: `npm.cmd run lint` — passed; initially emitted three warnings, which were fixed.
- In `web/`: `npx.cmd tsc --noEmit` — passed (no diagnostics).
- In `web/`: `npm.cmd run format:check` — `All matched files use Prettier code style!`
- In `web/`: `npm.cmd run build` — passed; Next.js generated all 14 routes.
- In `backend/`: `.\.venv\Scripts\ruff.exe check .` — `All checks passed!`
- In `backend/`: `.\.venv\Scripts\black.exe --check .` — `92 files would be left unchanged.`
- In `backend/`, with `$env:DATABASE_URL='sqlite:///m5-local.sqlite3'`: `.\.venv\Scripts\python.exe -m pytest -q tests/test_health.py tests/test_payments.py::test_local_fake_topup_credits_only_through_confirmed_wallet_service` — `4 passed in 2.55s`.
- In `backend/`, with the same SQLite URL: full `pytest -q` — `45 passed, 6 failed in 77.15s`. Song storage tests could not reach MinIO at `host.docker.internal`; two concurrency tests failed with SQLite table-lock errors. These results do not establish a passing full suite on the documented Postgres/MinIO setup.
- `git diff --check` — no whitespace errors (Git printed line-ending conversion warnings).
- `docker compose up --build -d` and `docker compose ps` — could not connect to `npipe:////./pipe/dockerDesktopLinuxEngine`; Docker Desktop’s Linux engine was not running/available. No services were started or health-checked.

## Next actions

1. Check that Docker Desktop/WSL is running and `docker info` works. If unavailable, tell the user the specific engine issue and keep working on independent review tasks.
2. Review the uncommitted M5 diff and resolve any implementation issues found. Do not call real paid provider APIs.
3. From the project root, run `docker compose up --build`, wait for services, and verify health. If Compose starts, apply migrations with `docker compose exec api python manage.py migrate` if needed.
4. Verify the M5 flow in a phone-sized browser: signup → verify email from API logs → local demo top-up → create with fake music engine → listen to both versions → download. Confirm no external provider call is made.
5. Run the backend suite against Compose Postgres/MinIO, plus backend linters and web lint/format/build. Report the actual command output and any remaining failures.
6. Finish with the five-part end-of-milestone report required by `AGENTS.md`. Only after M5 is verified and checked should the next session consider M6.

## Important constraints

- Do not add dependencies, frameworks, databases, or services without asking.
- Money is integer TZS. Balance changes go only through `backend/apps/wallet/services.py` and must remain idempotent.
- Never call real Mureka, Suno, or Snippe in automated tests. Use fake engines/mocks.
- Do not automatically resubmit a paid generation. Follow only official Suno API documentation; if `DOCS/SUNO.md` §3 is empty, leave Suno as a skeleton.
- Filter private data by the authenticated user. Keep secrets in backend environment variables only.
- If two project docs conflict or a required rule is unclear, stop and ask rather than guessing.
