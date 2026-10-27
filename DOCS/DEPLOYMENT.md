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
| db | `postgres:16-alpine` | 1 GB | private project-scoped volume |
| redis | `redis:7-alpine` (`--maxmemory 128mb`) | 192 MB | no persistence needed |

Total ≈ 3.1 GB — fits next to the existing systems. Check `free -h` after start.

Bind web and api only to localhost so the existing proxy can reach them:
```yaml
web:  ports: ["127.0.0.1:3100:3000"]
api:  ports: ["127.0.0.1:8100:8000"]
```
(Pick other ports if 3100/8100 are taken — check `ss -tulpn`.)

Every long-running service has a healthcheck, restart policy, and bounded logs.
Postgres and Redis have no published ports. The API and web bind to loopback only.

Create the host directories before the first start so the non-root API user can
write static files and backups:
```bash
sudo install -d -o 10001 -g 10001 -m 0755 /opt/osp-music/staticfiles
sudo install -d -o 10001 -g 10001 -m 0750 /opt/osp-music/backups
```

## 3. Reverse proxy and HTTPS

**Case A — nginx already serves 80/443 (most likely):** inspect the VPS first,
then copy `deploy/nginx/osp-music.conf.example` to
`/etc/nginx/sites-available/osp-music`, replace the example hostname, and enable
only this new site. Do not edit the other sites. The config serves collected
Django static files directly from `/opt/osp-music/staticfiles`.

Then run `sudo nginx -t && sudo systemctl reload nginx` (reload, not restart)
and `sudo certbot --nginx -d <your-domain>`. Confirm DNS already points to the
VPS before requesting a certificate.

**Case B — nothing on 80/443:** do not enable a proxy until port availability,
DNS, and the VPS firewall have been checked. Add a dedicated proxy service only
after confirming it will not conflict with existing systems.

Django production settings fail closed unless HTTPS, host/origin, database,
Redis, R2, SMTP, Mureka, and Snippe configuration is present. Fake music
generation is rejected in production.

## 4. Environment variables (`.env.prod.example`)

Copy `.env.prod.example` to `/opt/osp-music/.env`, fill every required value,
and set permissions to `600`. Generate a fresh Django key and a long random,
hex-only PostgreSQL password; use the same password in `POSTGRES_PASSWORD` and
`DATABASE_URL`. Do not copy the repository's local `.env` to the server.

The production image rejects `MUSIC_ENGINE=fake` and missing provider
credentials to prevent paid requests from silently using `FakeEngine`. Keep
Suno disabled until the official API contract in `SUNO.md` §3 is complete.

## 5. Storage

- Cloudflare R2 bucket `osp-music-songs`: **private** (no public access). The api creates 10-minute signed URLs.
- R2 free tier covers 10 GB storage; a song is ~4–8 MB per version → roughly 600–1,200 requests free, then ~$0.015/GB/month. No download (egress) fees.

## 6. Backups

- `scripts/backup-postgres.sh` creates a PostgreSQL 16 custom-format dump
  (compressed by `pg_dump`), uploads it to the private R2 bucket
  `osp-music-backups`, and removes backups older than 14 days. The local
  temporary dump is permission-restricted and removed after upload.
- Install it in root's crontab at 02:00 East Africa Time, for example:
  `CRON_TZ=Africa/Dar_es_Salaam` followed by
  `0 2 * * * bash /opt/osp-music/scripts/backup-postgres.sh >> /var/log/osp-music-backup.log 2>&1`.
- Run `sudo bash /opt/osp-music/scripts/test-postgres-restore.sh` after the first
  backup and monthly. It downloads the newest dump and restores it inside a
  disposable PostgreSQL 16 container with no network or published ports.
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
The Compose file publishes only `127.0.0.1:3100` and `127.0.0.1:8100`;
confirm those ports are free before starting it. For the first release, configure
the DNS, proxy, and HTTPS only after inspecting the VPS as described in §1.

## 8. Launch checklist

- [ ] Existing systems still working after OSP started (check them manually).
- [ ] HTTPS works; `/api/health` OK.
- [ ] `/admin` reachable only with a staff account; strong password.
- [ ] Snippe live key, webhook secret set; real TZS 1,000 top-up works (SNIPPE.md §8).
- [ ] Mureka key set; balance ≥ $10; one real song generated end-to-end.
- [ ] Suno is not selected unless SUNO.md §3 has an official, implemented API contract and its separate launch checks are complete.
- [ ] Refund path tested with `FakeEngine` on staging (`#fail1`, `#fail2`).
- [ ] Backup ran and restore tested.
- [ ] Postgres/Redis ports not reachable from outside (`nmap` from your laptop).
- [ ] Terms, Privacy, Refund pages published; WhatsApp number set in AppSettings.
