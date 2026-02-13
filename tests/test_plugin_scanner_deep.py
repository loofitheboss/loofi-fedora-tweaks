"""Tests for core.plugins.scanner — PluginScanner (72 miss, 56.6%)."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


VALID_MANIFEST = {
    "id": "test-plugin",
    "name": "Test Plugin",
    "version": "1.0.0",
    "description": "A test plugin",
    "author": "Test Author",
    "entry_point": "plugin.py",
    "permissions": ["network"],
    "requires": [],
    "min_app_version": "1.0.0",
    "icon": "🔌",
    "category": "Test",
}


class TestPluginScannerInit(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def test_default_dir(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        s = PluginScanner()
        self.assertIn("plugins", str(s.plugins_dir))

    @patch("core.plugins.scanner.Path.mkdir")
    def test_custom_dir(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        s = PluginScanner(Path("/tmp/test_plugins"))
        self.assertEqual(s.plugins_dir, Path("/tmp/test_plugins"))


class TestParseManifest(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_valid_manifest(self):
        manifest_path = MagicMock()
        manifest_path.read_text.return_value = json.dumps(VALID_MANIFEST)
        result = self.scanner._parse_manifest(manifest_path)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "test-plugin")
        self.assertEqual(result.version, "1.0.0")

    def test_missing_fields(self):
        manifest_path = MagicMock()
        manifest_path.read_text.return_value = json.dumps({"id": "x"})
        result = self.scanner._parse_manifest(manifest_path)
        self.assertIsNone(result)

    def test_invalid_json(self):
        manifest_path = MagicMock()
        manifest_path.read_text.side_effect = json.JSONDecodeError("e", "", 0)
        result = self.scanner._parse_manifest(manifest_path)
        self.assertIsNone(result)

    def test_read_error(self):
        manifest_path = MagicMock()
        manifest_path.read_text.side_effect = OSError("denied")
        result = self.scanner._parse_manifest(manifest_path)
        self.assertIsNone(result)


class TestValidatePlugin(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_missing_manifest(self):
        plugin_dir = MagicMock()
        plugin_dir.name = "test"
        manifest_path = MagicMock()
        manifest_path.exists.return_value = False
        plugin_dir.__truediv__ = lambda self_unused, other: manifest_path
        result = self.scanner._validate_plugin(plugin_dir)
        self.assertIsNone(result)

    def test_valid_plugin(self):
        plugin_dir = MagicMock()
        plugin_dir.name = "test-plugin"

        manifest_file = MagicMock()
        manifest_file.exists.return_value = True

        entry_file = MagicMock()
        entry_file.exists.return_value = True

        def truediv(self_unused, other):
            if other == "plugin.json":
                return manifest_file
            return entry_file

        plugin_dir.__truediv__ = truediv

        with patch.object(self.scanner, '_parse_manifest') as mock_parse:
            from core.plugins.package import PluginManifest
            fake_manifest = PluginManifest(
                id="test-plugin", name="Test", version="1.0.0",
                description="desc", author="auth",
                entry_point="plugin.py", min_app_version=None
            )
            mock_parse.return_value = fake_manifest
            result = self.scanner._validate_plugin(plugin_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result.id, "test-plugin")

    def test_missing_entry_point(self):
        plugin_dir = MagicMock()
        plugin_dir.name = "test-plugin"

        manifest_file = MagicMock()
        manifest_file.exists.return_value = True

        entry_file = MagicMock()
        entry_file.exists.return_value = False

        def truediv(self_unused, other):
            if other == "plugin.json":
                return manifest_file
            return entry_file

        plugin_dir.__truediv__ = truediv

        with patch.object(self.scanner, '_parse_manifest') as mock_parse:
            from core.plugins.package import PluginManifest
            fake_manifest = PluginManifest(
                id="test-plugin", name="Test", version="1.0.0",
                description="desc", author="auth",
                entry_point="plugin.py", min_app_version=None
            )
            mock_parse.return_value = fake_manifest
            result = self.scanner._validate_plugin(plugin_dir)
            self.assertIsNone(result)


class TestIsEnabled(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_default_enabled(self):
        self.assertTrue(self.scanner._is_enabled("x", {}))

    def test_old_format_disabled(self):
        state = {"enabled": {"x": False}}
        self.assertFalse(self.scanner._is_enabled("x", state))

    def test_old_format_enabled(self):
        state = {"enabled": {"x": True}}
        self.assertTrue(self.scanner._is_enabled("x", state))

    def test_new_format_disabled(self):
        state = {"x": {"enabled": False}}
        self.assertFalse(self.scanner._is_enabled("x", state))

    def test_new_format_enabled(self):
        state = {"x": {"enabled": True}}
        self.assertTrue(self.scanner._is_enabled("x", state))


class TestLoadState(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_no_file(self):
        self.scanner.state_file = MagicMock()
        self.scanner.state_file.exists.return_value = False
        self.assertEqual(self.scanner._load_state(), {"enabled": {}})

    def test_invalid_json(self):
        self.scanner.state_file = MagicMock()
        self.scanner.state_file.exists.return_value = True
        self.scanner.state_file.read_text.side_effect = json.JSONDecodeError("e", "", 0)
        self.assertEqual(self.scanner._load_state(), {"enabled": {}})

    def test_valid_file(self):
        self.scanner.state_file = MagicMock()
        self.scanner.state_file.exists.return_value = True
        self.scanner.state_file.read_text.return_value = '{"enabled": {"x": true}}'
        result = self.scanner._load_state()
        self.assertTrue(result["enabled"]["x"])


class TestParseVersion(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_normal(self):
        self.assertEqual(self.scanner._parse_version("1.2.3"), (1, 2, 3))

    def test_non_numeric(self):
        self.assertEqual(self.scanner._parse_version("1.abc.3"), (1, 0, 3))


class TestIsVersionCompatible(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    @patch("core.plugins.scanner.APP_VERSION", "29.0.0")
    def test_compatible(self):
        self.assertTrue(self.scanner._is_version_compatible("1.0.0"))

    @patch("core.plugins.scanner.APP_VERSION", "1.0.0")
    def test_incompatible(self):
        self.assertFalse(self.scanner._is_version_compatible("99.0.0"))


class TestBuildPluginFingerprint(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_nonexistent_dir(self):
        d = MagicMock(spec=Path)
        d.exists.return_value = False
        self.assertEqual(self.scanner.build_plugin_fingerprint(d), "")

    def test_not_a_dir(self):
        d = MagicMock(spec=Path)
        d.exists.return_value = True
        d.is_dir.return_value = False
        self.assertEqual(self.scanner.build_plugin_fingerprint(d), "")


class TestScan(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_no_directory(self):
        self.scanner.plugins_dir = MagicMock(spec=Path)
        self.scanner.plugins_dir.exists.return_value = False
        self.assertEqual(self.scanner.scan(), [])

    def test_permission_error(self):
        self.scanner.plugins_dir = MagicMock(spec=Path)
        self.scanner.plugins_dir.exists.return_value = True
        self.scanner.plugins_dir.iterdir.side_effect = PermissionError("denied")
        self.assertEqual(self.scanner.scan(), [])


class TestCollectSnapshots(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_empty(self):
        with patch.object(self.scanner, 'scan', return_value=[]):
            result = self.scanner.collect_snapshots()
            self.assertEqual(result, {})


class TestDetectChangedPlugins(unittest.TestCase):
    @patch("core.plugins.scanner.Path.mkdir")
    def setUp(self, mock_mkdir):
        from core.plugins.scanner import PluginScanner
        self.scanner = PluginScanner(Path("/tmp/test_plugins"))

    def test_no_changes(self):
        with patch.object(self.scanner, 'scan', return_value=[]):
            with patch.object(self.scanner, 'collect_snapshots', return_value={}):
                result = self.scanner.detect_changed_plugins({})
                self.assertEqual(result, [])

    def test_removed_plugin(self):
        with patch.object(self.scanner, 'scan', return_value=[]):
            with patch.object(self.scanner, 'collect_snapshots', return_value={}):
                result = self.scanner.detect_changed_plugins({"old-plugin": "abc123"})
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].plugin_id, "old-plugin")


class TestPluginChangeSet(unittest.TestCase):
    def test_dataclass(self):
        from core.plugins.scanner import PluginChangeSet
        cs = PluginChangeSet(plugin_id="x", fingerprint_before="a", fingerprint_after="b")
        self.assertEqual(cs.plugin_id, "x")
        self.assertEqual(cs.changed_files, ())


if __name__ == "__main__":
    unittest.main()
