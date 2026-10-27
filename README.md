# OSP Music AI

Local development stack for OSP Music AI. The backend uses Django REST Framework, PostgreSQL, Celery, Redis, and S3-compatible object storage (MinIO/SILO in Compose). Music generation defaults to `MUSIC_ENGINE=fake`; the deterministic fake engine exercises song jobs without provider credentials. The wallet uses `SNIPPE_FAKE_MODE=true` locally to simulate a confirmed top-up through the regular wallet settlement path. This mode makes no payment-provider network calls and is disabled in production. Mureka and Suno credentials can be added later; Suno remains a non-networking skeleton until its official API details are added to `DOCS/SUNO.md` section 3.

## Run locally

Requirements: Docker Engine with the Docker Compose plugin.

1. Copy `.env.example` to `.env`. The example values are only for local development.
2. Start the stack from the project root:

   ```sh
   docker compose up --build
   ```

3. Open <http://localhost:3000>. The home page calls `/api/health`; a working stack reports `db: ok` and `redis: ok`. Django is also available at <http://localhost:8000/api/health>.
4. Apply the database migrations:

   ```sh
   docker compose exec api python manage.py migrate
   ```

5. Read signup, verification, and password reset email from the API logs:

   ```sh
   docker compose logs -f api
   ```

6. Stop with `Ctrl+C`; remove the local stack and volumes with `docker compose down -v` to reset local data.

The headless browser auth API is mounted at `/api/auth/browser/v1/auth/`. Profile read/update and avatar upload use `/api/me`, `/api/me/avatar`; account deletion uses `/api/me/delete`. Song endpoints are under `/api/songs`; the lyrics helper is `/api/lyrics`. Generated audio is stored in the local S3-compatible bucket and served through short-lived signed URLs.

The interface is English-only and follows the device theme by default. Theme preferences are saved to the signed-in profile and cached on the device. Song language can still be selected independently. The web app includes an installable PWA manifest and app icon; use the in-app install action or the browser's Add to Home Screen option. Offline audio or page caching is not enabled.

The public FAQ and contact form are at `/faq` and `/contact`. Set `support_email` and `support_whatsapp` in the application settings in Django admin, and configure the SMTP environment variables before accepting support messages. Draft Terms, Privacy, and Refund pages are at `/terms`, `/privacy`, and `/refunds`; they require owner/legal approval before launch. Account deletion in Settings requires the current password, removes songs and lyrics, deletes stored files, and retains anonymized song, wallet, ledger, and payment records; any remaining wallet balance is lost.

PostgreSQL and Redis are private to the Compose network. The S3-compatible `minio` service uses SILO, a MinIO community fork, because upstream MinIO images are no longer pullable; its local console is at <http://localhost:9001> (credentials are in `docker-compose.yml`), and local song download links use the host-accessible endpoint at <http://localhost:9000>. Local account avatars use the persistent `media` volume; production storage is configured for Cloudflare R2. No external API credentials are needed for local development flows. Demo wallet top-ups are labeled on the wallet screen and complete instantly without contacting Snippe.

## Backend checks

With Python 3.12 and dependencies installed:

```sh
cd backend
python -m pip install -e '.[dev]'
pytest
ruff check .
black --check .
```

The Celery task test executes the task eagerly in-process. To run it through a live worker, start Compose and run `docker compose exec api python manage.py shell -c "from apps.core.tasks import sample_task; print(sample_task.delay().get(timeout=10))"`.

## Web checks

```sh
cd web
npm install
npm run lint
npm run format:check
```
