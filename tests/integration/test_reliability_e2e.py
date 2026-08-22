from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.hardware import HardwareProfile
from orbit.core.lifecycle import LifecycleState
from orbit.core.load_control import RuntimeLoadController
from orbit.core.models import ModelModality, ModelSpec
from orbit.core.orchestrator import InferenceOrchestrator
from orbit.core.recovery import RecoveryManager
from orbit.core.request_manager import RequestManager
from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler
from orbit.core.shutdown import ShutdownCoordinator


class ScriptedRuntime(RuntimeAdapter):
    def __init__(self, name: str, tokens: tuple[str, ...], *, fail: bool = False) -> None:
        self._info = RuntimeInfo(name, "e2e", frozenset({"text-generation"}))
        self.tokens = tokens
        self.fail = fail

    @property
    def info(self) -> RuntimeInfo:
        return self._info

    async def health(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        if self.fail:
            raise RuntimeError(f"{self.info.name} unavailable")
        for token in self.tokens:
            yield token


@pytest.mark.asyncio
async def test_end_to_end_failover_persistence_recovery_and_shutdown(tmp_path: Path) -> None:
    hardware = HardwareProfile("linux", "x86_64", 8 * 1024**3, ())
    scheduler = ResourceScheduler(hardware)
    runtimes = RuntimeManager()
    primary = ScriptedRuntime("primary", ("bad",), fail=True)
    backup = ScriptedRuntime("backup", ("hello", " world"))
    runtimes.register(primary)
    runtimes.register(backup)
    await runtimes.check_all()

    model = ModelSpec(
        "e2e-model",
        "E2E Model",
        modality=ModelModality.TEXT,
        runtimes=frozenset({"backup", "primary"}),
        capabilities=frozenset({"text-generation"}),
    )
    orchestrator = InferenceOrchestrator(
        scheduler,
        runtimes,
        load_control=RuntimeLoadController(),
    )

    request_manager = RequestManager(journal_path=tmp_path / "requests.jsonl")
    request_manager.start("req-e2e", model.model_id, "primary")
    output: list[str] = []
    async for token in orchestrator.generate(model, "ping"):
        output.append(token)
    request_manager.complete("req-e2e", tokens=len(output))

    assert "".join(output) == "hello world"
    assert runtimes.active_name == "backup"
    record = request_manager.get("req-e2e")
    assert record is not None
    assert record.state == "completed"

    request_manager.start("req-interrupted", model.model_id, "backup")
    recovered_manager, recovery_report = RecoveryManager(tmp_path).recover_requests()
    recovered = recovered_manager.get("req-interrupted")
    assert recovered is not None
    assert recovered.state == "failed"
    assert recovery_report.recovered_requests == 1

    shutdown = ShutdownCoordinator()
    calls: list[str] = []

    async def request_cleanup() -> None:
        calls.append("request-manager")

    async def runtime_cleanup() -> None:
        calls.append("runtime-manager")

    shutdown.register(request_cleanup)
    shutdown.register(runtime_cleanup)
    shutdown_report = await shutdown.shutdown(timeout=1.0)
    assert shutdown_report.completed == 2
    assert calls == ["runtime-manager", "request-manager"]


def test_app_bootstrap_and_recovery_share_configured_data_dir(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    assert app.state is LifecycleState.READY
    assert app.recovery_report is not None
    assert (tmp_path / ".orbit" / "requests.jsonl").parent.is_dir()
