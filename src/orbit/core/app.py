"""ORBIT core application bootstrap."""

from __future__ import annotations

from dataclasses import dataclass, field

from orbit.core.config import OrbitConfig
from orbit.core.hardware import HardwareProfile
from orbit.core.hardware_detect import detect_hardware
from orbit.core.lifecycle import LifecycleState
from orbit.core.model_store import ModelStore
from orbit.core.models import ModelCatalog
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler


@dataclass(slots=True)
class OrbitApp:
    """Control-plane object coordinating ORBIT's platform primitives."""

    config: OrbitConfig
    state: LifecycleState = LifecycleState.CREATED
    hardware: HardwareProfile | None = None
    models: ModelCatalog = field(default_factory=ModelCatalog)
    runtimes: RuntimeManager = field(default_factory=RuntimeManager)
    scheduler: ResourceScheduler | None = None
    model_store: ModelStore | None = None

    def start(self) -> None:
        self.state = LifecycleState.STARTING
        self.config.ensure_directories()
        self.hardware = detect_hardware()
        self.scheduler = ResourceScheduler(self.hardware)
        self.model_store = ModelStore(self.config.data_dir / "models.json")
        self.models = self.model_store.load()
        self.state = LifecycleState.READY

    def save_models(self) -> None:
        """Persist the current catalog after an explicit catalog mutation."""
        if self.model_store is None:
            raise RuntimeError("ORBIT must be started before saving models")
        self.model_store.save(self.models)

    def stop(self) -> None:
        self.state = LifecycleState.STOPPING
        self.state = LifecycleState.STOPPED
