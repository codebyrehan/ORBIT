"""Security boundaries for ORBIT's local control plane."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path


class SecurityError(ValueError):
    """Raised when a security boundary rejects an operation."""


def constant_time_token_match(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided.encode(), expected.encode())


def configured_api_token() -> str | None:
    token = os.getenv("ORBIT_API_TOKEN")
    return token if token else None


def safe_child_path(root: Path, candidate: Path) -> Path:
    """Resolve a candidate and reject traversal outside root."""
    root_resolved = root.expanduser().resolve()
    candidate_resolved = candidate.expanduser().resolve()
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise SecurityError("path escapes configured storage root") from exc
    return candidate_resolved


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
