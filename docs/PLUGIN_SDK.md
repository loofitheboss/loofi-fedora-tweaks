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
    "min_app_version": "15.0.0",
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

### Optional: Quick Actions (v15.0)

Plugins can register custom actions in the Quick Actions Bar (`Ctrl+Shift+K`):

```python
def on_load(self) -> None:
    from ui.quick_actions import QuickActionRegistry, QuickAction
    
    registry = QuickActionRegistry()
    registry.register(QuickAction(
        name="My Plugin Action",
        description="Run my plugin's main feature",
        category="My Plugin",
        callback=self._run_feature,
        icon="🔧"
    ))
```

Actions appear in the Quick Actions palette alongside built-in actions and support fuzzy search.

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
    "min_app_version": "15.0.0",
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

---

## Plugin Marketplace (v27.0+)

### Overview

The Plugin Marketplace enables:
- **Discovery**: Browse and search external plugins from a CDN-first signed index
- **Installation**: One-click install from `.loofi-plugin` archives
- **Sandboxing**: Runtime permission enforcement for installed plugins
- **Integrity**: SHA256 + GPG signature verification
- **Auto-Updates**: Automatic plugin updates via daemon service
- **Dependencies**: Automatic resolution of plugin dependencies
- **Trust + Quality**: Verified publisher badges plus ratings/reviews support

### Marketplace Architecture

```
PluginCDNClient → PluginMarketplaceAPI (fallback-aware) → PluginInstaller → PluginSandbox → PluginLoader
```

Plugin lifecycle:
1. Fetch signed marketplace index from CDN (with local cache + fallback provider)
2. Download `.loofi-plugin` archive
3. Verify integrity (SHA256, optional GPG)
4. Extract to `plugins/`
5. Scan and register plugin
6. Load with sandboxed permissions

### CLI Commands

```bash
# Search marketplace
loofi-fedora-tweaks --cli plugin-marketplace search --query backup

# Get plugin details
loofi-fedora-tweaks --cli plugin-marketplace info backup-manager

# Install plugin
loofi-fedora-tweaks --cli plugin-marketplace install backup-manager --accept-permissions

# Update all plugins
loofi-fedora-tweaks --cli plugin-marketplace update

# Uninstall plugin
loofi-fedora-tweaks --cli plugin-marketplace uninstall backup-manager

# Ratings/reviews
loofi-fedora-tweaks --cli plugin-marketplace reviews backup-manager --limit 10
loofi-fedora-tweaks --cli plugin-marketplace review-submit backup-manager --reviewer "alice" --rating 5 --title "Great" --comment "Stable and useful"
loofi-fedora-tweaks --cli plugin-marketplace rating backup-manager
```

### Marketplace UI

Access via **Community Tab** → **Marketplace** section:
- **Browse**: Grid view of available plugins
- **Search**: Filter by name, description, or tags
- **Install**: One-click install with permission consent dialog
- **Details**: View plugin info, permissions, dependencies, reviews, and verified publisher badge

### Plugin Package Format

External plugins are distributed as `.loofi-plugin` archives:

```
my-plugin.loofi-plugin (ZIP archive)
├── plugin.json         # Manifest
├── plugin.py           # Entry point
├── metadata.json       # Package metadata (publisher, license, tags)
├── checksum.txt        # SHA256 hash
└── signature.asc       # Optional GPG signature
```

**metadata.json** structure:
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

### Creating Marketplace Plugins

1. **Develop Locally**
   - Follow standard plugin structure
   - Test with local PluginLoader

2. **Add Metadata**
   - Create `metadata.json` with package info
   - Add dependencies if needed

3. **Package Plugin**
   ```bash
   cd plugins/my-plugin
   zip -r my-plugin.loofi-plugin plugin.json plugin.py metadata.json
   sha256sum my-plugin.loofi-plugin > checksum.txt
   ```

4. **Sign (Optional)**
   ```bash
   gpg --detach-sign --armor my-plugin.loofi-plugin
   ```

5. **Publish to Marketplace**
   - Host the `.loofi-plugin` archive at a stable HTTPS URL
   - Submit metadata to the marketplace ingestion workflow with publisher verification data
   - Include index-ready fields: `name`, `version`, `download_url`, checksum/signature metadata

### Permission Sandboxing

Plugins request permissions in `plugin.json`:

```json
{
    "permissions": ["filesystem", "network"]
}
```

**Available Permissions:**
- `filesystem`: Read/write user files
- `network`: HTTP/HTTPS requests
- `sudo`: Privileged operations (pkexec)
- `clipboard`: Access clipboard data
- `notifications`: Send desktop notifications

**Permission Grant Flow:**
1. User installs plugin from marketplace
2. Permission dialog shows requested permissions
3. User accepts or declines
4. PluginSandbox enforces granted permissions at runtime

**Permission Enforcement:**
- File operations wrapped via `PluginSandbox.safe_write()`
- Network requests proxied through `PluginSandbox.safe_request()`
- Privileged commands validated before execution

### Dependency Resolution

If a plugin depends on other plugins:

```json
{
    "dependencies": ["logger>=1.0.0", "utils>=2.1.0"]
}
```

`PluginDependencyResolver` will:
1. Parse dependency specifications
2. Check installed versions
3. Install missing dependencies from marketplace
4. Verify version constraints
5. Load plugins in dependency order

### Auto-Update Service

Enable auto-updates in **Settings** → **Plugins** → **Auto-Update**:

```bash
# Manual check for updates
loofi-fedora-tweaks --cli plugin-marketplace update

# Daemon mode (runs background update service)
loofi-fedora-tweaks --daemon
```

The updater checks for new versions daily and notifies the user.

### API Reference

#### `PluginMarketplaceAPI`

```python
from utils.plugin_marketplace import PluginMarketplaceAPI

api = PluginMarketplaceAPI()
plugins = api.search_plugins("backup")  # Returns list[PluginPackage]
details = api.get_plugin_details("backup-manager")  # Returns PluginPackage
```

#### `PluginInstaller`

```python
from utils.plugin_installer import PluginInstaller

installer = PluginInstaller()
installer.install_plugin("backup-manager", verify_signature=True)
installer.uninstall_plugin("backup-manager")
```

#### `PluginSandbox`

```python
from core.plugins.sandbox import PluginSandbox

sandbox = PluginSandbox.for_plugin("my-plugin", ["filesystem", "network"])
sandbox.safe_write("/path/to/file", "content")  # Permission-checked
```

#### `PluginDependencyResolver`

```python
from core.plugins.resolver import PluginDependencyResolver

resolver = PluginDependencyResolver()
order = resolver.resolve_dependencies(["plugin-a", "plugin-b"])
```

### Testing Marketplace Plugins

All marketplace functionality is covered by unit tests:

```bash
# Run marketplace test suite
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_plugin_marketplace.py -v

# Run full plugin test suite
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_plugin_*.py -v
```

### Security Considerations

1. **Integrity Verification**: Always enable signature verification for production
2. **Permission Minimization**: Request only necessary permissions
3. **Code Review**: Review plugin source before installation
4. **Sandboxing**: Permissions are enforced at runtime, but Python sandbox limitations apply
5. **Updates**: Keep plugins updated via auto-update service

---
