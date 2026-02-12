"""Tests for PluginLoader hot-reload flow and rollback behavior."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.loader import PluginLoader, HotReloadRequest
from core.plugins.registry import PluginRegistry
from core.plugins.metadata import PluginMetadata


class _StubPlugin:
    """Minimal plugin stub with metadata() for registry operations."""

    def __init__(self, plugin_id: str):
        self._meta = PluginMetadata(
            id=plugin_id,
            name=plugin_id,
            description="stub",
            category="Test",
            icon="",
            badge="",
            order=100,
        )

    def metadata(self):
        return self._meta


class TestPluginHotReload:
    """Tests for hot-reload result contracts and rollback guarantees."""

    def setup_method(self):
        PluginRegistry.reset()

    def teardown_method(self):
        PluginRegistry.reset()

    @patch("core.plugins.loader.PluginAdapter")
    @patch("core.plugins.loader.create_sandbox")
    def test_reload_external_plugin_success(self, mock_create_sandbox, mock_adapter_cls):
        """Successful reload unregisters old plugin and registers replacement."""
        registry = PluginRegistry.instance()
        previous = _StubPlugin("demo")
        registry.register(previous)

        loader = PluginLoader(registry=registry)
        loader._external_context = {"main_window": object()}

        manifest = SimpleNamespace(id="demo", permissions=[], entry_point="plugin.py")
        sandbox = MagicMock()
        sandbox.enforce_isolation.return_value = True
        mock_create_sandbox.return_value = sandbox

        plugin_instance = MagicMock()
        loader._load_external_plugin = MagicMock(return_value=plugin_instance)

        adapter = MagicMock()
        adapter.metadata.return_value = PluginMetadata(
            id="demo",
            name="demo",
            description="adapter",
            category="Test",
            icon="",
            badge="",
            order=100,
        )
        mock_adapter_cls.return_value = adapter
        loader._detector.check = MagicMock(return_value=SimpleNamespace(compatible=True, reason=""))

        result = loader._reload_external_plugin(
            plugin_id="demo",
            plugin_dir=Path("/tmp/demo"),
            manifest=manifest,
            previous_plugin=previous,
            previous_registry_id="demo",
            new_fingerprint="newfp",
            reason="filesystem",
        )

        assert result.reloaded is True
        assert result.rolled_back is False
        assert registry.get("demo") is adapter
        assert loader._external_snapshots["demo"] == "newfp"

    @patch("core.plugins.loader.create_sandbox")
    def test_reload_external_plugin_failure_restores_previous_plugin(self, mock_create_sandbox):
        """Failed reload restores previous plugin registration."""
        registry = PluginRegistry.instance()
        previous = _StubPlugin("demo")
        registry.register(previous)

        loader = PluginLoader(registry=registry)
        manifest = SimpleNamespace(id="demo", permissions=[], entry_point="plugin.py")

        sandbox = MagicMock()
        sandbox.enforce_isolation.return_value = False
        mock_create_sandbox.return_value = sandbox

        result = loader._reload_external_plugin(
            plugin_id="demo",
            plugin_dir=Path("/tmp/demo"),
            manifest=manifest,
            previous_plugin=previous,
            previous_registry_id="demo",
            new_fingerprint="newfp",
            reason="manual",
        )

        assert result.reloaded is False
        assert result.rolled_back is True
        assert "Hot reload failed" in result.message
        assert registry.get("demo") is previous

    @patch("core.plugins.loader.create_sandbox", side_effect=RuntimeError("sandbox exploded"))
    def test_reload_external_plugin_failure_with_restore_failure(self, mock_create_sandbox):
        """If rollback itself fails, result reports rolled_back=False."""
        registry = PluginRegistry.instance()
        previous = _StubPlugin("demo")
        registry.register(previous)

        loader = PluginLoader(registry=registry)
        manifest = SimpleNamespace(id="demo", permissions=[], entry_point="plugin.py")
        loader._restore_previous_plugin = MagicMock(return_value=False)

        result = loader._reload_external_plugin(
            plugin_id="demo",
            plugin_dir=Path("/tmp/demo"),
            manifest=manifest,
            previous_plugin=previous,
            previous_registry_id="demo",
            new_fingerprint="newfp",
            reason="manual",
        )

        assert result.reloaded is False
        assert result.rolled_back is False

    @patch("core.plugins.loader.PluginScanner")
    def test_request_reload_no_changes_detected(self, mock_scanner_cls):
        """request_reload short-circuits when fingerprint did not change."""
        registry = PluginRegistry.instance()
        previous = _StubPlugin("demo")
        registry.register(previous)

        loader = PluginLoader(registry=registry)
        loader._external_plugin_dirs["demo"] = Path("/tmp/demo")
        loader._external_registry_ids["demo"] = "demo"
        loader._external_snapshots["demo"] = "same"

        scanner = MagicMock()
        scanner._validate_plugin.return_value = SimpleNamespace(entry_point="plugin.py")
        scanner.build_plugin_fingerprint.return_value = "same"
        mock_scanner_cls.return_value = scanner

        result = loader.request_reload(HotReloadRequest(plugin_id="demo", reason="filesystem"))

        assert result.reloaded is False
        assert "No changes detected" in result.message

    @patch("core.plugins.loader.PluginScanner")
    @patch.object(PluginLoader, "_reload_external_plugin")
    def test_request_reload_with_changed_files_forces_reload(self, mock_reload, mock_scanner_cls):
        """Explicit changed_files triggers reload even if fingerprint is unchanged."""
        registry = PluginRegistry.instance()
        previous = _StubPlugin("demo")
        registry.register(previous)

        loader = PluginLoader(registry=registry)
        loader._external_plugin_dirs["demo"] = Path("/tmp/demo")
        loader._external_registry_ids["demo"] = "demo"
        loader._external_snapshots["demo"] = "same"

        scanner = MagicMock()
        scanner._validate_plugin.return_value = SimpleNamespace(entry_point="plugin.py")
        scanner.build_plugin_fingerprint.return_value = "same"
        mock_scanner_cls.return_value = scanner

        mock_reload.return_value = SimpleNamespace(
            plugin_id="demo",
            reloaded=True,
            message="ok",
            rolled_back=False,
        )

        result = loader.request_reload(
            HotReloadRequest(plugin_id="demo", changed_files=("plugin.py",), reason="filesystem")
        )

        assert result.reloaded is True
        assert mock_reload.call_count == 1

    def test_request_reload_requires_plugin_id(self):
        """Blank plugin id is rejected."""
        loader = PluginLoader(registry=PluginRegistry.instance())
        result = loader.request_reload(HotReloadRequest(plugin_id=" "))
        assert result.reloaded is False
        assert result.message == "Plugin ID is required"
