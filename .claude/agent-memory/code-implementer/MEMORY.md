# Code Implementer Memory

## Project Structure
- App code lives in `loofi-fedora-tweaks/loofi-fedora-tweaks/` (inner dir), NOT the outer root
- Working directory for code: `loofi-fedora-tweaks/loofi-fedora-tweaks/`
- UI tabs: `loofi-fedora-tweaks/loofi-fedora-tweaks/ui/*_tab.py` (26 tab files + base_tab.py)
- Plugin core: `loofi-fedora-tweaks/loofi-fedora-tweaks/core/plugins/`

## Plugin Architecture (v25.0)
- `core/plugins/interface.py` — PluginInterface ABC with `metadata()`, `create_widget()`, `set_context()`, `on_activate()`, `on_deactivate()`, `check_compat()`
- `core/plugins/metadata.py` — PluginMetadata frozen dataclass
- `ui/base_tab.py` — already implements `QWidget, PluginInterface` with stub _METADATA and default methods
- 26 built-in tabs all migrated in v25.0 Tasks 12/13

## Tab Migration Pattern

### BaseTab subclasses (13 tabs): add PluginMetadata import + _METADATA + metadata() + create_widget()
```python
from core.plugins.metadata import PluginMetadata
class FooTab(BaseTab):
    _METADATA = PluginMetadata(id="foo", name="Foo", description="...", category="Bar", icon="X", badge="", order=N)
    def metadata(self): return self._METADATA
    def create_widget(self): return self
```

### QWidget-only tabs (13 tabs): also add PluginInterface as second parent
```python
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata
class FooTab(QWidget, PluginInterface):  # QWidget MUST come first
    _METADATA = PluginMetadata(...)
    def metadata(self): return self._METADATA
    def create_widget(self): return self
```

### set_context() special case (SettingsTab, DashboardTab): tabs with MainWindow constructor arg
- Change `__init__(self, main_window)` to `__init__(self, main_window=None)`
- Defer UI build (if it needs main_window) to `set_context()` or just store as optional
- settings_tab: defers `_init_ui()` to `set_context()`; dashboard_tab: `main_window=None` default is enough (only used in button handlers with hasattr guards)

## Arch Spec Location
- `.workflow/specs/arch-v25.0.md` — full plugin interface spec, metadata reference table, per-task notes

## Exception Handler Narrowing Rules (applied across services/ and ui/)
- subprocess.run/Popen in services → `except (subprocess.SubprocessError, OSError)`
- File I/O (open, sysfs reads, /proc) → `except (OSError, IOError)`
- glob.glob on sysfs → `except OSError`
- shutil.disk_usage → `except OSError`
- UI tabs calling mixed utils (subprocess + file I/O) → `except (RuntimeError, OSError, ValueError)`
- UI tabs calling BackupWizard/SnapshotManager/UpdateManager → `except (RuntimeError, OSError, ValueError)`
- save_tuning_entry (pure file I/O) → `except (OSError, IOError)`
- get_tuning_history (file read + JSON) → `except (OSError, ValueError)`
- teleport: list_saved_packages → `except (OSError, ValueError)`; send_file → `except (OSError, RuntimeError)`
- KEEP broad `except Exception` only at: main.py, cli/main.py, top-level entry points
- `except (ValueError, FileNotFoundError, Exception)` is equivalent to broad → narrow to `except (ValueError, FileNotFoundError, OSError)`
- hardware_tab.py has NO subprocess import; UI-level service calls bubble as OSError/RuntimeError, not SubprocessError

## Critical Edit Warning

- When editing class docstrings, be careful not to accidentally insert class body code INSIDE the docstring
- Always use a separate old_string that ends the docstring with `"""` before placing new class attributes
