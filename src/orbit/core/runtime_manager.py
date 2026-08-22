"""Lifecycle management for inference runtime adapters."""

from __future__ import annotations

from dataclasses import dataclass

from orbit.core.runtime import RuntimeAdapter


@dataclass(slots=True)
class RuntimeManager:
    """Registry for runtime adapters and their active state."""

    _runtimes: dict[str, RuntimeAdapter]
    _active: str | None = None

    def __init__(self) -> None:
        self._runtimes = {}
        self._active = None

    def register(self, adapter: RuntimeAdapter) -> None:
        name = adapter.info.name
        if name in self._runtimes:
            raise ValueError(f"runtime already registered: {name}")
        self._runtimes[name] = adapter

    def get(self, name: str) -> RuntimeAdapter | None:
        return self._runtimes.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(self._runtimes)

    @property
    def active(self) -> RuntimeAdapter | None:
        return self._runtimes.get(self._active) if self._active else None

    def select(self, name: str) -> RuntimeAdapter:
        adapter = self._runtimes.get(name)
        if adapter is None:
            raise KeyError(f"unknown runtime: {name}")
        self._active = name
        return adapter
