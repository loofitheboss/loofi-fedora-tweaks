# Plugin Architecture — v25.0

## Source Root
All source code lives in: `loofi-fedora-tweaks/loofi-fedora-tweaks/`
(NOT the project root — there is a nested same-name directory)

## core/plugins/ Package Location
`loofi-fedora-tweaks/loofi-fedora-tweaks/core/plugins/`

## Module Dependency Order (acyclic)
```
metadata.py   (no project imports)
compat.py     --> metadata.py
interface.py  --> metadata.py, compat.py [TYPE_CHECKING guard only]
registry.py   --> interface.py, metadata.py
loader.py     --> registry.py, interface.py, compat.py
              --> ui/*_tab.py [importlib only, NOT static]
```

## Key Patterns

### TYPE_CHECKING guard in interface.py
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.plugins.compat import CompatibilityDetector
```
Used to avoid circular import: interface -> compat -> metadata (compat already imports metadata).

### PluginMetadata frozen dataclass
- `frozen=True` — immutable after creation
- `compat: dict` uses `field(default_factory=dict)` (mutable default workaround)
- `requires: tuple[str, ...]` (tuple for hashability)

### PluginRegistry singleton
- `PluginRegistry.instance()` — get singleton
- `PluginRegistry.reset()` — test isolation only
- `_sort_order()` sorts by `(category, order)` — stable Python sort

### BaseTab MRO
`class BaseTab(QWidget, PluginInterface):`
- QWidget MUST come before PluginInterface
- `_METADATA: PluginMetadata = _STUB_META` — class attribute
- Warning logged in `metadata()` if `_METADATA.id == "__stub__"`
- `set_context()` stores to `self._plugin_context`
- Existing CommandRunner wiring, output_area, runner — UNTOUCHED

### CompatibilityDetector
- All I/O in private methods: `_read_fedora_version`, `_read_desktop_env`, `_check_package`
- Results cached in `self._cache` dict per instance
- Test mocking: replace private methods directly on instance

## Stub Metadata Value
```python
_STUB_META = PluginMetadata(
    id="__stub__", name="Unnamed Tab", description="",
    category="General", icon="", badge="",
)
```

## Tasks Completed (v25.0 P3)
- Task 1: core/plugins/__init__.py, interface.py, metadata.py
- Task 2: core/plugins/registry.py
- Task 3: core/plugins/loader.py
- Task 4: core/plugins/compat.py
- Task 8: ui/base_tab.py modified (PluginInterface mixin added)

## Remaining Tasks (v25.0 P3)
- Task 5-7: Tests (test_plugin_registry.py, test_plugin_loader.py, test_plugin_compat.py)
- Task 9: ui/main_window.py refactor (_build_sidebar_from_registry)
- Task 10: Sidebar disabled rendering + DisabledPluginPage
- Task 11: Integration tests
- Task 12: Migrate 5 representative tabs (dashboard, hardware, network, profiles, settings)
- Task 13: Migrate remaining 21 tabs
