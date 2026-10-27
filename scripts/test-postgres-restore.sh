#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR=/opt/osp-music
BACKUP_DIR="$PROJECT_DIR/backups"
COMPOSE=(docker compose -p osp-music -f "$PROJECT_DIR/docker-compose.prod.yml")
backup_file="$BACKUP_DIR/osp-music-restore-test-$$.dump"
restore_container=""

cleanup() {
  if [ -f "$backup_file" ]; then
    rm -f -- "$backup_file"
  fi
  if [ -n "$restore_container" ] && docker container inspect "$restore_container" >/dev/null 2>&1; then
    docker rm -f "$restore_container" >/dev/null
  fi
}
trap cleanup EXIT

"${COMPOSE[@]}" run --rm --no-deps api \
  python manage.py download_database_backup --output "/backups/$(basename "$backup_file")"

restore_container="$(docker run --detach --rm --network none \
  -e POSTGRES_PASSWORD=restore-test postgres:16-alpine)"

ready=false
for attempt in $(seq 1 30); do
  if docker exec "$restore_container" pg_isready -U postgres >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
if [ "$ready" != true ]; then
  echo "Temporary PostgreSQL did not become ready." >&2
  exit 1
fi

docker exec -i "$restore_container" \
  pg_restore --exit-on-error --no-owner --no-acl -U postgres -d postgres \
  < "$backup_file"
echo "Database backup restored successfully into an isolated temporary PostgreSQL 16 container."
