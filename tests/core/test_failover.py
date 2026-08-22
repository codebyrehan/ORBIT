from __future__ import annotations

import pytest

from orbit.core.failover import RuntimeFailover
from orbit.core.runtime import RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager


class FakeRuntime:
    def __init__(self, name: str) -> None:
        self.info = RuntimeInfo(name=name, version="test")

    async def health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_failover_selects_first_healthy_candidate() -> None:
    manager = RuntimeManager()
    manager.register(FakeRuntime("a"))
    manager.register(FakeRuntime("b"))
    manager.register(FakeRuntime("c"))
    await manager.check_all()

    decision = await RuntimeFailover(manager).recover("a", ("a", "b", "c"))

    assert decision is not None
    assert decision.runtime_name == "b"
    assert decision.attempted == ("a", "b")
    assert manager.active_name == "b"


@pytest.mark.asyncio
async def test_failover_skips_unhealthy_and_unknown_candidates() -> None:
    manager = RuntimeManager()
    manager.register(FakeRuntime("a"))
    manager.register(FakeRuntime("b"))
    await manager.check_all()
    manager._health["b"] = manager._health["b"].__class__("b", False, "offline")

    decision = await RuntimeFailover(manager).recover("a", ("a", "missing", "b"))

    assert decision is None
    assert manager.active_name is None
