# Tasks — v48.0.0 "Sidebar Index"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json` | Dep: - | Agent: project-coordinator | Description: Transition active roadmap target and race lock to v48.0.0 Sidebar Index.
  Acceptance: Roadmap includes v48 as `[ACTIVE]` and race lock targets `v48.0.0`.
  Docs: ROADMAP
  Tests: none

## Phase: Build

- [x] ID: TASK-002 | Files: `loofi-fedora-tweaks/ui/main_window.py` | Dep: TASK-001 | Agent: backend-builder | Description: Add SidebarEntry dataclass and SidebarIndex infrastructure with backward-compatible pages property.
  Acceptance: SidebarEntry holds plugin_id, display_name, tree_item, page_widget, metadata, status; _sidebar_index dict replaces pages dict.
  Docs: ARCHITECTURE.md
  Tests: `tests/test_sidebar_index.py`

- [x] ID: TASK-003 | Files: `loofi-fedora-tweaks/ui/main_window.py` | Dep: TASK-002 | Agent: backend-builder | Description: Decompose monolithic add_page() into _find_or_create_category(), _create_tab_item(), and _register_in_index() helpers.
  Acceptance: add_page() is a thin orchestrator; _add_plugin_page() uses canonical meta.id.
  Docs: none
  Tests: `tests/test_sidebar_index.py`

- [x] ID: TASK-004 | Files: `loofi-fedora-tweaks/ui/main_window.py` | Dep: TASK-003 | Agent: backend-builder | Description: Fix favorites with O(1) ID-based lookup replacing fragile name heuristic. Log stale favorites.
  Acceptance: _build_favorites_section() uses _sidebar_index.get(fav_id) directly; stale favorites logged as warnings.
  Docs: none
  Tests: `tests/test_sidebar_index.py`

- [x] ID: TASK-005 | Files: `loofi-fedora-tweaks/ui/main_window.py` | Dep: TASK-003 | Agent: backend-builder | Description: Fix _set_tab_status() with O(1) lookup and data role storage. Add SidebarItemDelegate for colored status dots.
  Acceptance: Status stored via data role; SidebarItemDelegate paints green/amber/red dots; no text munging.
  Docs: none
  Tests: `tests/test_sidebar_index.py`

- [x] ID: TASK-006 | Files: `loofi-fedora-tweaks/ui/main_window.py` | Dep: TASK-003 | Agent: backend-builder | Description: Fix switch_to_tab() with O(1) plugin ID lookup and display name fallback.
  Acceptance: Primary lookup by plugin ID; fallback by display_name with deprecation log.
  Docs: none
  Tests: `tests/test_sidebar_index.py`

- [x] ID: TASK-007 | Files: `loofi-fedora-tweaks/utils/experience_level.py, loofi-fedora-tweaks/ui/main_window.py` | Dep: TASK-003 | Agent: backend-builder | Description: Add experience level sync validation with get_all_declared_tab_ids() and build-time warnings.
  Acceptance: Orphaned and advanced-only tab IDs logged at sidebar build time.
  Docs: none
  Tests: `tests/test_sidebar_index.py`

- [x] ID: TASK-008 | Files: `loofi-fedora-tweaks/ui/main_window.py, loofi-fedora-tweaks/core/plugins/loader.py` | Dep: TASK-006,TASK-007 | Agent: backend-builder | Description: Update closeEvent, _rebuild_sidebar, add loader order comment, final cleanup.
  Acceptance: closeEvent iterates _sidebar_index; rebuild clears all caches; loader has order comment.
  Docs: none
  Tests: existing

## Phase: Test

- [x] ID: TASK-009 | Files: `tests/test_sidebar_index.py` | Dep: TASK-008 | Agent: test-writer | Description: Full regression test — 6036 tests pass, 81.52% coverage, linter clean, mypy clean.
  Acceptance: All tests pass; coverage >= 80%; no lint or type errors in changed files.
  Docs: none
  Tests: self

## Phase: Doc

- [x] ID: TASK-010 | Files: `ARCHITECTURE.md, ROADMAP.md, CHANGELOG.md, docs/releases/RELEASE-NOTES-v48.0.0.md` | Dep: TASK-009 | Agent: release-planner | Description: Document v48 sidebar index restructure scope and outcomes.
  Acceptance: Docs and changelog reflect v48 features and release summary.
  Docs: CHANGELOG, RELEASE-NOTES, ARCHITECTURE, ROADMAP
  Tests: none

## Phase: Release

- [x] ID: TASK-011 | Files: `loofi-fedora-tweaks/version.py, pyproject.toml, loofi-fedora-tweaks.spec, .workflow/specs/.race-lock.json` | Dep: TASK-010 | Agent: release-planner | Description: Align version artifacts and workflow reports to v48.0.0 release state.
  Acceptance: Version files and race lock are aligned to v48.0.0.
  Docs: none
  Tests: `tests/test_version.py`
