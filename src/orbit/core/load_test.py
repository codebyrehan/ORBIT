"""Deterministic load-test primitives for ORBIT performance validation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Awaitable, Callable


@dataclass(frozen=True, slots=True)
class LoadTestResult:
    requests: int
    succeeded: int
    failed: int
    elapsed_ms: float
    throughput_rps: float


async def run_load_test(
    operation: Callable[[], Awaitable[None]],
    *,
    requests: int,
    concurrency: int,
) -> LoadTestResult:
    if requests <= 0 or concurrency <= 0:
        raise ValueError("requests and concurrency must be positive")
    semaphore = asyncio.Semaphore(concurrency)
    succeeded = 0
    failed = 0

    async def run_one() -> None:
        nonlocal succeeded, failed
        async with semaphore:
            try:
                await operation()
            except Exception:
                failed += 1
            else:
                succeeded += 1

    started = monotonic()
    await asyncio.gather(*(run_one() for _ in range(requests)))
    elapsed_ms = (monotonic() - started) * 1000.0
    elapsed_s = max(elapsed_ms / 1000.0, 1e-9)
    return LoadTestResult(requests, succeeded, failed, elapsed_ms, requests / elapsed_s)
