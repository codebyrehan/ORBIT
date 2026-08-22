"""Model lifecycle orchestration for ORBIT.

The manager deliberately owns metadata and lifecycle state, while actual model
processes remain runtime responsibilities. This keeps installation and runtime
execution independently replaceable.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from orbit.core.model_store import ModelStore
from orbit.core.models import ModelSpec


class ModelState(StrEnum):
    REGISTERED = "registered"
    READY = "ready"
    LOADING = "loading"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ManagedModel:
    spec: ModelSpec
    state: ModelState = ModelState.REGISTERED
    path: Path | None = None
    error: str | None = None


class ModelManager:
    """Persist and validate model lifecycle state without owning inference."""

    def __init__(self, store: ModelStore, models_dir: Path) -> None:
        self.store = store
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._states: dict[str, ManagedModel] = {}
        self._restore()

    def _restore(self) -> None:
        for spec in self.store.all():
            path = Path(spec.local_path) if spec.local_path else None
            state = ModelState.READY if path and path.exists() else ModelState.REGISTERED
            self._states[spec.model_id] = ManagedModel(spec=spec, state=state, path=path)

    def register(self, spec: ModelSpec) -> ManagedModel:
        self.store.upsert(spec)
        managed = ManagedModel(spec=spec, state=ModelState.REGISTERED)
        self._states[spec.model_id] = managed
        return managed

    def register_many(self, specs: Iterable[ModelSpec]) -> list[ManagedModel]:
        return [self.register(spec) for spec in specs]

    def get(self, model_id: str) -> ManagedModel | None:
        return self._states.get(model_id)

    def all(self) -> list[ManagedModel]:
        return list(self._states.values())

    def mark_ready(self, model_id: str, path: Path) -> ManagedModel:
        current = self._require(model_id)
        if not path.exists() or not path.is_file():
            raise ValueError(f"model file does not exist: {path}")
        updated_spec = current.spec.with_local_path(str(path))
        self.store.upsert(updated_spec)
        managed = ManagedModel(updated_spec, ModelState.READY, path)
        self._states[model_id] = managed
        return managed

    def mark_running(self, model_id: str) -> ManagedModel:
        current = self._require(model_id)
        if current.state not in {ModelState.READY, ModelState.STOPPED, ModelState.RUNNING}:
            raise ValueError(f"model {model_id!r} is not ready")
        managed = ManagedModel(current.spec, ModelState.RUNNING, current.path)
        self._states[model_id] = managed
        return managed

    def mark_stopped(self, model_id: str) -> ManagedModel:
        current = self._require(model_id)
        managed = ManagedModel(current.spec, ModelState.STOPPED, current.path)
        self._states[model_id] = managed
        return managed

    def mark_error(self, model_id: str, error: str) -> ManagedModel:
        current = self._require(model_id)
        managed = ManagedModel(current.spec, ModelState.ERROR, current.path, error)
        self._states[model_id] = managed
        return managed

    def _require(self, model_id: str) -> ManagedModel:
        model = self.get(model_id)
        if model is None:
            raise KeyError(f"unknown model: {model_id}")
        return model
