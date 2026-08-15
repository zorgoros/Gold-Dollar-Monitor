#!/usr/bin/env bash
# Pull the collector's database off the market-data branch and keep a local copy.
#
# The branch holds one commit that every run amends and force-pushes, so GitHub
# is a single copy, not a history. This is the second copy. It runs on a machine
# that is sometimes off, and that is the accepted limit: a backup taken most
# days beats a backup taken never.
#
# Extraction only — it never pushes, and never touches the working tree.
set -euo pipefail

DEST="${1:-$HOME/market-monitor-backups}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${BRANCH:-market-data}"

cd "$REPO"
git fetch -q origin "$BRANCH"

# `git show` writes the committed blob, so a half-written working file cannot be
# copied by mistake — the commit is the only thing that exists on that branch.
TMP="$(mktemp -t market-remote-db)"
trap 'rm -f "$TMP"' EXIT
git show "origin/$BRANCH:market.db" > "$TMP"

# Reuse backup_db.sh for the copy itself: it takes a consistent .backup, gzips
# it, stamps the date, and drops anything older than KEEP_DAYS.
DB_PATH="$TMP" "$REPO/scripts/backup_db.sh" "$DEST"
