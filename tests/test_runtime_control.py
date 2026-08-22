import asyncio

import pytest

from orbit.api.runtime_control import RuntimeExecutionError, RuntimeExecutor
from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo


class FakeRuntime(RuntimeAdapter):
    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo("fake", "1", frozenset({"text"}))

    async def health(self) -> bool:
        return True

    async def _generate(self, request: GenerationRequest):
        yield "hello"
        yield " world"

    def generate(self, request: GenerationRequest):
        return self._generate(request)


class SlowRuntime(FakeRuntime):
    async def _generate(self, request: GenerationRequest):
        await asyncio.sleep(0.05)
        yield "late"


class BrokenRuntime(FakeRuntime):
    async def _generate(self, request: GenerationRequest):
        raise ValueError("backend failed")
        yield "never"


@pytest.mark.asyncio
async def test_execute_returns_text_request_id_and_latency() -> None:
    executor = RuntimeExecutor(FakeRuntime(), timeout_seconds=1)
    result = await executor.execute(GenerationRequest(prompt="hi", model="demo"))
    assert result.text == "hello world"
    assert result.request_id
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_execute_preserves_caller_request_id() -> None:
    executor = RuntimeExecutor(FakeRuntime(), timeout_seconds=1)
    result = await executor.execute(GenerationRequest(prompt="hi", model="demo"), request_id="req-123")
    assert result.request_id == "req-123"


@pytest.mark.asyncio
async def test_stream_preserves_chunks() -> None:
    executor = RuntimeExecutor(FakeRuntime(), timeout_seconds=1)
    chunks = [chunk async for chunk in executor.stream(GenerationRequest(prompt="hi", model="demo"))]
    assert chunks == ["hello", " world"]


@pytest.mark.asyncio
async def test_stream_preserves_caller_request_id_in_errors() -> None:
    executor = RuntimeExecutor(BrokenRuntime(), timeout_seconds=1)
    with pytest.raises(RuntimeExecutionError, match="req-stream"):
        async for _ in executor.stream(GenerationRequest(prompt="hi", model="demo"), request_id="req-stream"):
            pass


@pytest.mark.asyncio
async def test_timeout_is_normalized() -> None:
    executor = RuntimeExecutor(SlowRuntime(), timeout_seconds=0.001)
    with pytest.raises(RuntimeExecutionError, match="generation timed out"):
        await executor.execute(GenerationRequest(prompt="hi", model="demo"))


@pytest.mark.asyncio
async def test_backend_failure_is_normalized() -> None:
    executor = RuntimeExecutor(BrokenRuntime(), timeout_seconds=1)
    with pytest.raises(RuntimeExecutionError, match="generation failed"):
        await executor.execute(GenerationRequest(prompt="hi", model="demo"))


@pytest.mark.asyncio
async def test_cancellation_propagates() -> None:
    executor = RuntimeExecutor(SlowRuntime(), timeout_seconds=1)
    task = asyncio.create_task(executor.execute(GenerationRequest(prompt="hi", model="demo")))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
