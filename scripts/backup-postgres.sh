#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR=/opt/osp-music
BACKUP_DIR="$PROJECT_DIR/backups"
COMPOSE=(docker compose -p osp-music -f "$PROJECT_DIR/docker-compose.prod.yml")

install -d -o 10001 -g 10001 -m 0750 "$BACKUP_DIR"
backup_file="$(mktemp --suffix=.dump "$BACKUP_DIR/osp-music-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
trap 'rm -f -- "$backup_file"' EXIT
chmod 0600 "$backup_file"

"${COMPOSE[@]}" exec -T db sh -c \
  'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --no-owner --no-acl' \
  > "$backup_file"
chown 10001:10001 "$backup_file"

"${COMPOSE[@]}" run --rm --no-deps api \
  python manage.py backup_database --file "/backups/$(basename "$backup_file")"
