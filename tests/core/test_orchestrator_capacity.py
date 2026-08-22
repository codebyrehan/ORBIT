from __future__ import annotations

import asyncio

import pytest

from orbit.core.hardware import HardwareProfile
from orbit.core.load_control import RuntimeLoadController
from orbit.core.models import ModelSpec
from orbit.core.orchestrator import InferenceOrchestrator
from orbit.core.runtime import RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler


class BlockingRuntime:
    def __init__(self, name: str) -> None:
        self.info = RuntimeInfo(name=name, version="test", capabilities=frozenset())
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def health(self) -> bool:
        return True

    def generate(self, request):
        async def stream():
            self.started.set()
            await self.release.wait()
            yield "done"

        return stream()


@pytest.mark.asyncio
async def test_orchestrator_enforces_runtime_capacity() -> None:
    runtime = BlockingRuntime("test")
    runtimes = RuntimeManager()
    runtimes.register(runtime)
    await runtimes.check_all()
    controller = RuntimeLoadController(default_limit=1)
    orchestrator = InferenceOrchestrator(ResourceScheduler(HardwareProfile("test", "x86_64", 1024)), runtimes, load_control=controller)
    model = ModelSpec(model_id="m", display_name="M", runtimes=frozenset({"test"}))

    first = orchestrator.generate(model, "prompt")
    first_task = asyncio.create_task(first.__anext__())
    await runtime.started.wait()

    second = orchestrator.generate(model, "prompt", capacity_timeout=0.01)
    with pytest.raises(TimeoutError):
        await second.__anext__()

    runtime.release.set()
    assert await first_task == "done"
    await first.aclose()
