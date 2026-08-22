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
    assert sha256_file(path) == "4fa1a13ac468ac495f3390e859d76d5e8ef49806815b45a21de7711bcc624194"
