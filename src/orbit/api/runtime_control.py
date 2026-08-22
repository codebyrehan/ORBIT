"""Production controls for bounded inference execution."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

import asyncio

from orbit.core.runtime import GenerationRequest, RuntimeAdapter


@dataclass(frozen=True, slots=True)
class GenerationResult:
    request_id: str
    text: str
    duration_ms: float


class RuntimeExecutionError(RuntimeError):
    """Raised when a generation cannot be completed."""


class RuntimeExecutor:
    """Execute generations with timeout and concurrency bounds."""

    def __init__(self, runtime: RuntimeAdapter, *, max_concurrency: int = 1, timeout_seconds: float = 120.0) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.runtime = runtime
        self.timeout_seconds = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        request_id = uuid4().hex
        async with self._semaphore:
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    async for chunk in self.runtime.generate(request):
                        yield chunk
            except asyncio.CancelledError:
                raise
            except TimeoutError as exc:
                raise RuntimeExecutionError(f"generation timed out: {request_id}") from exc
            except Exception as exc:
                raise RuntimeExecutionError(f"generation failed: {request_id}") from exc

    async def execute(self, request: GenerationRequest) -> GenerationResult:
        request_id = uuid4().hex
        started = monotonic()
        chunks: list[str] = []
        async with self._semaphore:
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    async for chunk in self.runtime.generate(request):
                        chunks.append(chunk)
            except asyncio.CancelledError:
                raise
            except TimeoutError as exc:
                raise RuntimeExecutionError(f"generation timed out: {request_id}") from exc
            except Exception as exc:
                raise RuntimeExecutionError(f"generation failed: {request_id}") from exc
        return GenerationResult(request_id, "".join(chunks), (monotonic() - started) * 1000)
