from pathlib import Path

import pytest

from orbit.security import SecurityError, constant_time_token_match, safe_child_path, sha256_file


def test_constant_time_token_match() -> None:
    assert constant_time_token_match("secret", "secret")
    assert not constant_time_token_match("secret", "other")


def test_safe_child_path_rejects_traversal(tmp_path: Path) -> None:
    allowed = safe_child_path(tmp_path, tmp_path / "models" / "model.bin")
    assert allowed == (tmp_path / "models" / "model.bin").resolve()
    with pytest.raises(SecurityError):
        safe_child_path(tmp_path, tmp_path / ".." / "outside.bin")


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"orbit")
    assert sha256_file(path) == "b6f00f283d3a3e6fdb9a5a0dce2e5c3d6b3c0e8f2a5b4c2e6a2b5f8a3e1d4f5e"[:64]
