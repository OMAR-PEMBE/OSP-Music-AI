# SUNO.md — Second music engine

Suno is OSP Music AI's **second engine**, next to Mureka ([MUREKA.md](MUREKA.md)). Both plug into the same `MusicEngine` interface (ARCHITECTURE.md §4), so wallet, jobs, refunds and the UI work the same for both.

## 1. Which Suno API

- Use **only the official Suno API**: `https://platform.suno.com` (sign in with the Suno account → API keys, docs, billing).
- **Do NOT use unofficial "Suno API" wrapper sites** or scripts that automate the suno.com website. They can be shut down or banned at any time, which would break paid jobs and lose user money.
- The API docs are behind login. Omar copies the details into §3 below after signing in. **The agent must not invent endpoints** — if §3 is empty, build only the skeleton (§5) and stop.

## 2. Before enabling Suno in production (Omar checks once)

- [ ] API key created on platform.suno.com.
- [ ] Price per song/version known → put into AppSettings `suno_cost_per_version_usd_cents`.
- [ ] Commercial use of API outputs allowed for users of OSP (read the API terms; Suno's general terms have restricted use in competing music apps — the API terms must allow our use).
- [ ] Number of songs returned per request (we need 2 per request; if Suno returns 1, we make 2 calls).
- [ ] Concurrency / rate limits.
- [ ] How long output audio URLs stay valid.

## 3. API details (fill in from official docs)

| Item | Value |
|---|---|
| Base URL | _TBD_ |
| Auth header | _TBD_ (expected: `Authorization: Bearer $SUNO_API_KEY`) |
| Start song (with lyrics) | _TBD_ method + path + body fields |
| Check status | _TBD_ |
| Status values | _TBD_ → map to ours in §4 |
| Output fields | _TBD_ (audio URL, duration, stream URL?) |
| Lyrics endpoint (if any) | _TBD_ — if none, use Mureka lyrics (MUREKA.md §5) |
| Songs per request | _TBD_ |
| Price | _TBD_ |
| Webhook/callback support | _TBD_ (if yes, still confirm by polling) |

## 4. Mapping to our job states

Map Suno's statuses onto the same states used for Mureka (MUREKA.md §6):

| Our state | Meaning |
|---|---|
| running | accepted, generating |
| streaming | partial audio playable (only if Suno supports it) |
| succeeded → `store_version` | audio ready |
| failed | failed / cancelled / timed out |

All the same rules apply: never auto-resubmit a paid request, 20-minute timeout, copy MP3 to R2, settle refunds exactly once (WALLET.md §4).

## 5. What to build (skeleton — always)

- `backend/engines/suno.py` → `SunoEngine(MusicEngine)` with `submit_song`, `get_status`, `get_capacity`; `generate_lyrics` delegates to Mureka unless Suno has its own lyrics endpoint.
- `SUNO_API_KEY`, `SUNO_BASE_URL` env vars.
- `FakeEngine` tests run against both engine names so the job pipeline is proven engine-independent.
- If `SUNO_API_KEY` is empty, `SunoEngine` is marked unavailable and can't be selected.
- While §3 is still TBD, `SunoEngine` delegates lyrics to Mureka, reports zero song capacity, and refuses song submission without making a network request. The fake engine can exercise the Suno route in tests.

## 6. How the two engines are used (MVP)

Controlled in AppSettings by the admin — the user does not pick an engine in MVP:

| Setting | Values | Default |
|---|---|---|
| `active_engine` | `mureka`, `suno` | `mureka` |
| `fallback_engine` | `none`, `mureka`, `suno` | `none` → set to `suno` once Suno is verified |

- New jobs use `active_engine`. The engine used is saved on `SongJob.engine` (each job stays on one engine for its whole life).
- **Fallback** (only at submit time, never after a task was accepted): if the active engine is paused (low balance), returns a capacity error for more than 2 minutes, or has its API key missing → submit to `fallback_engine` instead.
- **Margin guard:** an engine can't be active or fallback unless its per-version cost is set and `(2 × per-version USD cents + Mureka lyrics USD cents) × usd_to_tzs ≤ 60 × song_price_tzs`. Admin sees a validation error otherwise.
- `generation_enabled` is the global admin pause. A low Mureka balance makes Mureka unavailable to the router; it does not disable a configured fallback.
- Phase 2 option: let users choose "Sauti A / Sauti B" (engine choice) in Create, after comparing quality.
