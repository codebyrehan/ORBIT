"""Safe local model installation and lifecycle activation."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from orbit.core.model_artifacts import ModelArtifactError, ModelArtifactManager
from orbit.core.model_manager import ManagedModel, ModelManager
from orbit.core.models import ModelSpec


class ModelInstallError(ValueError):
    """Raised when a model cannot be installed safely."""


class ModelInstaller:
    """Install local artifacts into ORBIT's managed model directory atomically."""

    def __init__(self, manager: ModelManager) -> None:
        self.manager = manager
        self.artifacts = ModelArtifactManager(manager)

    def install(
        self,
        spec: ModelSpec,
        source: Path,
        *,
        expected_sha256: str | None = None,
    ) -> ManagedModel:
        if not source.exists() or not source.is_file():
            raise ModelInstallError(f"model source does not exist: {source}")
        if source.is_symlink():
            raise ModelInstallError("model source must not be a symbolic link")
        if expected_sha256 is not None and len(expected_sha256) != 64:
            raise ModelInstallError("expected_sha256 must be a 64-character SHA-256 digest")

        self.manager.register(spec)
        target = self.manager.models_dir / spec.model_id / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.partial")
        try:
            if temporary.exists():
                temporary.unlink()
            shutil.copyfile(source, temporary)
            if spec.size_bytes is not None and temporary.stat().st_size != spec.size_bytes:
                raise ModelInstallError(f"artifact size mismatch for {spec.model_id}")
            digest = _sha256(temporary)
            if expected_sha256 is not None and digest.lower() != expected_sha256.lower():
                raise ModelInstallError(f"artifact checksum mismatch for {spec.model_id}")
            os.replace(temporary, target)
            return self.artifacts.activate(spec.model_id, target, expected_sha256=expected_sha256)
        except ModelInstallError:
            if temporary.exists():
                temporary.unlink()
            raise
        except (OSError, ModelArtifactError) as exc:
            if temporary.exists():
                temporary.unlink()
            raise ModelInstallError(str(exc)) from exc

    def remove(self, model_id: str) -> None:
        try:
            self.artifacts.remove(model_id)
        except (KeyError, ModelArtifactError, OSError, ValueError) as exc:
            raise ModelInstallError(str(exc)) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
