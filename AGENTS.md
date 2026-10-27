# AGENTS.md — Read this first

You are the senior engineer building **OSP Music AI**: a Tanzanian web app where users type a song idea, get **2 AI song versions** (Mureka API, with Suno as second engine), and pay from a **TZS wallet** topped up by mobile money (Snippe).

## Which document to read

| Task | Read |
|---|---|
| Anything — what the product does and what NOT to build | `docs/PRD.md` |
| Stack, folders, how parts connect | `docs/ARCHITECTURE.md` |
| Models, tables, fields | `docs/DATABASE.md` |
| Anything that changes a balance | `docs/WALLET.md` (**mandatory**) |
| Endpoints, request/response shapes, errors | `docs/API.md` |
| Lyrics, song generation, job states | `docs/MUREKA.md` |
| Second engine, engine switching/fallback | `docs/SUNO.md` |
| Top-ups, webhooks | `docs/SNIPPE.md` |
| Docker, VPS, HTTPS, backups | `docs/DEPLOYMENT.md` |
| What to build next | `docs/MILESTONES.md` |

Each fact lives in **one** document. If two documents seem to disagree, **stop and ask** — do not guess.

## Rules

1. **Build only the current milestone** from MILESTONES.md. No extra features, no "nice to have" additions, nothing from PRD "Not in MVP".
2. **Stack is fixed:** Next.js + TypeScript + Tailwind / Django + DRF / PostgreSQL / Celery + Redis / Cloudflare R2. Do not add frameworks, databases, or services without asking.
3. **Money:** integer TZS only; change balances only through `apps/wallet/services.py`; every operation idempotent. Read WALLET.md every time.
4. **Secrets:** API keys only in backend environment variables. Never in `web/`, Git, logs, or error messages.
5. **Privacy:** every query for private data is filtered by `request.user`.
6. **External APIs:** never call the real Mureka, Suno or Snippe API in automated tests — use `FakeEngine` and mocks. Never automatically resubmit a paid generation. Use only the official Suno API; never invent endpoints — if SUNO.md §3 is empty, build the skeleton only.
7. **Tests:** write tests with the code. Don't say tests passed unless you ran them and they passed.
8. **Small steps:** inspect existing code before changing it; don't rewrite working code unasked.
9. **User-facing text** is English-only and goes in `web/messages/en.json`. Song-language choices (Swahili, English, Mixed) are separate product functionality.
10. **Docs:** if your change makes a doc wrong, update the doc in the same change.

## End-of-milestone report

1. What you built (short list)
2. Files added/changed
3. Tests run + results (actual output)
4. Anything unclear, risky, or left undone
5. Suggested next step
