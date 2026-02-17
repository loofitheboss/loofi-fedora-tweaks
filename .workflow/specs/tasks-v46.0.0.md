# Tasks — v46.0.0 "Navigator"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json` | Dep: - | Agent: project-coordinator | Description: Transition active roadmap target and race lock to v46.0.0 Navigator.
  Acceptance: Roadmap includes v46 as `[ACTIVE]` and race lock targets `v46.0.0`.
  Docs: ROADMAP
  Tests: none

## Phase: Build

- [x] ID: TASK-002 | Files: `loofi-fedora-tweaks/core/plugins/registry.py` | Dep: TASK-001 | Agent: backend-builder | Description: Replace legacy sidebar category taxonomy with the technical category model used for v46.
  Acceptance: `CATEGORY_ORDER` and `CATEGORY_ICONS` define `System, Packages, Hardware, Network, Security, Appearance, Tools, Maintenance`.
  Docs: none
  Tests: `tests/test_main_window.py, tests/test_plugins.py`

- [x] ID: TASK-003 | Files: `loofi-fedora-tweaks/ui/*_tab.py` (metadata updates) | Dep: TASK-002 | Agent: frontend-integration-builder | Description: Align tab `_METADATA.category` and ordering with the new taxonomy and remove orphan/legacy category strings.
  Acceptance: All built-in tabs map to defined categories; no orphan category labels remain.
  Docs: none
  Tests: `tests/test_backup_tab.py, tests/test_community_tab.py, tests/test_development_tab.py, tests/test_diagnostics_tab.py, tests/test_maintenance_tab.py, tests/test_monitor_tab.py, tests/test_network_tab.py`

- [x] ID: TASK-004 | Files: `loofi-fedora-tweaks/ui/command_palette.py` | Dep: TASK-003 | Agent: frontend-integration-builder | Description: Align command palette display categories with the sidebar taxonomy for discoverability consistency.
  Acceptance: Palette category labels no longer use old taxonomy labels and lint remains clean.
  Docs: none
  Tests: `tests/test_main_window.py, flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203`

## Phase: Test

- [x] ID: TASK-005 | Files: `tests/test_backup_tab.py, tests/test_community_tab.py, tests/test_development_tab.py, tests/test_diagnostics_tab.py, tests/test_maintenance_tab.py, tests/test_monitor_tab.py, tests/test_network_tab.py` | Dep: TASK-003,TASK-004 | Agent: test-writer | Description: Update metadata assertions for the new category mapping.
  Acceptance: Updated tests assert new category values and pass.
  Docs: none
  Tests: self

- [x] ID: TASK-006 | Files: repository-wide | Dep: TASK-005 | Agent: test-writer | Description: Validate full project quality gates after taxonomy changes.
  Acceptance: Full test suite and lint pass.
  Docs: none
  Tests: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q --tb=short`, `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203`

## Phase: Doc

- [x] ID: TASK-007 | Files: `ARCHITECTURE.md, wiki/GUI-Tabs-Reference.md, CHANGELOG.md, docs/releases/RELEASE-NOTES-v46.0.0.md` | Dep: TASK-006 | Agent: release-planner | Description: Document v46 category/navigation release scope and outcomes.
  Acceptance: Docs and changelog reflect v46 taxonomy and release summary.
  Docs: ARCHITECTURE, CHANGELOG, RELEASE-NOTES
  Tests: `python3 scripts/check_release_docs.py`

## Phase: Release

- [x] ID: TASK-008 | Files: `loofi-fedora-tweaks/version.py, pyproject.toml, loofi-fedora-tweaks.spec, .workflow/specs/.race-lock.json, .workflow/reports/test-results-v46.0.json, .workflow/reports/run-manifest-v46.0.json` | Dep: TASK-007 | Agent: release-planner | Description: Align version artifacts and workflow reports to v46.0.0 release state.
  Acceptance: Version files, race lock, and report artifacts are present and aligned to v46.0.0.
  Docs: none
  Tests: `tests/test_version.py`
