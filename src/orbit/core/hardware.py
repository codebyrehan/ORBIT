"""Hardware capability contracts.

Detection implementations are intentionally separate from the contract so
new platforms can be added without changing the rest of ORBIT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AcceleratorVendor(StrEnum):
    CPU = "cpu"
    NVIDIA = "nvidia"
    AMD = "amd"
    APPLE = "apple"
    INTEL = "intel"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Accelerator:
    vendor: AcceleratorVendor
    name: str
    memory_bytes: int | None = None
    compute_capability: str | None = None


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    """Normalized machine capabilities used for scheduling decisions."""

    platform: str
    architecture: str
    memory_bytes: int | None
    accelerators: tuple[Accelerator, ...] = field(default_factory=tuple)

    @property
    def accelerator_memory_bytes(self) -> int:
        return sum(a.memory_bytes or 0 for a in self.accelerators)
