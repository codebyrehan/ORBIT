"""Bounded concurrency and backpressure for runtime execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoadSnapshot:
    runtime: str
    active: int
    limit: int

    @property
    def available(self) -> int:
        return max(0, self.limit - self.active)


class RuntimeLoadController:
    """Keep runtime concurrency bounded without retaining request contents."""

    def __init__(self, default_limit: int = 4) -> None:
        if default_limit <= 0:
            raise ValueError("default_limit must be positive")
        self.default_limit = default_limit
        self._limits: dict[str, int] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._active: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def configure(self, runtime: str, limit: int | None = None) -> None:
        value = self.default_limit if limit is None else limit
        if value <= 0:
            raise ValueError("runtime limit must be positive")
        async with self._lock:
            if runtime in self._semaphores:
                if self._active.get(runtime, 0) > 0:
                    raise RuntimeError(f"cannot reconfigure active runtime: {runtime}")
            self._limits[runtime] = value
            self._semaphores[runtime] = asyncio.Semaphore(value)
            self._active[runtime] = 0

    async def acquire(self, runtime: str, *, timeout: float | None = None) -> None:
        async with self._lock:
            if runtime not in self._semaphores:
                self._limits[runtime] = self.default_limit
                self._semaphores[runtime] = asyncio.Semaphore(self.default_limit)
                self._active[runtime] = 0
            semaphore = self._semaphores[runtime]
        if timeout is None:
            await semaphore.acquire()
        else:
            try:
                await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
            except TimeoutError as exc:
                raise TimeoutError(f"runtime capacity unavailable: {runtime}") from exc
        async with self._lock:
            self._active[runtime] = self._active.get(runtime, 0) + 1

    async def release(self, runtime: str) -> None:
        async with self._lock:
            semaphore = self._semaphores.get(runtime)
            if semaphore is None:
                return
            self._active[runtime] = max(0, self._active.get(runtime, 1) - 1)
            semaphore.release()

    async def snapshot(self, runtime: str) -> LoadSnapshot:
        async with self._lock:
            return LoadSnapshot(runtime, self._active.get(runtime, 0), self._limits.get(runtime, self.default_limit))

    async def all_snapshots(self) -> tuple[LoadSnapshot, ...]:
        async with self._lock:
            return tuple(LoadSnapshot(name, self._active.get(name, 0), self._limits.get(name, self.default_limit)) for name in self._semaphores)
