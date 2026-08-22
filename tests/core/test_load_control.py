from __future__ import annotations

import asyncio

import pytest

from orbit.core.load_control import RuntimeLoadController


@pytest.mark.asyncio
async def test_load_controller_limits_concurrency() -> None:
    controller = RuntimeLoadController(default_limit=1)
    started = asyncio.Event()
    release = asyncio.Event()

    async def first() -> None:
        await controller.acquire("runtime")
        started.set()
        await release.wait()
        await controller.release("runtime")

    first_task = asyncio.create_task(first())
    await started.wait()

    snapshot = await controller.snapshot("runtime")
    assert snapshot.active == 1
    assert snapshot.available == 0

    with pytest.raises(TimeoutError):
        await controller.acquire("runtime", timeout=0.01)

    release.set()
    await first_task
    snapshot = await controller.snapshot("runtime")
    assert snapshot.active == 0
    assert snapshot.available == 1


@pytest.mark.asyncio
async def test_load_controller_can_reconfigure_when_idle() -> None:
    controller = RuntimeLoadController(default_limit=2)
    await controller.configure("runtime", 3)
    snapshot = await controller.snapshot("runtime")
    assert snapshot.limit == 3
    assert snapshot.available == 3

    await controller.acquire("runtime")
    with pytest.raises(RuntimeError):
        await controller.configure("runtime", 1)
    await controller.release("runtime")
