#!/bin/sh
# Manual/cron-triggered Postgres backup. The managed DB provider's own
# automated backups are the primary strategy now (see .env.example /
# DB_HOST) — this is for an occasional ad-hoc snapshot, e.g. before a risky
# migration. Requires DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT in the
# environment — `set -a; . ./.env; set +a` before running this.
#
# Usage: ./scripts/backup_db.sh [output-directory]
set -e

BACKUP_DIR="${1:-./backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_FILE="$BACKUP_DIR/acc_platform_${TIMESTAMP}.sql.gz"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" \
    --no-owner --no-acl \
    | gzip > "$OUT_FILE"

echo "Backup written to $OUT_FILE"

# To restore:
#   gunzip -c "$OUT_FILE" | psql --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME"
