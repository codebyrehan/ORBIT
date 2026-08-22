"""Small deterministic resource scheduler for model placement."""

from __future__ import annotations

from dataclasses import dataclass

from orbit.core.hardware import HardwareProfile
from orbit.core.models import ModelSpec


@dataclass(frozen=True, slots=True)
class Placement:
    model_id: str
    runtime: str
    score: float
    reason: str


class ResourceScheduler:
    """Chooses a model/runtime pair without owning process orchestration."""

    def __init__(self, hardware: HardwareProfile) -> None:
        self.hardware = hardware

    def place(self, model: ModelSpec, runtime: str) -> Placement | None:
        score = model.compatibility_score(self.hardware, runtime)
        if score <= 0:
            return None
        accelerator = self.hardware.accelerators[0]
        reason = f"compatible with {accelerator.vendor.value} on {self.hardware.architecture}"
        return Placement(model.model_id, runtime, score, reason)
