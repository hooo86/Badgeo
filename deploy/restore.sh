#!/usr/bin/env bash
# Restore an encrypted backup into the running database. DESTRUCTIVE: replaces current data.
# Usage: BACKUP_PASSPHRASE=... deploy/restore.sh backups/badgeo-XXXX.sql.gz.enc
set -euo pipefail
cd "$(dirname "$0")/.."
: "${BACKUP_PASSPHRASE:?Set BACKUP_PASSPHRASE}"
file="${1:?backup file required}"
set -a; . ./.env; set +a
read -r -p "This REPLACES database '$POSTGRES_DB'. Type 'yes' to continue: " ok
[ "$ok" = "yes" ] || { echo "Aborted."; exit 1; }
docker compose stop web worker beat
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\"" -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\""
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE -in "$file" | gunzip \
  | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q
docker compose up -d web worker beat
echo "Restore complete."
