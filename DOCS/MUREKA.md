# MUREKA.md — Music engine integration

Source: Mureka API docs (platform.mureka.ai/docs), checked 27 Oct 2026. If the live docs differ, the live docs win — update this file.

## 1. Basics

- Base URL: `https://api.mureka.ai`
- Auth header: `Authorization: Bearer $MUREKA_API_KEY` (backend only).
- Billing is prepaid; each song version and each lyrics call is charged.
- Always log the `trace_id` returned by Mureka (response header / body) with the job — Mureka support needs it.
- Commercial use: Mureka FAQ states content from paid API calls includes commercial rights. This is what we tell users (PRD 4.7).
- Language: Swahili is **not** on Mureka's official language list. We still send Swahili lyrics; quality is monitored from real usage.

## 2. Endpoints we use

| Purpose | Method + path | Notes |
|---|---|---|
| Write lyrics | `POST /v1/lyrics/generate` | body `{ "prompt": "..." }` → `{ title, lyrics }` |
| Start song | `POST /v1/song/generate` | returns task `{ id, status, ... }` |
| Check song | `GET /v1/song/query/{task_id}` | returns status + `choices` |
| Account balance | `GET /v1/account/billing` | `balance` (US cents), `concurrent_request_limit` |

### 2.1 `POST /v1/song/generate` body we send

```json
{
  "lyrics": "<= 5000 chars, with [Verse] [Chorus] tags>",
  "model": "mureka-9",
  "prompt": "bongo flava, swahili vocals, romantic, male vocal",
  "gender": "male",
  "n": 2,
  "stream": true
}
```

- `lyrics` is **required** (we always use lyrics-to-song — it is much cheaper than prompt-only).
- `model`: from `AppSettings.mureka_model`. Configured in OSP as `mureka-7.6`, `mureka-8`, `mureka-9`, or `mureka-9.5`. Default `mureka-9`.
- The live API also lists `mureka-o2`; OSP does not expose it until its cost estimate is confirmed and configured.
- `prompt` ≤ 1,024 chars. Built by `build_style_prompt(genre, language, voice, idea)` — see §4.
- `gender`: `male` / `female`; omit when voice = `auto`.
- `n`: always 2.
- `stream`: always true (users can listen while it's being made).
- Do NOT send `vocal_id`, `reference_id`, `melody_id` in MVP.

### 2.2 Task statuses (from Mureka)

`preparing`, `queued`, `running`, `streaming`, `succeeded`, `failed`, `timeouted`, `cancelled`

### 2.3 `choices[]` (in query response)

`index`, `id`, `url` (MP3, valid 30 days), `flac_url`, `wav_url`, `stream_url` (during streaming), `duration` (ms), `lyrics_sections`.

We store the MP3 (`url`) in R2. FLAC/WAV are not used in MVP.

## 3. Prices we assume (for reports only — real charge comes from Mureka)

| Item | USD |
|---|---|
| Lyrics generation | $0.009 per call |
| Lyrics-to-song, mureka-7.6 | $0.03 per version |
| Lyrics-to-song, mureka-8 / 9 | $0.045 per version |
| Lyrics-to-song, mureka-9.5 | $0.15 per version |

At default settings one request ≈ 2 × $0.045 + $0.009 = **$0.099 ≈ TZS 260**.
Admin rule: if `mureka_model = mureka-9.5`, the admin page shows a warning unless `song_price_tzs ≥ 1,500`.

## 4. Style prompt builder

```python
GENRE_TAGS = {
  "bongo_flava": "bongo flava, east african pop, swahili",
  "rnb":         "r&b, smooth, soulful",
  "afrobeats":   "afrobeats, west african groove",
  "amapiano":    "amapiano, log drum, south african house",
  "gospel":      "african gospel, choir, uplifting",
  "hiphop":      "hip hop, rap",
}
LANG_TAGS = {"sw": "swahili lyrics", "en": "english lyrics", "mixed": "swahili and english lyrics"}
```
`prompt = ", ".join([GENRE_TAGS[genre] or other_text, LANG_TAGS[language], voice_tag, short_mood_from_idea])[:1024]`

Keep the builder in one function so we can tune it without touching anything else.

## 5. Lyrics

- Called by `POST /api/lyrics` ("Write lyrics for me") and automatically at job submit if lyrics are empty.
- Prompt sent to Mureka: `"{language instruction}. Genre: {genre}. Song about: {idea}. Use [Verse], [Chorus], [Bridge] sections."` where the language instruction is e.g. `"Andika mashairi kwa Kiswahili"` for `sw`.
- Free for the user, max `lyrics_daily_limit` per user per day (count `LyricsRequest` rows today, EAT timezone). Auto-lyrics at job submit do not count toward the limit.
- Truncate to 5,000 chars.

## 6. Job lifecycle (our side)

```
queued → submitting → running → streaming → ready | partial | failed
```

### 6.1 `dispatch_jobs` (Celery Beat, every 5 s)
1. `engine = router.get_engine_for_new_job()`; `capacity = engine.get_capacity()` (Mureka: cached `concurrent_request_limit`, refreshed from `/v1/account/billing` every 10 min; default 1).
2. `in_flight = count(jobs of that engine in submitting/running/streaming)`; capacity is tracked separately for each engine.
3. While `in_flight < capacity`: pick the oldest `queued` job with `select_for_update(skip_locked=True)`, set `submitting`, commit, then call `submit_song`.
4. If the global admin `generation_enabled` switch is false → do nothing (jobs wait). Low Mureka balance marks Mureka unavailable; the router may use the configured fallback. If no fallback is available, queued jobs wait.

### 6.2 Submitting
- Success → save `provider_task_id`, `trace_id`, status `running`, `submitted_at`.
- Mureka returns 4xx (bad input) → job `failed`, settle (full refund).
- Mureka returns 429 / "concurrency" error → put back to `queued`, retry later.
- Network timeout / 5xx with **no task id** → **do not resubmit**. Mark `failed` with reason `submit_uncertain`, settle (full refund), log loudly. (We may lose ~TZS 260 if Mureka actually made it; that is cheaper and safer than double-charging.)

### 6.3 `poll_jobs` (Celery Beat, every 5 s)
For each job in `running` / `streaming` (oldest first, max 50 per run):
- Call `GET /v1/song/query/{task_id}`, `poll_attempts += 1`.
- `streaming` → save `stream_url` on versions, version status `streaming`, job `streaming`.
- `succeeded` → for each choice: enqueue `store_version(job_id, index, url, duration)`.
- `failed` / `timeouted` / `cancelled` → all versions `failed` → settle.
- Still running after **20 minutes** since `submitted_at` → mark `failed` (reason `timeout_ours`) → settle.
- Network error while polling → just try again next run (polling is always safe).

### 6.4 `store_version` (Celery task, retries 5× with backoff)
- Download MP3 from `url` → upload to R2 `songs/{user_id}/{job_id}/{index}.mp3` → save `storage_key`, `size_bytes`, `duration_ms`, status `ready`.
- If the task finally fails → version `failed`.
- If `succeeded` returned fewer than 2 choices → missing versions are `failed`.

### 6.5 Final state + settle
When every version is `ready` or `failed`:
- 2 ready → job `ready`; 1 → `partial`; 0 → `failed`.
- `finished_at = now()`, `seen_by_user = false`, then call settlement (WALLET.md §4).

## 7. Low balance alert

Every 10 min (with the capacity refresh): if `balance / 100 < mureka_low_balance_usd` → admin warning banner + error log. If balance is below the estimated cost of one request, Mureka is marked unavailable to the router. This does not change the global `generation_enabled` switch, so a configured fallback can receive new jobs. Without a usable fallback, queued jobs wait.

## 8. FakeEngine (dev & tests)

`MUSIC_ENGINE=fake` → `FakeEngine`:
- lyrics: returns fixed Swahili sample lyrics.
- submit: returns `fake-{uuid}`.
- status: `running` for 2 polls, `streaming` 1 poll, then `succeeded` with 2 choices pointing to a sample MP3 in `backend/tests/fixtures/`.
- Special idea text `#fail1` → only 1 choice; `#fail2` → `failed`; `#timeout` → never finishes. Used to test refunds.

Routine tests must never call the real Mureka API.

## 9. Suno

Suno is the second engine and uses the same job lifecycle (§6), with the engine saved on each job. The dispatcher asks `engines/router.py` which engine to use; capacity is counted per engine. See [SUNO.md](SUNO.md).
