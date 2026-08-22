from collections.abc import AsyncIterator

import pytest

from orbit.core.hardware import HardwareProfile
from orbit.core.models import ModelSpec
from orbit.core.orchestrator import InferenceOrchestrator
from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler


class FakeRuntime(RuntimeAdapter):
    def __init__(self, name: str = "fake", healthy: bool = True) -> None:
        self._info = RuntimeInfo(name, "1.0", frozenset({"text"}))
        self._healthy = healthy

    @property
    def info(self) -> RuntimeInfo:
        return self._info

    async def health(self) -> bool:
        return self._healthy

    async def _tokens(self, request: GenerationRequest) -> AsyncIterator[str]:
        yield f"{request.model}:{request.prompt}"

    def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        return self._tokens(request)


def test_hardware() -> HardwareProfile:
    return HardwareProfile(platform="test", architecture="x86_64", memory_bytes=16 * 1024**3)


@pytest.mark.asyncio
async def test_orchestrator_plans_healthy_compatible_runtime() -> None:
    scheduler = ResourceScheduler(test_hardware())
    runtimes = RuntimeManager()
    runtimes.register(FakeRuntime())
    orchestrator = InferenceOrchestrator(scheduler, runtimes)
    model = ModelSpec("demo", "Demo", runtimes=frozenset({"fake"}))

    plan = await orchestrator.plan(model)
    output = [token async for token in orchestrator.generate(model, "hello")]

    assert plan.runtime.info.name == "fake"
    assert plan.placement.model_id == "demo"
    assert output == ["demo:hello"]


@pytest.mark.asyncio
async def test_orchestrator_rejects_unhealthy_runtime() -> None:
    runtimes = RuntimeManager()
    runtimes.register(FakeRuntime(healthy=False))
    orchestrator = InferenceOrchestrator(ResourceScheduler(test_hardware()), runtimes)
    model = ModelSpec("demo", "Demo", runtimes=frozenset({"fake"}))

    with pytest.raises(RuntimeError, match="no healthy compatible runtime"):
        await orchestrator.plan(model)
