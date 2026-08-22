import pytest

from orbit.core.capabilities import CapabilitySet
from orbit.plugins.manifest import PluginManifest
from orbit.plugins.registry import PluginRegistry


def test_capability_set_denies_unlisted_operation():
    capabilities = CapabilitySet(frozenset({"knowledge.read"}))
    capabilities.require("knowledge.read")
    with pytest.raises(PermissionError):
        capabilities.require("shell.execute")


def test_plugin_registry_preserves_declared_permissions():
    registry = PluginRegistry()
    plugin = registry.register(
        PluginManifest(
            name="example",
            version="1.0.0",
            capabilities=frozenset({"network.read"}),
            tools=frozenset({"search"}),
        )
    )

    assert plugin.permissions.permits("network.read")
    assert not plugin.permissions.permits("filesystem.write")
    assert plugin.manifest.tools == frozenset({"search"})


def test_plugin_registry_rejects_duplicates():
    registry = PluginRegistry()
    registry.register(PluginManifest("example", "1.0.0"))
    with pytest.raises(ValueError, match="plugin already registered"):
        registry.register(PluginManifest("example", "1.0.1"))
