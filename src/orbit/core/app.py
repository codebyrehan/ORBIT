"""ORBIT core application bootstrap."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

from orbit.core.config import OrbitConfig
from orbit.core.hardware import HardwareProfile
from orbit.core.hardware_detect import detect_hardware
from orbit.core.health import HealthCheck, HealthRegistry, HealthStatus
from orbit.core.lifecycle import LifecycleState
from orbit.core.model_manager import ModelManager
from orbit.core.model_store import ModelStore
from orbit.core.models import ModelCatalog, ModelModality, ModelSpec
from orbit.core.orchestrator import InferenceOrchestrator
from orbit.core.recovery import RecoveryManager
from orbit.core.request_manager import RequestManager
from orbit.core.router import InferenceRouter
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler
from orbit.core.shutdown import ShutdownCoordinator, ShutdownReport
from orbit.runtimes.demo import DemoRuntime
from orbit.runtimes.llama_cpp import LlamaCppRuntime


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
    router: InferenceRouter | None = None
    request_manager: RequestManager = field(default_factory=RequestManager)
    recovery_report: object | None = None
    health: HealthRegistry = field(default_factory=HealthRegistry)
    shutdown_coordinator: ShutdownCoordinator = field(default_factory=ShutdownCoordinator)

    def start(self) -> None:
        if self.state not in (LifecycleState.CREATED, LifecycleState.STOPPED):
            raise RuntimeError(f"cannot start ORBIT from state: {self.state.value}")
        self.state = LifecycleState.STARTING
        self.config.ensure_directories()
        self.hardware = detect_hardware()
        self.scheduler = ResourceScheduler(self.hardware)
        self.model_store = ModelStore(self.config.data_dir / "models.json")
        self.models = self.model_store.load()
        self.model_manager = ModelManager(self.model_store, self.config.data_dir / "models")
        self._register_runtimes()
        self._ensure_demo_model()
        self.orchestrator = InferenceOrchestrator(self.scheduler, self.runtimes)
        self.router = InferenceRouter(self.models, self.orchestrator)
        self.request_manager, self.recovery_report = RecoveryManager(self.config.data_dir).recover_requests()
        self._register_health_checks()
        self.state = LifecycleState.READY

    @staticmethod
    def _demo_enabled() -> bool:
        return os.getenv("ORBIT_ENABLE_DEMO_MODEL", "false").lower() not in {"0", "false", "no", "off"}

    def _register_runtimes(self) -> None:
        if self._demo_enabled() and self.runtimes.get("orbit-demo") is None:
            self.runtimes.register(DemoRuntime())
        llama_url = os.getenv("ORBIT_LLAMA_CPP_URL", "").strip()
        if llama_url and self.runtimes.get("llama.cpp") is None:
            self.runtimes.register(LlamaCppRuntime(base_url=llama_url))

    def _ensure_demo_model(self) -> None:
        if not self._demo_enabled() or self.models.all():
            return
        llama_model = os.getenv("ORBIT_LLAMA_CPP_MODEL", "").strip()
        if llama_model and self.runtimes.get("llama.cpp") is not None:
            spec = ModelSpec(model_id=llama_model, display_name=llama_model, modality=ModelModality.TEXT, capabilities=frozenset({"text-generation", "chat", "openai-compatible"}), runtimes=frozenset({"llama.cpp"}), tags=frozenset({"remote-runtime"}))
        else:
            spec = ModelSpec(model_id="orbit-demo", display_name="ORBIT Demo Runtime", modality=ModelModality.TEXT, capabilities=frozenset({"text-generation", "chat", "streaming", "demo"}), runtimes=frozenset({"orbit-demo"}), tags=frozenset({"built-in", "smoke-test"}))
        self.models.register(spec)
        if self.model_manager is not None:
            self.model_manager.register(spec)

    def _register_health_checks(self) -> None:
        self.health.register("hardware", lambda: HealthCheck("hardware", HealthStatus.HEALTHY if self.hardware is not None else HealthStatus.UNHEALTHY, "hardware profile available" if self.hardware is not None else "hardware discovery unavailable"))
        self.health.register("models", lambda: HealthCheck("models", HealthStatus.HEALTHY if self.model_store is not None else HealthStatus.UNHEALTHY, f"{len(self.models.all())} catalog entries"))
        self.health.register("scheduler", lambda: HealthCheck("scheduler", HealthStatus.HEALTHY if self.scheduler is not None else HealthStatus.UNHEALTHY, "resource scheduler ready" if self.scheduler is not None else "scheduler unavailable"))
        self.health.register("orchestrator", lambda: HealthCheck("orchestrator", HealthStatus.HEALTHY if self.orchestrator is not None else HealthStatus.UNHEALTHY, "inference orchestration ready" if self.orchestrator is not None else "orchestrator unavailable"))
        self.health.register("router", lambda: HealthCheck("router", HealthStatus.HEALTHY if self.router is not None else HealthStatus.UNHEALTHY, "inference router ready" if self.router is not None else "router unavailable"))

    def save_models(self) -> None:
        if self.model_store is None:
            raise RuntimeError("ORBIT must be started before saving models")
        self.model_store.save(self.models)

    async def stop_async(self, timeout: float = 10.0) -> ShutdownReport:
        if self.state == LifecycleState.STOPPED:
            return ShutdownReport(0, 0, 0)
        if self.state not in (LifecycleState.READY, LifecycleState.STARTING, LifecycleState.STOPPING):
            raise RuntimeError(f"cannot stop ORBIT from state: {self.state.value}")
        self.state = LifecycleState.STOPPING
        report = await self.shutdown_coordinator.shutdown(timeout)
        self.state = LifecycleState.STOPPED
        return report

    def stop(self) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.stop_async())
            return
        raise RuntimeError("stop() cannot run inside an active event loop; use await stop_async()")
