"""
UI Smoke Tests for Loofi Fedora Tweaks v13.0.

These tests verify that all tab modules and plugin modules can be imported
without errors. They do NOT instantiate widgets (which would require a
running QApplication and display server). Instead they confirm:

- Every tab module can be imported
- Every tab module exposes the expected class
- The lazy loading map in main_window covers all expected tabs
- Plugin base classes can be imported
- All plugin modules have a valid LoofiPlugin subclass
- All plugin manifests (plugin.json) are valid JSON with required fields

Total: ~30+ tests.
"""

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

# Add source path so that 'ui.*' and 'utils.*' imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Check if PyQt6.QtWidgets is available (requires libGL on the host)
try:
    importlib.import_module("PyQt6.QtWidgets")
    _HAS_QT_WIDGETS = True
except ImportError:
    _HAS_QT_WIDGETS = False

_PLUGINS_DIR = Path(os.path.join(
    os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'plugins',
))

# The 18 main-window tabs and their expected classes.
# These match the _lazy_tab loaders in main_window.py plus the two eagerly
# loaded tabs (dashboard, system_info).
TAB_MODULES = {
    "ui.dashboard_tab": "DashboardTab",
    "ui.system_info_tab": "SystemInfoTab",
    "ui.monitor_tab": "MonitorTab",
    "ui.maintenance_tab": "MaintenanceTab",
    "ui.hardware_tab": "HardwareTab",
    "ui.software_tab": "SoftwareTab",
    "ui.security_tab": "SecurityTab",
    "ui.network_tab": "NetworkTab",
    "ui.gaming_tab": "GamingTab",
    "ui.desktop_tab": "DesktopTab",
    "ui.development_tab": "DevelopmentTab",
    "ui.ai_enhanced_tab": "AIEnhancedTab",
    "ui.automation_tab": "AutomationTab",
    "ui.community_tab": "CommunityTab",
    "ui.diagnostics_tab": "DiagnosticsTab",
    "ui.virtualization_tab": "VirtualizationTab",
    "ui.mesh_tab": "MeshTab",
    "ui.teleport_tab": "TeleportTab",
}

# These are the _lazy_tab keys defined in MainWindow._lazy_tab()
LAZY_TAB_KEYS = {
    "monitor", "maintenance", "hardware", "software", "security",
    "network", "gaming", "desktop", "development", "ai",
    "automation", "community", "diagnostics", "virtualization",
    "mesh", "teleport",
}


# ---------------------------------------------------------------------------
# Test: Tab module imports
# ---------------------------------------------------------------------------

@unittest.skipUnless(_HAS_QT_WIDGETS, "PyQt6.QtWidgets not available (headless environment)")
class TestTabImports(unittest.TestCase):
    """Verify every tab module can be imported and exposes its class."""

    def test_import_dashboard_tab(self):
        mod = importlib.import_module("ui.dashboard_tab")
        self.assertTrue(hasattr(mod, "DashboardTab"))

    def test_import_system_info_tab(self):
        mod = importlib.import_module("ui.system_info_tab")
        self.assertTrue(hasattr(mod, "SystemInfoTab"))

    def test_import_monitor_tab(self):
        mod = importlib.import_module("ui.monitor_tab")
        self.assertTrue(hasattr(mod, "MonitorTab"))

    def test_import_maintenance_tab(self):
        mod = importlib.import_module("ui.maintenance_tab")
        self.assertTrue(hasattr(mod, "MaintenanceTab"))

    def test_import_hardware_tab(self):
        mod = importlib.import_module("ui.hardware_tab")
        self.assertTrue(hasattr(mod, "HardwareTab"))

    def test_import_software_tab(self):
        mod = importlib.import_module("ui.software_tab")
        self.assertTrue(hasattr(mod, "SoftwareTab"))

    def test_import_security_tab(self):
        mod = importlib.import_module("ui.security_tab")
        self.assertTrue(hasattr(mod, "SecurityTab"))

    def test_import_network_tab(self):
        mod = importlib.import_module("ui.network_tab")
        self.assertTrue(hasattr(mod, "NetworkTab"))

    def test_import_gaming_tab(self):
        mod = importlib.import_module("ui.gaming_tab")
        self.assertTrue(hasattr(mod, "GamingTab"))

    def test_import_desktop_tab(self):
        mod = importlib.import_module("ui.desktop_tab")
        self.assertTrue(hasattr(mod, "DesktopTab"))

    def test_import_development_tab(self):
        mod = importlib.import_module("ui.development_tab")
        self.assertTrue(hasattr(mod, "DevelopmentTab"))

    def test_import_ai_enhanced_tab(self):
        mod = importlib.import_module("ui.ai_enhanced_tab")
        self.assertTrue(hasattr(mod, "AIEnhancedTab"))

    def test_import_automation_tab(self):
        mod = importlib.import_module("ui.automation_tab")
        self.assertTrue(hasattr(mod, "AutomationTab"))

    def test_import_community_tab(self):
        mod = importlib.import_module("ui.community_tab")
        self.assertTrue(hasattr(mod, "CommunityTab"))

    def test_import_diagnostics_tab(self):
        mod = importlib.import_module("ui.diagnostics_tab")
        self.assertTrue(hasattr(mod, "DiagnosticsTab"))

    def test_import_virtualization_tab(self):
        mod = importlib.import_module("ui.virtualization_tab")
        self.assertTrue(hasattr(mod, "VirtualizationTab"))

    def test_import_mesh_tab(self):
        mod = importlib.import_module("ui.mesh_tab")
        self.assertTrue(hasattr(mod, "MeshTab"))

    def test_import_teleport_tab(self):
        mod = importlib.import_module("ui.teleport_tab")
        self.assertTrue(hasattr(mod, "TeleportTab"))


# ---------------------------------------------------------------------------
# Test: Lazy loading mechanism
# ---------------------------------------------------------------------------

@unittest.skipUnless(_HAS_QT_WIDGETS, "PyQt6.QtWidgets not available (headless environment)")
class TestLazyLoadingMechanism(unittest.TestCase):
    """Verify the lazy loading infrastructure works."""

    def test_lazy_widget_module_importable(self):
        """LazyWidget class can be imported."""
        mod = importlib.import_module("ui.lazy_widget")
        self.assertTrue(hasattr(mod, "LazyWidget"))

    def test_main_window_module_importable(self):
        """main_window module can be imported."""
        try:
            mod = importlib.import_module("ui.main_window")
        except ImportError:
            self.skipTest("PyQt6 not available in this environment")
        self.assertTrue(hasattr(mod, "MainWindow"))

    def test_lazy_tab_keys_match_expected(self):
        """MainWindow._lazy_tab covers all expected tab keys."""
        try:
            mod = importlib.import_module("ui.main_window")
        except ImportError:
            self.skipTest("PyQt6 not available in this environment")
        # Inspect the _lazy_tab method source to find the loader keys.
        # We use a structural check: instantiate-free approach by reading
        # the source and verifying the dict keys.
        import inspect
        source = inspect.getsource(mod.MainWindow._lazy_tab)
        for key in LAZY_TAB_KEYS:
            self.assertIn(
                f'"{key}"', source,
                f"Lazy tab key '{key}' not found in _lazy_tab loader map",
            )

    def test_all_tab_modules_in_mapping(self):
        """Every module in TAB_MODULES can be imported and has its class."""
        for module_name, class_name in TAB_MODULES.items():
            with self.subTest(module=module_name):
                mod = importlib.import_module(module_name)
                self.assertTrue(
                    hasattr(mod, class_name),
                    f"{module_name} missing expected class {class_name}",
                )


# ---------------------------------------------------------------------------
# Test: Plugin base classes
# ---------------------------------------------------------------------------

class TestPluginBaseImports(unittest.TestCase):
    """Verify plugin infrastructure can be imported."""

    def test_import_plugin_base(self):
        mod = importlib.import_module("utils.plugin_base")
        self.assertTrue(hasattr(mod, "LoofiPlugin"))
        self.assertTrue(hasattr(mod, "PluginInfo"))
        self.assertTrue(hasattr(mod, "PluginManifest"))
        self.assertTrue(hasattr(mod, "PluginLoader"))

    def test_valid_permissions_defined(self):
        from utils.plugin_base import VALID_PERMISSIONS
        self.assertIsInstance(VALID_PERMISSIONS, set)
        self.assertIn("network", VALID_PERMISSIONS)
        self.assertIn("filesystem", VALID_PERMISSIONS)
        self.assertIn("sudo", VALID_PERMISSIONS)
        self.assertIn("clipboard", VALID_PERMISSIONS)
        self.assertIn("notifications", VALID_PERMISSIONS)

    def test_plugin_manifest_has_update_url_field(self):
        from utils.plugin_base import PluginManifest
        manifest = PluginManifest(
            name="test", version="1.0.0", author="t", description="t",
        )
        self.assertEqual(manifest.update_url, "")
        self.assertEqual(manifest.permissions, [])

    def test_plugin_loader_has_check_permissions(self):
        from utils.plugin_base import PluginLoader
        loader = PluginLoader()
        self.assertTrue(hasattr(loader, "check_permissions"))
        self.assertTrue(callable(loader.check_permissions))

    def test_plugin_loader_has_check_for_updates(self):
        from utils.plugin_base import PluginLoader
        loader = PluginLoader()
        self.assertTrue(hasattr(loader, "check_for_updates"))
        self.assertTrue(callable(loader.check_for_updates))


# ---------------------------------------------------------------------------
# Test: Plugin modules have LoofiPlugin subclass
# ---------------------------------------------------------------------------

class TestPluginModules(unittest.TestCase):
    """Verify all plugin modules contain a valid LoofiPlugin subclass."""

    def _load_plugin_module(self, plugin_name):
        """Dynamically load a plugin module and return it."""
        import importlib.util as ilu
        plugin_file = _PLUGINS_DIR / plugin_name / "plugin.py"
        spec = ilu.spec_from_file_location(
            f"plugins.{plugin_name}", plugin_file,
        )
        module = ilu.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _find_plugin_class(self, module):
        from utils.plugin_base import LoofiPlugin
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, LoofiPlugin)
                    and attr is not LoofiPlugin):
                return attr
        return None

    def test_ai_lab_plugin_has_subclass(self):
        mod = self._load_plugin_module("ai_lab")
        cls = self._find_plugin_class(mod)
        self.assertIsNotNone(cls, "ai_lab plugin.py has no LoofiPlugin subclass")

    def test_virtualization_plugin_has_subclass(self):
        mod = self._load_plugin_module("virtualization")
        cls = self._find_plugin_class(mod)
        self.assertIsNotNone(cls, "virtualization plugin.py has no LoofiPlugin subclass")

    def test_hello_world_plugin_has_subclass(self):
        mod = self._load_plugin_module("hello_world")
        cls = self._find_plugin_class(mod)
        self.assertIsNotNone(cls, "hello_world plugin.py has no LoofiPlugin subclass")

    def test_hello_world_plugin_cli_command(self):
        mod = self._load_plugin_module("hello_world")
        cls = self._find_plugin_class(mod)
        plugin = cls()
        cmds = plugin.get_cli_commands()
        self.assertIn("hello", cmds)
        result = cmds["hello"]()
        self.assertEqual(result, "Hello from the Loofi Plugin SDK!")


# ---------------------------------------------------------------------------
# Test: Plugin manifests (plugin.json) are valid
# ---------------------------------------------------------------------------

class TestPluginManifests(unittest.TestCase):
    """Verify all plugin.json manifests are valid JSON with required fields."""

    REQUIRED_FIELDS = {"name", "version", "author", "description"}

    def _get_plugin_dirs(self):
        """Return list of plugin directory names that have plugin.json."""
        dirs = []
        for item in _PLUGINS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                if (item / "plugin.json").exists():
                    dirs.append(item.name)
        return dirs

    def test_ai_lab_manifest_valid_json(self):
        path = _PLUGINS_DIR / "ai_lab" / "plugin.json"
        with open(path) as f:
            data = json.load(f)
        self.assertTrue(self.REQUIRED_FIELDS.issubset(set(data.keys())))

    def test_virtualization_manifest_valid_json(self):
        path = _PLUGINS_DIR / "virtualization" / "plugin.json"
        with open(path) as f:
            data = json.load(f)
        self.assertTrue(self.REQUIRED_FIELDS.issubset(set(data.keys())))

    def test_hello_world_manifest_valid_json(self):
        path = _PLUGINS_DIR / "hello_world" / "plugin.json"
        with open(path) as f:
            data = json.load(f)
        self.assertTrue(self.REQUIRED_FIELDS.issubset(set(data.keys())))

    def test_hello_world_manifest_permissions(self):
        path = _PLUGINS_DIR / "hello_world" / "plugin.json"
        with open(path) as f:
            data = json.load(f)
        self.assertIn("permissions", data)
        self.assertIsInstance(data["permissions"], list)
        self.assertIn("notifications", data["permissions"])

    def test_all_manifests_have_required_fields(self):
        """Every plugin.json has the minimum required fields."""
        for plugin_name in self._get_plugin_dirs():
            with self.subTest(plugin=plugin_name):
                path = _PLUGINS_DIR / plugin_name / "plugin.json"
                with open(path) as f:
                    data = json.load(f)
                missing = self.REQUIRED_FIELDS - set(data.keys())
                self.assertEqual(
                    missing, set(),
                    f"{plugin_name}/plugin.json missing: {missing}",
                )

    def test_all_manifests_version_format(self):
        """Every plugin version follows semver x.y.z format."""
        for plugin_name in self._get_plugin_dirs():
            with self.subTest(plugin=plugin_name):
                path = _PLUGINS_DIR / plugin_name / "plugin.json"
                with open(path) as f:
                    data = json.load(f)
                version = data.get("version", "")
                parts = version.split(".")
                self.assertEqual(
                    len(parts), 3,
                    f"{plugin_name} version '{version}' is not semver x.y.z",
                )
                for part in parts:
                    self.assertTrue(
                        part.isdigit(),
                        f"{plugin_name} version part '{part}' is not numeric",
                    )


if __name__ == '__main__':
    unittest.main()
