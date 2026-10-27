# DEPLOYMENT.md — Running on the Contabo VPS

VPS: Contabo, ~200 GB SSD, ~11 GB RAM, **already running two other systems** (one directly on the server, one in Docker). OSP Music AI must not break them.

## 1. Golden rules

1. **Inspect before changing anything.** Before the first deploy, run and save the output of:
   ```bash
   docker ps -a; docker network ls; docker volume ls
   sudo ss -tulpn          # which ports are in use (80/443?)
   free -h; df -h
   ls /etc/nginx/sites-enabled 2>/dev/null; systemctl status nginx caddy apache2 2>/dev/null
   ```
2. Never stop, restart, or edit the existing systems' containers, volumes, or configs.
3. OSP runs as its own Compose project: `docker compose -p osp-music -f docker-compose.prod.yml ...`.
4. Postgres and Redis are **never** exposed to the internet (no `ports:` for them).
5. Secrets live in `/opt/osp-music/.env` (chmod 600), never in Git.

## 2. Services (docker-compose.prod.yml)

| Service | Image / build | Memory limit | Notes |
|---|---|---|---|
| web | `./web` (Next.js standalone) | 512 MB | listens 3000 inside network |
| api | `./backend` (gunicorn, 3 workers) | 768 MB | listens 8000 inside network |
| worker | `./backend` (`celery worker -c 4`) | 512 MB | |
| beat | `./backend` (`celery beat`) | 128 MB | exactly ONE instance |
| db | `postgres:16-alpine` | 1 GB | volume `osp_pgdata` |
| redis | `redis:7-alpine` (`--maxmemory 128mb`) | 192 MB | no persistence needed |

Total ≈ 3.1 GB — fits next to the existing systems. Check `free -h` after start.

Bind web and api only to localhost so the existing proxy can reach them:
```yaml
web:  ports: ["127.0.0.1:3100:3000"]
api:  ports: ["127.0.0.1:8100:8000"]
```
(Pick other ports if 3100/8100 are taken — check `ss -tulpn`.)

Every service: `restart: unless-stopped`, healthcheck, and log rotation:
```yaml
logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }
```

## 3. Reverse proxy and HTTPS

**Case A — nginx already serves 80/443 (most likely):** add one new file `/etc/nginx/sites-available/osp-music` and symlink it. Do not edit the other sites.

```nginx
server {
  server_name music.example.co.tz;          # real domain
  client_max_body_size 5m;
  location /api/      { proxy_pass http://127.0.0.1:8100; include proxy_params; }
  location /admin/    { proxy_pass http://127.0.0.1:8100; include proxy_params; }
  location /webhooks/ { proxy_pass http://127.0.0.1:8100; include proxy_params; }
  location /static/   { proxy_pass http://127.0.0.1:8100; }
  location /          { proxy_pass http://127.0.0.1:3100; include proxy_params; }
}
```
Then `sudo nginx -t && sudo systemctl reload nginx` (reload, not restart) and `sudo certbot --nginx -d music.example.co.tz`.

**Case B — nothing on 80/443:** add a `caddy` service to the Compose file with the same routes; Caddy gets HTTPS automatically.

Django settings for production: `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`.

## 4. Environment variables (`.env.example`)

```
# Django
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=music.example.co.tz
PUBLIC_BASE_URL=https://music.example.co.tz
DATABASE_URL=postgres://osp:<password>@db:5432/osp_music
REDIS_URL=redis://redis:6379/0
# Engines
MUSIC_ENGINE=mureka            # or fake
MUREKA_API_KEY=
SUNO_API_KEY=                  # official key from platform.suno.com
SUNO_BASE_URL=                 # from Suno's official docs
# Payments
SNIPPE_API_KEY=
SNIPPE_WEBHOOK_SECRET=
# Storage (Cloudflare R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=osp-music-songs
R2_BACKUP_BUCKET=osp-music-backups
# Email
EMAIL_HOST= EMAIL_PORT=587 EMAIL_HOST_USER= EMAIL_HOST_PASSWORD= DEFAULT_FROM_EMAIL=
# Optional
SENTRY_DSN=
```

## 5. Storage

- Cloudflare R2 bucket `osp-music-songs`: **private** (no public access). The api creates 10-minute signed URLs.
- R2 free tier covers 10 GB storage; a song is ~4–8 MB per version → roughly 600–1,200 requests free, then ~$0.015/GB/month. No download (egress) fees.

## 6. Backups

- Nightly 02:00 EAT: `pg_dump | gzip` → upload to R2 bucket `osp-music-backups` (keep 14 days). Run as a small `backup` service or host cron.
- **Test a restore** into a temporary database before launch and once a month.
- Songs are already in R2, so only the database needs backing up.

## 7. Deploy steps (each release)

```bash
cd /opt/osp-music && git pull
docker compose -p osp-music -f docker-compose.prod.yml build
docker compose -p osp-music -f docker-compose.prod.yml run --rm api python manage.py migrate
docker compose -p osp-music -f docker-compose.prod.yml run --rm api python manage.py collectstatic --noinput
docker compose -p osp-music -f docker-compose.prod.yml up -d
curl -fsS https://music.example.co.tz/api/health
```
Rollback: `git checkout <previous tag>` and repeat (migrations must be backward-compatible — never drop a column in the same release that stops using it).

## 8. Launch checklist

- [ ] Existing systems still working after OSP started (check them manually).
- [ ] HTTPS works; `/api/health` OK.
- [ ] `/admin` reachable only with a staff account; strong password.
- [ ] Snippe live key, webhook secret set; real TZS 1,000 top-up works (SNIPPE.md §8).
- [ ] Mureka key set; balance ≥ $10; one real song generated end-to-end.
- [ ] Suno: SUNO.md §2 checklist done, key set, one real song end-to-end — then set it as fallback engine.
- [ ] Refund path tested with `FakeEngine` on staging (`#fail1`, `#fail2`).
- [ ] Backup ran and restore tested.
- [ ] Postgres/Redis ports not reachable from outside (`nmap` from your laptop).
- [ ] Terms, Privacy, Refund pages published; WhatsApp number set in AppSettings.
