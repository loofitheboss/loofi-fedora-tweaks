"""Deep tests for utils/plugin_base.py — PluginLoader, permissions, updates, manifest."""

import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.plugin_base import (
    VALID_PERMISSIONS,
    LoofiPlugin,
    PluginInfo,
    PluginLoader,
    PluginManifest,
)


class TestPluginInfo(unittest.TestCase):
    def test_defaults(self):
        info = PluginInfo(name="x", version="1.0", author="a", description="d")
        self.assertEqual(info.icon, "🔌")

    def test_custom_icon(self):
        info = PluginInfo(name="x", version="1.0", author="a", description="d", icon="🔥")
        self.assertEqual(info.icon, "🔥")


class TestPluginManifest(unittest.TestCase):
    def test_defaults(self):
        m = PluginManifest(name="x", version="1.0", author="a", description="d")
        self.assertIsNone(m.entry)
        self.assertIsNone(m.min_app_version)
        self.assertEqual(m.permissions, [])
        self.assertEqual(m.update_url, "")

    def test_custom(self):
        m = PluginManifest(
            name="test", version="2.0", author="me", description="d",
            entry="main.py", permissions=["network"]
        )
        self.assertEqual(m.entry, "main.py")
        self.assertEqual(m.permissions, ["network"])


class TestPluginLoaderInit(unittest.TestCase):
    def test_init_creates_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            plugins_dir = Path(td) / "plugins"
            config_dir = Path(td) / "config"
            state_file = config_dir / "plugins.json"
            with patch.object(PluginLoader, 'PLUGINS_DIR', plugins_dir):
                with patch.object(PluginLoader, 'CONFIG_DIR', config_dir):
                    with patch.object(PluginLoader, 'STATE_FILE', state_file):
                        loader = PluginLoader()
                        self.assertTrue(plugins_dir.exists())
                        self.assertTrue(state_file.exists())
                        init_file = plugins_dir / "__init__.py"
                        self.assertTrue(init_file.exists())


class TestPluginLoaderState(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.td.name) / "plugins"
        self.config_dir = Path(self.td.name) / "config"
        self.state_file = self.config_dir / "plugins.json"
        self.patches = [
            patch.object(PluginLoader, 'PLUGINS_DIR', self.plugins_dir),
            patch.object(PluginLoader, 'CONFIG_DIR', self.config_dir),
            patch.object(PluginLoader, 'STATE_FILE', self.state_file),
        ]
        for p in self.patches:
            p.start()
        self.loader = PluginLoader()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def test_load_state_default(self):
        state = self.loader._load_state()
        self.assertIn("enabled", state)

    def test_save_and_load_state(self):
        state = {"enabled": {"test-plugin": False}}
        self.loader._save_state(state)
        loaded = self.loader._load_state()
        self.assertFalse(loaded["enabled"]["test-plugin"])

    def test_load_state_corrupt(self):
        self.state_file.write_text("not json")
        state = self.loader._load_state()
        self.assertEqual(state, {"enabled": {}})

    def test_set_enabled(self):
        self.loader.set_enabled("myplugin", False)
        self.assertFalse(self.loader.is_enabled("myplugin"))

    def test_set_enabled_true(self):
        self.loader.set_enabled("myplugin", False)
        self.loader.set_enabled("myplugin", True)
        self.assertTrue(self.loader.is_enabled("myplugin"))

    def test_is_enabled_default(self):
        self.assertTrue(self.loader.is_enabled("unknown-plugin"))

    def test_parse_version(self):
        self.assertEqual(self.loader._parse_version("1.2.3"), (1, 2, 3))
        self.assertEqual(self.loader._parse_version("10.0.0"), (10, 0, 0))
        self.assertEqual(self.loader._parse_version("1.2.beta"), (1, 2, 0))

    def test_is_version_compatible_none(self):
        self.assertTrue(self.loader._is_version_compatible(None))

    @patch("utils.plugin_base.APP_VERSION", "5.0.0")
    def test_is_version_compatible_newer(self):
        self.assertTrue(self.loader._is_version_compatible("3.0.0"))

    @patch("utils.plugin_base.APP_VERSION", "1.0.0")
    def test_is_version_incompatible(self):
        self.assertFalse(self.loader._is_version_compatible("99.0.0"))


class TestPluginLoaderManifest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.td.name) / "plugins"
        self.config_dir = Path(self.td.name) / "config"
        self.state_file = self.config_dir / "plugins.json"
        self.patches = [
            patch.object(PluginLoader, 'PLUGINS_DIR', self.plugins_dir),
            patch.object(PluginLoader, 'CONFIG_DIR', self.config_dir),
            patch.object(PluginLoader, 'STATE_FILE', self.state_file),
        ]
        for p in self.patches:
            p.start()
        self.loader = PluginLoader()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def test_load_manifest_no_file(self):
        plugin_dir = self.plugins_dir / "nomanifest"
        plugin_dir.mkdir(parents=True)
        self.assertIsNone(self.loader._load_manifest(plugin_dir))

    def test_load_manifest_valid(self):
        plugin_dir = self.plugins_dir / "valid"
        plugin_dir.mkdir(parents=True)
        manifest = {
            "name": "Valid", "version": "1.0.0", "author": "Dev",
            "description": "Test plugin"
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
        with patch("utils.plugin_base.APP_VERSION", "99.0.0"):
            result = self.loader._load_manifest(plugin_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "Valid")

    def test_load_manifest_invalid_json(self):
        plugin_dir = self.plugins_dir / "badjson"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text("{{bad")
        self.assertIsNone(self.loader._load_manifest(plugin_dir))

    @patch("utils.plugin_base.APP_VERSION", "1.0.0")
    def test_load_manifest_incompatible_version(self):
        plugin_dir = self.plugins_dir / "toonew"
        plugin_dir.mkdir(parents=True)
        manifest = {
            "name": "TooNew", "version": "1.0.0", "author": "Dev",
            "description": "Needs future app", "min_app_version": "999.0.0"
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
        self.assertIsNone(self.loader._load_manifest(plugin_dir))


class TestPluginLoaderDiscover(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.td.name) / "plugins"
        self.config_dir = Path(self.td.name) / "config"
        self.state_file = self.config_dir / "plugins.json"
        self.patches = [
            patch.object(PluginLoader, 'PLUGINS_DIR', self.plugins_dir),
            patch.object(PluginLoader, 'CONFIG_DIR', self.config_dir),
            patch.object(PluginLoader, 'STATE_FILE', self.state_file),
        ]
        for p in self.patches:
            p.start()
        self.loader = PluginLoader()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def test_no_plugins(self):
        self.assertEqual(self.loader.discover_plugins(), [])

    def test_discover_plugin_py(self):
        pd = self.plugins_dir / "myplugin"
        pd.mkdir()
        (pd / "plugin.py").write_text("# plugin")
        found = self.loader.discover_plugins()
        self.assertIn("myplugin", found)

    def test_discover_init_py(self):
        pd = self.plugins_dir / "initplugin"
        pd.mkdir()
        (pd / "__init__.py").write_text("# plugin")
        found = self.loader.discover_plugins()
        self.assertIn("initplugin", found)

    def test_skip_underscore(self):
        pd = self.plugins_dir / "_internal"
        pd.mkdir()
        (pd / "plugin.py").write_text("# hidden")
        found = self.loader.discover_plugins()
        self.assertNotIn("_internal", found)

    def test_skip_no_entry(self):
        pd = self.plugins_dir / "noplugin"
        pd.mkdir()
        (pd / "readme.txt").write_text("just a readme")
        found = self.loader.discover_plugins()
        self.assertNotIn("noplugin", found)


class TestPluginLoaderLoadPlugin(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.td.name) / "plugins"
        self.config_dir = Path(self.td.name) / "config"
        self.state_file = self.config_dir / "plugins.json"
        self.patches = [
            patch.object(PluginLoader, 'PLUGINS_DIR', self.plugins_dir),
            patch.object(PluginLoader, 'CONFIG_DIR', self.config_dir),
            patch.object(PluginLoader, 'STATE_FILE', self.state_file),
        ]
        for p in self.patches:
            p.start()
        self.loader = PluginLoader()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def test_nonexistent(self):
        self.assertIsNone(self.loader.load_plugin("nonexistent"))

    def test_disabled_plugin(self):
        pd = self.plugins_dir / "disabled"
        pd.mkdir()
        (pd / "plugin.py").write_text("# disabled")
        self.loader.set_enabled("disabled", False)
        self.assertIsNone(self.loader.load_plugin("disabled"))

    def test_no_entry_file(self):
        pd = self.plugins_dir / "noentry"
        pd.mkdir()
        self.assertIsNone(self.loader.load_plugin("noentry"))


class TestPluginLoaderUnload(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.td.name) / "plugins"
        self.config_dir = Path(self.td.name) / "config"
        self.state_file = self.config_dir / "plugins.json"
        self.patches = [
            patch.object(PluginLoader, 'PLUGINS_DIR', self.plugins_dir),
            patch.object(PluginLoader, 'CONFIG_DIR', self.config_dir),
            patch.object(PluginLoader, 'STATE_FILE', self.state_file),
        ]
        for p in self.patches:
            p.start()
        self.loader = PluginLoader()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def test_unload_loaded(self):
        mock_plugin = MagicMock(spec=LoofiPlugin)
        self.loader.plugins["test"] = mock_plugin
        self.assertTrue(self.loader.unload_plugin("test"))
        mock_plugin.on_unload.assert_called_once()
        self.assertNotIn("test", self.loader.plugins)

    def test_unload_not_loaded(self):
        self.assertFalse(self.loader.unload_plugin("nope"))

    def test_unload_error(self):
        mock_plugin = MagicMock(spec=LoofiPlugin)
        mock_plugin.on_unload.side_effect = RuntimeError("cleanup fail")
        self.loader.plugins["err"] = mock_plugin
        self.assertFalse(self.loader.unload_plugin("err"))


class TestCheckPermissions(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.td.name) / "plugins"
        self.config_dir = Path(self.td.name) / "config"
        self.state_file = self.config_dir / "plugins.json"
        self.patches = [
            patch.object(PluginLoader, 'PLUGINS_DIR', self.plugins_dir),
            patch.object(PluginLoader, 'CONFIG_DIR', self.config_dir),
            patch.object(PluginLoader, 'STATE_FILE', self.state_file),
        ]
        for p in self.patches:
            p.start()
        self.loader = PluginLoader()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def test_no_manifest(self):
        pd = self.plugins_dir / "nomanifest"
        pd.mkdir()
        result = self.loader.check_permissions("nomanifest")
        self.assertEqual(result, {"granted": [], "denied": []})

    def test_valid_permissions(self):
        pd = self.plugins_dir / "perm"
        pd.mkdir()
        manifest = {
            "name": "Perm", "version": "1.0", "author": "x",
            "description": "d", "permissions": ["network", "filesystem"]
        }
        (pd / "plugin.json").write_text(json.dumps(manifest))
        with patch("utils.plugin_base.APP_VERSION", "99.0.0"):
            result = self.loader.check_permissions("perm")
            self.assertIn("network", result["granted"])
            self.assertEqual(result["denied"], [])

    def test_invalid_permissions(self):
        pd = self.plugins_dir / "badperm"
        pd.mkdir()
        manifest = {
            "name": "Bad", "version": "1.0", "author": "x",
            "description": "d", "permissions": ["network", "hack_system"]
        }
        (pd / "plugin.json").write_text(json.dumps(manifest))
        with patch("utils.plugin_base.APP_VERSION", "99.0.0"):
            result = self.loader.check_permissions("badperm")
            self.assertIn("network", result["granted"])
            self.assertIn("hack_system", result["denied"])


class TestCheckForUpdates(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.td.name) / "plugins"
        self.config_dir = Path(self.td.name) / "config"
        self.state_file = self.config_dir / "plugins.json"
        self.patches = [
            patch.object(PluginLoader, 'PLUGINS_DIR', self.plugins_dir),
            patch.object(PluginLoader, 'CONFIG_DIR', self.config_dir),
            patch.object(PluginLoader, 'STATE_FILE', self.state_file),
        ]
        for p in self.patches:
            p.start()
        self.loader = PluginLoader()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def test_no_update_url(self):
        pd = self.plugins_dir / "nourl"
        pd.mkdir()
        manifest = {"name": "No URL", "version": "1.0", "author": "x", "description": "d"}
        (pd / "plugin.json").write_text(json.dumps(manifest))
        self.loader.plugins["nourl"] = MagicMock()
        with patch("utils.plugin_base.APP_VERSION", "99.0.0"):
            results = self.loader.check_for_updates()
            self.assertEqual(results, [])

    @patch("urllib.request.urlopen")
    def test_update_available(self, mock_urlopen):
        pd = self.plugins_dir / "updatable"
        pd.mkdir()
        manifest = {
            "name": "Updatable", "version": "1.0.0", "author": "x",
            "description": "d", "update_url": "http://example.com/update.json"
        }
        (pd / "plugin.json").write_text(json.dumps(manifest))
        self.loader.plugins["updatable"] = MagicMock()

        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"version": "2.0.0"}).encode()
        mock_urlopen.return_value = mock_resp

        with patch("utils.plugin_base.APP_VERSION", "99.0.0"):
            results = self.loader.check_for_updates("updatable")
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["update_available"])
            self.assertEqual(results[0]["latest_version"], "2.0.0")

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("network fail"))
    def test_network_error(self, _):
        pd = self.plugins_dir / "failing"
        pd.mkdir()
        manifest = {
            "name": "Failing", "version": "1.0.0", "author": "x",
            "description": "d", "update_url": "http://bad.example.com"
        }
        (pd / "plugin.json").write_text(json.dumps(manifest))
        self.loader.plugins["failing"] = MagicMock()

        with patch("utils.plugin_base.APP_VERSION", "99.0.0"):
            results = self.loader.check_for_updates("failing")
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0]["update_available"])


class TestGetAllCliCommands(unittest.TestCase):
    def test_merges(self):
        td = tempfile.TemporaryDirectory()
        plugins_dir = Path(td.name) / "plugins"
        config_dir = Path(td.name) / "config"
        state_file = config_dir / "plugins.json"
        with patch.object(PluginLoader, 'PLUGINS_DIR', plugins_dir):
            with patch.object(PluginLoader, 'CONFIG_DIR', config_dir):
                with patch.object(PluginLoader, 'STATE_FILE', state_file):
                    loader = PluginLoader()
                    p1 = MagicMock()
                    p1.get_cli_commands.return_value = {"cmd1": lambda: None}
                    p2 = MagicMock()
                    p2.get_cli_commands.return_value = {"cmd2": lambda: None}
                    loader.plugins = {"a": p1, "b": p2}
                    cmds = loader.get_all_cli_commands()
                    self.assertIn("cmd1", cmds)
                    self.assertIn("cmd2", cmds)
        td.cleanup()


class TestListPlugins(unittest.TestCase):
    def test_returns_list(self):
        td = tempfile.TemporaryDirectory()
        plugins_dir = Path(td.name) / "plugins"
        config_dir = Path(td.name) / "config"
        state_file = config_dir / "plugins.json"
        with patch.object(PluginLoader, 'PLUGINS_DIR', plugins_dir):
            with patch.object(PluginLoader, 'CONFIG_DIR', config_dir):
                with patch.object(PluginLoader, 'STATE_FILE', state_file):
                    loader = PluginLoader()
                    pd = plugins_dir / "myplugin"
                    pd.mkdir()
                    (pd / "plugin.py").write_text("# plugin")
                    manifest = {"name": "My", "version": "1.0", "author": "x", "description": "d"}
                    (pd / "plugin.json").write_text(json.dumps(manifest))
                    with patch("utils.plugin_base.APP_VERSION", "99.0.0"):
                        plugins = loader.list_plugins()
                        self.assertEqual(len(plugins), 1)
                        self.assertEqual(plugins[0]["name"], "myplugin")
                        self.assertTrue(plugins[0]["enabled"])
        td.cleanup()


if __name__ == "__main__":
    unittest.main()
