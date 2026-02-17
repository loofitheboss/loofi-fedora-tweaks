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

## _Dummy Stub Pattern in test_main_window.py

- `_Dummy.__getattr__` returns `_Dummy()` for ANY attribute — so `hasattr(dummy_instance, "anything")` is ALWAYS True
- `isinstance(getattr(obj, "_field", None), dict)` is the correct guard when obj may be a `_Dummy`
- `_make_window(skip_init=True)` bypasses `__init__` via `object.__new__`; any attribute set via property setter runs through the property
- Properties on MainWindow with only a getter break `_make_window` test helpers that do `win.pages = {}` — always add a setter for any converted property

## SidebarEntry / SidebarIndex Pattern (v45.0 Tasks 1-4)

- `SidebarEntry` dataclass is in `ui/main_window.py` (module level)
- `_sidebar_index: dict[str, SidebarEntry]` keyed by `plugin_id = name.lower().replace(" ", "_")`
- `pages` property returns `{display_name: original_widget}` — NOT the wrapped scroll area
- `SidebarEntry.page_widget` stores the ORIGINAL widget passed to `add_page()`, not the scroll-area wrapper
- `_pages_cache = None` invalidated each time `add_page()` / `_register_in_index()` is called
- `_category_items: dict[str, QTreeWidgetItem]` — O(1) cache for category tree items

## add_page() Decomposition (v45.0 Tasks 3-4)

Three helper methods extracted from monolithic `add_page()`:
- `_find_or_create_category(category)` — uses `_category_items` cache, creates if missing
- `_create_tab_item(category_item, name, icon, badge, description, disabled, disabled_reason)` — creates tree item with badge/tooltip/disabled logic
- `_register_in_index(plugin_id, entry, scroll_widget=None)` — registers in `_sidebar_index`, invalidates cache, adds `scroll_widget` (wrapped) to `content_area`
  - NOTE: `scroll_widget` param is required because `entry.page_widget` is the ORIGINAL (unwrapped) widget, but `content_area` needs the scroll-area wrapper
- `_add_plugin_page()` uses helpers directly with `meta.id` (not name-derived) as canonical plugin ID
- `add_page()` also uses all three helpers; it derives `plugin_id` from name as before

## O(1) Sidebar Methods (v45.0 Tasks 5-8)

- `_build_favorites_section()` uses `_sidebar_index.get(fav_id)`; scroll-wrapped widget from `entry.tree_item.data(0, Qt.ItemDataRole.UserRole)`
- `_set_tab_status(tab_id, status, tooltip)` — param renamed to `tab_id`; callers use plugin IDs (lowercase): `"maintenance"`, `"storage"`
- `_set_tab_status` no longer appends `[OK]`/`[WARN]`/`[ERR]` text to tree item text; stores status on `entry.status` and `tree_item.setData(_ROLE_STATUS)`
- `switch_to_tab(name)` tries `_sidebar_index.get(name)` first (plugin ID), then iterates values matching `name in entry.display_name`
- Tests for `TestSetTabStatus` must check `entry.status` field, NOT `child.text(0)` for status markers

## SidebarItemDelegate (v48.0 Task 7)

- `SidebarItemDelegate(QStyledItemDelegate)` is at module level in `ui/main_window.py`, after `SidebarEntry`
- `_STATUS_COLORS`: `"ok"` → QColor(76,175,80), `"warning"` → QColor(255,193,7), `"error"` → QColor(244,67,54)
- Wired in `MainWindow.__init__()` via `self.sidebar.setItemDelegate(SidebarItemDelegate(self.sidebar))`
- New imports needed: `QRect` from `PyQt6.QtCore`, `QColor, QPainter` from `PyQt6.QtGui`, `QStyledItemDelegate, QStyleOptionViewItem` from `PyQt6.QtWidgets`
- test_main_window.py stubs must include: `qt_core.QRect = _Dummy`, `qt_gui.QPainter = _Dummy`, `qt_widgets.QStyledItemDelegate = _Dummy`, `qt_widgets.QStyleOptionViewItem = _Dummy`

## Experience Level Validation (v48.0 Task 9)

- `ExperienceLevelManager.get_all_declared_tab_ids()` in `utils/experience_level.py` returns `set(_INTERMEDIATE_TABS)` (superset of BEGINNER)
- Post-loop validation block in `_build_sidebar_from_registry` warns on orphaned experience-level IDs and logs ADVANCED-only tabs

## closeEvent and Rebuild (v48.0 Tasks 10, 11)

- `closeEvent` now iterates `self._sidebar_index.values()` for cleanup, accessing `entry.page_widget`
- Tests that set `win.pages = {...}` to test closeEvent must be updated to populate `win._sidebar_index` with real `SidebarEntry` instances
- `_rebuild_sidebar_for_experience_level()` clears sidebar + index + category cache + content_area, then calls `_build_sidebar_from_registry` + `_build_favorites_section` + `_refresh_sidebar_icon_tints`

## loader.py Order Comment (v48.0 Task 12)

- `_BUILTIN_PLUGINS` list order does NOT affect sidebar order; replaced misleading comment with accurate one
- Final order is (CATEGORY_ORDER rank, PluginMetadata.order) — see `core/plugins/registry.py`

## Read Tool Cache Warning

- The Read tool can return stale file content when the file has been edited since the last actual read
- Always use `git diff HEAD -- <file>` to verify actual working tree state vs what was read

## Commit Hygiene Warning

- `git add <specific files>` before committing — untracked image files (*.png) in root can sneak into commits if not careful
