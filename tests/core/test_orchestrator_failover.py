from __future__ import annotations

import pytest

from orbit.core.failover import RuntimeFailover
from orbit.core.models import ModelSpec
from orbit.core.orchestrator import InferenceOrchestrator
from orbit.core.runtime import GenerationRequest, RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler


class FakeRuntime:
    def __init__(self, name: str, chunks: tuple[str, ...], fail: bool = False) -> None:
        self.info = RuntimeInfo(name=name, version="test", capabilities=frozenset())
        self.chunks = chunks
        self.fail = fail

    async def health(self) -> bool:
        return True

    def generate(self, request: GenerationRequest):
        async def stream():
            if self.fail:
                raise RuntimeError(f"{self.info.name} failed")
            for chunk in self.chunks:
                yield chunk

        return stream()


@pytest.mark.asyncio
async def test_orchestrator_retries_before_first_chunk() -> None:
    runtimes = RuntimeManager()
    runtimes.register(FakeRuntime("a", (), fail=True))
    runtimes.register(FakeRuntime("b", ("hello", " world")))
    await runtimes.check_all()
    orchestrator = InferenceOrchestrator(ResourceScheduler(), runtimes, failover=RuntimeFailover(runtimes))
    model = ModelSpec(model_id="m", display_name="M", runtimes=frozenset({"a", "b"}))

    chunks = [chunk async for chunk in orchestrator.generate(model, "prompt", runtime_name="a")]

    assert chunks == ["hello", " world"]
    assert runtimes.active_name == "b"


@pytest.mark.asyncio
async def test_orchestrator_does_not_retry_after_partial_output() -> None:
    runtimes = RuntimeManager()
    runtimes.register(FakeRuntime("a", ("hello",), fail=False))
    await runtimes.check_all()
    orchestrator = InferenceOrchestrator(ResourceScheduler(), runtimes, failover=RuntimeFailover(runtimes))
    model = ModelSpec(model_id="m", display_name="M", runtimes=frozenset({"a"}))

    chunks = [chunk async for chunk in orchestrator.generate(model, "prompt", runtime_name="a")]

    assert chunks == ["hello"]
