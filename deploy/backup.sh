#!/usr/bin/env bash
# Encrypted PostgreSQL backup. Usage: BACKUP_PASSPHRASE=... deploy/backup.sh [output_dir]
set -euo pipefail
cd "$(dirname "$0")/.."
: "${BACKUP_PASSPHRASE:?Set BACKUP_PASSPHRASE (store it separately from the backups)}"
set -a; . ./.env; set +a
out="${1:-backups}"; mkdir -p "$out"; chmod 700 "$out"
file="$out/badgeo-$(date +%Y%m%d-%H%M%S).sql.gz.enc"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASSPHRASE > "$file"
chmod 600 "$file"
echo "Backup written: $file"
# retention: keep the 30 most recent
ls -1t "$out"/badgeo-*.enc | tail -n +31 | xargs -r rm --
