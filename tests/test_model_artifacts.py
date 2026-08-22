from pathlib import Path

import pytest

from orbit.core.model_artifacts import ModelArtifactError, ModelArtifactManager, sha256_file
from orbit.core.model_manager import ModelManager, ModelState
from orbit.core.model_store import ModelStore
from orbit.core.models import ModelSpec


def make_manager(tmp_path: Path, size: int | None = None) -> ModelManager:
    manager = ModelManager(ModelStore(tmp_path / "models.json"), tmp_path / "models")
    manager.register(ModelSpec("demo", "Demo", size_bytes=size))
    return manager


def test_verify_and_activate_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "demo.gguf"
    artifact.write_bytes(b"orbit-model")
    manager = make_manager(tmp_path, artifact.stat().st_size)
    artifacts = ModelArtifactManager(manager)

    report = artifacts.verify("demo", artifact, expected_sha256=sha256_file(artifact))
    activated = artifacts.activate("demo", artifact)

    assert report.verified
    assert report.size_bytes == artifact.stat().st_size
    assert activated.state is ModelState.READY
    assert activated.path == artifact


def test_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "demo.gguf"
    artifact.write_bytes(b"orbit-model")
    artifacts = ModelArtifactManager(make_manager(tmp_path))

    with pytest.raises(ModelArtifactError, match="checksum mismatch"):
        artifacts.verify("demo", artifact, expected_sha256="0" * 64)


def test_size_mismatch_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "demo.gguf"
    artifact.write_bytes(b"orbit-model")
    artifacts = ModelArtifactManager(make_manager(tmp_path, size=999))

    with pytest.raises(ModelArtifactError, match="size mismatch"):
        artifacts.verify("demo", artifact)


def test_running_model_cannot_be_removed(tmp_path: Path) -> None:
    artifact = tmp_path / "demo.gguf"
    artifact.write_bytes(b"orbit-model")
    manager = make_manager(tmp_path)
    artifacts = ModelArtifactManager(manager)
    artifacts.activate("demo", artifact)
    manager.mark_running("demo")

    with pytest.raises(ModelArtifactError, match="running model"):
        artifacts.remove("demo")
