"""ORBIT core application bootstrap."""

from __future__ import annotations

from dataclasses import dataclass, field

from orbit.core.config import OrbitConfig
from orbit.core.hardware import HardwareProfile
from orbit.core.hardware_detect import detect_hardware
from orbit.core.health import HealthCheck, HealthRegistry, HealthStatus
from orbit.core.lifecycle import LifecycleState
from orbit.core.model_manager import ModelManager
from orbit.core.model_store import ModelStore
from orbit.core.models import ModelCatalog
from orbit.core.orchestrator import InferenceOrchestrator
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
    model_manager: ModelManager | None = None
    orchestrator: InferenceOrchestrator | None = None
    health: HealthRegistry = field(default_factory=HealthRegistry)

    def start(self) -> None:
        self.state = LifecycleState.STARTING
        self.config.ensure_directories()
        self.hardware = detect_hardware()
        self.scheduler = ResourceScheduler(self.hardware)
        self.model_store = ModelStore(self.config.data_dir / "models.json")
        self.models = self.model_store.load()
        self.model_manager = ModelManager(self.model_store, self.config.data_dir / "models")
        self.orchestrator = InferenceOrchestrator(self.scheduler, self.runtimes)
        self._register_health_checks()
        self.state = LifecycleState.READY

    def _register_health_checks(self) -> None:
        self.health.register(
            "hardware",
            lambda: HealthCheck(
                "hardware",
                HealthStatus.HEALTHY if self.hardware is not None else HealthStatus.UNHEALTHY,
                "hardware profile available" if self.hardware is not None else "hardware discovery unavailable",
            ),
        )
        self.health.register(
            "models",
            lambda: HealthCheck(
                "models",
                HealthStatus.HEALTHY if self.model_store is not None else HealthStatus.UNHEALTHY,
                f"{len(self.models.all())} catalog entries",
            ),
        )
        self.health.register(
            "scheduler",
            lambda: HealthCheck(
                "scheduler",
                HealthStatus.HEALTHY if self.scheduler is not None else HealthStatus.UNHEALTHY,
                "resource scheduler ready" if self.scheduler is not None else "scheduler unavailable",
            ),
        )
        self.health.register(
            "orchestrator",
            lambda: HealthCheck(
                "orchestrator",
                HealthStatus.HEALTHY if self.orchestrator is not None else HealthStatus.UNHEALTHY,
                "inference orchestration ready" if self.orchestrator is not None else "orchestrator unavailable",
            ),
        )

    def save_models(self) -> None:
        """Persist the current catalog after an explicit catalog mutation."""
        if self.model_store is None:
            raise RuntimeError("ORBIT must be started before saving models")
        self.model_store.save(self.models)

    def stop(self) -> None:
        self.state = LifecycleState.STOPPING
        self.state = LifecycleState.STOPPED
