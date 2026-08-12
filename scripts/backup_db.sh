#!/usr/bin/env bash
# Online SQLite backup. Safe against a concurrent writer — .backup takes a
# consistent copy rather than reading the file out from under WAL.
set -euo pipefail

DEST="${1:?usage: backup_db.sh <destination-dir>}"
DB="${DB_PATH:-$(cd "$(dirname "$0")/.." && pwd)/data/market.db}"
KEEP_DAYS="${KEEP_DAYS:-30}"

[ -f "$DB" ] || { echo "no database at $DB" >&2; exit 1; }
mkdir -p "$DEST"

STAMP="$(date +%F)"
TMP="$DEST/market-$STAMP.db"
sqlite3 "$DB" ".backup '$TMP'"
gzip -f "$TMP"

find "$DEST" -name 'market-*.db.gz' -mtime "+$KEEP_DAYS" -delete
echo "backed up to $TMP.gz"
