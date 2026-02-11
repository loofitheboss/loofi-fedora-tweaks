# Release Notes — Loofi Fedora Tweaks v25.0.0

> **Codename**: Plugin Architecture + UI Redesign
> **Release date**: TBD
> **Status**: DRAFT (pre-documentation, P5 phase)

---

## What's New

### Plugin-Based Tab Architecture

Loofi Fedora Tweaks v25.0 transforms the internal tab system from a hardcoded list into a modular plugin architecture. Every tab is now a self-describing plugin that declares its own name, category, icon, badge, and display order. This makes the application significantly more maintainable and lays the foundation for user-installable plugins in a future release.

From a user perspective, the application looks and works the same — all 26 tabs are present, in the same order, with the same categories. The change is architectural: the sidebar is now dynamically built from the plugin registry rather than from a hardcoded list.

### Compatibility-Aware Feature Gating

Tabs can now declare compatibility requirements and the application will check them at startup. If a feature requires a minimum Fedora version, a specific desktop environment, or packages that are not installed, the tab will appear in the sidebar as grayed-out with a tooltip explaining why it is unavailable. Previously, incompatible features would appear but fail silently or show errors.

Supported compatibility checks:
- Minimum Fedora version (e.g., requires Fedora 38+)
- Desktop environment (e.g., GNOME-only or KDE-only features)
- Wayland or X11 session requirement
- Required RPM packages

### Sidebar Improvements

- Incompatible tabs now render as visually disabled items with an explanatory tooltip
- Disabled tabs show a clear "not available" message in the content area instead of a broken UI
- Tab ordering is now governed by metadata rather than insertion order, making future reordering straightforward

---

## Breaking Changes

### For End Users

None. All tabs, keyboard shortcuts, search, and navigation work identically to v24.0.

### For Developers and Plugin Authors

The `_TAB_META` dict in `ui/main_window.py` has been removed. Tab metadata now lives in each tab's `PluginMetadata` class attribute.

The `_lazy_tab()` private method in `MainWindow` has been removed. Tab instantiation is now handled by `PluginLoader`.

The `SettingsTab.__init__` signature changes: `main_window` argument is deprecated. Inject context via `set_context()` instead. The old signature is still accepted for backward compatibility but will be removed in a future version.

---

## Plugin Developer Guide

### Overview

Every tab in Loofi Fedora Tweaks is a plugin that implements `PluginInterface`. If you are building a new tab or extending an existing one, this is the API you need.

### Minimum Implementation

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata, CompatStatus

class MyFeatureTab(QWidget, PluginInterface):
    """Example plugin tab."""

    _METADATA = PluginMetadata(
        id="my_feature",          # unique slug — never change after release
        name="My Feature",        # display name in sidebar
        description="Does something useful",
        category="Tools",         # sidebar category group
        icon="🔧",                # emoji shown in sidebar
        badge="",                 # "recommended", "advanced", or ""
        version="1.0.0",
        order=50,                 # sort position within category (lower = higher)
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello from My Feature!"))
```

### Declaring Compatibility Requirements

Override `check_compat()` to gate your plugin on system properties:

```python
def check_compat(self, detector) -> CompatStatus:
    # Use detector to check system state
    if detector.fedora_version() < 39:
        return CompatStatus(
            compatible=False,
            reason="My Feature requires Fedora 39 or later"
        )
    return CompatStatus(compatible=True)
```

Or use the declarative `compat` dict in `PluginMetadata` for simple checks:

```python
_METADATA = PluginMetadata(
    id="wayland_tool",
    ...
    compat={
        "min_fedora": 39,
        "de": ["gnome", "kde"],
        "wayland_only": True,
        "requires_packages": ["some-package"],
    }
)
```

The `compat` dict is checked automatically by `CompatibilityDetector.check_plugin_compat()`. The `check_compat()` method override gives you full programmatic control when the declarative dict is insufficient.

### Lifecycle Hooks

```python
def on_activate(self) -> None:
    """Called when your tab becomes the active page. Start timers here."""
    self._start_refresh_timer()

def on_deactivate(self) -> None:
    """Called when the user navigates away. Stop timers here."""
    self._stop_refresh_timer()
```

### Accessing Application Context

If your tab needs a reference to `MainWindow`, `ConfigManager`, or `ActionExecutor`:

```python
def set_context(self, context: dict) -> None:
    self._main_window = context.get("main_window")
    self._executor = context.get("executor")
    # Safe to initialize UI that depends on these references
    self._init_ui()
```

`set_context()` is called by `PluginLoader` immediately after instantiation, before the widget is shown. Do not access `self._main_window` in `__init__` — use `set_context()` instead.

### PluginMetadata Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | Yes | Unique slug. Never change after release — used as storage key. |
| `name` | str | Yes | Display name in sidebar and breadcrumb. |
| `description` | str | Yes | Tooltip text and breadcrumb subtitle. |
| `category` | str | Yes | Sidebar category group. Use an existing category or create a new one. |
| `icon` | str | Yes | Unicode emoji displayed before name in sidebar. |
| `badge` | str | No | `"recommended"`, `"advanced"`, or `""` (default). |
| `version` | str | No | Plugin version string (default `"1.0.0"`). |
| `requires` | tuple[str] | No | IDs of plugins that must be loaded first. |
| `compat` | dict | No | Declarative compatibility spec (see above). |
| `order` | int | No | Sort position within category. Lower = higher. Default 100. |
| `enabled` | bool | No | Default enabled state. Default True. |

### Registering a Built-in Plugin

Built-in plugins are listed in `core/plugins/loader.py` in the `_BUILTIN_PLUGINS` list:

```python
_BUILTIN_PLUGINS = [
    ...
    ("ui.my_feature_tab", "MyFeatureTab"),
]
```

Add your entry in the desired position within the list. The `order` field in `PluginMetadata` controls final sort position within the category; the list position sets the initial category ordering.

### Testing Your Plugin

```python
from core.plugins.registry import PluginRegistry
from core.plugins.compat import CompatibilityDetector

def test_my_feature_metadata():
    registry = PluginRegistry()
    plugin = MyFeatureTab()
    registry.register(plugin)

    meta = plugin.metadata()
    assert meta.id == "my_feature"
    assert meta.category == "Tools"

def test_my_feature_compat():
    detector = CompatibilityDetector()
    detector._read_fedora_version = lambda: 40   # mock
    plugin = MyFeatureTab()
    result = plugin.check_compat(detector)
    assert result.compatible
```

---

## Upgrade Notes

### From v24.0

No action required. The application upgrades transparently. All configuration, profiles, and settings from v24.0 are preserved.

### For Packagers (RPM/Flatpak)

New package: `core/plugins/` directory with 6 new Python files. These are included automatically if you use the standard package build (RPM spec, Flatpak YAML, or `pip install`). No spec file changes are required beyond the version bump.

---

## Known Limitations in v25.0

- External plugin loading (user-installed plugins from `~/.config/loofi-fedora-tweaks/plugins/`) is not yet supported. This is planned for v26.0.
- The `PluginInterface.requires` field (inter-plugin dependencies) is declared in metadata but dependency resolution is not enforced in v25.0. Plugins with unfulfilled `requires` will still load.

---

## What's Coming in v26.0

- External plugin support: install plugins from the filesystem or a community registry
- Plugin sandboxing: resource and permission limits for external plugins
- Dependency resolution: plugins that require other plugins will load in correct order
- Plugin management UI: enable/disable, update, and remove plugins from within the app

---

*This document is a pre-release draft produced during P2 DESIGN. Final release notes will be updated in P5 DOCUMENT after all tasks are complete.*
