#!/usr/bin/env bash
# Backs up the production Postgres database to a timestamped, gzipped
# SQL dump. Run manually, or point a scheduler (Render Cron Job, GitHub
# Actions on a schedule, or plain crontab on any machine with `pg_dump`
# installed) at this script.
#
# Requires DATABASE_URL to be set to the *external* connection string
# from the Render Postgres dashboard (Render > your Postgres instance >
# Connections > External Database URL) — the internal one only works
# from inside Render's network.
#
# Usage:
#   DATABASE_URL="postgresql://user:pass@host:5432/dbname" ./backup_db.sh
#
# Restores with:
#   gunzip -c backups/blazingtrail_2026-08-11_120000.sql.gz | psql "$DATABASE_URL"

set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set. Export it (external connection string) and re-run." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date -u +"%Y-%m-%d_%H%M%S")"
OUT_FILE="$BACKUP_DIR/blazingtrail_${TIMESTAMP}.sql.gz"

echo "Backing up $DATABASE_URL to $OUT_FILE ..."
pg_dump "$DATABASE_URL" | gzip > "$OUT_FILE"
echo "Done: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"

# Keep the last 30 local backups only, so this doesn't grow unbounded if
# it's ever run from a machine with persistent storage (e.g. a VPS cron).
# Render's own filesystem is ephemeral, so if you run this FROM Render
# (a Cron Job), ship $OUT_FILE somewhere durable — e.g. `aws s3 cp` or
# similar — before the job's container is torn down. A local `find
# -delete` alone is not a backup strategy on Render.
find "$BACKUP_DIR" -name "blazingtrail_*.sql.gz" -type f -printf "%T@ %p\n" \
  | sort -rn | tail -n +31 | cut -d' ' -f2- | xargs -r rm -f
