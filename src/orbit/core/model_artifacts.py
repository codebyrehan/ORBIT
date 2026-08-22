"""Local model artifact verification and safe activation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from orbit.core.model_manager import ManagedModel, ModelManager, ModelState


@dataclass(frozen=True, slots=True)
class ArtifactReport:
    model_id: str
    path: Path
    size_bytes: int
    sha256: str
    verified: bool


class ModelArtifactError(ValueError):
    """Raised when a local model artifact is invalid or unsafe."""


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


class ModelArtifactManager:
    """Verify artifacts before allowing a model to become ready."""

    def __init__(self, models: ModelManager) -> None:
        self.models = models

    def verify(self, model_id: str, path: Path, *, expected_sha256: str | None = None) -> ArtifactReport:
        model = self.models.get(model_id)
        if model is None:
            raise ModelArtifactError(f"unknown model: {model_id}")
        if not path.exists() or not path.is_file():
            raise ModelArtifactError(f"model artifact does not exist: {path}")
        size = path.stat().st_size
        if model.spec.size_bytes is not None and size != model.spec.size_bytes:
            raise ModelArtifactError(f"artifact size mismatch for {model_id}")
        checksum = sha256_file(path)
        if expected_sha256 is not None and checksum.lower() != expected_sha256.lower():
            raise ModelArtifactError(f"artifact checksum mismatch for {model_id}")
        return ArtifactReport(model_id, path, size, checksum, True)

    def activate(self, model_id: str, path: Path, *, expected_sha256: str | None = None) -> ManagedModel:
        self.verify(model_id, path, expected_sha256=expected_sha256)
        return self.models.mark_ready(model_id, path)

    def remove(self, model_id: str) -> None:
        model = self.models.get(model_id)
        if model is None:
            raise ModelArtifactError(f"unknown model: {model_id}")
        if model.state is ModelState.RUNNING:
            raise ModelArtifactError(f"cannot remove running model: {model_id}")
        if model.path is not None and model.path.exists():
            model.path.unlink()
        self.models.mark_stopped(model_id)
