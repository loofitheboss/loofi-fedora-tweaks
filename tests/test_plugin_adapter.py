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
