from __future__ import annotations

import asyncio

import pytest

from orbit.core.shutdown import ShutdownCoordinator


@pytest.mark.asyncio
async def test_shutdown_runs_handlers_in_reverse_registration_order() -> None:
    coordinator = ShutdownCoordinator()
    events: list[str] = []

    async def first() -> None:
        events.append("first")

    async def second() -> None:
        events.append("second")

    coordinator.register(first)
    coordinator.register(second)

    report = await coordinator.shutdown()

    assert events == ["second", "first"]
    assert report.completed == 2
    assert report.timed_out == 0
    assert report.errors == 0
    assert coordinator.shutting_down


@pytest.mark.asyncio
async def test_shutdown_is_bounded_and_cancels_slow_handler() -> None:
    coordinator = ShutdownCoordinator()
    cancelled = False

    async def slow() -> None:
        nonlocal cancelled
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            cancelled = True
            raise

    coordinator.register(slow)
    report = await coordinator.shutdown(timeout=0.01)

    assert report.timed_out == 1
    assert cancelled


@pytest.mark.asyncio
async def test_shutdown_counts_handler_errors_and_is_idempotent() -> None:
    coordinator = ShutdownCoordinator()

    async def broken() -> None:
        raise RuntimeError("cleanup failed")

    coordinator.register(broken)
    first = await coordinator.shutdown()
    second = await coordinator.shutdown()

    assert first.errors == 1
    assert second == type(second)(0, 0, 0)
