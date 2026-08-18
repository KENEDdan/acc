#!/bin/sh
# Manual/cron-triggered Postgres backup, for when you're not using the
# `backup` service in docker-compose.prod.yml (e.g. a managed DB, or you
# just want an ad-hoc dump). Requires DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/
# DB_PORT in the environment — `set -a; . ./.env; set +a` before running
# this if you're calling it outside of docker compose.
#
# Usage: ./scripts/backup_db.sh [output-directory]
#
# IMPORTANT: this alone does not protect you from losing the whole host —
# copy BACKUP_DIR off-box regularly (e.g. `aws s3 sync`, rclone, rsync to
# another machine). A backup that only exists on the server it's backing up
# is not a backup.
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
