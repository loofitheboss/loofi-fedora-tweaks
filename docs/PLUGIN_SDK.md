# Loofi Fedora Tweaks Plugin SDK

## Overview

The Loofi Plugin SDK allows developers to extend Loofi Fedora Tweaks with custom
tabs, CLI commands, and system integrations. Plugins are self-contained Python
packages that live in the `plugins/` directory and are discovered automatically
at startup.

### Architecture

```
loofi-fedora-tweaks/
  plugins/
    my_plugin/
      __init__.py        # Can be empty
      plugin.json        # Manifest (required)
      plugin.py          # Entry point with LoofiPlugin subclass
```

Each plugin:
- Declares metadata and requirements in `plugin.json`
- Implements the `LoofiPlugin` abstract base class
- Can provide a PyQt6 widget (displayed as a tab) and/or CLI commands
- Is loaded dynamically by the `PluginLoader` at runtime
- Can be enabled or disabled without restarting the application

---

## Getting Started

### 1. Create the Plugin Directory

Create a new directory under `loofi-fedora-tweaks/plugins/`:

```bash
mkdir -p plugins/my_plugin
touch plugins/my_plugin/__init__.py
```

### 2. Write the Manifest (`plugin.json`)

Every plugin must have a `plugin.json` in its root directory:

```json
{
    "name": "My Plugin",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "A short description of what your plugin does.",
    "entry": "plugin.py",
    "min_app_version": "13.0.0",
    "permissions": ["network", "notifications"],
    "update_url": "https://example.com/my-plugin/latest.json",
    "icon": "\ud83d\udd0c"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable plugin name |
| `version` | Yes | Semantic version string (e.g., `"1.0.0"`) |
| `author` | Yes | Plugin author or team |
| `description` | Yes | Brief description of plugin functionality |
| `entry` | No | Entry point file (defaults to `plugin.py`) |
| `min_app_version` | No | Minimum Loofi version required (blocks loading if unmet) |
| `permissions` | No | List of permissions the plugin requests (see Permissions below) |
| `update_url` | No | URL returning JSON with a `"version"` key for update checking |
| `icon` | No | Emoji icon for sidebar display (defaults to plug emoji) |

### 3. Implement the Plugin Class

Create `plugin.py` with a class that extends `LoofiPlugin`:

```python
from utils.plugin_base import LoofiPlugin, PluginInfo


class MyPlugin(LoofiPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="My Plugin",
            version="1.0.0",
            author="Your Name",
            description="What this plugin does.",
            icon="\ud83d\udd0c",
        )

    def create_widget(self):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Hello from My Plugin!"))
        return widget

    def get_cli_commands(self) -> dict:
        return {
            "my-command": lambda: "Output from my command",
        }

    def on_load(self) -> None:
        pass  # Initialization logic

    def on_unload(self) -> None:
        pass  # Cleanup logic
```

---

## Implementing LoofiPlugin

### Required: `info` Property

Return a `PluginInfo` dataclass with your plugin's metadata. This is used
by the plugin manager UI and CLI.

### Required: `create_widget()`

Return a `QWidget` instance that will be displayed as a tab in the main
window. Use lazy imports for PyQt6 to keep module-level imports lightweight:

```python
def create_widget(self):
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.addWidget(QLabel("My Plugin Tab"))
    return widget
```

### Required: `get_cli_commands()`

Return a dictionary mapping command names (strings) to callable functions.
Each function should return a string result:

```python
def get_cli_commands(self) -> dict:
    return {
        "greet": lambda: "Hello!",
        "status": self._check_status,
    }
```

Commands are available via: `loofi <command-name>`

### Optional: `on_load()` / `on_unload()`

These lifecycle hooks are called when the plugin is loaded or unloaded.
Use them for initialization and cleanup:

```python
def on_load(self) -> None:
    logger.info("Plugin loaded, initializing resources")

def on_unload(self) -> None:
    logger.info("Plugin unloading, cleaning up")
```

---

## Permissions Model

Plugins declare the permissions they need in `plugin.json`. The app validates
these against the set of recognized permissions. Unrecognized permissions are
flagged as denied.

| Permission | Description |
|------------|-------------|
| `network` | Access to network resources (HTTP requests, sockets) |
| `filesystem` | Read/write access to the local filesystem |
| `sudo` | Ability to run privileged commands via pkexec/sudo |
| `clipboard` | Access to the system clipboard |
| `notifications` | Ability to send desktop notifications |

### How Permissions Work

When a plugin is loaded, `PluginLoader.check_permissions(plugin_name)` returns:

```python
{
    "granted": ["network", "notifications"],  # Valid, recognized permissions
    "denied": ["custom_perm"]                  # Unrecognized permissions
}
```

Only permissions listed in `VALID_PERMISSIONS` are granted. Any permission
string not in the set is reported as denied. This allows the application to
warn users when plugins request unrecognized capabilities.

---

## Update Checking

Plugins can opt into update checking by setting `update_url` in their manifest.
The URL should return JSON with at least a `"version"` key:

```json
{
    "version": "1.2.0"
}
```

The `PluginLoader.check_for_updates()` method fetches each plugin's update
URL and compares the remote version against the installed version using
semantic version comparison:

```python
loader = PluginLoader()
loader.load_all_plugins()
updates = loader.check_for_updates()
# [{"name": "my_plugin", "current_version": "1.0.0",
#   "latest_version": "1.2.0", "update_available": True}]
```

To check a single plugin: `loader.check_for_updates("my_plugin")`

---

## Testing Your Plugin

Write tests that validate your plugin without requiring a display server:

```python
import unittest
import importlib.util
from utils.plugin_base import LoofiPlugin, PluginInfo

class TestMyPlugin(unittest.TestCase):
    def _load_class(self):
        spec = importlib.util.spec_from_file_location(
            "plugins.my_plugin",
            "plugins/my_plugin/plugin.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.MyPlugin

    def test_instantiation(self):
        plugin = self._load_class()()
        self.assertIsInstance(plugin, LoofiPlugin)

    def test_info_fields(self):
        info = self._load_class()().info
        self.assertIsInstance(info, PluginInfo)
        self.assertTrue(len(info.name) > 0)

    def test_cli_commands(self):
        cmds = self._load_class()().get_cli_commands()
        self.assertIsInstance(cmds, dict)
        for func in cmds.values():
            self.assertTrue(callable(func))

    def test_lifecycle(self):
        plugin = self._load_class()()
        plugin.on_load()
        plugin.on_unload()
```

Run tests with: `python -m pytest tests/ -v`

---

## Complete Example: Hello World Plugin

### `plugins/hello_world/plugin.json`

```json
{
    "name": "Hello World",
    "version": "1.0.0",
    "author": "Loofi Team",
    "description": "Example plugin demonstrating the Loofi Plugin SDK",
    "min_app_version": "13.0.0",
    "permissions": ["notifications"],
    "update_url": ""
}
```

### `plugins/hello_world/plugin.py`

```python
import logging
from utils.plugin_base import LoofiPlugin, PluginInfo

logger = logging.getLogger("loofi.plugins.hello_world")


class HelloWorldPlugin(LoofiPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="Hello World",
            version="1.0.0",
            author="Loofi Team",
            description="Example plugin demonstrating the Loofi Plugin SDK",
            icon="\U0001f44b",
        )

    def create_widget(self):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel("Hello from the Loofi Plugin SDK!")
        layout.addWidget(label)
        button = QPushButton("Say Hello")
        button.clicked.connect(lambda: label.setText("Hello World!"))
        layout.addWidget(button)
        layout.addStretch()
        return widget

    def get_cli_commands(self) -> dict:
        return {"hello": lambda: "Hello from the Loofi Plugin SDK!"}

    def on_load(self) -> None:
        logger.info("Hello World plugin loaded")

    def on_unload(self) -> None:
        logger.info("Hello World plugin unloaded")
```

---

## Publishing Your Plugin

> This section is a placeholder. A plugin registry and distribution mechanism
> will be available in a future release.

For now, plugins can be shared by distributing the plugin directory as a
tarball or zip archive. Users install by extracting into `plugins/`.

---

## CLI Management

Manage plugins from the command line:

```bash
loofi plugins list               # List all discovered plugins
loofi plugins enable my_plugin   # Enable a plugin
loofi plugins disable my_plugin  # Disable a plugin
```

---

## API Reference

### `PluginInfo` (dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | -- | Plugin display name |
| `version` | `str` | -- | Plugin version |
| `author` | `str` | -- | Author name |
| `description` | `str` | -- | Brief description |
| `icon` | `str` | `"\ud83d\udd0c"` | Emoji icon |

### `PluginManifest` (dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | -- | Plugin name |
| `version` | `str` | -- | Plugin version |
| `author` | `str` | -- | Author name |
| `description` | `str` | -- | Description |
| `entry` | `str \| None` | `None` | Entry point file |
| `min_app_version` | `str \| None` | `None` | Minimum app version |
| `permissions` | `list[str]` | `[]` | Requested permissions |
| `update_url` | `str` | `""` | URL for update checking |
| `icon` | `str` | `"\ud83d\udd0c"` | Emoji icon |

### `LoofiPlugin` (abstract base class)

| Member | Type | Description |
|--------|------|-------------|
| `info` | property | Returns `PluginInfo` |
| `create_widget()` | method | Returns a `QWidget` for the tab |
| `get_cli_commands()` | method | Returns `dict[str, callable]` |
| `on_load()` | method | Called on plugin load |
| `on_unload()` | method | Called on plugin unload |

### `PluginLoader`

| Method | Returns | Description |
|--------|---------|-------------|
| `discover_plugins()` | `list[str]` | List plugin directory names |
| `load_plugin(name)` | `LoofiPlugin \| None` | Load a single plugin |
| `load_all_plugins()` | `dict[str, LoofiPlugin]` | Load all discovered plugins |
| `unload_plugin(name)` | `bool` | Unload a plugin |
| `list_plugins()` | `list[dict]` | List plugins with manifest data |
| `set_enabled(name, bool)` | `None` | Enable or disable a plugin |
| `is_enabled(name)` | `bool` | Check if plugin is enabled |
| `check_permissions(name)` | `dict` | Check granted/denied permissions |
| `check_for_updates(name?)` | `list[dict]` | Check for available updates |
| `get_all_cli_commands()` | `dict[str, callable]` | Merged CLI commands from all plugins |

### `VALID_PERMISSIONS` (module-level set)

```python
{"network", "filesystem", "sudo", "clipboard", "notifications"}
```
