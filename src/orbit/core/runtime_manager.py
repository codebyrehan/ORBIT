"""Lifecycle and health management for inference runtime adapters."""

from __future__ import annotations

from dataclasses import dataclass, field

from orbit.core.runtime import RuntimeAdapter


@dataclass(frozen=True, slots=True)
class RuntimeHealth:
    name: str
    healthy: bool
    detail: str


@dataclass(slots=True)
class RuntimeManager:
    """Registry for runtime adapters with explicit health state."""

    _runtimes: dict[str, RuntimeAdapter]
    _health: dict[str, RuntimeHealth] = field(default_factory=dict)
    _active: str | None = None

    def __init__(self) -> None:
        self._runtimes = {}
        self._health = {}
        self._active = None

    def register(self, adapter: RuntimeAdapter) -> None:
        name = adapter.info.name
        if name in self._runtimes:
            raise ValueError(f"runtime already registered: {name}")
        self._runtimes[name] = adapter
        self._health[name] = RuntimeHealth(name, False, "health not checked")

    def get(self, name: str) -> RuntimeAdapter | None:
        return self._runtimes.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(self._runtimes)

    def healthy_names(self) -> tuple[str, ...]:
        return tuple(name for name in self._runtimes if self._health[name].healthy)

    def health_status(self, name: str) -> RuntimeHealth | None:
        return self._health.get(name)

    async def check_health(self, name: str) -> RuntimeHealth:
        adapter = self._runtimes.get(name)
        if adapter is None:
            raise KeyError(f"unknown runtime: {name}")
        try:
            healthy = await adapter.health()
            detail = "healthy" if healthy else "health check reported unhealthy"
        except Exception as exc:
            healthy = False
            detail = f"health check failed: {exc}"
        status = RuntimeHealth(name, healthy, detail)
        self._health[name] = status
        if not healthy and self._active == name:
            self._active = None
        return status

    async def check_all(self) -> tuple[RuntimeHealth, ...]:
        results = []
        for name in self._runtimes:
            results.append(await self.check_health(name))
        return tuple(results)

    @property
    def active(self) -> RuntimeAdapter | None:
        return self._runtimes.get(self._active) if self._active else None

    @property
    def active_name(self) -> str | None:
        return self._active

    def select(self, name: str) -> RuntimeAdapter:
        adapter = self._runtimes.get(name)
        if adapter is None:
            raise KeyError(f"unknown runtime: {name}")
        status = self._health.get(name)
        if status is None or not status.healthy:
            raise RuntimeError(f"runtime is not healthy: {name}")
        self._active = name
        return adapter

    def clear_active(self) -> None:
        self._active = None
