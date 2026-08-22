"""Health and readiness primitives for ORBIT components."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from typing import Callable


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class HealthCheck:
    name: str
    status: HealthStatus
    detail: str = ""
    latency_ms: float | None = None


class HealthRegistry:
    """Run registered health checks and produce a deterministic snapshot."""

    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], HealthCheck]] = {}

    def register(self, name: str, check: Callable[[], HealthCheck]) -> None:
        if not name.strip():
            raise ValueError("health check name cannot be empty")
        self._checks[name] = check

    def check(self) -> tuple[HealthCheck, ...]:
        results: list[HealthCheck] = []
        for name, callback in sorted(self._checks.items()):
            started = monotonic()
            try:
                result = callback()
            except Exception as exc:
                result = HealthCheck(name=name, status=HealthStatus.UNHEALTHY, detail=str(exc))
            if result.name != name:
                result = HealthCheck(name=name, status=result.status, detail=result.detail, latency_ms=result.latency_ms)
            if result.latency_ms is None:
                result = HealthCheck(
                    name=result.name,
                    status=result.status,
                    detail=result.detail,
                    latency_ms=(monotonic() - started) * 1000,
                )
            results.append(result)
        return tuple(results)

    def overall(self) -> HealthStatus:
        results = self.check()
        if any(item.status is HealthStatus.UNHEALTHY for item in results):
            return HealthStatus.UNHEALTHY
        if any(item.status is HealthStatus.DEGRADED for item in results):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
