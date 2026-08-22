from collections.abc import AsyncIterator

import pytest

from orbit.core.hardware import HardwareProfile
from orbit.core.models import ModelCatalog, ModelSpec
from orbit.core.orchestrator import InferenceOrchestrator
from orbit.core.router import InferenceRouter, RouteRequest
from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler


class FakeRuntime(RuntimeAdapter):
    def __init__(self, name: str, healthy: bool = True) -> None:
        self._info = RuntimeInfo(name, "1.0", frozenset({"text"}))
        self._healthy = healthy

    @property
    def info(self) -> RuntimeInfo:
        return self._info

    async def health(self) -> bool:
        return self._healthy

    async def _tokens(self, request: GenerationRequest) -> AsyncIterator[str]:
        yield f"{request.model}@{self.info.name}:{request.prompt}"

    def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        return self._tokens(request)


def router() -> InferenceRouter:
    runtimes = RuntimeManager()
    runtimes.register(FakeRuntime("fast"))
    runtimes.register(FakeRuntime("backup"))
    hardware = HardwareProfile(platform="test", architecture="x86_64", memory_bytes=16 * 1024**3)
    orchestrator = InferenceOrchestrator(ResourceScheduler(hardware), runtimes)
    catalog = ModelCatalog((ModelSpec("demo", "Demo", runtimes=frozenset({"fast", "backup"})),))
    return InferenceRouter(catalog, orchestrator)


@pytest.mark.asyncio
async def test_router_resolves_model_and_runtime() -> None:
    decision = await router().route(RouteRequest("demo"))

    assert decision.model_id == "demo"
    assert decision.runtime_name in {"fast", "backup"}
    assert decision.score > 0
    assert decision.reason


@pytest.mark.asyncio
async def test_router_honors_explicit_runtime() -> None:
    decision = await router().route(RouteRequest("demo", "backup"))

    assert decision.runtime_name == "backup"


@pytest.mark.asyncio
async def test_router_rejects_unknown_model() -> None:
    with pytest.raises(LookupError, match="unknown model"):
        await router().route(RouteRequest("missing"))


@pytest.mark.asyncio
async def test_router_skips_unhealthy_runtime() -> None:
    runtimes = RuntimeManager()
    runtimes.register(FakeRuntime("broken", healthy=False))
    runtimes.register(FakeRuntime("healthy"))
    hardware = HardwareProfile(platform="test", architecture="x86_64", memory_bytes=16 * 1024**3)
    orchestrator = InferenceOrchestrator(ResourceScheduler(hardware), runtimes)
    catalog = ModelCatalog((ModelSpec("demo", "Demo", runtimes=frozenset({"broken", "healthy"})),))
    decision = await InferenceRouter(catalog, orchestrator).route(RouteRequest("demo"))

    assert decision.runtime_name == "healthy"


@pytest.mark.asyncio
async def test_router_generates_through_selected_runtime() -> None:
    chunks = [chunk async for chunk in router().generate(RouteRequest("demo", "backup"), "hello")]

    assert chunks == ["demo@backup:hello"]
