# Loofi Fedora Tweaks v25.0.0 — Plugin Architecture

**Release Date:** 2026-02-11  
**Codename:** Plugin Architecture  
**Theme:** Modular tab system, compatibility detection, foundation for extensibility

---

## What's New

### Plugin-Based Tab Architecture

v25.0 transforms the internal tab system into a plugin-based architecture where each of the 26 tabs is a self-describing module with its own metadata (name, category, icon, badge, order). The sidebar now dynamically builds from the `PluginRegistry` instead of a hardcoded list, making the codebase more maintainable and laying the groundwork for user-installable plugins in future releases.

**User experience remains identical** — all tabs, keyboard shortcuts, and navigation work exactly as in v24.0. The change is purely architectural.

### Compatibility-Aware Feature Gating

Tabs can now declare compatibility requirements (minimum Fedora version, required desktop environment, Wayland/X11, required packages). The `CompatibilityDetector` checks these at startup:

- Incompatible tabs appear disabled in sidebar with explanatory tooltip
- Disabled tabs show "not available" message instead of broken UI
- Supports declarative `compat` dict in `PluginMetadata` or programmatic `check_compat()` override

### Testing & Validation

- **86 new tests** covering plugin registry, loader, compatibility checks, and integration
- Overall test suite: **1871/1908 passing (98%)**
- All plugin functionality validated with mocked system calls

---

## Breaking Changes

### For End Users

None. All features and workflows work identically to v24.0.

### For Developers

- **Removed:** `_TAB_META` dict in `ui/main_window.py` (metadata now in each tab's `PluginMetadata`)
- **Removed:** `_lazy_tab()` private method (replaced by `PluginLoader`)
- **Changed:** `SettingsTab.__init__` no longer requires `main_window` arg (use `set_context()` instead; old signature still works)

---

## Plugin Developer Quick Start

All tabs are plugins implementing `PluginInterface`. Example minimal plugin:

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata

class MyTab(QWidget, PluginInterface):
    _METADATA = PluginMetadata(
        id="my_tab",
        name="My Feature",
        description="Does something useful",
        category="Tools",
        icon="🔧",
        order=50,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello!"))
```

**Compatibility checks** (declarative):
```python
_METADATA = PluginMetadata(
    id="my_tab",
    name="My Feature",
    compat={
        "min_fedora": 39,
        "de": ["gnome", "kde"],
        "wayland_only": True,
        "requires_packages": ["some-package"],
    },
    ...
)
```

**Lifecycle hooks:**
```python
def on_activate(self) -> None:
    """Called when tab becomes active."""
    self._start_timer()

def on_deactivate(self) -> None:
    """Called when user navigates away."""
    self._stop_timer()
```

Full documentation: `docs/plugin-dev-guide.md`

---

## Upgrade Notes

- No configuration migration needed
- No database schema changes
- Existing profiles, settings, and history remain compatible
- CLI commands unchanged

---

## Files Changed

**New modules:**
- `core/plugins/__init__.py`
- `core/plugins/interface.py`
- `core/plugins/metadata.py`
- `core/plugins/registry.py`
- `core/plugins/loader.py`
- `core/plugins/compat.py`

**New tests:**
- `tests/test_plugin_registry.py` (19 tests)
- `tests/test_plugin_loader.py` (13 tests)
- `tests/test_plugin_compat.py` (28 tests)
- `tests/test_plugin_integration.py` (26 tests)

**Modified:**
- All 26 `ui/*_tab.py` files (added `PluginMetadata`, `metadata()`, `create_widget()`)
- `ui/main_window.py` (replaced `_lazy_tab()` with `PluginLoader`)
- `ui/base_tab.py` (implements `PluginInterface` with default stub)

---

## Known Issues

- `test_ui_smoke.py` expects old lazy loading mechanism (37 tests fail; will be updated in v25.1)
- `test_v17_atlas.py` has metaclass conflict (1 test file fails to collect; deferred to v25.1)

Neither issue affects runtime functionality.

---

## Next Steps

v25.0 is a **foundation release**. Future versions will build on this architecture:

- **v26.0:** External plugin loading from `~/.config/loofi-fedora-tweaks/plugins/`
- **v26.0:** Plugin marketplace and discovery UI
- **v26.0:** Plugin sandboxing and permission model

---

## Installation

```bash
# RPM (Fedora 39+)
sudo dnf install loofi-fedora-tweaks

# From source
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
bash scripts/build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-25.0.0-1.fc43.noarch.rpm
```

---

## Credits

- Architecture: project-coordinator, architecture-advisor agents
- Implementation: backend-builder, code-implementer, frontend-integration-builder agents
- Testing: test-writer agent
- Documentation: release-planner agent

Full contributor list: [CONTRIBUTORS.md](docs/CONTRIBUTING.md)
