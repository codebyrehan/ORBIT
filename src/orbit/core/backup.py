"""Durable request-journal snapshot and restore helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class BackupError(RuntimeError):
    """Raised when a durable request-journal backup cannot be created/restored."""


def create_request_backup(journal_path: Path, destination: Path) -> Path:
    """Create an atomic, validated snapshot of a request journal."""
    if not journal_path.exists():
        raise BackupError(f"request journal does not exist: {journal_path}")

    valid_lines: list[str] = []
    try:
        with journal_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict) or "request_id" not in value or "state" not in value:
                        raise ValueError
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                valid_lines.append(json.dumps(value, separators=(",", ":"), sort_keys=True))
    except OSError as exc:
        raise BackupError(str(exc)) from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            if valid_lines:
                handle.write("\n".join(valid_lines) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except OSError as exc:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise BackupError(str(exc)) from exc
    return destination


def restore_request_backup(backup: Path, journal_path: Path) -> Path:
    """Atomically restore a validated request-journal snapshot."""
    if not backup.exists():
        raise BackupError(f"backup does not exist: {backup}")
    return create_request_backup(backup, journal_path)
