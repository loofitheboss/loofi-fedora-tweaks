"""Integration tests for the full plugin loading pipeline (Task 11).

Tests the round-trip: PluginLoader.load_builtins() → PluginRegistry.

All 26 built-in UI tab imports are mocked so this test runs headless
without PyQt6, Qt application, or any GUI.  Each stub plugin uses the
same category/order values as defined in loader._BUILTIN_PLUGINS so that
category structure tests remain realistic.
"""
import os
import sys
import logging
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QListWidgetItem

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.registry import PluginRegistry
from core.plugins.loader import PluginLoader, _BUILTIN_PLUGINS
from core.plugins.metadata import PluginMetadata
from utils.plugin_marketplace import MarketplaceRatingAggregate, MarketplaceResult, PluginMetadata as MarketplacePluginMetadata


# ---------------------------------------------------------------------------
# Stub plugin factory
# ---------------------------------------------------------------------------

# Map module → (id, category, order) so stubs look like real plugins.
# Category groupings mirror the intended sidebar structure.
_PLUGIN_INFO: dict[str, tuple[str, str, int]] = {
    "ui.dashboard_tab":       ("dashboard",       "Overview",      10),
    "ui.agents_tab":          ("agents",          "AI",            10),
    "ui.automation_tab":      ("automation",      "AI",            20),
    "ui.system_info_tab":     ("system_info",     "System",        10),
    "ui.monitor_tab":         ("monitor",         "System",        20),
    "ui.health_timeline_tab": ("health_timeline", "System",        30),
    "ui.logs_tab":            ("logs",            "System",        40),
    "ui.hardware_tab":        ("hardware",        "Hardware",      10),
    "ui.performance_tab":     ("performance",     "Hardware",      20),
    "ui.storage_tab":         ("storage",         "Hardware",      30),
    "ui.software_tab":        ("software",        "Software",      10),
    "ui.maintenance_tab":     ("maintenance",     "Software",      20),
    "ui.snapshot_tab":        ("snapshot",        "Software",      30),
    "ui.virtualization_tab":  ("virtualization",  "Software",      40),
    "ui.development_tab":     ("development",     "Developer",     10),
    "ui.network_tab":         ("network",         "Network",       10),
    "ui.mesh_tab":            ("mesh",            "Network",       20),
    "ui.security_tab":        ("security",        "Security",      10),
    "ui.desktop_tab":         ("desktop",         "Desktop",       10),
    "ui.profiles_tab":        ("profiles",        "Desktop",       20),
    "ui.gaming_tab":          ("gaming",          "Entertainment", 10),
    "ui.ai_enhanced_tab":     ("ai_enhanced",     "AI",            30),
    "ui.teleport_tab":        ("teleport",        "Network",       30),
    "ui.diagnostics_tab":     ("diagnostics",     "System",        50),
    "ui.community_tab":       ("community",       "Community",     10),
    "ui.settings_tab":        ("settings",        "Settings",      10),
}

assert len(_PLUGIN_INFO) == 26, "Plugin count must match _BUILTIN_PLUGINS"


def _make_stub_plugin(module_path: str, class_name: str):
    """Return a minimal concrete PluginInterface stub for a given module entry."""
    from core.plugins.interface import PluginInterface

    plugin_id, category, order = _PLUGIN_INFO[module_path]
    meta = PluginMetadata(
        id=plugin_id,
        name=plugin_id.replace("_", " ").title(),
        description=f"Stub for {module_path}",
        category=category,
        icon="",
        badge="",
        order=order,
    )

    class _Stub(PluginInterface):
        def metadata(self):
            return meta

        def create_widget(self):  # pragma: no cover
            raise NotImplementedError("No Qt in unit tests")

    _Stub.__name__ = class_name
    return _Stub


def _build_fake_import_function():
    """
    Returns a side_effect function for importlib.import_module that returns
    a fake module exposing the correct stub class for each builtin entry.
    """
    module_map: dict[str, object] = {}
    for module_path, class_name in _BUILTIN_PLUGINS:
        stub_cls = _make_stub_plugin(module_path, class_name)
        fake_mod = MagicMock()
        setattr(fake_mod, class_name, stub_cls)
        module_map[module_path] = fake_mod

    def _fake_import(module_path):
        if module_path in module_map:
            return module_map[module_path]
        raise ImportError(f"Unexpected import: {module_path}")

    return _fake_import


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginIntegrationLoadBuiltins:
    """Full pipeline: load all 26 builtins into the registry via mocked imports."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_load_builtins_loads_all_26_plugins(self):
        """load_builtins() returns exactly 26 plugin IDs under mocked imports."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loaded = loader.load_builtins()

        assert len(loaded) == 26

    def test_registry_contains_all_26_plugins(self):
        """After load_builtins(), PluginRegistry holds 26 entries."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loader.load_builtins()

        assert len(registry) == 26

    def test_all_loaded_ids_are_unique(self):
        """Every loaded plugin ID is distinct."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loaded = loader.load_builtins()

        assert len(loaded) == len(set(loaded)), "Duplicate plugin IDs detected"

    def test_known_plugin_ids_present(self):
        """Key plugin IDs are reachable via registry.get()."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loader.load_builtins()

        for expected_id in ("dashboard", "hardware", "network", "security", "settings"):
            plugin = registry.get(expected_id)
            assert plugin is not None, f"Expected plugin '{expected_id}' not found"

    def test_list_all_returns_all_registered_plugins(self):
        """list_all() contains every plugin returned by load_builtins()."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loaded = loader.load_builtins()

        listed_ids = {p.metadata().id for p in registry.list_all()}
        assert set(loaded) == listed_ids


class TestPluginIntegrationCategoryStructure:
    """Verify that the expected category groups appear in the loaded registry."""

    EXPECTED_CATEGORIES = {
        "Overview", "AI", "System", "Hardware", "Software",
        "Developer", "Network", "Security", "Desktop", "Entertainment",
        "Community", "Settings",
    }

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def _load_all(self):
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)
        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loader.load_builtins()
        return registry

    def test_all_expected_categories_present(self):
        """Every expected category appears in registry.categories()."""
        registry = self._load_all()
        actual = set(registry.categories())
        assert self.EXPECTED_CATEGORIES == actual, (
            f"Missing: {self.EXPECTED_CATEGORIES - actual}, "
            f"Extra: {actual - self.EXPECTED_CATEGORIES}"
        )

    def test_category_count_matches_expected(self):
        """Number of categories matches the count of expected category groups."""
        registry = self._load_all()
        assert len(registry.categories()) == len(self.EXPECTED_CATEGORIES)

    def test_list_by_category_system_has_correct_plugins(self):
        """'System' category contains exactly the expected plugin IDs."""
        registry = self._load_all()
        system_plugins = registry.list_by_category("System")
        system_ids = {p.metadata().id for p in system_plugins}
        expected = {"system_info", "monitor", "health_timeline", "logs", "diagnostics"}
        assert system_ids == expected

    def test_list_by_category_network_has_correct_plugins(self):
        """'Network' category contains mesh, network, and teleport."""
        registry = self._load_all()
        net_plugins = registry.list_by_category("Network")
        net_ids = {p.metadata().id for p in net_plugins}
        expected = {"network", "mesh", "teleport"}
        assert net_ids == expected

    def test_plugins_within_category_sorted_by_order(self):
        """Plugins within 'System' category are returned in ascending order."""
        registry = self._load_all()
        system_plugins = registry.list_by_category("System")
        orders = [p.metadata().order for p in system_plugins]
        assert orders == sorted(orders), (
            f"System plugins not sorted by order: {orders}"
        )

    def test_each_category_has_at_least_one_plugin(self):
        """Every category returned by categories() has at least one plugin."""
        registry = self._load_all()
        for cat in registry.categories():
            plugins = registry.list_by_category(cat)
            assert len(plugins) >= 1, f"Category '{cat}' has no plugins"


class TestPluginIntegrationPartialFailure:
    """Verify graceful degradation when some builtins fail to load."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_partial_failure_loads_remaining_plugins(self, caplog):
        """If 3 builtins fail, the remaining 23 are still loaded."""
        fake_import = _build_fake_import_function()
        failing = {"ui.gaming_tab", "ui.teleport_tab", "ui.mesh_tab"}

        def selective_import(module_path):
            if module_path in failing:
                raise ImportError(f"Simulated failure for {module_path}")
            return fake_import(module_path)

        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=selective_import), \
             caplog.at_level(logging.WARNING):
            loaded = loader.load_builtins()

        assert len(loaded) == 23
        assert len(registry) == 23

    def test_failed_plugin_ids_not_in_loaded_list(self, caplog):
        """Plugin IDs that fail to import must not appear in the returned list."""
        fake_import = _build_fake_import_function()

        def selective_import(module_path):
            if module_path == "ui.gaming_tab":
                raise ImportError("no gaming")
            return fake_import(module_path)

        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=selective_import), \
             caplog.at_level(logging.WARNING):
            loaded = loader.load_builtins()

        assert "gaming" not in loaded

    def test_warnings_logged_for_failed_plugins(self, caplog):
        """A WARNING log entry is emitted for each failed plugin import."""
        fake_import = _build_fake_import_function()

        def selective_import(module_path):
            if module_path in {"ui.gaming_tab", "ui.community_tab"}:
                raise ImportError("deliberate failure")
            return fake_import(module_path)

        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=selective_import), \
             caplog.at_level(logging.WARNING, logger="core.plugins.loader"):
            loader.load_builtins()

        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_msgs) == 2


class TestPluginIntegrationRegistryIsolation:
    """Verify that PluginRegistry.reset() provides proper test isolation."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_second_load_after_reset_starts_fresh(self):
        """Loading builtins twice with a reset in between does not duplicate plugins."""
        fake_import = _build_fake_import_function()

        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loader.load_builtins()

        assert len(registry) == 26

        # Reset and reload
        PluginRegistry.reset()
        registry2 = PluginRegistry.instance()
        assert len(registry2) == 0

        loader2 = PluginLoader(registry=registry2)
        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loaded2 = loader2.load_builtins()

        assert len(loaded2) == 26
        assert len(registry2) == 26

    def test_second_load_without_reset_raises_on_duplicate(self):
        """Attempting to load builtins twice into the same registry raises ValueError."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loader.load_builtins()

        # Second load into same registry — first duplicate will trigger ValueError
        # which load_builtins catches as a warning; all subsequent will also warn.
        with patch("importlib.import_module", side_effect=_build_fake_import_function()):
            loaded_second = loader.load_builtins()

        # None should succeed since all IDs are already registered
        assert loaded_second == []


class TestCommunityTabMarketplaceIntegration:
    """Integration checks for CommunityTab marketplace UI/backend interaction."""

    _app = None

    @classmethod
    def setup_class(cls):
        cls._app = QApplication.instance() or QApplication(sys.argv)

    @patch("ui.community_tab.CommunityTab.refresh_marketplace")
    @patch("ui.community_tab.PluginLoader")
    @patch("ui.community_tab.PluginInstaller")
    @patch("ui.community_tab.PluginMarketplace")
    @patch("ui.community_tab.DriftDetector")
    @patch("ui.community_tab.PresetManager")
    @patch("ui.community_tab.CloudSyncManager")
    @patch("ui.community_tab.ConfigManager")
    @patch("ui.community_tab.PresetMarketplace")
    def test_marketplace_selection_triggers_rating_and_review_calls(
        self,
        _preset_marketplace,
        _config_manager,
        mock_cloud_sync,
        _preset_manager,
        _drift_detector,
        mock_plugin_marketplace_cls,
        _plugin_installer,
        mock_plugin_loader_cls,
        _refresh_marketplace,
    ):
        """Selecting a marketplace item invokes aggregate/review backend lookups."""
        mock_cloud_sync.get_gist_token.return_value = ""
        mock_cloud_sync.get_gist_id.return_value = ""

        mock_plugin_loader = MagicMock()
        mock_plugin_loader.list_plugins.return_value = []
        mock_plugin_loader_cls.return_value = mock_plugin_loader

        mock_marketplace = MagicMock()
        mock_marketplace.get_rating_aggregate.return_value = MarketplaceResult(
            success=True,
            data=MarketplaceRatingAggregate(
                plugin_id="test-plugin",
                average_rating=4.9,
                rating_count=10,
                review_count=8,
                breakdown={5: 8, 4: 2},
            ),
        )
        mock_marketplace.fetch_reviews.return_value = MarketplaceResult(success=True, data=[])
        mock_plugin_marketplace_cls.return_value = mock_marketplace

        from ui.community_tab import CommunityTab
        tab = CommunityTab()

        plugin_meta = MarketplacePluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            description="Plugin",
            version="1.0.0",
            author="Author",
            category="System",
            download_url="https://example.com/plugin.loofi-plugin",
            checksum_sha256="a" * 64,
            verified_publisher=True,
            publisher_badge="verified",
        )
        tab.marketplace_plugin_metadata = {"test-plugin": plugin_meta}

        preset = SimpleNamespace(
            id="test-plugin",
            plugin_id="test-plugin",
            name="Test Plugin",
            author="Preset Author",
            category="System",
            description="Preset description",
            stars=5,
            download_count=42,
            tags=["fedora"],
        )
        item = QListWidgetItem("preset")
        item.setData(Qt.ItemDataRole.UserRole, preset)

        tab.on_marketplace_preset_selected(item)

        mock_marketplace.get_rating_aggregate.assert_called_once_with("test-plugin")
        mock_marketplace.fetch_reviews.assert_called_once_with("test-plugin", limit=5, offset=0)
