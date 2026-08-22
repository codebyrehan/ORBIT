from __future__ import annotations

from pathlib import Path

import pytest

from orbit.core.security_policy import confined_path, require_bearer, resolve_api_token
from orbit.security import SecurityError


def test_resolve_api_token_accepts_valid_explicit_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORBIT_API_TOKEN", "environment-token-that-is-long-enough-123")
    assert resolve_api_token("explicit-token-that-is-long-enough-123") == "explicit-token-that-is-long-enough-123"


def test_resolve_api_token_rejects_short_or_whitespace_tokens() -> None:
    with pytest.raises(SecurityError):
        resolve_api_token("short")
    with pytest.raises(SecurityError):
        resolve_api_token("x" * 32 + " ")


def test_require_bearer_uses_constant_time_policy() -> None:
    expected = "x" * 32
    require_bearer(f"Bearer {expected}", expected)
    with pytest.raises(SecurityError):
        require_bearer("Basic xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", expected)


def test_confined_path_resolves_relative_candidates_inside_root(tmp_path: Path) -> None:
    assert confined_path(tmp_path, "models/a.bin") == (tmp_path / "models/a.bin").resolve()


def test_confined_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(SecurityError):
        confined_path(tmp_path, "../outside.bin")


def test_confined_path_rejects_absolute_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.bin"
    with pytest.raises(SecurityError):
        confined_path(tmp_path, outside)
