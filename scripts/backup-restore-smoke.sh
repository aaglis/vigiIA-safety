#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-infra/compose/docker-compose.dev.yml}"
project_name="${COMPOSE_PROJECT_NAME:-vigia_backup_restore_smoke}"
backup_dir="${BACKUP_DIR:-/tmp/vigia-backup-restore-smoke}"
export POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-35432}"
export REDIS_HOST_PORT="${REDIS_HOST_PORT:-36379}"
export MINIO_HOST_PORT="${MINIO_HOST_PORT:-39000}"
export MINIO_CONSOLE_HOST_PORT="${MINIO_CONSOLE_HOST_PORT:-39001}"
export API_HOST_PORT="${API_HOST_PORT:-38000}"

cleanup() {
  docker compose -p "$project_name" -f "$compose_file" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

rm -rf "$backup_dir"
mkdir -p "$backup_dir"

echo "Backup/restore smoke: validando Compose isolado..."
docker compose -p "$project_name" -f "$compose_file" config -q

echo "Backup/restore smoke: construindo imagens necessárias..."
docker compose -p "$project_name" -f "$compose_file" build api migrate seed >/dev/null

echo "Backup/restore smoke: subindo banco e storage limpos..."
docker compose -p "$project_name" -f "$compose_file" up -d postgres minio >/dev/null

echo "Backup/restore smoke: aplicando migrations e seed demo..."
docker compose -p "$project_name" -f "$compose_file" run --rm migrate >/dev/null
docker compose -p "$project_name" -f "$compose_file" run --rm seed >/dev/null

echo "Backup/restore smoke: gerando dump PostgreSQL..."
docker compose -p "$project_name" -f "$compose_file" exec -T postgres pg_dump -U vigia -d vigia > "$backup_dir/postgres.sql"
test -s "$backup_dir/postgres.sql"

echo "Backup/restore smoke: gerando snapshot do volume MinIO..."
docker run --rm -v "${project_name}_minio-data:/data:ro" -v "$backup_dir:/backup" busybox sh -c 'tar -czf /backup/minio-data.tgz -C /data .'
test -s "$backup_dir/minio-data.tgz"

echo "Backup/restore smoke: recriando volumes limpos..."
docker compose -p "$project_name" -f "$compose_file" down -v --remove-orphans >/dev/null
docker compose -p "$project_name" -f "$compose_file" up -d postgres minio >/dev/null

for _ in $(seq 1 30); do
  if docker compose -p "$project_name" -f "$compose_file" exec -T postgres pg_isready -U vigia -d vigia >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker compose -p "$project_name" -f "$compose_file" exec -T postgres pg_isready -U vigia -d vigia >/dev/null

echo "Backup/restore smoke: restaurando PostgreSQL..."
docker compose -p "$project_name" -f "$compose_file" exec -T postgres psql -U vigia -d vigia < "$backup_dir/postgres.sql" >/dev/null

echo "Backup/restore smoke: restaurando MinIO..."
docker run --rm -v "${project_name}_minio-data:/data" -v "$backup_dir:/backup:ro" busybox sh -c 'tar -xzf /backup/minio-data.tgz -C /data'

echo "Backup/restore smoke: verificando dados restaurados..."
docker compose -p "$project_name" -f "$compose_file" exec -T postgres psql -U vigia -d vigia -tAc "select count(*) from users where email = 'admin@vigia.local';" | grep -qx "1"
docker compose -p "$project_name" -f "$compose_file" exec -T postgres psql -U vigia -d vigia -tAc "select count(*) from organizations where id = 'org-demo';" | grep -qx "1"

echo "Backup/restore smoke: OK. Artefatos temporários em $backup_dir"
