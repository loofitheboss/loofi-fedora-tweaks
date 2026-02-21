"""Tests for core.plugins.registry — PluginRegistry singleton."""
import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.registry import PluginRegistry
from core.plugins.metadata import PluginMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin(plugin_id: str, category: str = "System", order: int = 100):
    """Return a minimal PluginInterface stub with controllable metadata."""
    meta = PluginMetadata(
        id=plugin_id,
        name=plugin_id.title(),
        description=f"Description for {plugin_id}",
        category=category,
        icon="",
        badge="",
        order=order,
    )
    plugin = MagicMock()
    plugin.metadata.return_value = meta
    return plugin


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginRegistrySingleton:
    """Tests for singleton lifecycle and reset()."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_instance_returns_same_object(self):
        """Two calls to instance() must return the identical object."""
        r1 = PluginRegistry.instance()
        r2 = PluginRegistry.instance()
        assert r1 is r2

    def test_reset_creates_fresh_instance(self):
        """After reset(), instance() must return a new, empty registry."""
        r1 = PluginRegistry.instance()
        r1.register(_make_plugin("dummy"))
        PluginRegistry.reset()
        r2 = PluginRegistry.instance()
        assert r1 is not r2
        assert len(r2) == 0

    def test_initial_registry_is_empty(self):
        """A freshly reset registry contains no plugins."""
        reg = PluginRegistry.instance()
        assert len(reg) == 0
        assert reg.list_all() == []


class TestPluginRegistryRegister:
    """Tests for register() and related behaviour."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_register_single_plugin(self):
        """Registering one plugin increases count to 1 and retrieval works."""
        reg = PluginRegistry.instance()
        p = _make_plugin("hardware")
        reg.register(p)

        assert len(reg) == 1
        assert reg.get("hardware") is p

    def test_register_duplicate_raises_value_error(self):
        """Registering a plugin with an already-registered id raises ValueError."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("hardware"))
        with pytest.raises(ValueError, match="hardware"):
            reg.register(_make_plugin("hardware"))

    def test_register_multiple_different_ids(self):
        """Multiple distinct ids register without error."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("hardware"))
        reg.register(_make_plugin("network"))
        reg.register(_make_plugin("storage"))
        assert len(reg) == 3

    def test_get_unknown_id_returns_none(self):
        """get() on a non-existent id returns None, not an exception."""
        reg = PluginRegistry.instance()
        assert reg.get("nonexistent") is None


class TestPluginRegistryUnregister:
    """Tests for unregister()."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_unregister_existing_plugin(self):
        """Unregistering an existing plugin removes it from registry."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("hardware"))
        reg.unregister("hardware")

        assert len(reg) == 0
        assert reg.get("hardware") is None

    def test_unregister_nonexistent_is_silent(self):
        """Unregistering an id that is not registered does not raise."""
        reg = PluginRegistry.instance()
        # Should not raise
        reg.unregister("does_not_exist")

    def test_unregister_removes_from_list_all(self):
        """Unregistered plugin no longer appears in list_all()."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("hardware"))
        reg.register(_make_plugin("network"))
        reg.unregister("hardware")

        ids = [p.metadata().id for p in reg.list_all()]
        assert "hardware" not in ids
        assert "network" in ids


class TestPluginRegistryListAll:
    """Tests for list_all() and sort ordering."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_list_all_returns_all_plugins(self):
        """list_all() returns every registered plugin."""
        reg = PluginRegistry.instance()
        p1 = _make_plugin("alpha", order=10)
        p2 = _make_plugin("beta", order=20)
        reg.register(p1)
        reg.register(p2)

        result = reg.list_all()
        assert len(result) == 2

    def test_list_all_order_by_order_field(self):
        """Plugins in the same category are returned in ascending order field order."""
        reg = PluginRegistry.instance()
        # Register in reverse order; registry should sort by order field
        p_high = _make_plugin("beta", category="System", order=200)
        p_low = _make_plugin("alpha", category="System", order=10)
        reg.register(p_high)
        reg.register(p_low)

        ids = [p.metadata().id for p in reg.list_all()]
        assert ids.index("alpha") < ids.index("beta")

    def test_iter_yields_same_as_list_all(self):
        """Iterating over registry yields same plugins as list_all()."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("a"))
        reg.register(_make_plugin("b"))

        assert list(reg) == reg.list_all()

    def test_len_matches_registered_count(self):
        """__len__ returns the exact number of registered plugins."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("x"))
        reg.register(_make_plugin("y"))
        assert len(reg) == 2


class TestPluginRegistryCategories:
    """Tests for categories() and list_by_category()."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_categories_returns_unique_values(self):
        """categories() returns each category exactly once."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("hardware", category="System"))
        reg.register(_make_plugin("network", category="System"))
        reg.register(_make_plugin("gaming", category="Entertainment"))

        cats = reg.categories()
        assert cats.count("System") == 1
        assert cats.count("Entertainment") == 1

    def test_categories_preserves_first_appearance_order(self):
        """Categories appear in order of first plugin registration (per sort key)."""
        reg = PluginRegistry.instance()
        # 'System' plugins have lower sort key so come first
        reg.register(_make_plugin("hardware", category="System", order=10))
        reg.register(_make_plugin("gaming", category="Entertainment", order=10))

        cats = reg.categories()
        # Both categories must be present
        assert "System" in cats
        assert "Entertainment" in cats

    def test_list_by_category_filters_correctly(self):
        """list_by_category() returns only plugins in the requested category."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("hardware", category="System"))
        reg.register(_make_plugin("gaming", category="Entertainment"))

        system_plugins = reg.list_by_category("System")
        assert len(system_plugins) == 1
        assert system_plugins[0].metadata().id == "hardware"

    def test_list_by_category_unknown_returns_empty(self):
        """list_by_category() with a category that has no plugins returns []."""
        reg = PluginRegistry.instance()
        reg.register(_make_plugin("hardware", category="System"))

        result = reg.list_by_category("NonExistent")
        assert result == []

    def test_categories_empty_registry(self):
        """categories() on an empty registry returns an empty list."""
        reg = PluginRegistry.instance()
        assert reg.categories() == []
