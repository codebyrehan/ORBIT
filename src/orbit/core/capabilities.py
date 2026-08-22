"""Capability-based permissions for tools and autonomous agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapabilitySet:
    """Immutable allow-list used to authorize privileged operations."""

    allowed: frozenset[str] = frozenset()

    def permits(self, capability: str) -> bool:
        return capability in self.allowed or "*" in self.allowed

    def require(self, capability: str) -> None:
        if not self.permits(capability):
            raise PermissionError(f"capability denied: {capability}")
