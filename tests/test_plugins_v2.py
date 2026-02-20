"""
Tests for first-party plugins — Virtualization and AI Lab.
Covers: manifest loading, plugin instantiation, CLI commands, PluginInfo fields,
min_app_version enforcement, structure validation, enable/disable, and lifecycle.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.plugin_base import (
    PluginLoader,
    LoofiPlugin,
    PluginInfo,
    PluginManifest,
)

# Paths to the actual first-party plugins
_PLUGINS_DIR = Path(os.path.join(
    os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'plugins'
))


# ---------------------------------------------------------------------------
# TestVirtualizationPluginManifest — plugin.json correctness
# ---------------------------------------------------------------------------

class TestVirtualizationPluginManifest(unittest.TestCase):
    """Tests for the Virtualization plugin manifest."""

    def setUp(self):
        self.manifest_path = _PLUGINS_DIR / "virtualization" / "plugin.json"
        with open(self.manifest_path, "r") as f:
            self.manifest = json.load(f)

    def test_manifest_has_required_keys(self):
        """Manifest contains all required keys."""
        required = {"name", "version", "author", "description", "entry"}
        self.assertTrue(required.issubset(set(self.manifest.keys())))

    def test_manifest_name(self):
        """Manifest name is 'Virtualization'."""
        self.assertEqual(self.manifest["name"], "Virtualization")

    def test_manifest_version_format(self):
        """Version follows semver format (x.y.z)."""
        parts = self.manifest["version"].split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_manifest_entry_points_to_file(self):
        """Entry file actually exists."""
        entry = self.manifest["entry"]
        entry_path = _PLUGINS_DIR / "virtualization" / entry
        self.assertTrue(entry_path.exists())

    def test_manifest_has_min_app_version(self):
        """min_app_version is present."""
        self.assertIn("min_app_version", self.manifest)

    def test_manifest_permissions_list(self):
        """Permissions is a list with expected entries."""
        perms = self.manifest.get("permissions", [])
        self.assertIsInstance(perms, list)
        self.assertIn("subprocess", perms)
        self.assertIn("privileged", perms)


# ---------------------------------------------------------------------------
# TestAILabPluginManifest — plugin.json correctness
# ---------------------------------------------------------------------------

class TestAILabPluginManifest(unittest.TestCase):
    """Tests for the AI Lab plugin manifest."""

    def setUp(self):
        self.manifest_path = _PLUGINS_DIR / "ai_lab" / "plugin.json"
        with open(self.manifest_path, "r") as f:
            self.manifest = json.load(f)

    def test_manifest_has_required_keys(self):
        """Manifest contains all required keys."""
        required = {"name", "version", "author", "description", "entry"}
        self.assertTrue(required.issubset(set(self.manifest.keys())))

    def test_manifest_name(self):
        """Manifest name is 'AI Lab'."""
        self.assertEqual(self.manifest["name"], "AI Lab")

    def test_manifest_entry_points_to_file(self):
        """Entry file actually exists."""
        entry = self.manifest["entry"]
        entry_path = _PLUGINS_DIR / "ai_lab" / entry
        self.assertTrue(entry_path.exists())

    def test_manifest_min_app_version(self):
        """min_app_version is present and reasonable."""
        min_ver = self.manifest.get("min_app_version", "")
        self.assertTrue(len(min_ver) > 0)
        parts = min_ver.split(".")
        self.assertEqual(len(parts), 3)

    def test_manifest_permissions_include_network(self):
        """AI Lab plugin requests network permission."""
        perms = self.manifest.get("permissions", [])
        self.assertIn("network", perms)


# ---------------------------------------------------------------------------
# TestVirtualizationPluginClass — instantiation and interface
# ---------------------------------------------------------------------------

class TestVirtualizationPluginClass(unittest.TestCase):
    """Tests for the VirtualizationPlugin class."""

    def _load_plugin_class(self):
        """Import and return the VirtualizationPlugin class."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugins.virtualization",
            _PLUGINS_DIR / "virtualization" / "plugin.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.VirtualizationPlugin

    def test_instantiation(self):
        """Plugin can be instantiated."""
        cls = self._load_plugin_class()
        plugin = cls()
        self.assertIsInstance(plugin, LoofiPlugin)

    def test_info_has_required_fields(self):
        """PluginInfo has all required fields populated."""
        plugin = self._load_plugin_class()()
        info = plugin.info
        self.assertIsInstance(info, PluginInfo)
        self.assertTrue(len(info.name) > 0)
        self.assertTrue(len(info.version) > 0)
        self.assertTrue(len(info.author) > 0)
        self.assertTrue(len(info.description) > 0)
        self.assertTrue(len(info.icon) > 0)

    def test_cli_commands_returned(self):
        """get_cli_commands returns expected command keys."""
        plugin = self._load_plugin_class()()
        cmds = plugin.get_cli_commands()
        self.assertIsInstance(cmds, dict)
        self.assertIn("vm-list", cmds)
        self.assertIn("vm-status", cmds)
        self.assertIn("vfio-check", cmds)

    def test_cli_commands_are_callable(self):
        """All CLI commands are callable."""
        plugin = self._load_plugin_class()()
        cmds = plugin.get_cli_commands()
        for name, func in cmds.items():
            self.assertTrue(
                callable(func),
                f"CLI command '{name}' is not callable",
            )

    def test_on_load_runs_without_error(self):
        """on_load can be called without raising."""
        plugin = self._load_plugin_class()()
        plugin.on_load()  # Should not raise

    def test_on_unload_runs_without_error(self):
        """on_unload can be called without raising."""
        plugin = self._load_plugin_class()()
        plugin.on_unload()  # Should not raise


# ---------------------------------------------------------------------------
# TestAILabPluginClass — instantiation and interface
# ---------------------------------------------------------------------------

class TestAILabPluginClass(unittest.TestCase):
    """Tests for the AILabPlugin class."""

    def _load_plugin_class(self):
        """Import and return the AILabPlugin class."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugins.ai_lab",
            _PLUGINS_DIR / "ai_lab" / "plugin.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.AILabPlugin

    def test_instantiation(self):
        """Plugin can be instantiated."""
        cls = self._load_plugin_class()
        plugin = cls()
        self.assertIsInstance(plugin, LoofiPlugin)

    def test_info_has_required_fields(self):
        """PluginInfo has all required fields populated."""
        plugin = self._load_plugin_class()()
        info = plugin.info
        self.assertIsInstance(info, PluginInfo)
        self.assertEqual(info.name, "AI Lab")
        self.assertTrue(len(info.version) > 0)
        self.assertTrue(len(info.author) > 0)

    def test_cli_commands_returned(self):
        """get_cli_commands returns expected command keys."""
        plugin = self._load_plugin_class()()
        cmds = plugin.get_cli_commands()
        self.assertIsInstance(cmds, dict)
        self.assertIn("ai-models", cmds)
        self.assertIn("ai-status", cmds)
        self.assertIn("rag-index", cmds)
        self.assertIn("rag-search", cmds)

    def test_cli_commands_are_callable(self):
        """All CLI commands are callable."""
        plugin = self._load_plugin_class()()
        cmds = plugin.get_cli_commands()
        for name, func in cmds.items():
            self.assertTrue(
                callable(func),
                f"CLI command '{name}' is not callable",
            )

    def test_on_load_runs_without_error(self):
        """on_load can be called without raising."""
        plugin = self._load_plugin_class()()
        plugin.on_load()

    def test_on_unload_runs_without_error(self):
        """on_unload can be called without raising."""
        plugin = self._load_plugin_class()()
        plugin.on_unload()


# ---------------------------------------------------------------------------
# TestMinAppVersionEnforcement — PluginLoader version gating
# ---------------------------------------------------------------------------

class TestMinAppVersionEnforcement(unittest.TestCase):
    """Tests for min_app_version enforcement via PluginLoader."""

    @patch('utils.plugin_base.APP_VERSION', "11.0.0")
    def test_compatible_version_loads(self):
        """Plugin with min_app_version <= current version loads successfully."""
        loader = PluginLoader()
        self.assertTrue(loader._is_version_compatible("11.0.0"))

    def test_future_version_blocks(self):
        """Plugin requiring a future version is blocked."""
        loader = PluginLoader()
        self.assertFalse(loader._is_version_compatible("99.0.0"))

    def test_no_min_version_is_compatible(self):
        """Plugin without min_app_version is always compatible."""
        loader = PluginLoader()
        self.assertTrue(loader._is_version_compatible(None))

    @patch('utils.plugin_base.APP_VERSION', "12.0.0")
    def test_version_11_5_compatible_with_12(self):
        """min_app_version 11.5.0 is compatible when app is 12.0.0."""
        loader = PluginLoader()
        self.assertTrue(loader._is_version_compatible("11.5.0"))


# ---------------------------------------------------------------------------
# TestPluginStructure — directory structure validation
# ---------------------------------------------------------------------------

class TestPluginStructure(unittest.TestCase):
    """Tests that plugin directories have valid structure."""

    def test_virtualization_has_plugin_py(self):
        """Virtualization plugin has plugin.py."""
        path = _PLUGINS_DIR / "virtualization" / "plugin.py"
        self.assertTrue(path.exists())

    def test_virtualization_has_manifest(self):
        """Virtualization plugin has plugin.json."""
        path = _PLUGINS_DIR / "virtualization" / "plugin.json"
        self.assertTrue(path.exists())

    def test_ai_lab_has_plugin_py(self):
        """AI Lab plugin has plugin.py."""
        path = _PLUGINS_DIR / "ai_lab" / "plugin.py"
        self.assertTrue(path.exists())

    def test_ai_lab_has_manifest(self):
        """AI Lab plugin has plugin.json."""
        path = _PLUGINS_DIR / "ai_lab" / "plugin.json"
        self.assertTrue(path.exists())

    def test_both_plugins_discoverable(self):
        """PluginLoader.discover_plugins finds both first-party plugins."""
        loader = PluginLoader()
        original_dir = loader.PLUGINS_DIR
        try:
            loader.PLUGINS_DIR = _PLUGINS_DIR
            discovered = loader.discover_plugins()
            self.assertIn("virtualization", discovered)
            self.assertIn("ai_lab", discovered)
        finally:
            loader.PLUGINS_DIR = original_dir


if __name__ == '__main__':
    unittest.main()
