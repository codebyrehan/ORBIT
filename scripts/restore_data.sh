#!/usr/bin/env bash
set -euo pipefail

ARCHIVE="${1:?usage: restore_data.sh BACKUP.tar.gz TARGET_DIR}"
TARGET_DIR="${2:?usage: restore_data.sh BACKUP.tar.gz TARGET_DIR}"

if [[ ! -f "$ARCHIVE" ]]; then
  echo "backup archive not found: $ARCHIVE" >&2
  exit 1
fi
if [[ -f "$ARCHIVE.sha256" ]]; then
  sha256sum --check "$ARCHIVE.sha256"
fi
mkdir -p "$TARGET_DIR"
tar -C "$TARGET_DIR" -xzf "$ARCHIVE"
printf 'backup restored: %s -> %s\n' "$ARCHIVE" "$TARGET_DIR"
