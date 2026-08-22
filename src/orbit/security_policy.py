"""Production security policy helpers for ORBIT."""

from __future__ import annotations

from pathlib import Path

from orbit.security import SecurityError


def confine_path(root: Path, candidate: Path) -> Path:
    """Return a resolved path only when it remains under ``root``."""
    root = root.expanduser().resolve()
    candidate = candidate.expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SecurityError("path escapes configured storage root") from exc
    return candidate


def validate_bearer_token(token: str | None, *, minimum_length: int = 32) -> None:
    """Validate the shape of an API bearer token without logging its value."""
    if token is None:
        return
    if minimum_length < 1:
        raise ValueError("minimum_length must be positive")
    if len(token) < minimum_length:
        raise SecurityError("API token is too short")
    if any(char.isspace() for char in token):
        raise SecurityError("API token must not contain whitespace")


def redact(value: str | None, *, visible_suffix: int = 4) -> str | None:
    """Redact sensitive values for diagnostics."""
    if value is None:
        return None
    if visible_suffix < 0:
        raise ValueError("visible_suffix must be non-negative")
    if len(value) <= visible_suffix:
        return "*" * len(value)
    return "*" * (len(value) - visible_suffix) + value[-visible_suffix:]
