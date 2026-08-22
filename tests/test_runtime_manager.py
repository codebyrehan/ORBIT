from collections.abc import AsyncIterator

import pytest

from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager


class FakeRuntime(RuntimeAdapter):
    def __init__(self, name: str, healthy: bool = True) -> None:
        self._info = RuntimeInfo(name, "1.0", frozenset({"text"}))
        self.healthy = healthy

    @property
    def info(self) -> RuntimeInfo:
        return self._info

    async def health(self) -> bool:
        return self.healthy

    async def _generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        yield request.prompt

    def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        return self._generate(request)


@pytest.mark.asyncio
async def test_check_health_marks_runtime_healthy_and_allows_selection() -> None:
    manager = RuntimeManager()
    manager.register(FakeRuntime("test"))

    status = await manager.check_health("test")

    assert status.healthy is True
    assert manager.healthy_names() == ("test",)
    assert manager.select("test").info.name == "test"
    assert manager.active_name == "test"


@pytest.mark.asyncio
async def test_unhealthy_runtime_is_quarantined() -> None:
    manager = RuntimeManager()
    runtime = FakeRuntime("test", healthy=False)
    manager.register(runtime)

    status = await manager.check_health("test")

    assert status.healthy is False
    assert manager.healthy_names() == ()
    with pytest.raises(RuntimeError, match="not healthy"):
        manager.select("test")


@pytest.mark.asyncio
async def test_active_runtime_is_cleared_when_health_check_fails() -> None:
    manager = RuntimeManager()
    runtime = FakeRuntime("test")
    manager.register(runtime)
    await manager.check_health("test")
    manager.select("test")

    runtime.healthy = False
    status = await manager.check_health("test")

    assert status.healthy is False
    assert manager.active is None
    assert manager.active_name is None


@pytest.mark.asyncio
async def test_check_health_converts_adapter_exception_to_unhealthy() -> None:
    manager = RuntimeManager()
    runtime = FakeRuntime("test")

    async def broken_health() -> bool:
        raise RuntimeError("backend unavailable")

    runtime.health = broken_health  # type: ignore[method-assign]
    manager.register(runtime)

    status = await manager.check_health("test")

    assert status.healthy is False
    assert "backend unavailable" in status.detail
