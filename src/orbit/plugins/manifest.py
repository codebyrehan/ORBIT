"""Plugin metadata and permission contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Declarative plugin metadata loaded before plugin code executes."""

    name: str
    version: str
    description: str = ""
    capabilities: frozenset[str] = field(default_factory=frozenset)
    tools: frozenset[str] = field(default_factory=frozenset)
    events: frozenset[str] = field(default_factory=frozenset)
