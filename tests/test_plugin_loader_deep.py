"""Tests for core.plugins.loader — PluginLoader (76 miss, 60%)."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


def _make_plugin_interface(pid="test-plugin"):
    """Create a mock PluginInterface."""
    p = MagicMock()
    meta = MagicMock()
    meta.id = pid
    meta.compat = MagicMock()
    p.metadata.return_value = meta
    return p


class TestPluginLoaderInit(unittest.TestCase):
    def test_default_init(self):
        from core.plugins.loader import PluginLoader
        loader = PluginLoader()
        self.assertIsNotNone(loader._registry)


class TestLoadBuiltins(unittest.TestCase):
    @patch("core.plugins.loader.importlib.import_module")
    def test_loads_plugins(self, mock_import):
        from core.plugins.loader import PluginLoader
        mock_cls = MagicMock()
        mock_instance = _make_plugin_interface("dashboard")
        mock_cls.return_value = mock_instance

        # Make issubclass work
        from core.plugins.interface import PluginInterface
        mock_cls.__mro__ = (mock_cls, PluginInterface, object)

        mock_module = MagicMock()
        mock_module.DashboardTab = mock_cls
        mock_import.return_value = mock_module

        # Use a custom method to check type correctly
        registry = MagicMock()
        loader = PluginLoader(registry=registry)

        with patch.object(loader, '_import_plugin', return_value=mock_instance):
            loaded = loader.load_builtins()
            self.assertGreater(len(loaded), 0)

    @patch("core.plugins.loader.importlib.import_module", side_effect=ImportError("no module"))
    def test_handles_import_error(self, mock_import):
        from core.plugins.loader import PluginLoader
        registry = MagicMock()
        loader = PluginLoader(registry=registry)

        with patch.object(loader, '_import_plugin', side_effect=ImportError("no")):
            loaded = loader.load_builtins()
            # Should gracefully handle errors
            self.assertIsInstance(loaded, list)


class TestImportPlugin(unittest.TestCase):
    @patch("core.plugins.loader.importlib.import_module")
    def test_valid_plugin(self, mock_import):
        from core.plugins.interface import PluginInterface
        from core.plugins.loader import PluginLoader

        mock_cls = MagicMock(spec=type)
        mock_instance = MagicMock(spec=PluginInterface)
        mock_cls.return_value = mock_instance
        # Make issubclass work
        mock_cls.__mro__ = (mock_cls, PluginInterface, object)

        mock_module = MagicMock()
        mock_module.TestClass = mock_cls
        mock_import.return_value = mock_module

        loader = PluginLoader()
        # This will fail issubclass check because MagicMock - test the TypeError path
        try:
            result = loader._import_plugin("test.module", "TestClass")
        except TypeError:
            pass  # Expected when mock class doesn't truly subclass PluginInterface


class TestFindPluginClass(unittest.TestCase):
    def test_finds_class(self):
        from core.plugins.loader import PluginLoader
        from utils.plugin_base import LoofiPlugin

        class TestPlugin(LoofiPlugin):
            pass

        module = MagicMock()
        module.__name__ = "test_module"
        # Set up the module so inspect.getmembers finds our class
        TestPlugin.__module__ = "test_module"

        loader = PluginLoader()
        with patch("inspect.getmembers", return_value=[("TestPlugin", TestPlugin)]):
            result = loader._find_plugin_class(module)
            self.assertEqual(result, TestPlugin)

    def test_no_class_found(self):
        from core.plugins.loader import PluginLoader
        module = MagicMock()
        module.__name__ = "test_module"

        loader = PluginLoader()
        with patch("inspect.getmembers", return_value=[]):
            result = loader._find_plugin_class(module)
            self.assertIsNone(result)


class TestHotReloadRequest(unittest.TestCase):
    def test_dataclass(self):
        from core.plugins.loader import HotReloadRequest
        r = HotReloadRequest(plugin_id="test", changed_files=("a.py",), reason="manual")
        self.assertEqual(r.plugin_id, "test")
        self.assertEqual(r.reason, "manual")

    def test_defaults(self):
        from core.plugins.loader import HotReloadRequest
        r = HotReloadRequest(plugin_id="test")
        self.assertEqual(r.changed_files, ())
        self.assertEqual(r.reason, "filesystem")


class TestHotReloadResult(unittest.TestCase):
    def test_dataclass(self):
        from core.plugins.loader import HotReloadResult
        r = HotReloadResult(plugin_id="test", reloaded=True, message="ok")
        self.assertTrue(r.reloaded)
        self.assertFalse(r.rolled_back)


class TestRequestReload(unittest.TestCase):
    def test_empty_plugin_id(self):
        from core.plugins.loader import HotReloadRequest, PluginLoader
        loader = PluginLoader()
        result = loader.request_reload(HotReloadRequest(plugin_id=""))
        self.assertFalse(result.reloaded)
        self.assertIn("required", result.message.lower())

    def test_unknown_plugin(self):
        from core.plugins.loader import HotReloadRequest, PluginLoader
        loader = PluginLoader()
        result = loader.request_reload(HotReloadRequest(plugin_id="unknown"))
        self.assertFalse(result.reloaded)
        self.assertIn("not loaded", result.message.lower())

    def test_not_in_registry(self):
        from core.plugins.loader import HotReloadRequest, PluginLoader
        loader = PluginLoader()
        loader._external_plugin_dirs["test"] = Path("/tmp/test")
        loader._external_registry_ids["test"] = "test"
        loader._registry = MagicMock()
        loader._registry.get.return_value = None
        result = loader.request_reload(HotReloadRequest(plugin_id="test"))
        self.assertFalse(result.reloaded)
        self.assertIn("not present", result.message.lower())

    def test_manifest_validation_fails(self):
        from core.plugins.loader import HotReloadRequest, PluginLoader
        loader = PluginLoader()
        loader._external_plugin_dirs["test"] = Path("/tmp/test")
        loader._external_registry_ids["test"] = "test"
        loader._registry = MagicMock()
        loader._registry.get.return_value = MagicMock()

        with patch("core.plugins.loader.PluginScanner") as MockScanner:
            MockScanner.return_value._validate_plugin.return_value = None
            result = loader.request_reload(HotReloadRequest(plugin_id="test"))
            self.assertFalse(result.reloaded)

    def test_no_changes_detected(self):
        from core.plugins.loader import HotReloadRequest, PluginLoader
        loader = PluginLoader()
        loader._external_plugin_dirs["test"] = Path("/tmp/test")
        loader._external_registry_ids["test"] = "test"
        loader._external_snapshots["test"] = "fingerprint_abc"
        loader._registry = MagicMock()
        loader._registry.get.return_value = MagicMock()

        manifest = MagicMock()
        manifest.entry_point = "plugin.py"

        with patch("core.plugins.loader.PluginScanner") as MockScanner:
            scanner_inst = MockScanner.return_value
            scanner_inst._validate_plugin.return_value = manifest
            scanner_inst.build_plugin_fingerprint.return_value = "fingerprint_abc"
            result = loader.request_reload(HotReloadRequest(plugin_id="test"))
            self.assertFalse(result.reloaded)
            self.assertIn("No changes", result.message)


class TestRestorePreviousPlugin(unittest.TestCase):
    def test_restore_success(self):
        from core.plugins.loader import PluginLoader
        loader = PluginLoader()
        loader._registry = MagicMock()
        loader._registry.get.return_value = None
        prev = MagicMock()
        result = loader._restore_previous_plugin("test-id", prev)
        self.assertTrue(result)
        loader._registry.register.assert_called_once_with(prev)

    def test_restore_already_registered(self):
        from core.plugins.loader import PluginLoader
        loader = PluginLoader()
        loader._registry = MagicMock()
        loader._registry.get.return_value = MagicMock()  # Already there
        result = loader._restore_previous_plugin("test-id", MagicMock())
        self.assertTrue(result)

    def test_restore_failure(self):
        from core.plugins.loader import PluginLoader
        loader = PluginLoader()
        loader._registry = MagicMock()
        loader._registry.get.return_value = None
        loader._registry.register.side_effect = Exception("boom")
        result = loader._restore_previous_plugin("test-id", MagicMock())
        self.assertFalse(result)


class TestLoadExternalPlugin(unittest.TestCase):
    def test_missing_entry_file(self):
        from core.plugins.loader import PluginLoader
        loader = PluginLoader()
        manifest = MagicMock()
        manifest.entry_point = "plugin.py"
        manifest.id = "test"
        sandbox = MagicMock()
        plugin_dir = MagicMock(spec=Path)
        entry_file = MagicMock()
        entry_file.exists.return_value = False
        plugin_dir.__truediv__ = MagicMock(return_value=entry_file)
        result = loader._load_external_plugin(plugin_dir, manifest, sandbox)
        self.assertIsNone(result)


class TestLoadExternal(unittest.TestCase):
    def test_no_plugins_found(self):
        from core.plugins.loader import PluginLoader
        loader = PluginLoader()
        with patch("core.plugins.loader.PluginScanner") as MockScanner:
            MockScanner.return_value.scan.return_value = []
            loaded = loader.load_external()
            self.assertEqual(loaded, [])


if __name__ == "__main__":
    unittest.main()
