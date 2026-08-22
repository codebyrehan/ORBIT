"""Runtime failover policy for inference requests."""

from __future__ import annotations

from dataclasses import dataclass

from orbit.core.runtime import RuntimeAdapter
from orbit.core.runtime_manager import RuntimeManager


@dataclass(frozen=True, slots=True)
class FailoverDecision:
    runtime_name: str
    reason: str
    attempted: tuple[str, ...]


class RuntimeFailover:
    """Choose the first healthy compatible runtime after a failed attempt."""

    def __init__(self, runtimes: RuntimeManager) -> None:
        self.runtimes = runtimes

    async def recover(self, failed_runtime: str, candidates: tuple[str, ...]) -> FailoverDecision | None:
        attempted: list[str] = [failed_runtime]
        for name in candidates:
            if name == failed_runtime:
                continue
            attempted.append(name)
            status = self.runtimes.health_status(name)
            if status is None:
                continue
            if not status.healthy:
                continue
            adapter: RuntimeAdapter | None = self.runtimes.get(name)
            if adapter is None:
                continue
            self.runtimes.select(name)
            return FailoverDecision(name, f"failed over from {failed_runtime}", tuple(attempted))
        return None
