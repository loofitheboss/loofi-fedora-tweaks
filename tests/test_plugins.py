from pathlib import Path

from utils.plugin_base import PluginLoader


def _write_plugin(dir_path: Path, name: str, manifest: dict, code: str):
    plugin_dir = dir_path / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        __import__("json").dumps(manifest, indent=2)
    )
    (plugin_dir / "plugin.py").write_text(code)


def test_plugin_manifest_and_enable_disable(tmp_path):
    plugins_dir = tmp_path / "plugins"
    config_dir = tmp_path / "config"

    loader = PluginLoader()
    loader.PLUGINS_DIR = plugins_dir
    loader.CONFIG_DIR = config_dir
    loader.STATE_FILE = config_dir / "plugins.json"
    loader._ensure_plugins_dir()
    loader._ensure_state()

    manifest = {
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Tester",
        "description": "A test plugin",
        "entry": "plugin.py",
        "min_app_version": "11.0.0",
    }
    code = """
from utils.plugin_base import LoofiPlugin, PluginInfo

class TestPlugin(LoofiPlugin):
    @property
    def info(self):
        return PluginInfo(name="Test Plugin", version="1.0.0", author="Tester", description="A test")
    def create_widget(self):
        return None
    def get_cli_commands(self):
        return {}
"""
    _write_plugin(plugins_dir, "test_plugin", manifest, code)

    plugins = loader.list_plugins()
    assert plugins[0]["enabled"] is True

    loader.set_enabled("test_plugin", False)
    assert loader.is_enabled("test_plugin") is False
    assert loader.load_plugin("test_plugin") is None


def test_plugin_min_version_blocks_load(tmp_path):
    plugins_dir = tmp_path / "plugins"
    config_dir = tmp_path / "config"

    loader = PluginLoader()
    loader.PLUGINS_DIR = plugins_dir
    loader.CONFIG_DIR = config_dir
    loader.STATE_FILE = config_dir / "plugins.json"
    loader._ensure_plugins_dir()
    loader._ensure_state()

    manifest = {
        "name": "Future Plugin",
        "version": "1.0.0",
        "author": "Tester",
        "description": "Requires newer app",
        "entry": "plugin.py",
        "min_app_version": "99.0.0",
    }
    code = """
from utils.plugin_base import LoofiPlugin, PluginInfo

class FuturePlugin(LoofiPlugin):
    @property
    def info(self):
        return PluginInfo(name="Future Plugin", version="1.0.0", author="Tester", description="A test")
    def create_widget(self):
        return None
    def get_cli_commands(self):
        return {}
"""
    _write_plugin(plugins_dir, "future_plugin", manifest, code)

    # Manifest min_app_version should block loading
    assert loader.load_plugin("future_plugin") is None
