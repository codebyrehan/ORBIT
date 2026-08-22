import hashlib
from pathlib import Path

import pytest

from orbit.core.model_installer import ModelInstallError, ModelInstaller
from orbit.core.model_manager import ModelManager, ModelState
from orbit.core.model_store import ModelStore
from orbit.core.models import ModelSpec


def test_installs_and_verifies_local_artifact(tmp_path: Path) -> None:
    source = tmp_path / "demo.gguf"
    source.write_bytes(b"model-data")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manager = ModelManager(ModelStore(tmp_path / "models.json"), tmp_path / "models")

    installed = ModelInstaller(manager).install(
        ModelSpec("demo", "Demo", size_bytes=source.stat().st_size),
        source,
        expected_sha256=digest,
    )

    assert installed.state == ModelState.READY
    assert installed.path is not None
    assert installed.path.read_bytes() == b"model-data"
    assert installed.path.parent == tmp_path / "models" / "demo"


def test_rejects_checksum_mismatch_without_leaving_partial_file(tmp_path: Path) -> None:
    source = tmp_path / "demo.gguf"
    source.write_bytes(b"model-data")
    manager = ModelManager(ModelStore(tmp_path / "models.json"), tmp_path / "models")

    with pytest.raises(ModelInstallError, match="checksum mismatch"):
        ModelInstaller(manager).install(ModelSpec("demo", "Demo"), source, expected_sha256="0" * 64)

    assert not list((tmp_path / "models" / "demo").glob("*.partial"))
    assert manager.get("demo").state == ModelState.REGISTERED


def test_rejects_symlink_source(tmp_path: Path) -> None:
    source = tmp_path / "source.gguf"
    source.write_bytes(b"model-data")
    link = tmp_path / "link.gguf"
    link.symlink_to(source)
    manager = ModelManager(ModelStore(tmp_path / "models.json"), tmp_path / "models")

    with pytest.raises(ModelInstallError, match="symbolic link"):
        ModelInstaller(manager).install(ModelSpec("demo", "Demo"), link)
