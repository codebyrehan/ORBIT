"""ORBIT core application bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from orbit.core.config import OrbitConfig
from orbit.core.lifecycle import LifecycleState


@dataclass(slots=True)
class OrbitApp:
    """Minimal control-plane object used by the CLI and future API layer."""

    config: OrbitConfig
    state: LifecycleState = LifecycleState.CREATED

    def start(self) -> None:
        self.state = LifecycleState.STARTING
        self.config.ensure_directories()
        self.state = LifecycleState.READY

    def stop(self) -> None:
        self.state = LifecycleState.STOPPING
        self.state = LifecycleState.STOPPED
