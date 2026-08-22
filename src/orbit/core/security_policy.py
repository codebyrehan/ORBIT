"""Production security policy helpers for ORBIT's API boundary."""

from __future__ import annotations

import os
from pathlib import Path

from orbit.security import SecurityError, constant_time_token_match, safe_child_path


MIN_API_TOKEN_LENGTH = 32


def resolve_api_token(configured: str | None) -> str | None:
    """Resolve the API token from explicit config, then the environment."""
    token = configured or os.getenv("ORBIT_API_TOKEN")
    if token is None:
        return None
    if len(token) < MIN_API_TOKEN_LENGTH or token != token.strip():
        raise SecurityError("ORBIT API token must be at least 32 characters and contain no surrounding whitespace")
    return token


def require_bearer(authorization: str, expected: str) -> None:
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token or not constant_time_token_match(token, expected):
        raise SecurityError("authentication required")


def confined_path(root: Path, candidate: str | Path) -> Path:
    return safe_child_path(root, Path(candidate))
