#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="${1:-${ORBIT_DATA_DIR:-$HOME/.orbit}}"
BACKUP_DIR="${2:-${ORBIT_BACKUP_DIR:-./backups}}"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "backup source does not exist: $SOURCE_DIR" >&2
  exit 1
fi
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="$BACKUP_DIR/orbit-data-$STAMP.tar.gz"
MANIFEST="$ARCHIVE.sha256"

tar -C "$SOURCE_DIR" -czf "$ARCHIVE" .
sha256sum "$ARCHIVE" | tee "$MANIFEST"
printf 'backup created: %s\n' "$ARCHIVE"
