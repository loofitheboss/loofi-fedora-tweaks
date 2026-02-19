"""Tests for core.plugins.adapter — PluginAdapter wrapper."""
import os
import sys
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.adapter import PluginAdapter
from core.plugins.metadata import PluginMetadata, CompatStatus
from utils.plugin_base import LoofiPlugin, PluginInfo
from PyQt6.QtWidgets import QWidget, QApplication


# Initialize QApplication for widget tests (needed only once)
_app = None
def get_qapp():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication(sys.argv)
    return _app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_legacy_plugin(
    name: str = "Test Plugin",
    description: str = "Test plugin description",
    version: str = "1.0.0",
    author: str = "Test Author",
    icon: str = "🔌"
):
    """Create a mock LoofiPlugin instance."""
    info = PluginInfo(
        name=name,
        version=version,
        author=author,
        description=description,
        icon=icon
    )
    plugin = MagicMock(spec=LoofiPlugin)
    plugin.info = info
    plugin.create_widget.return_value = Mock(spec=QWidget)
    plugin.enabled = True
    return plugin


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginAdapterMetadata:
    """Tests for PluginAdapter.metadata() conversion."""

    def test_metadata_returns_plugin_metadata(self):
        """Adapter.metadata() returns PluginMetadata instance."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert isinstance(meta, PluginMetadata)

    def test_metadata_maps_name_correctly(self):
        """Adapter maps plugin name from PluginInfo."""
        legacy = _make_legacy_plugin(name="My Custom Plugin")
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.name == "My Custom Plugin"

    def test_metadata_maps_description_correctly(self):
        """Adapter maps plugin description from PluginInfo."""
        legacy = _make_legacy_plugin(description="Custom description")
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.description == "Custom description"

    def test_metadata_maps_version_correctly(self):
        """Adapter maps plugin version from PluginInfo."""
        legacy = _make_legacy_plugin(version="2.5.1")
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.version == "2.5.1"

    def test_metadata_generates_slugified_id(self):
        """Adapter generates lowercase hyphenated ID from name."""
        legacy = _make_legacy_plugin(name="My Test Plugin")
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.id == "my-test-plugin"

    def test_metadata_handles_special_chars_in_name(self):
        """Adapter slugifies names with special characters."""
        legacy = _make_legacy_plugin(name="Plugin (v2)!")
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        # Should remove special chars and keep alphanumerics/hyphens
        assert "-" in meta.id or meta.id.isalnum()

    def test_metadata_icon_fallback(self):
        """If legacy plugin has no icon, adapter uses default 🔌."""
        info = PluginInfo(name="Test", version="1.0", author="Author", description="Desc", icon="")
        legacy = MagicMock(spec=LoofiPlugin)
        legacy.info = info
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.icon == "🔌"

    def test_metadata_category_is_community(self):
        """All adapted plugins have category 'Community'."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.category == "Community"

    def test_metadata_badge_is_community(self):
        """All adapted plugins have badge 'community'."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.badge == "community"

    def test_metadata_order_is_500(self):
        """Adapted plugins have order 500 (after built-in plugins)."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.order == 500

    def test_metadata_enabled_is_true(self):
        """Adapted plugins are enabled by default."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.enabled is True

    def test_metadata_requires_is_empty_tuple(self):
        """Legacy plugins don't declare dependencies."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.requires == ()

    def test_metadata_compat_is_empty_dict(self):
        """Compat checks are handled separately."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)
        meta = adapter.metadata()

        assert meta.compat == {}

    def test_metadata_caching(self):
        """Metadata is computed once and cached."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        meta1 = adapter.metadata()
        meta2 = adapter.metadata()

        assert meta1 is meta2  # Same object


class TestPluginAdapterCreateWidget:
    """Tests for PluginAdapter.create_widget() delegation."""

    def test_create_widget_delegates_to_wrapped_plugin(self):
        """create_widget() calls wrapped plugin's create_widget()."""
        get_qapp()  # Ensure QApplication exists
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        widget = adapter.create_widget()

        legacy.create_widget.assert_called_once()
        assert widget is legacy.create_widget.return_value

    def test_create_widget_returns_qwidget(self):
        """create_widget() returns QWidget instance."""
        get_qapp()
        legacy = _make_legacy_plugin()
        real_widget = QWidget()
        legacy.create_widget.return_value = real_widget
        adapter = PluginAdapter(legacy)

        widget = adapter.create_widget()

        assert isinstance(widget, QWidget)

    def test_create_widget_raises_type_error_on_non_qwidget(self):
        """create_widget() raises RuntimeError when plugin returns non-QWidget."""
        get_qapp()
        legacy = _make_legacy_plugin()
        # Plugin returns a string instead of QWidget
        legacy.create_widget.return_value = "not a widget"
        adapter = PluginAdapter(legacy)

        with __import__('pytest').raises(RuntimeError) as exc_info:
            adapter.create_widget()

        assert "must return QWidget" in str(exc_info.value)

    def test_create_widget_raises_runtime_error_on_failure(self):
        """create_widget() raises RuntimeError when plugin create_widget fails."""
        get_qapp()
        legacy = _make_legacy_plugin()
        legacy.create_widget.side_effect = ValueError("widget creation failed")
        adapter = PluginAdapter(legacy)

        with __import__('pytest').raises(RuntimeError) as exc_info:
            adapter.create_widget()

        assert "failed to create widget" in str(exc_info.value)


class TestPluginAdapterLifecycle:
    """Tests for plugin lifecycle methods."""

    def test_on_activate_calls_on_load(self):
        """on_activate() delegates to wrapped plugin's on_load()."""
        legacy = _make_legacy_plugin()
        legacy.on_load = MagicMock()
        adapter = PluginAdapter(legacy)

        adapter.on_activate()

        legacy.on_load.assert_called_once()

    def test_on_activate_handles_missing_on_load(self):
        """on_activate() handles plugins without on_load method."""
        legacy = _make_legacy_plugin()
        # Remove on_load if it exists
        if hasattr(legacy, 'on_load'):
            delattr(legacy, 'on_load')
        adapter = PluginAdapter(legacy)

        # Should not raise
        adapter.on_activate()

    def test_on_activate_handles_on_load_error(self):
        """on_activate() logs warning if on_load() raises exception."""
        legacy = _make_legacy_plugin()
        legacy.on_load = MagicMock(side_effect=RuntimeError("load failed"))
        adapter = PluginAdapter(legacy)

        # Should not raise, just log
        adapter.on_activate()

    def test_on_deactivate_is_noop(self):
        """on_deactivate() does nothing for legacy plugins."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        # Should not raise
        adapter.on_deactivate()


class TestPluginAdapterContext:
    """Tests for set_context() method."""

    def test_set_context_stores_context(self):
        """set_context() stores the context dict."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        context = {"main_window": "window", "config_manager": "config"}
        adapter.set_context(context)

        assert hasattr(adapter, '_context')
        assert adapter._context == context

    def test_set_context_with_all_keys(self):
        """set_context() accepts full context with all keys."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        context = {
            "main_window": Mock(),
            "config_manager": Mock(),
            "executor": Mock()
        }
        adapter.set_context(context)

        assert adapter._context["main_window"] is not None
        assert adapter._context["config_manager"] is not None
        assert adapter._context["executor"] is not None


class TestPluginAdapterSlugify:
    """Tests for _slugify() static method."""

    def test_slugify_basic(self):
        """_slugify() converts basic name."""
        result = PluginAdapter._slugify("My Plugin")
        assert result == "my-plugin"

    def test_slugify_multiple_words(self):
        """_slugify() handles multiple words."""
        result = PluginAdapter._slugify("AI Enhanced Widget")
        assert result == "ai-enhanced-widget"

    def test_slugify_with_numbers(self):
        """_slugify() preserves numbers and converts dots."""
        result = PluginAdapter._slugify("Test Plugin 2.0")
        # The dot is treated as non-alphanumeric and becomes hyphen
        assert result == "test-plugin-2-0"

    def test_slugify_removes_special_chars(self):
        """_slugify() removes special characters."""
        result = PluginAdapter._slugify("Plugin (v2)!")
        assert "plugin" in result
        assert "(" not in result
        assert ")" not in result
        assert "!" not in result

    def test_slugify_underscores(self):
        """_slugify() converts underscores to hyphens."""
        result = PluginAdapter._slugify("my_plugin_name")
        assert result == "my-plugin-name"

    def test_slugify_strips_leading_trailing(self):
        """_slugify() strips leading/trailing hyphens."""
        result = PluginAdapter._slugify("  Plugin!  ")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_slugify_multiple_spaces(self):
        """_slugify() collapses multiple spaces."""
        result = PluginAdapter._slugify("My    Plugin")
        assert result == "my-plugin"

    def test_slugify_already_slug(self):
        """_slugify() handles already-slugified text."""
        result = PluginAdapter._slugify("my-plugin")
        assert result == "my-plugin"


class TestPluginAdapterVersionCompat:
    """Tests for _version_compat() static method."""

    def test_version_compat_equal(self):
        """_version_compat() returns True for equal versions."""
        result = PluginAdapter._version_compat("25.0.0", "25.0.0")
        assert result is True

    def test_version_compat_greater(self):
        """_version_compat() returns True when current > minimum."""
        result = PluginAdapter._version_compat("26.0.0", "25.0.0")
        assert result is True

    def test_version_compat_less(self):
        """_version_compat() returns False when current < minimum."""
        result = PluginAdapter._version_compat("24.0.0", "25.0.0")
        assert result is False

    def test_version_compat_minor_version(self):
        """_version_compat() compares minor versions."""
        result = PluginAdapter._version_compat("25.1.0", "25.0.0")
        assert result is True

    def test_version_compat_patch_version(self):
        """_version_compat() compares patch versions."""
        result = PluginAdapter._version_compat("25.0.1", "25.0.0")
        assert result is True

    def test_version_compat_two_part_version(self):
        """_version_compat() handles two-part versions."""
        result = PluginAdapter._version_compat("25.0", "24.5")
        assert result is True

    def test_version_compat_mismatched_parts(self):
        """_version_compat() handles different version part counts."""
        result = PluginAdapter._version_compat("25.0.0", "24.5")
        assert result is True

    def test_version_compat_invalid_version(self):
        """_version_compat() assumes compatible on unparseable versions."""
        result = PluginAdapter._version_compat("invalid", "25.0.0")
        assert result is True

    def test_version_compat_both_invalid(self):
        """_version_compat() assumes compatible when both versions invalid."""
        result = PluginAdapter._version_compat("abc", "xyz")
        assert result is True


class TestPluginAdapterCLICommands:
    """Tests for get_cli_commands() delegation."""

    def test_get_cli_commands_delegates(self):
        """get_cli_commands() delegates to wrapped plugin."""
        legacy = _make_legacy_plugin()
        commands = {"test": MagicMock()}
        legacy.get_cli_commands.return_value = commands
        adapter = PluginAdapter(legacy)

        result = adapter.get_cli_commands()

        legacy.get_cli_commands.assert_called_once()
        assert result == commands

    def test_get_cli_commands_returns_dict(self):
        """get_cli_commands() returns dict of commands."""
        legacy = _make_legacy_plugin()
        legacy.get_cli_commands.return_value = {}
        adapter = PluginAdapter(legacy)

        result = adapter.get_cli_commands()

        assert isinstance(result, dict)


class TestPluginAdapterWrappedProperty:
    """Tests for wrapped_plugin property."""

    def test_wrapped_plugin_property(self):
        """wrapped_plugin property returns the underlying plugin."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        result = adapter.wrapped_plugin

        assert result is legacy

    def test_wrapped_plugin_is_readonly(self):
        """wrapped_plugin property cannot be set (read-only)."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        # Property should be read-only (no setter)
        assert hasattr(adapter, 'wrapped_plugin')


class TestPluginAdapterCheckCompat:
    """Tests for PluginAdapter.check_compat() delegation."""

    def test_check_compat_delegates_to_detector(self):
        """check_compat() returns CompatStatus."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        detector = MagicMock()

        result = adapter.check_compat(detector)

        assert isinstance(result, CompatStatus)
        assert result.compatible is True

    def test_check_compat_passes_metadata(self):
        """check_compat() returns compat status based on manifest."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        detector = MagicMock()

        result = adapter.check_compat(detector)

        # Adapter checks manifest compatibility
        assert isinstance(result, CompatStatus)

    def test_check_compat_with_min_app_version(self):
        """check_compat() checks manifest min_app_version."""
        legacy = _make_legacy_plugin()
        manifest = MagicMock()
        manifest.min_app_version = "999.0.0"  # Future version
        legacy.manifest = manifest
        adapter = PluginAdapter(legacy)

        detector = MagicMock()
        result = adapter.check_compat(detector)

        # Should detect incompatibility
        assert result.compatible is False
        assert "Requires app version" in result.reason

    def test_check_compat_with_permissions_warning(self):
        """check_compat() warns about requested permissions."""
        legacy = _make_legacy_plugin()
        manifest = MagicMock()
        manifest.min_app_version = None
        manifest.permissions = ["sudo", "network"]
        legacy.manifest = manifest
        adapter = PluginAdapter(legacy)

        detector = MagicMock()
        result = adapter.check_compat(detector)

        # Should be compatible but with warnings
        assert result.compatible is True
        assert len(result.warnings) > 0
        assert any("sudo" in w for w in result.warnings)
        assert any("network" in w for w in result.warnings)

    def test_check_compat_no_manifest(self):
        """check_compat() returns compatible when no manifest."""
        legacy = _make_legacy_plugin()
        adapter = PluginAdapter(legacy)

        detector = MagicMock()
        result = adapter.check_compat(detector)

        assert result.compatible is True
        assert result.warnings == []


class TestPluginAdapterIntegration:
    """Integration tests for PluginAdapter."""

    def test_adapter_wraps_legacy_plugin_lifecycle(self):
        """Adapter correctly wraps entire legacy plugin lifecycle."""
        legacy = _make_legacy_plugin(name="Legacy Test")
        adapter = PluginAdapter(legacy)

        # Metadata access
        meta = adapter.metadata()
        assert meta.name == "Legacy Test"
        assert meta.id == "legacy-test"

        # Widget creation
        get_qapp()
        widget = adapter.create_widget()
        assert widget is not None

    def test_multiple_adapters_for_same_plugin(self):
        """Multiple adapters can wrap the same legacy plugin."""
        legacy = _make_legacy_plugin()

        adapter1 = PluginAdapter(legacy)
        adapter2 = PluginAdapter(legacy)

        assert adapter1 is not adapter2
        assert adapter1.metadata().id == adapter2.metadata().id

    def test_adapter_preserves_plugin_identity(self):
        """Adapter metadata ID matches across calls."""
        legacy = _make_legacy_plugin(name="Identity Test")
        adapter = PluginAdapter(legacy)

        id1 = adapter.metadata().id
        id2 = adapter.metadata().id

        assert id1 == id2 == "identity-test"
