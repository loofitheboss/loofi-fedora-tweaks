---
goal: Restructure the tab/sidebar system with ID-based SidebarIndex for O(1) lookups, fixing fragile favorites, string-munged status, and monolithic add_page()
version: 1.0
date_created: 2026-02-17
last_updated: 2026-02-17
owner: Loofi Fedora Tweaks
status: Approved
tags: [refactor, architecture, sidebar, v48]
---

# Sidebar Index Restructure — v48.0

![Status: Approved](https://img.shields.io/badge/status-Approved-green)

Replace scattered O(n) sidebar tree scans with a centralized `SidebarIndex` dict keyed by plugin ID. Fixes 5 identified pain points: fragile favorites matching, status string munging, experience level sync drift, monolithic `add_page()`, and misleading loader list ordering.

## 1. Requirements & Constraints

- **REQ-001**: All sidebar lookups (favorites, status, navigation) must be O(1) by plugin ID
- **REQ-002**: `add_page()` must be decomposed into focused helper methods
- **REQ-003**: Tab status must use data roles only — no text modification of display names
- **REQ-004**: Favorites must match by canonical plugin ID, not name heuristics
- **REQ-005**: Experience level tab lists must be validated against the registry at build time
- **REQ-006**: Backward compatibility — `self.pages` dict and `add_page()` public API preserved
- **SEC-001**: No new privileged capabilities — pure UI refactor
- **CON-001**: No visual changes to sidebar appearance (except status dots replacing text markers)
- **CON-002**: Stabilization guide compliance — no new subprocess calls
- **PAT-001**: All new code follows existing patterns (logging via get_logger, %s formatting)

## 2. Core Data Structure

### SidebarEntry dataclass

```python
@dataclass
class SidebarEntry:
    plugin_id: str              # canonical ID from PluginMetadata.id
    display_name: str           # human-readable name
    tree_item: QTreeWidgetItem  # the sidebar tree item
    page_widget: QWidget        # the scroll-wrapped page widget
    metadata: PluginMetadata    # full metadata reference
    status: str = ""            # "ok" | "warning" | "error" | ""
```

### SidebarIndex

```python
# In MainWindow
self._sidebar_index: dict[str, SidebarEntry] = {}
self._category_items: dict[str, QTreeWidgetItem] = {}  # category cache
```

Replaces `self.pages: dict[str, QWidget]` as the primary data store. A `self.pages` property provides backward-compatible `{display_name: widget}` view.

## 3. Implementation Steps

### Phase 1 — SidebarEntry and Index Infrastructure

| Task | Description |
|------|-------------|
| TASK-001 | Define `SidebarEntry` dataclass in `main_window.py` (or `ui/sidebar_types.py` if preferred) |
| TASK-002 | Add `self._sidebar_index: dict[str, SidebarEntry]` and `self._category_items: dict[str, QTreeWidgetItem]` to `MainWindow.__init__()` |
| TASK-003 | Add backward-compatible `self.pages` property returning `{display_name: page_widget}` |

### Phase 2 — Decompose add_page()

| Task | Description |
|------|-------------|
| TASK-004 | Extract `_find_or_create_category(category: str) -> QTreeWidgetItem` — uses `_category_items` cache, O(1) lookup |
| TASK-005 | Extract `_create_tab_item(category_item, name, icon, badge, description, disabled, disabled_reason) -> QTreeWidgetItem` — creates child item with badge suffix, icon, tooltip |
| TASK-006 | Extract `_register_in_index(plugin_id, entry: SidebarEntry)` — populates `_sidebar_index`, adds to `content_area` |
| TASK-007 | Refactor `add_page()` to be a thin orchestrator calling the 3 helpers + existing `_wrap_page_widget()` |

### Phase 3 — Fix Favorites (ID-based)

| Task | Description |
|------|-------------|
| TASK-008 | Rewrite `_build_favorites_section()` to use `self._sidebar_index[fav_id]` for O(1) lookup |
| TASK-009 | Log `logger.warning("Stale favorite ignored: %s", fav_id)` for unmatched favorites |
| TASK-010 | Remove the nested O(n²) tree traversal loop |

### Phase 4 — Fix Status (data role + delegate)

| Task | Description |
|------|-------------|
| TASK-011 | Create `SidebarItemDelegate(QStyledItemDelegate)` that reads `_ROLE_STATUS` and paints a colored dot (green/amber/red) |
| TASK-012 | Refactor `_set_tab_status(tab_id, status, tooltip)` to use `_sidebar_index[tab_id]` — O(1), no text munging |
| TASK-013 | Update `entry.status` field alongside the data role |
| TASK-014 | Set delegate on sidebar tree widget: `self.sidebar.setItemDelegate(SidebarItemDelegate())` |
| TASK-015 | Update all callers of `_set_tab_status()` to use plugin IDs instead of display names |

### Phase 5 — Experience Level Validation

| Task | Description |
|------|-------------|
| TASK-016 | Add `ExperienceLevelManager.get_all_declared_tab_ids() -> set[str]` combining BEGINNER + INTERMEDIATE lists |
| TASK-017 | Add validation in `_build_sidebar_from_registry()` after index population — log warnings for orphaned and advanced-only IDs |

### Phase 6 — Navigate by ID

| Task | Description |
|------|-------------|
| TASK-018 | Update `navigate_to_tab()` to accept plugin ID (primary) or display name (fallback with deprecation log) |
| TASK-019 | Update internal callers to use plugin IDs |

### Phase 7 — Testing

| Task | Description |
|------|-------------|
| TASK-020 | Create `tests/test_sidebar_index.py` — test SidebarEntry creation, index population, O(1) lookups |
| TASK-021 | Test favorites: ID-based matching, stale favorite logging, icon copying |
| TASK-022 | Test status: delegate rendering, data role storage, no text modification |
| TASK-023 | Test backward compatibility: `self.pages` property returns correct {name: widget} |
| TASK-024 | Test experience level validation: orphaned IDs logged, advanced-only IDs logged |
| TASK-025 | Update existing `main_window.py` tests for plugin ID usage |

### Phase 8 — Documentation & Version

| Task | Description |
|------|-------------|
| TASK-026 | Update ARCHITECTURE.md — document SidebarIndex, SidebarEntry, new add_page() decomposition |
| TASK-027 | Update ROADMAP.md — add v48.0 entry |
| TASK-028 | Run `scripts/bump_version.py` to v48.0.0 |
| TASK-029 | Add loader.py comment clarifying that list order doesn't affect sidebar order |

## 4. Alternatives Considered

- **ALT-001**: Extract full `SidebarWidget` class — cleaner separation but larger scope and higher regression risk. Can be done as v49 follow-up building on the index.
- **ALT-002**: Minimal targeted fixes without index — lowest risk but doesn't address fundamental O(n) scanning or prepare for v47 UX features.
- **ALT-003**: Replace QTreeWidget with QListWidget + collapsible sections — unnecessary visual change, adds risk without fixing the data layer problems.

## 5. Dependencies

- **DEP-001**: `core/plugins/metadata.py` — `PluginMetadata` (read-only, no changes)
- **DEP-002**: `core/plugins/registry.py` — `CATEGORY_ORDER`, `CATEGORY_ICONS` (no changes)
- **DEP-003**: `utils/experience_level.py` — Add `get_all_declared_tab_ids()` method
- **DEP-004**: `ui/base_tab.py` — No changes needed
- **DEP-005**: v46.0 Navigator must be complete (stable baseline)

## 6. Files

| File | Status | Change |
|------|--------|--------|
| `ui/main_window.py` | MODIFIED | Core refactor — SidebarEntry, index, split add_page, favorites, status, delegate |
| `utils/experience_level.py` | MODIFIED | Add `get_all_declared_tab_ids()` |
| `core/plugins/loader.py` | MODIFIED | Add comment about list order |
| `tests/test_sidebar_index.py` | NEW | SidebarEntry, index, favorites, status, backward compat tests |
| `ARCHITECTURE.md` | MODIFIED | Document SidebarIndex |
| `ROADMAP.md` | MODIFIED | Add v48.0 entry |

## 7. Testing

- **TEST-001**: SidebarEntry creation with all fields, default status
- **TEST-002**: Index population from registry — correct plugin IDs, O(1) access
- **TEST-003**: `_find_or_create_category()` — cache hit, cache miss, icon assignment
- **TEST-004**: Favorites — ID match, stale ID warning, icon copy
- **TEST-005**: Status — data role set, entry.status updated, no text change, delegate painting
- **TEST-006**: `self.pages` property — returns {display_name: widget} from index
- **TEST-007**: `navigate_to_tab()` — by ID (primary), by name (fallback), unknown ID
- **TEST-008**: Experience level validation — orphaned IDs, advanced-only IDs
- **TEST-009**: Full regression — existing test suite passes unchanged

## 8. Risks

- **RISK-001**: Plugin code referencing `self.pages[display_name]` will still work via property but is slower (dict rebuild on each access). Mitigated by caching the property result on sidebar rebuild.
- **RISK-002**: Callers of `_set_tab_status("Storage", ...)` with display names will silently fail. Mitigated by updating all callers in the same PR.
- **RISK-003**: SidebarItemDelegate may interact poorly with existing QSS styling. Mitigated by testing with all themes.
