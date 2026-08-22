from __future__ import annotations

from pathlib import Path

import pytest

from orbit.security import SecurityError
from orbit.security_policy import confine_path, redact, validate_bearer_token


def test_confine_path_rejects_traversal(tmp_path: Path) -> None:
    root = tmp_path / "orbit"
    root.mkdir()
    assert confine_path(root, root / "models" / "model.bin") == (root / "models" / "model.bin").resolve()
    with pytest.raises(SecurityError, match="escapes"):
        confine_path(root, tmp_path / "outside.bin")


def test_validate_bearer_token_rejects_weak_values() -> None:
    validate_bearer_token("x" * 32)
    with pytest.raises(SecurityError, match="short"):
        validate_bearer_token("x" * 31)
    with pytest.raises(SecurityError, match="whitespace"):
        validate_bearer_token("x" * 31 + " ")


def test_redact_keeps_only_safe_suffix() -> None:
    assert redact("super-secret-token") == "**************oken"
    assert redact("abcd") == "****"
    assert redact(None) is None
