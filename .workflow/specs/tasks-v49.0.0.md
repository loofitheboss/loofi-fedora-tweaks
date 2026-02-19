# Tasks — v49.0.0 "Shield"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json` | Dep: - | Agent: project-coordinator | Description: Transition active roadmap target and race lock to v49.0.0 Shield.
  Acceptance: Roadmap includes v49 as `[ACTIVE]` and race lock targets `v49.0.0`.
  Docs: ROADMAP
  Tests: none

## Phase: Build

- [x] ID: TASK-002 | Files: `tests/test_formatting.py` | Dep: TASK-001 | Agent: test-writer | Description: Create comprehensive test suite for formatting utilities (bytes_to_human, seconds_to_human, percent_bar, truncate).
  Acceptance: 26 tests covering all formatting functions with edge cases; coverage rises from 0%.
  Docs: none
  Tests: `tests/test_formatting.py`

- [x] ID: TASK-003 | Files: `tests/test_battery_service.py` | Dep: TASK-001 | Agent: test-writer | Description: Create test suite for BatteryManager.set_limit covering success, failure steps, OSError, SubprocessError, timeout enforcement.
  Acceptance: 13 tests covering all failure paths; coverage rises from 24%.
  Docs: none
  Tests: `tests/test_battery_service.py`

- [x] ID: TASK-004 | Files: `tests/test_update_manager.py` | Dep: TASK-001 | Agent: test-writer | Description: Enhance update_manager tests with proper shutil.which + SystemManager mocking, DNF not found and OSError paths. Deduplicate stale tests.
  Acceptance: 28 total tests with clean mocking; coverage rises from 27%.
  Docs: none
  Tests: `tests/test_update_manager.py`

- [x] ID: TASK-005 | Files: `tests/test_plugin_adapter.py` | Dep: TASK-001 | Agent: test-writer | Description: Expand plugin_adapter tests with lifecycle, slugify, version compat, CLI commands, check_compat manifest/permissions, context, integration.
  Acceptance: 53 total tests covering all adapter functionality; coverage rises from 30%.
  Docs: none
  Tests: `tests/test_plugin_adapter.py`

## Phase: Doc

- [x] ID: TASK-006 | Files: `CHANGELOG.md, ROADMAP.md, loofi-fedora-tweaks/version.py, loofi-fedora-tweaks.spec, pyproject.toml` | Dep: TASK-005 | Agent: release-planner | Description: Version bump to v49.0.0, update CHANGELOG and ROADMAP.
  Acceptance: Version files in sync; CHANGELOG has v49.0.0 entry; ROADMAP shows v49.0 as DONE.
  Docs: CHANGELOG, ROADMAP
  Tests: none

## Phase: Release

- [x] ID: TASK-007 | Files: `README.md, docs/releases/RELEASE-NOTES-v49.0.0.md, .workflow/reports/` | Dep: TASK-006 | Agent: release-planner | Description: Update README, generate workflow reports, tag and push v49.0.0.
  Acceptance: README reflects v49.0.0; release notes exist; tag v49.0.0 pushed.
  Docs: README, RELEASE-NOTES
  Tests: none
