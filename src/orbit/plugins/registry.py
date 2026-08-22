"""In-process plugin registry with duplicate and permission checks."""

from __future__ import annotations

from dataclasses import dataclass

from orbit.core.capabilities import CapabilitySet
from orbit.plugins.manifest import PluginManifest


@dataclass(frozen=True, slots=True)
class RegisteredPlugin:
    manifest: PluginManifest
    permissions: CapabilitySet


class PluginRegistry:
    """Registry for installed plugin manifests; execution remains an adapter concern."""

    def __init__(self) -> None:
        self._plugins: dict[str, RegisteredPlugin] = {}

    def register(self, manifest: PluginManifest) -> RegisteredPlugin:
        if manifest.name in self._plugins:
            raise ValueError(f"plugin already registered: {manifest.name}")
        registered = RegisteredPlugin(manifest, CapabilitySet(manifest.capabilities))
        self._plugins[manifest.name] = registered
        return registered

    def get(self, name: str) -> RegisteredPlugin | None:
        return self._plugins.get(name)

    def all(self) -> tuple[RegisteredPlugin, ...]:
        return tuple(self._plugins.values())
