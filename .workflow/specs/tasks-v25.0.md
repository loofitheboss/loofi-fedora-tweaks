# Tasks for v25.0 — Plugin Architecture + UI Redesign

> **Version**: v25.0
> **Phase**: P6 PACKAGE — COMPLETE / P7 RELEASE — PENDING
> **Date**: 2026-02-11
> **Agent**: release-planner
> **Status**: P1 ✅ P2 ✅ P3 ✅ P4 ✅ P5 ✅ P6 ✅ P7 🔲

---

## Summary

v25.0 transforms the monolithic tab registration system into a plugin-based architecture where each tab/feature self-registers as a module. It adds a compatibility detection engine for hardware/DE-aware feature gating and redesigns the sidebar for dynamic navigation sourced from the plugin registry.

## Prerequisites

- v23.0 (DONE): `core/executor/`, `BaseActionExecutor`, service layer directories
- v24.0 (DONE): `core/profiles/`, profile storage, config patterns

---

## Task List

| # | Task | Phase | Agent | Size | Depends | Files | Done |
|---|------|-------|-------|------|---------|-------|------|
| 1 | Define PluginInterface ABC and PluginMetadata dataclass | P3 | architecture-advisor | M | - | `core/plugins/__init__.py`, `core/plugins/interface.py`, `core/plugins/metadata.py` | [x] |
| 2 | Implement PluginRegistry (register, unregister, get, list, lifecycle hooks) | P3 | backend-builder | M | 1 | `core/plugins/registry.py` | [x] |
| 3 | Implement PluginLoader (directory scan, entrypoint import, validation) | P3 | backend-builder | L | 1,2 | `core/plugins/loader.py` | [x] |
| 4 | Implement CompatibilityDetector (Fedora version, DE, hardware, package checks) | P3 | backend-builder | M | 1 | `core/plugins/compat.py` | [x] |
| 5 | Unit tests for PluginInterface, PluginMetadata, PluginRegistry | P4 | test-writer | M | 1,2 | `tests/test_plugin_registry.py` | [x] |
| 6 | Unit tests for PluginLoader (discovery, validation, error handling) | P4 | test-writer | M | 3 | `tests/test_plugin_loader.py` | [x] |
| 7 | Unit tests for CompatibilityDetector (mocked system calls) | P4 | test-writer | M | 4 | `tests/test_plugin_compat.py` | [x] |
| 8 | Convert BaseTab to implement PluginInterface; add default metadata | P3 | backend-builder | S | 1,2 | `ui/base_tab.py`, `core/plugins/interface.py` | [x] |
| 9 | Refactor MainWindow to source tabs from PluginRegistry instead of hardcoded list | P3 | frontend-integration-builder | L | 2,3,8 | `ui/main_window.py` | [x] |
| 10 | Redesign sidebar: dynamic categories from plugin metadata, icon+badge from registry | P3 | frontend-integration-builder | M | 9 | `ui/main_window.py`, `assets/modern.qss` | [x] |
| 11 | Integration tests for plugin-driven MainWindow (load, sidebar, navigation) | P4 | test-writer | M | 9,10 | `tests/test_plugin_integration.py` | [x] |
| 12 | Migrate 5 representative built-in tabs to PluginInterface (dashboard, hardware, network, profiles, settings) | P3 | code-implementer | L | 8,9 | `ui/dashboard_tab.py`, `ui/hardware_tab.py`, `ui/network_tab.py`, `ui/profiles_tab.py`, `ui/settings_tab.py` | [x] |
| 13 | Migrate remaining 21 built-in tabs to PluginInterface | P3 | code-implementer | L | 12 | All remaining `ui/*_tab.py` files | [x] |
| 14 | Plugin developer guide and API reference | P5 | release-planner | M | 1,2,3,4 | `docs/plugin-dev-guide.md`, `CONTRIBUTING.md` | [x] |
| 15 | Update README, CHANGELOG, RELEASE-NOTES, ROADMAP status | P5 | release-planner | S | 11,13 | `README.md`, `CHANGELOG.md`, `RELEASE-NOTES-v25.0.0.md`, `ROADMAP.md` | [x] |

---

## Critical Path

```
Task 1 (PluginInterface ABC)
  |
  +---> Task 2 (Registry) ---> Task 3 (Loader) ---> Task 9 (MainWindow refactor) ---> Task 10 (Sidebar redesign)
  |                                                       |                                |
  |                                                       +---> Task 12 (Migrate 5 tabs)   +---> Task 11 (Integration tests)
  |                                                                  |
  +---> Task 4 (CompatDetector)                                      +---> Task 13 (Migrate 21 tabs)
  |                                                                            |
  +---> Task 8 (BaseTab adapts)                                                +---> Task 15 (Release docs)
                                                                               |
                                                           Task 14 (Dev guide) +
```

**Longest path**: 1 -> 2 -> 3 -> 9 -> 12 -> 13 -> 15 (7 tasks)

**Parallelizable**:
- Tasks 4, 5, 8 can run in parallel after Task 1
- Tasks 6, 7 can run in parallel after their respective deps
- Task 14 can start after Tasks 1-4 complete (does not block release)

---

## Architectural Decisions (for P2 to validate)

### D1: Plugin interface shape

```python
class PluginInterface(ABC):
    @abstractmethod
    def metadata(self) -> PluginMetadata: ...
    @abstractmethod
    def create_widget(self) -> QWidget: ...
    def on_activate(self) -> None: ...     # lifecycle hook
    def on_deactivate(self) -> None: ...   # lifecycle hook
    def is_compatible(self, detector: CompatibilityDetector) -> bool: ...
```

### D2: PluginMetadata dataclass

```python
@dataclass
class PluginMetadata:
    id: str                   # unique slug, e.g. "hardware"
    name: str                 # display name
    description: str          # tooltip/breadcrumb
    category: str             # sidebar category, e.g. "System"
    icon: str                 # emoji or icon ref
    badge: str                # "recommended" | "advanced" | ""
    version: str              # plugin version
    requires: list[str]       # dependency plugin IDs
    compat: dict[str, Any]    # {min_fedora: 38, de: ["gnome","kde"], ...}
    order: int                # sort order within category
```

### D3: Plugin discovery strategy

Built-in plugins: scanned from `ui/*_tab.py` via registry auto-registration in `__init__`.
External plugins: future -- `~/.config/loofi-fedora-tweaks/plugins/` directory scan (v25.0 scope is built-in only; external is stretch goal).

### D4: Backward compatibility

- `_lazy_tab()` dict and hardcoded `add_page()` calls remain as fallback during migration (removed in Task 13 completion)
- `BaseTab` gains a default `metadata()` returning stub `PluginMetadata`, so existing tabs work before explicit migration
- `_TAB_META` dict moves into `PluginMetadata` on each tab

---

## Risks and Open Questions

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Tab ordering regression -- dynamic loading may change sidebar order | High | `PluginMetadata.order` field + integration test asserting exact sidebar structure |
| R2 | 15 tabs extend plain QWidget, not BaseTab -- migration surface is large | Medium | Task 12 validates pattern on 5 diverse tabs first; Task 13 batch-applies |
| R3 | Circular imports -- `core/plugins/` importing from `ui/` | High | Plugin interface lives in `core/`; tabs implement it but core never imports `ui/` directly |
| R4 | LazyWidget interaction -- plugins must still lazy-load | Medium | PluginLoader uses `create_widget()` inside `LazyWidget` wrapper, preserving existing pattern |
| R5 | Compatibility detector needs system calls (Fedora version, DE) | Low | Mock in tests; reuse `ConfigManager.get_system_info()` pattern |
| R6 | Settings tab takes `self` (MainWindow ref) as constructor arg | Medium | Plugin interface provides optional `set_main_window()` hook or dependency injection |

---

## Open Questions for P2 DESIGN

1. Should external plugin loading (filesystem scan) be in v25.0 scope or deferred to v26.0?
2. Should `PluginInterface` be a Protocol (structural) or ABC (nominal)? Protocol is lighter but less discoverable.
3. Should compatibility checks run at load time (skip incompatible) or at runtime (show disabled with reason)?
4. Should plugin metadata be declarative (class attributes / decorator) or method-based (`def metadata()`)? Decorator is more Pythonic for static data.
