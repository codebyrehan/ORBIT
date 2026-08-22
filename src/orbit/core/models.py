"""Model catalog and compatibility primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from orbit.core.hardware import HardwareProfile


class ModelModality(StrEnum):
    TEXT = "text"
    VISION = "vision"
    EMBEDDING = "embedding"
    AUDIO = "audio"
    IMAGE = "image"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """A runtime-neutral description of an installable model."""

    model_id: str
    display_name: str
    modality: ModelModality = ModelModality.TEXT
    size_bytes: int | None = None
    min_memory_bytes: int | None = None
    capabilities: frozenset[str] = field(default_factory=frozenset)
    runtimes: frozenset[str] = field(default_factory=frozenset)
    tags: frozenset[str] = field(default_factory=frozenset)

    def compatibility_score(self, hardware: HardwareProfile, runtime: str) -> float:
        """Return a conservative 0..1 score for scheduling decisions."""
        if self.runtimes and runtime not in self.runtimes:
            return 0.0
        if self.min_memory_bytes and hardware.accelerator_memory_bytes:
            available = hardware.accelerator_memory_bytes
            if available < self.min_memory_bytes:
                return 0.0
            return min(1.0, available / self.min_memory_bytes) * 0.9 + 0.1
        if self.min_memory_bytes and hardware.memory_bytes:
            return 0.8 if hardware.memory_bytes >= self.min_memory_bytes else 0.0
        return 0.5


class ModelCatalog:
    """In-memory catalog; persistence and remote registries can be adapters later."""

    def __init__(self, models: tuple[ModelSpec, ...] = ()) -> None:
        self._models: dict[str, ModelSpec] = {model.model_id: model for model in models}

    def register(self, model: ModelSpec) -> None:
        self._models[model.model_id] = model

    def get(self, model_id: str) -> ModelSpec | None:
        return self._models.get(model_id)

    def all(self) -> tuple[ModelSpec, ...]:
        return tuple(self._models.values())

    def recommend(self, hardware: HardwareProfile, runtime: str, limit: int = 5) -> tuple[ModelSpec, ...]:
        ranked = sorted(
            self._models.values(),
            key=lambda model: model.compatibility_score(hardware, runtime),
            reverse=True,
        )
        return tuple(model for model in ranked if model.compatibility_score(hardware, runtime) > 0)[:limit]
