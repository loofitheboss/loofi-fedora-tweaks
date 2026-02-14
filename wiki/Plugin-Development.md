# Plugin Development

Guide to developing plugins for Loofi Fedora Tweaks using the Plugin SDK.

---

## Overview

The Loofi Plugin SDK allows developers to extend Loofi Fedora Tweaks with custom tabs, CLI commands, and system integrations. Plugins are self-contained Python packages discovered automatically at startup.

### Plugin Architecture

```
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

## Quick Start

### 1. Create Plugin Directory

```bash
mkdir -p plugins/my_plugin
touch plugins/my_plugin/__init__.py
```

### 2. Write Manifest (`plugin.json`)

Every plugin must have a `plugin.json`:

```json
{
  "name": "My Plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "A short description of what your plugin does.",
  "entry": "plugin.py",
  "min_app_version": "40.0.0",
  "permissions": ["network", "notifications"],
  "update_url": "https://example.com/my-plugin/latest.json",
  "icon": "🔌"
}
```

### 3. Implement Plugin Class

Create `plugin.py` with a class extending `LoofiPlugin`:

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
            icon="🔌",
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

## Manifest Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Human-readable plugin name |
| `version` | Yes | string | Semantic version (e.g., "1.0.0") |
| `author` | Yes | string | Plugin author or team |
| `description` | Yes | string | Brief description of functionality |
| `entry` | No | string | Entry point file (defaults to "plugin.py") |
| `min_app_version` | No | string | Minimum Loofi version required |
| `permissions` | No | array | Requested permissions (see Permissions below) |
| `update_url` | No | string | URL for update checking |
| `icon` | No | string | Emoji icon for sidebar (defaults to 🔌) |

---

## LoofiPlugin Abstract Base Class

### Required Methods

#### `info` (property)
Returns `PluginInfo` with plugin metadata:

```python
@property
def info(self) -> PluginInfo:
    return PluginInfo(
        name="My Plugin",
        version="1.0.0",
        author="Your Name",
        description="Plugin description",
        icon="🔌",
    )
```

#### `create_widget()`
Returns a `QWidget` instance displayed as a tab:

```python
def create_widget(self):
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.addWidget(QLabel("My Plugin Tab"))
    return widget
```

**Tip**: Use lazy imports for PyQt6 to keep module-level imports lightweight.

#### `get_cli_commands()`
Returns dict mapping command names to callable functions:

```python
def get_cli_commands(self) -> dict:
    return {
        "greet": lambda: "Hello!",
        "status": self._check_status,
    }
```

Commands available via: `loofi-fedora-tweaks --cli <command>`

### Optional Lifecycle Hooks

#### `on_load()`
Called when plugin is loaded:

```python
def on_load(self) -> None:
    logger.info("Plugin loaded, initializing resources")
```

#### `on_unload()`
Called when plugin is unloaded:

```python
def on_unload(self) -> None:
    logger.info("Plugin unloading, cleaning up")
```

---

## Permissions Model

Plugins declare permissions in `plugin.json`:

```json
{
  "permissions": ["network", "filesystem", "sudo"]
}
```

### Available Permissions

| Permission | Description |
|------------|-------------|
| `network` | HTTP requests, sockets, network access |
| `filesystem` | Read/write local filesystem |
| `sudo` | Run privileged commands via pkexec |
| `clipboard` | Access system clipboard |
| `notifications` | Send desktop notifications |

### Permission Grant Flow

1. User installs plugin from marketplace
2. Permission dialog shows requested permissions
3. User accepts or declines
4. `PluginSandbox` enforces granted permissions at runtime

---

## Plugin Marketplace (v27.0+)

### Overview

The Plugin Marketplace enables:
- **Discovery**: Browse and search external plugins from CDN-first signed index
- **Installation**: One-click install from `.loofi-plugin` archives
- **Sandboxing**: Runtime permission enforcement
- **Integrity**: SHA256 + GPG signature verification
- **Auto-Updates**: Automatic plugin updates via daemon service
- **Trust**: Verified publisher badges, ratings, and reviews

### Publishing Your Plugin

#### 1. Develop Locally

Follow standard plugin structure and test with local `PluginLoader`.

#### 2. Add Metadata

Create `metadata.json`:

```json
{
  "publisher": "Your Name",
  "license": "MIT",
  "tags": ["backup", "automation"],
  "homepage": "https://github.com/user/plugin",
  "source": "https://github.com/user/plugin",
  "checksum": "sha256:abc123...",
  "signature": "gpg:xyz789...",
  "dependencies": ["another-plugin>=1.0.0"]
}
```

#### 3. Package Plugin

```bash
cd plugins/my-plugin
zip -r my-plugin.loofi-plugin plugin.json plugin.py metadata.json
sha256sum my-plugin.loofi-plugin > checksum.txt
```

#### 4. Sign (Optional)

```bash
gpg --detach-sign --armor my-plugin.loofi-plugin
```

#### 5. Publish to Marketplace

- Host the `.loofi-plugin` archive at a stable HTTPS URL
- Submit metadata to marketplace ingestion workflow
- Include publisher verification data

### CLI Commands

```bash
# Search marketplace
loofi-fedora-tweaks --cli plugin-marketplace search --query backup

# Install plugin
loofi-fedora-tweaks --cli plugin-marketplace install backup-manager --accept-permissions

# Update all plugins
loofi-fedora-tweaks --cli plugin-marketplace update

# View reviews
loofi-fedora-tweaks --cli plugin-marketplace reviews backup-manager --limit 10
```

---

## Update Checking

Plugins can opt into update checking by setting `update_url` in manifest:

```json
{
  "update_url": "https://example.com/my-plugin/latest.json"
}
```

The URL should return JSON with at least a `version` key:

```json
{
  "version": "1.2.0"
}
```

Check for updates:

```python
loader = PluginLoader()
loader.load_all_plugins()
updates = loader.check_for_updates()
# [{"name": "my_plugin", "current_version": "1.0.0",
#   "latest_version": "1.2.0", "update_available": True}]
```

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
```

Run tests:

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v
```

---

## Complete Example: Hello World Plugin

### `plugins/hello_world/plugin.json`

```json
{
  "name": "Hello World",
  "version": "1.0.0",
  "author": "Loofi Team",
  "description": "Example plugin demonstrating the Loofi Plugin SDK",
  "min_app_version": "40.0.0",
  "permissions": ["notifications"],
  "icon": "👋"
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
            description="Example plugin",
            icon="👋",
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
        return {
            "hello": lambda: "Hello from the Loofi Plugin SDK!"
        }

    def on_load(self) -> None:
        logger.info("Hello World plugin loaded")

    def on_unload(self) -> None:
        logger.info("Hello World plugin unloaded")
```

---

## CLI Management

Manage plugins from command line:

```bash
# List all plugins
loofi-fedora-tweaks --cli plugins list

# Enable a plugin
loofi-fedora-tweaks --cli plugins enable my_plugin

# Disable a plugin
loofi-fedora-tweaks --cli plugins disable my_plugin

# Check for updates
loofi-fedora-tweaks --cli plugins update
```

---

## Security Considerations

1. **Request only necessary permissions** — Users are shown permission requests
2. **Validate all inputs** — Don't trust user input or external data
3. **Use PluginSandbox** — For permission-checked file/network operations
4. **Code review** — Review plugin source before installation
5. **Signature verification** — Enable GPG signature checking for production

---

## Next Steps

- [Architecture](Architecture) — Understand layer rules and patterns
- [Security Model](Security-Model) — Learn about privilege escalation
- [CLI Reference](CLI-Reference) — Plugin CLI command integration
- [Contributing](Contributing) — Submit plugins to marketplace
