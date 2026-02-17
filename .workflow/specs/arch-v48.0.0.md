# Architecture Spec - v48.0.0 "Sidebar Index"

## Design Rationale

v48.0.0 is a sidebar architecture release. The objective is to replace O(n) sidebar
tree scans with a centralized `SidebarIndex` dict keyed by plugin ID, fixing fragile
favorites matching, status string munging, monolithic add_page(), experience level
sync drift, and misleading loader list ordering.

## Scope

1. SidebarEntry dataclass — centralized per-tab state container.
2. SidebarIndex — O(1) lookups for all sidebar operations.
3. Favorites fix — ID-based matching replacing name heuristics.
4. Status rendering — data roles + SidebarItemDelegate colored dots.
5. Experience level validation — build-time sync warnings.

## Key Decisions

### SidebarEntry Dataclass

Mutable dataclass holding `plugin_id`, `display_name`, `tree_item`, `page_widget`,
`metadata` (PluginMetadata), and `status` (mutable string). Keyed by `PluginMetadata.id`
in `_sidebar_index: dict[str, SidebarEntry]`.

### Backward-Compatible Pages Property

`self.pages` property returns `{display_name: widget}` view with cache invalidation.
Existing code that accesses `self.pages` continues to work without modification.

### add_page() Decomposition

Split into three focused helpers:
- `_find_or_create_category()` — cached O(1) category item lookup
- `_create_tab_item()` — tree item creation with badge, icon, disabled state
- `_register_in_index()` — populates index, invalidates cache, adds to content area

### Status Dot Rendering

`SidebarItemDelegate(QStyledItemDelegate)` paints colored circles (green/amber/red)
using `_ROLE_STATUS` data role instead of text markers like `[OK]`/`[WARN]`/`[ERR]`.

### Experience Level Validation

`ExperienceLevelManager.get_all_declared_tab_ids()` returns the superset of tab IDs.
At build time, orphaned references and advanced-only tabs are logged as warnings.

## Risks

- Backward compatibility: Mitigated by `pages` property with cache.
- Plugin compatibility: `_add_plugin_page()` uses canonical `meta.id`.
- Performance: O(1) lookups improve on O(n) tree scans.

## Testing

- 20 new tests in `tests/test_sidebar_index.py`
- Full suite: 6036 passed, 81.52% coverage
- Linter: clean, Type checker: clean (our files)
