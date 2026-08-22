from __future__ import annotations

import asyncio

import pytest

from orbit.core.load_test import run_load_test


@pytest.mark.asyncio
async def test_load_test_respects_concurrency_and_counts_successes() -> None:
    active = 0
    peak = 0

    async def operation() -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.001)
        active -= 1

    result = await run_load_test(operation, requests=20, concurrency=4)

    assert result.requests == 20
    assert result.succeeded == 20
    assert result.failed == 0
    assert peak <= 4
    assert result.throughput_rps > 0


@pytest.mark.asyncio
async def test_load_test_counts_operation_failures() -> None:
    calls = 0

    async def operation() -> None:
        nonlocal calls
        calls += 1
        if calls % 2 == 0:
            raise RuntimeError("expected")

    result = await run_load_test(operation, requests=10, concurrency=2)

    assert result.requests == 10
    assert result.succeeded == 5
    assert result.failed == 5
