# Architecture Blueprint — v25.0 Plugin Architecture + UI Redesign

> **Version**: v25.0
> **Phase**: P2 DESIGN
> **Date**: 2026-02-11
> **Agent**: architecture-advisor
> **Status**: Implementation-ready

---

## Resolved Open Questions

### Q1: External plugin loading scope
**Decision: DEFER to v26.0.**
v25.0 scope is built-in plugins only. The `PluginLoader` will be architected to support future external scan (filesystem discovery from `~/.config/loofi-fedora-tweaks/plugins/`) but that code path is not wired up. A `PluginLoader.load_external(path)` stub raises `NotImplementedError` with a message directing to v26.0.

**Rationale**: External plugins require sandboxing, signature verification, and conflict resolution — all out of scope. Premature support would create security debt. The interface design accommodates it without implementing it.

### Q2: PluginInterface — Protocol or ABC
**Decision: ABC (Abstract Base Class).**
```python
from abc import ABC, abstractmethod
class PluginInterface(ABC):
    ...
```
**Rationale**: Protocol (structural subtyping) gives no enforcement at class definition time — errors surface only at call sites. ABC raises `TypeError` at instantiation if abstract methods are missing, providing fail-fast feedback during plugin development. Discoverability is better (IDE completion, `issubclass` checks work). The Protocol option offers no runtime benefit for a system where plugins explicitly declare their type.

### Q3: Compatibility checks — load-time (skip) or runtime (show disabled)
**Decision: RUNTIME with disabled state** — incompatible plugins load but render as visually disabled sidebar items with a reason tooltip.
**Rationale**: Load-time skipping hides features from users who may have correct hardware but a stale compatibility check. Runtime disabled state is more honest, allows override, and preserves the user's ability to see what exists. CompatibilityDetector results are cached per session to avoid repeated system calls.

### Q4: Plugin metadata — method-based or decorator
**Decision: CLASS ATTRIBUTE + `metadata()` method returning cached instance.**
```python
class HardwarePlugin(PluginInterface):
    _METADATA = PluginMetadata(id="hardware", name="Hardware", ...)
    def metadata(self) -> PluginMetadata:
        return self._METADATA
```
`PluginMetadata` is a frozen dataclass. Built-in tabs declare `_METADATA` as a class attribute; `metadata()` returns it. This is more explicit than decorators (no magic), simpler to test (just check the return value), and consistent with the existing `_TAB_META` dict pattern being migrated. A `@plugin_metadata(...)` decorator helper will be provided as optional syntactic sugar but is not required.

---

## Module Structure

```
loofi-fedora-tweaks/
  core/
    plugins/
      __init__.py          # re-exports: PluginInterface, PluginMetadata, PluginRegistry, PluginLoader
      interface.py         # PluginInterface ABC
      metadata.py          # PluginMetadata frozen dataclass + CompatStatus dataclass
      registry.py          # PluginRegistry singleton
      loader.py            # PluginLoader: scans built-ins, validates, calls registry.register()
      compat.py            # CompatibilityDetector: system checks, returns CompatStatus
  ui/
    base_tab.py            # MODIFIED: implements PluginInterface, adds default metadata()
    main_window.py         # MODIFIED: sources tabs from PluginRegistry
    [all *_tab.py files]   # MODIFIED: add _METADATA class attr + metadata() override
```

**Strict rule**: `core/plugins/` MUST NOT import from `ui/`. The interface is defined in `core/`; UI code imports from `core/`.

---

## Key Interfaces and Signatures

### `core/plugins/metadata.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PluginMetadata:
    id: str                          # unique slug, e.g. "hardware"
    name: str                        # display name
    description: str                 # tooltip and breadcrumb text
    category: str                    # sidebar category group, e.g. "System"
    icon: str                        # unicode emoji or icon ref string
    badge: str                       # "recommended" | "advanced" | ""
    version: str = "1.0.0"          # plugin version string
    requires: tuple[str, ...] = ()   # dependency plugin IDs (tuple for hashability)
    compat: dict[str, Any] = field(  # {min_fedora: 38, de: ["gnome","kde"], ...}
        default_factory=dict
    )
    order: int = 100                 # sort order within category (lower = higher in list)
    enabled: bool = True             # default enabled state


@dataclass
class CompatStatus:
    compatible: bool
    reason: str = ""                 # human-readable reason if not compatible
    warnings: list[str] = field(default_factory=list)
```

**Note**: `compat` dict uses `field(default_factory=dict)` to avoid mutable default. `frozen=True` ensures metadata is immutable after creation.

### `core/plugins/interface.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QWidget
from core.plugins.metadata import PluginMetadata, CompatStatus


class PluginInterface(ABC):
    """
    Abstract base class for all Loofi tab plugins.

    Every built-in tab and future external plugin must subclass this.
    Core never imports ui/; tabs import from core.
    """

    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return immutable plugin metadata. Must not perform I/O."""
        ...

    @abstractmethod
    def create_widget(self) -> QWidget:
        """
        Instantiate and return the tab's QWidget.
        Called lazily by PluginLoader inside a LazyWidget wrapper.
        Must not be called more than once per plugin instance.
        """
        ...

    def on_activate(self) -> None:
        """Called when this tab becomes the active page. Optional."""

    def on_deactivate(self) -> None:
        """Called when this tab is navigated away from. Optional."""

    def check_compat(self, detector: "CompatibilityDetector") -> CompatStatus:
        """
        Check whether this plugin is compatible with the current system.
        Default implementation: always compatible.
        Tabs override this to gate on Fedora version, DE, hardware, etc.
        """
        from core.plugins.metadata import CompatStatus
        return CompatStatus(compatible=True)

    def set_context(self, context: dict) -> None:
        """
        Inject shared application context (replaces direct MainWindow ref).
        Called by PluginLoader after registration.
        context keys: "main_window", "config_manager", "executor"
        """
```

### `core/plugins/registry.py`

```python
from __future__ import annotations
from typing import Iterator
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata


class PluginRegistry:
    """
    Singleton registry holding all registered plugin instances.

    Tabs self-register via PluginLoader. MainWindow sources its
    sidebar entirely from this registry.
    """

    _instance: "PluginRegistry | None" = None

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInterface] = {}  # id -> plugin
        self._order: list[str] = []                      # insertion/sort order

    @classmethod
    def instance(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — for use in tests only."""
        cls._instance = None

    def register(self, plugin: PluginInterface) -> None:
        """
        Register a plugin. Raises ValueError if id is already registered.
        Preserves order by PluginMetadata.order, then insertion order.
        """
        meta = plugin.metadata()
        if meta.id in self._plugins:
            raise ValueError(f"Plugin id already registered: {meta.id!r}")
        self._plugins[meta.id] = plugin
        self._order.append(meta.id)
        self._sort_order()

    def unregister(self, plugin_id: str) -> None:
        """Remove a plugin by id. Silent no-op if not found."""
        self._plugins.pop(plugin_id, None)
        if plugin_id in self._order:
            self._order.remove(plugin_id)

    def get(self, plugin_id: str) -> PluginInterface | None:
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[PluginInterface]:
        """Return all plugins in sorted order."""
        return [self._plugins[pid] for pid in self._order if pid in self._plugins]

    def list_by_category(self, category: str) -> list[PluginInterface]:
        return [p for p in self.list_all() if p.metadata().category == category]

    def categories(self) -> list[str]:
        """Return unique categories in order of first appearance."""
        seen: list[str] = []
        for pid in self._order:
            if pid in self._plugins:
                cat = self._plugins[pid].metadata().category
                if cat not in seen:
                    seen.append(cat)
        return seen

    def _sort_order(self) -> None:
        """Re-sort _order list by (category_first_seen_index, plugin.order, insertion)."""
        # Stable sort by order field within insertion order
        self._order.sort(key=lambda pid: (
            self._plugins[pid].metadata().category,
            self._plugins[pid].metadata().order,
        ))

    def __iter__(self) -> Iterator[PluginInterface]:
        return iter(self.list_all())

    def __len__(self) -> int:
        return len(self._plugins)
```

### `core/plugins/loader.py`

```python
from __future__ import annotations
import importlib
import logging
from core.plugins.registry import PluginRegistry
from core.plugins.interface import PluginInterface
from core.plugins.compat import CompatibilityDetector

log = logging.getLogger(__name__)

# Ordered list of (module_path, class_name) for all 26 built-in tabs.
# Order here determines initial registration order; PluginMetadata.order refines within category.
_BUILTIN_PLUGINS: list[tuple[str, str]] = [
    ("ui.dashboard_tab", "DashboardTab"),
    ("ui.agents_tab", "AgentsTab"),
    ("ui.automation_tab", "AutomationTab"),
    ("ui.system_info_tab", "SystemInfoTab"),
    ("ui.monitor_tab", "MonitorTab"),
    ("ui.health_timeline_tab", "HealthTimelineTab"),
    ("ui.logs_tab", "LogsTab"),
    ("ui.hardware_tab", "HardwareTab"),
    ("ui.performance_tab", "PerformanceTab"),
    ("ui.storage_tab", "StorageTab"),
    ("ui.software_tab", "SoftwareTab"),
    ("ui.maintenance_tab", "MaintenanceTab"),
    ("ui.snapshot_tab", "SnapshotTab"),
    ("ui.virtualization_tab", "VirtualizationTab"),
    ("ui.development_tab", "DevelopmentTab"),
    ("ui.network_tab", "NetworkTab"),
    ("ui.mesh_tab", "MeshTab"),
    ("ui.security_tab", "SecurityTab"),
    ("ui.desktop_tab", "DesktopTab"),
    ("ui.profiles_tab", "ProfilesTab"),
    ("ui.gaming_tab", "GamingTab"),
    ("ui.ai_enhanced_tab", "AIEnhancedTab"),
    ("ui.teleport_tab", "TeleportTab"),
    ("ui.diagnostics_tab", "DiagnosticsTab"),
    ("ui.community_tab", "CommunityTab"),
    ("ui.settings_tab", "SettingsTab"),
]


class PluginLoader:
    """
    Discovers and loads plugins into PluginRegistry.

    v25.0: built-in plugins only.
    v26.0: add load_external() for filesystem scan.
    """

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        detector: CompatibilityDetector | None = None,
    ) -> None:
        self._registry = registry or PluginRegistry.instance()
        self._detector = detector or CompatibilityDetector()

    def load_builtins(self, context: dict | None = None) -> list[str]:
        """
        Import all built-in plugin modules, instantiate, validate, and register.
        Returns list of successfully loaded plugin IDs.
        """
        loaded: list[str] = []
        for module_path, class_name in _BUILTIN_PLUGINS:
            try:
                plugin = self._import_plugin(module_path, class_name)
                if context:
                    plugin.set_context(context)
                self._registry.register(plugin)
                loaded.append(plugin.metadata().id)
                log.debug("Loaded plugin: %s", plugin.metadata().id)
            except Exception as exc:
                log.warning("Failed to load plugin %s.%s: %s", module_path, class_name, exc)
        return loaded

    def _import_plugin(self, module_path: str, class_name: str) -> PluginInterface:
        """Import module, instantiate class, validate it implements PluginInterface."""
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        if not (isinstance(cls, type) and issubclass(cls, PluginInterface)):
            raise TypeError(f"{class_name} does not subclass PluginInterface")
        return cls()

    def load_external(self, directory: str) -> list[str]:
        """
        Future: scan directory for external plugins.
        v26.0 scope — not implemented in v25.0.
        """
        raise NotImplementedError(
            "External plugin loading is scheduled for v26.0. "
            "See ROADMAP.md for details."
        )
```

### `core/plugins/compat.py`

```python
from __future__ import annotations
import os
import subprocess
import logging
from functools import lru_cache
from core.plugins.metadata import CompatStatus

log = logging.getLogger(__name__)


class CompatibilityDetector:
    """
    Detects system properties for plugin compatibility gating.

    All system calls are isolated in private methods for easy mocking in tests.
    Results are cached per detector instance (reset by creating a new instance).

    Checks performed:
    - Fedora version (from /etc/fedora-release or /etc/os-release)
    - Desktop Environment (XDG_CURRENT_DESKTOP, DESKTOP_SESSION)
    - Wayland vs X11 (WAYLAND_DISPLAY)
    - Hardware capabilities (module-specific, checked on demand)
    - Package availability (rpm -q, checked on demand)
    """

    def __init__(self) -> None:
        self._cache: dict[str, object] = {}

    # ---------------------------------------------------------------- Public API

    def fedora_version(self) -> int:
        """Return Fedora major version number, or 0 if not Fedora."""
        if "fedora_version" not in self._cache:
            self._cache["fedora_version"] = self._read_fedora_version()
        return self._cache["fedora_version"]

    def desktop_environment(self) -> str:
        """Return lowercase DE name: 'gnome', 'kde', 'xfce', 'other', or 'unknown'."""
        if "desktop_env" not in self._cache:
            self._cache["desktop_env"] = self._read_desktop_env()
        return self._cache["desktop_env"]

    def is_wayland(self) -> bool:
        """Return True if running under Wayland."""
        if "is_wayland" not in self._cache:
            self._cache["is_wayland"] = bool(os.environ.get("WAYLAND_DISPLAY"))
        return self._cache["is_wayland"]

    def has_package(self, package_name: str) -> bool:
        """Return True if RPM package is installed."""
        key = f"pkg:{package_name}"
        if key not in self._cache:
            self._cache[key] = self._check_package(package_name)
        return self._cache[key]

    def check_plugin_compat(self, compat_spec: dict) -> CompatStatus:
        """
        Evaluate a PluginMetadata.compat dict against system state.

        Supported keys:
            min_fedora: int        — minimum Fedora version
            de: list[str]         — allowed DEs (empty = all)
            requires_packages: list[str]  — required RPM packages
            wayland_only: bool    — requires Wayland
            x11_only: bool        — requires X11
        """
        warnings: list[str] = []

        min_fed = compat_spec.get("min_fedora", 0)
        if min_fed and self.fedora_version() < min_fed:
            return CompatStatus(
                compatible=False,
                reason=f"Requires Fedora {min_fed}+, detected {self.fedora_version()}"
            )

        allowed_de = compat_spec.get("de", [])
        if allowed_de and self.desktop_environment() not in allowed_de:
            return CompatStatus(
                compatible=False,
                reason=f"Requires DE in {allowed_de}, detected '{self.desktop_environment()}'"
            )

        if compat_spec.get("wayland_only") and not self.is_wayland():
            return CompatStatus(compatible=False, reason="Requires Wayland session")

        if compat_spec.get("x11_only") and self.is_wayland():
            return CompatStatus(compatible=False, reason="Requires X11 session")

        for pkg in compat_spec.get("requires_packages", []):
            if not self.has_package(pkg):
                warnings.append(f"Package not installed: {pkg}")

        return CompatStatus(compatible=True, warnings=warnings)

    # -------------------------------------------------------------- Private I/O

    def _read_fedora_version(self) -> int:
        try:
            with open("/etc/fedora-release") as fh:
                content = fh.read()
            import re
            m = re.search(r"release (\d+)", content)
            return int(m.group(1)) if m else 0
        except OSError:
            return 0

    def _read_desktop_env(self) -> str:
        de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "gnome" in de:
            return "gnome"
        if "kde" in de or "plasma" in de:
            return "kde"
        if "xfce" in de:
            return "xfce"
        if de:
            return "other"
        return "unknown"

    def _check_package(self, name: str) -> bool:
        try:
            result = subprocess.run(
                ["rpm", "-q", name],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
```

### `core/plugins/__init__.py`

```python
"""
core.plugins — Plugin architecture for Loofi Fedora Tweaks.

Public API:
    PluginInterface  — ABC for all plugins
    PluginMetadata   — frozen dataclass for plugin metadata
    CompatStatus     — dataclass for compatibility check results
    PluginRegistry   — singleton registry
    PluginLoader     — built-in plugin loader
    CompatibilityDetector — system compatibility checker
"""

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata, CompatStatus
from core.plugins.registry import PluginRegistry
from core.plugins.loader import PluginLoader
from core.plugins.compat import CompatibilityDetector

__all__ = [
    "PluginInterface",
    "PluginMetadata",
    "CompatStatus",
    "PluginRegistry",
    "PluginLoader",
    "CompatibilityDetector",
]
```

---

## Module Dependency Graph (Acyclic)

```
core/plugins/metadata.py
  (no project imports)

core/plugins/compat.py
  --> core/plugins/metadata.py

core/plugins/interface.py
  --> core/plugins/metadata.py
  --> core/plugins/compat.py  [type hint only, TYPE_CHECKING guard]

core/plugins/registry.py
  --> core/plugins/interface.py
  --> core/plugins/metadata.py

core/plugins/loader.py
  --> core/plugins/registry.py
  --> core/plugins/interface.py
  --> core/plugins/compat.py
  --> ui/*_tab.py  [dynamic import via importlib, NOT static]

ui/base_tab.py
  --> core/plugins/interface.py
  --> core/plugins/metadata.py

ui/*_tab.py
  --> ui/base_tab.py  (or QWidget directly)
  --> core/plugins/interface.py
  --> core/plugins/metadata.py

ui/main_window.py
  --> core/plugins/registry.py
  --> core/plugins/loader.py
  --> core/plugins/compat.py
  --> ui/lazy_widget.py
```

**Key rule enforced**: `core/plugins/loader.py` uses `importlib.import_module()` at runtime — NOT static imports of `ui/`. This prevents circular imports while still allowing the loader to instantiate UI classes.

---

## BaseTab Migration Strategy

### Modified `ui/base_tab.py`

BaseTab gains `PluginInterface` as a second parent (mixin pattern) and a default `metadata()` implementation:

```python
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata

_STUB_META = PluginMetadata(
    id="__stub__",
    name="Unnamed Tab",
    description="",
    category="General",
    icon="",
    badge="",
)

class BaseTab(QWidget, PluginInterface):
    """Common base class for all tabs that execute system commands."""

    # Subclasses MUST override _METADATA with their own PluginMetadata
    _METADATA: PluginMetadata = _STUB_META

    def __init__(self):
        QWidget.__init__(self)
        # ... existing init code unchanged ...

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> "QWidget":
        """Default: return self. Tabs that need fresh instances must override."""
        return self

    def set_context(self, context: dict) -> None:
        """Store context for tabs that need MainWindow or executor references."""
        self._plugin_context = context
```

**MRO note**: `QWidget` must come before `PluginInterface` in the MRO. `PluginInterface(ABC)` abstract methods `metadata()` and `create_widget()` are satisfied by BaseTab's concrete implementations. Subclasses that don't override will use the stub (logs a warning at load time).

### QWidget-only tabs (15 tabs not extending BaseTab)

These tabs implement `PluginInterface` directly, without going through `BaseTab`. Pattern:

```python
from PyQt6.QtWidgets import QWidget
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata, CompatStatus

class SomeTab(QWidget, PluginInterface):
    _METADATA = PluginMetadata(
        id="some",
        name="Some Tab",
        description="...",
        category="Category",
        icon="emoji",
        badge="",
        order=N,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self
```

---

## Built-in Tab Metadata Reference

Complete `_METADATA` assignments for all 26 tabs (P3 implementer reference):

| Tab class | id | name | category | icon | badge | order |
|-----------|-----|------|----------|------|-------|-------|
| DashboardTab | dashboard | Home | Dashboard | 🏠 | recommended | 10 |
| AgentsTab | agents | Agents | Automation | 🤖 | | 10 |
| AutomationTab | automation | Automation | Automation | ⏰ | | 20 |
| SystemInfoTab | system_info | System Info | System | ℹ️ | recommended | 10 |
| MonitorTab | monitor | System Monitor | System | 📊 | recommended | 20 |
| HealthTimelineTab | health | Health | System | 📈 | | 30 |
| LogsTab | logs | Logs | System | 📋 | advanced | 40 |
| HardwareTab | hardware | Hardware | Hardware | ⚡ | recommended | 10 |
| PerformanceTab | performance | Performance | Hardware | ⚙️ | advanced | 20 |
| StorageTab | storage | Storage | Hardware | 💾 | | 30 |
| SoftwareTab | software | Software | Software | 📦 | recommended | 10 |
| MaintenanceTab | maintenance | Maintenance | Software | 🔧 | recommended | 20 |
| SnapshotTab | snapshots | Snapshots | Software | 📸 | advanced | 30 |
| VirtualizationTab | virtualization | Virtualization | Software | 🖥️ | advanced | 40 |
| DevelopmentTab | development | Development | Software | 🛠️ | | 50 |
| NetworkTab | network | Network | Network | 🌐 | recommended | 10 |
| MeshTab | mesh | Loofi Link | Network | 🔗 | advanced | 20 |
| SecurityTab | security | Security & Privacy | Security | 🛡️ | recommended | 10 |
| DesktopTab | desktop | Desktop | Desktop | 🎨 | | 10 |
| ProfilesTab | profiles | Profiles | Desktop | 👤 | | 20 |
| GamingTab | gaming | Gaming | Desktop | 🎮 | | 30 |
| AIEnhancedTab | ai_lab | AI Lab | Tools | 🧠 | advanced | 10 |
| TeleportTab | teleport | State Teleport | Tools | 📡 | advanced | 20 |
| DiagnosticsTab | diagnostics | Diagnostics | Tools | 🔭 | | 30 |
| CommunityTab | community | Community | Tools | 🌍 | | 40 |
| SettingsTab | settings | Settings | Settings | ⚙️ | | 10 |

---

## MainWindow Refactor Strategy (Task 9)

### Key changes to `ui/main_window.py`

1. **Remove** `_TAB_META` dict (metadata moves into `PluginMetadata`)
2. **Remove** all `add_page()` call sites in `__init__` (26 hardcoded calls)
3. **Remove** `_lazy_tab()` method (LazyWidget wrapping moves into `_build_sidebar_from_registry()`)
4. **Keep** `add_page()` method signature unchanged during migration for backward compat
5. **Add** `_build_sidebar_from_registry()` called from `__init__`
6. **Add** `_wrap_in_lazy()` that wraps plugin's `create_widget` in `LazyWidget`

```python
def _build_sidebar_from_registry(self, context: dict) -> None:
    """Source all tabs from PluginRegistry. Replaces 26 hardcoded add_page() calls."""
    from core.plugins.loader import PluginLoader
    from core.plugins.compat import CompatibilityDetector

    detector = CompatibilityDetector()
    loader = PluginLoader(detector=detector)
    loader.load_builtins(context=context)

    registry = PluginRegistry.instance()

    for plugin in registry:
        meta = plugin.metadata()
        compat = plugin.check_compat(detector)
        lazy = self._wrap_in_lazy(plugin)

        # Pass compat status as extra data for disabled rendering
        self._add_plugin_page(meta, lazy, compat)

def _wrap_in_lazy(self, plugin: PluginInterface) -> LazyWidget:
    """Wrap plugin.create_widget() in LazyWidget for deferred instantiation."""
    return LazyWidget(plugin.create_widget)

def _add_plugin_page(
    self,
    meta: PluginMetadata,
    widget: LazyWidget,
    compat: CompatStatus,
) -> None:
    """Register a plugin page in the sidebar and content area."""
    # Reuses existing add_page() logic but sources data from PluginMetadata
    self.add_page(
        name=meta.name,
        icon=meta.icon,
        widget=widget,
        category=meta.category,
        description=meta.description,
        badge=meta.badge,
        disabled=not compat.compatible,
        disabled_reason=compat.reason,
    )
```

### Updated `add_page()` signature

```python
def add_page(
    self,
    name: str,
    icon: str,
    widget: QWidget,
    category: str = "General",
    description: str = "",
    badge: str = "",
    disabled: bool = False,
    disabled_reason: str = "",
) -> None:
```

New `disabled` and `disabled_reason` parameters are backward-compatible (default False/"").

### Context dict passed to plugins

```python
context = {
    "main_window": self,                    # MainWindow instance
    "config_manager": ConfigManager,        # class, not instance (matches existing usage)
    "executor": None,                       # populated after executor init
}
```

---

## SettingsTab DI Solution (R6)

`SettingsTab.__init__(self, main_window=None)` takes a MainWindow reference. This is incompatible with zero-arg instantiation in `PluginLoader._import_plugin()`.

**Solution**: `set_context()` hook, called by PluginLoader after instantiation.

```python
class SettingsTab(QWidget, PluginInterface):
    _METADATA = PluginMetadata(id="settings", ...)

    def __init__(self):
        super().__init__()
        self._main_window = None    # set via set_context()
        self._mgr = SettingsManager.instance()
        # Defer _init_ui() until after context is set

    def set_context(self, context: dict) -> None:
        self._main_window = context.get("main_window")
        self._init_ui()  # safe to call now

    def create_widget(self) -> QWidget:
        return self
```

**Backward compat**: `SettingsTab(main_window=None)` still works as before — the `main_window` arg is accepted but context injection is preferred. The `_lazy_tab("settings")` lambda in old code passes `self` (MainWindow); that code path is removed in Task 9 when the old `_lazy_tab` dict is deleted.

---

## Sidebar Redesign Spec (Task 10)

### Disabled item rendering

When `compat.compatible == False`, the sidebar item receives:
- Grayed text color via item flag or QSS
- `setDisabled(True)` on the QTreeWidgetItem (grays out automatically)
- Tooltip showing `compat.reason`
- Content area shows a disabled placeholder widget (not the real LazyWidget)

QSS additions to `assets/modern.qss`:

```css
/* Disabled plugin items in sidebar */
QTreeWidget#sidebar QTreeWidgetItem:disabled {
    color: #6c6f85;
    font-style: italic;
}

/* Badge icons inline with item text */
QTreeWidget#sidebar QTreeWidgetItem[badge="recommended"] {
    /* handled via item text suffix ★ — no CSS needed */
}
```

### Disabled placeholder widget

```python
class DisabledPluginPage(QWidget):
    """Shown in content area for incompatible plugins."""
    def __init__(self, meta: PluginMetadata, reason: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{meta.icon}  {meta.name} is not available on this system.\n\n{reason}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("disabledPluginLabel")
        layout.addWidget(label)
```

QSS for disabled page:
```css
QLabel#disabledPluginLabel {
    color: #6c6f85;
    font-size: 14px;
    padding: 40px;
}
```

---

## LazyWidget Interaction (R4)

`LazyWidget` in `ui/lazy_widget.py` takes a zero-arg callable that returns a `QWidget`. It defers instantiation until the widget is first shown.

`PluginLoader._wrap_in_lazy()` passes `plugin.create_widget` (a bound method, zero-arg) directly to `LazyWidget`. This preserves the existing lazy-load pattern without modification.

```python
# Existing pattern (removed in Task 9):
LazyWidget(lambda: HardwareTab())

# New pattern (Task 9):
LazyWidget(hardware_plugin.create_widget)
```

No changes to `ui/lazy_widget.py` are required.

---

## Risk Mitigations

### R1: Tab ordering regression
- `PluginMetadata.order: int` field determines sort order within category
- `PluginRegistry._sort_order()` sorts by `(category, order)`
- Integration test `tests/test_plugin_integration.py` asserts exact sidebar category and item structure
- Built-in tabs have explicit `order` values matching current hardcoded position

### R2: 15 QWidget-only tabs migration
- Task 12 migrates 5 diverse tabs first (including one QWidget-only: DashboardTab, SettingsTab)
- Batch pattern validated before Task 13 applies to remaining 21
- Pattern: `class Tab(QWidget, PluginInterface)` — add `_METADATA`, override `metadata()` and `create_widget()`
- No changes to existing `__init__` or UI logic required

### R3: Circular imports
- `core/plugins/` never contains a static import of `ui/`
- `PluginLoader` uses `importlib.import_module()` at runtime
- `PluginInterface` uses `TYPE_CHECKING` guard for `CompatibilityDetector` reference in type hints

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.plugins.compat import CompatibilityDetector
```

### R4: LazyWidget interaction
- Resolved above: `create_widget` bound method is a valid zero-arg callable for `LazyWidget`
- No modification to `LazyWidget` required

### R5: CompatibilityDetector system calls
- All I/O in private methods (`_read_fedora_version`, `_read_desktop_env`, `_check_package`)
- Tests mock these methods directly:
  ```python
  detector = CompatibilityDetector()
  detector._read_fedora_version = lambda: 40
  detector._read_desktop_env = lambda: "gnome"
  ```
- Alternatively, constructor accepts injectable callables (optional, for test convenience)

### R6: SettingsTab MainWindow ref
- Resolved above: `set_context()` hook injects context dict after zero-arg instantiation
- `_init_ui()` deferred until `set_context()` called
- Backward compat: `SettingsTab(main_window=...)` constructor arg still accepted but deprecated

---

## Per-Task Implementation Notes

### Task 1: PluginInterface ABC + PluginMetadata
- Files: `core/plugins/__init__.py`, `core/plugins/interface.py`, `core/plugins/metadata.py`
- No UI imports. Pure Python (no PyQt6 in metadata.py).
- `interface.py` imports PyQt6 only for `QWidget` type hint — use `TYPE_CHECKING` guard if import causes issues headless.
- `PluginMetadata` must be `frozen=True` dataclass.

### Task 2: PluginRegistry
- File: `core/plugins/registry.py`
- Singleton with `reset()` classmethod for test isolation.
- `_sort_order()` must be stable (Python's `list.sort` is stable).
- Categories preserve order of first-seen plugin (not alphabetical).

### Task 3: PluginLoader
- File: `core/plugins/loader.py`
- `_BUILTIN_PLUGINS` list order matches current sidebar order (Task 1 critical for R1).
- Failed imports log warning, do not raise — graceful degradation.
- `load_external()` raises `NotImplementedError`.

### Task 4: CompatibilityDetector
- File: `core/plugins/compat.py`
- All system I/O in private methods, public API caches via `self._cache`.
- `check_plugin_compat()` is the main entry point; tabs call `plugin.check_compat(detector)`.

### Task 5: Tests for PluginInterface, PluginMetadata, PluginRegistry
- File: `tests/test_plugin_registry.py`
- Use `PluginRegistry.reset()` in `setUp`/`teardown` for test isolation.
- Test: register, duplicate register raises ValueError, unregister, list_all order, categories order.

### Task 6: Tests for PluginLoader
- File: `tests/test_plugin_loader.py`
- Mock `importlib.import_module` or use minimal stub plugin classes.
- Test: successful load, failed import (warning logged, not raised), `load_external` raises NotImplementedError.

### Task 7: Tests for CompatibilityDetector
- File: `tests/test_plugin_compat.py`
- Mock private methods: `_read_fedora_version`, `_read_desktop_env`, `_check_package`.
- Test: min_fedora pass/fail, de filter, wayland_only, package check with warning.
- No actual system calls in any test.

### Task 8: BaseTab implements PluginInterface
- File: `ui/base_tab.py`
- Add `PluginInterface` as second parent.
- Add `_METADATA` class attribute with stub value.
- Add `metadata()`, `create_widget()`, `set_context()` methods.
- Add warning log if `_METADATA.id == "__stub__"` at load time.
- No changes to existing CommandRunner wiring or output_area.

### Task 9: MainWindow refactor
- File: `ui/main_window.py`
- Add `_build_sidebar_from_registry()` called from `__init__`.
- Remove 26 hardcoded `add_page()` calls.
- Remove `_lazy_tab()` method and `loaders` dict.
- Remove `_TAB_META` dict.
- Update `add_page()` signature with optional `disabled`, `disabled_reason` params.
- Keep `add_page()` method itself — used by integration tests and potentially external callers.

### Task 10: Sidebar redesign
- Files: `ui/main_window.py`, `assets/modern.qss`
- Add disabled item rendering in `add_page()`.
- Add `DisabledPluginPage` class (can live in `ui/main_window.py` or `ui/plugin_page.py`).
- Add QSS rules for `#disabledPluginLabel`.
- Badge rendering unchanged (text suffix ★ / ⚙).

### Task 11: Integration tests
- File: `tests/test_plugin_integration.py`
- Test full load: `PluginLoader.load_builtins()` + `PluginRegistry.list_all()` = 26 plugins.
- Test category structure matches expected order.
- Test sidebar item count per category.
- Mock PyQt6 widgets if running headless (or use `QApplication` fixture).

### Task 12: Migrate 5 representative tabs
- Files: `ui/dashboard_tab.py`, `ui/hardware_tab.py`, `ui/network_tab.py`, `ui/profiles_tab.py`, `ui/settings_tab.py`
- Priority: `settings_tab.py` first (R6 solution validation).
- Each: add `_METADATA`, override `metadata()`, override `create_widget()`, add `set_context()` if needed.
- `DashboardTab`: add `_METADATA` (currently eager-loaded, not lazy — becomes lazy via `create_widget()`).

### Task 13: Migrate remaining 21 tabs
- All remaining `ui/*_tab.py` files.
- Use validated pattern from Task 12.
- Each tab: add `_METADATA` class attribute with correct values from reference table above.
- Remove `_lazy_tab` lambda entries (already removed in Task 9, but tab classes must not have constructor args beyond `self`).
- QWidget-only tabs: add `PluginInterface` as second parent.

---

## Migration Sequence (Backward Compat)

During Tasks 8-13, the old `_lazy_tab()` and hardcoded `add_page()` calls serve as fallback:

```
Task 8:  BaseTab gains PluginInterface. App still uses old registration. ✓ No regression.
Task 9:  MainWindow switches to registry. _lazy_tab() removed. Requires Tasks 1-3, 8 complete.
Task 12: 5 tabs migrated. Registry has 5 real plugins + 21 stubs (from BaseTab default).
Task 13: All 26 tabs have explicit _METADATA. Registry fully populated.
```

After Task 13, the stub `_METADATA` path is dead code but harmless.

---

## File Checklist for P3

New files:
- `core/plugins/__init__.py`
- `core/plugins/interface.py`
- `core/plugins/metadata.py`
- `core/plugins/registry.py`
- `core/plugins/loader.py`
- `core/plugins/compat.py`

Modified files:
- `ui/base_tab.py`
- `ui/main_window.py`
- `assets/modern.qss`
- `ui/dashboard_tab.py`
- `ui/hardware_tab.py`
- `ui/network_tab.py`
- `ui/profiles_tab.py`
- `ui/settings_tab.py`
- All remaining `ui/*_tab.py` (21 files)

New test files:
- `tests/test_plugin_registry.py`
- `tests/test_plugin_loader.py`
- `tests/test_plugin_compat.py`
- `tests/test_plugin_integration.py`

New doc files (P5):
- `docs/plugin-dev-guide.md`
- `RELEASE-NOTES-v25.0.0.md`
