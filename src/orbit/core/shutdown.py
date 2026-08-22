"""Graceful shutdown coordination for ORBIT."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True, slots=True)
class ShutdownReport:
    completed: int
    timed_out: int
    errors: int


class ShutdownCoordinator:
    """Run registered async cleanup handlers within a bounded shutdown window."""

    def __init__(self) -> None:
        self._handlers: list[Callable[[], Awaitable[None]]] = []
        self._shutdown = False

    def register(self, handler: Callable[[], Awaitable[None]]) -> None:
        if self._shutdown:
            raise RuntimeError("shutdown already started")
        self._handlers.append(handler)

    @property
    def shutting_down(self) -> bool:
        return self._shutdown

    async def shutdown(self, timeout: float = 10.0) -> ShutdownReport:
        if timeout <= 0:
            raise ValueError("shutdown timeout must be positive")
        if self._shutdown:
            return ShutdownReport(0, 0, 0)
        self._shutdown = True
        completed = timed_out = errors = 0
        async def run() -> None:
            nonlocal completed, errors
            for handler in reversed(self._handlers):
                try:
                    await handler()
                    completed += 1
                except asyncio.CancelledError:
                    raise
                except Exception:
                    errors += 1
        task = asyncio.create_task(run())
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = 1
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return ShutdownReport(completed, timed_out, errors)
