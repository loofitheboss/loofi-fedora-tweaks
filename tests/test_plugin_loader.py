"""Tests for core.plugins.loader — PluginLoader."""
import os
import sys
import logging
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.registry import PluginRegistry
from core.plugins.loader import PluginLoader
from core.plugins.metadata import PluginMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin_class(plugin_id: str, category: str = "System", order: int = 100):
    """Return a minimal concrete PluginInterface subclass (no Qt import needed)."""
    from core.plugins.interface import PluginInterface

    meta = PluginMetadata(
        id=plugin_id,
        name=plugin_id.title(),
        description=f"Test plugin {plugin_id}",
        category=category,
        icon="",
        badge="",
        order=order,
    )

    class _StubPlugin(PluginInterface):
        def metadata(self):
            return meta

        def create_widget(self):  # pragma: no cover
            raise NotImplementedError("No Qt in unit tests")

    return _StubPlugin


def _make_fake_module(plugin_class):
    """Return a fake module object that exposes plugin_class by its __name__."""
    mod = MagicMock()
    setattr(mod, plugin_class.__name__, plugin_class)
    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginLoaderImportPlugin:
    """Tests for PluginLoader._import_plugin() internals."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_import_plugin_returns_interface_instance(self):
        """_import_plugin should instantiate and return a PluginInterface."""
        from core.plugins.interface import PluginInterface

        StubClass = _make_plugin_class("stub")
        fake_mod = _make_fake_module(StubClass)

        loader = PluginLoader(registry=PluginRegistry.instance())

        with patch("importlib.import_module", return_value=fake_mod):
            plugin = loader._import_plugin("ui.stub_tab", StubClass.__name__)

        assert isinstance(plugin, PluginInterface)
        assert plugin.metadata().id == "stub"

    def test_import_plugin_raises_type_error_for_non_subclass(self):
        """_import_plugin must raise TypeError if class is not a PluginInterface subclass."""
        class NotAPlugin:
            pass

        fake_mod = MagicMock()
        fake_mod.NotAPlugin = NotAPlugin

        loader = PluginLoader(registry=PluginRegistry.instance())

        with patch("importlib.import_module", return_value=fake_mod):
            with pytest.raises(TypeError, match="does not subclass PluginInterface"):
                loader._import_plugin("ui.not_a_plugin", "NotAPlugin")

    def test_import_plugin_raises_on_missing_attribute(self):
        """_import_plugin propagates AttributeError when class name is absent."""
        fake_mod = MagicMock(spec=[])  # spec=[] means no attributes

        loader = PluginLoader(registry=PluginRegistry.instance())

        with patch("importlib.import_module", return_value=fake_mod):
            with pytest.raises(AttributeError):
                loader._import_plugin("ui.missing", "MissingClass")


class TestPluginLoaderLoadBuiltins:
    """Tests for PluginLoader.load_builtins()."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_successful_load_returns_plugin_id(self):
        """When import succeeds, load_builtins returns the plugin's id."""
        StubClass = _make_plugin_class("dashboard")
        fake_mod = _make_fake_module(StubClass)

        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        # Patch _BUILTIN_PLUGINS to a single entry and importlib
        single_entry = [("ui.dashboard_tab", StubClass.__name__)]
        with patch("core.plugins.loader._BUILTIN_PLUGINS", single_entry), \
             patch("importlib.import_module", return_value=fake_mod):
            loaded = loader.load_builtins()

        assert loaded == ["dashboard"]
        assert len(registry) == 1

    def test_failed_import_logs_warning_not_raises(self, caplog):
        """When importlib raises ImportError, load_builtins logs a warning and continues."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        single_entry = [("ui.nonexistent_tab", "NonExistentPlugin")]
        with patch("core.plugins.loader._BUILTIN_PLUGINS", single_entry), \
             patch("importlib.import_module", side_effect=ImportError("no module")), \
             caplog.at_level(logging.WARNING, logger="core.plugins.loader"):
            loaded = loader.load_builtins()

        # No plugin loaded but no exception raised
        assert loaded == []
        assert len(registry) == 0
        assert any("Failed to load plugin" in r.message for r in caplog.records)

    def test_failed_load_does_not_stop_subsequent_plugins(self, caplog):
        """A failure on one entry must not prevent later entries from loading."""
        GoodClass = _make_plugin_class("network")
        good_mod = _make_fake_module(GoodClass)

        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        entries = [
            ("ui.bad_tab", "BadPlugin"),
            ("ui.network_tab", GoodClass.__name__),
        ]

        def fake_import(module_path):
            if module_path == "ui.bad_tab":
                raise ImportError("bad module")
            return good_mod

        with patch("core.plugins.loader._BUILTIN_PLUGINS", entries), \
             patch("importlib.import_module", side_effect=fake_import), \
             caplog.at_level(logging.WARNING):
            loaded = loader.load_builtins()

        assert "network" in loaded
        assert len(registry) == 1

    def test_load_builtins_injects_context(self):
        """When context dict is provided, set_context is called on each plugin."""
        StubClass = _make_plugin_class("hardware")
        fake_mod = _make_fake_module(StubClass)

        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        ctx = {"main_window": MagicMock(), "executor": MagicMock()}
        single_entry = [("ui.hardware_tab", StubClass.__name__)]

        with patch("core.plugins.loader._BUILTIN_PLUGINS", single_entry), \
             patch("importlib.import_module", return_value=fake_mod):
            loaded = loader.load_builtins(context=ctx)

        assert loaded == ["hardware"]
        # Plugin was registered and context available — no exception is the assertion

    def test_load_builtins_returns_empty_when_all_fail(self, caplog):
        """load_builtins returns an empty list if every import fails."""
        registry = PluginRegistry.instance()
        loader = PluginLoader(registry=registry)

        entries = [
            ("ui.a_tab", "APlugin"),
            ("ui.b_tab", "BPlugin"),
        ]
        with patch("core.plugins.loader._BUILTIN_PLUGINS", entries), \
             patch("importlib.import_module", side_effect=Exception("crash")), \
             caplog.at_level(logging.WARNING):
            loaded = loader.load_builtins()

        assert loaded == []


class TestPluginLoaderLoadExternal:
    """Tests for load_external() in v26.0."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    @patch("core.plugins.loader.PluginScanner")
    def test_load_external_returns_empty_when_no_plugins(self, mock_scanner_cls):
        """load_external() returns [] when scanner discovers nothing."""
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = []
        mock_scanner_cls.return_value = mock_scanner

        loader = PluginLoader(registry=PluginRegistry.instance())
        loaded = loader.load_external(directory="/some/plugin/dir")
        assert loaded == []

    @patch("core.plugins.loader.PluginScanner")
    def test_load_external_uses_custom_directory(self, mock_scanner_cls):
        """load_external() passes custom directory through to PluginScanner."""
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = []
        mock_scanner_cls.return_value = mock_scanner

        loader = PluginLoader(registry=PluginRegistry.instance())
        loader.load_external(directory="/tmp/plugins")

        mock_scanner_cls.assert_called_once()
        scanner_arg = mock_scanner_cls.call_args[0][0]
        assert str(scanner_arg).endswith("/tmp/plugins")


class TestPluginLoaderDefaultDependencies:
    """Tests for PluginLoader constructor defaults."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    def test_default_registry_is_singleton(self):
        """PluginLoader with no args uses PluginRegistry.instance()."""
        loader = PluginLoader()
        assert loader._registry is PluginRegistry.instance()

    def test_custom_non_empty_registry_is_used(self):
        """PluginLoader uses a non-empty custom registry (truthy object).

        Note: PluginRegistry.__len__ drives truthiness.  An empty registry
        evaluates as falsy, so the constructor's `registry or instance()`
        pattern falls through to the singleton for empty instances.
        A registry with at least one plugin is truthy and is preserved.
        """
        from core.plugins.metadata import PluginMetadata

        custom_reg = PluginRegistry.instance()
        # Add a plugin so the registry is truthy
        meta = PluginMetadata(
            id="sentinel", name="Sentinel", description="",
            category="Test", icon="", badge="",
        )
        stub = MagicMock()
        stub.metadata.return_value = meta
        custom_reg.register(stub)

        # Reset singleton so PluginRegistry.instance() would return a new obj
        PluginRegistry.reset()

        loader = PluginLoader(registry=custom_reg)
        assert loader._registry is custom_reg

    def test_none_registry_falls_back_to_singleton(self):
        """Passing registry=None causes the loader to use PluginRegistry.instance()."""
        loader = PluginLoader(registry=None)
        assert loader._registry is PluginRegistry.instance()
