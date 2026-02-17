# Release Notes — v48.0.0 "Sidebar Index"

**Release Date**: 2026-02-17
**Codename**: Sidebar Index
**Focus**: Sidebar architecture restructure with O(1) ID-based lookups

---

## Highlights

### SidebarEntry Dataclass & SidebarIndex

- New `SidebarEntry` dataclass holds all per-tab state: `plugin_id`, `display_name`, `tree_item`, `page_widget`, `metadata`, `status`
- `_sidebar_index: dict[str, SidebarEntry]` keyed by `PluginMetadata.id` replaces the old `pages` dict
- Backward-compatible `pages` property returns `{display_name: widget}` view with cache invalidation
- All sidebar lookups (favorites, status, navigation) are now O(1) dict accesses

### add_page() Decomposition

- Monolithic `add_page()` split into three focused helpers:
  - `_find_or_create_category()` — cached category item lookup
  - `_create_tab_item()` — tree item creation with badge, icon, disabled state
  - `_register_in_index()` — populates index, invalidates cache, adds to content area
- `_add_plugin_page()` now uses canonical `meta.id` from PluginMetadata

### Favorites Fix

- `_build_favorites_section()` uses `_sidebar_index.get(fav_id)` for O(1) lookup
- Replaces fragile `name.lower().replace(" ", "_")` heuristic that broke on dash-vs-underscore IDs
- Stale favorites logged as warnings instead of silently failing

### Status Dot Rendering

- `SidebarItemDelegate(QStyledItemDelegate)` paints colored status dots (green/amber/red)
- Status stored via `_ROLE_STATUS` data role instead of text markers like `[OK]`/`[WARN]`/`[ERR]`
- No more text munging — display text stays clean

### O(1) Navigation

- `switch_to_tab()` uses plugin ID as primary lookup with display name fallback
- `_set_tab_status()` uses direct index lookup instead of tree iteration

### Experience Level Validation

- `ExperienceLevelManager.get_all_declared_tab_ids()` returns all declared tab IDs
- Build-time warnings for orphaned references and advanced-only tab IDs
- Catches sync drift between experience level lists and plugin registry

---

## New Files

| File | Type | Description |
|------|------|-------------|
| `tests/test_sidebar_index.py` | Test | 20 tests for SidebarEntry, index, favorites, status, delegate, experience validation |

## Modified Files

| File | Changes |
|------|---------|
| `ui/main_window.py` | SidebarEntry dataclass, SidebarItemDelegate, decomposed add_page, O(1) favorites/status/navigation |
| `utils/experience_level.py` | Added `get_all_declared_tab_ids()`, fixed `is_tab_visible` type hint |
| `core/plugins/loader.py` | Added loader order comment |
| `ARCHITECTURE.md` | Added Sidebar Index section |
| `ROADMAP.md` | Added v48.0 entry |

## Test Results

- **Total tests**: 6036 passed, 35 skipped, 0 failed
- **Coverage**: 81.52%
- **Lint**: 0 errors
- **Type check**: 0 errors in changed files

---

## Upgrade Notes

- No breaking changes — `pages` property maintains backward compatibility
- Existing code accessing `self.pages[display_name]` continues to work
- Tab IDs in favorites config are now validated; stale entries logged as warnings
- Status indicators switch from text markers to colored dots (visual change only)
