# Tasks — v45.0.0 "Housekeeping"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/tasks-v45.0.0.md` | Dep: - | Agent: project-coordinator | Description: Re-scope v45.0.0 as a stability-first release and keep single active roadmap target aligned with the current race lock.
  Acceptance: Roadmap marks v45 as `[ACTIVE]`, v44 as `[DONE]`, and task file reflects the full v45 execution plan.
  Docs: ROADMAP
  Tests: none

## Phase: Build

- [x] ID: TASK-002 | Files: `loofi-fedora-tweaks/utils/network_monitor.py, loofi-fedora-tweaks/utils/performance.py` | Dep: TASK-001 | Agent: backend-builder | Description: Fix current lint blockers in runtime modules with minimal, no-behavior-change edits.
  Acceptance: Existing E203 violations are removed without altering runtime logic.
  Docs: none
  Tests: `flake8 loofi-fedora-tweaks/ --jobs=1 --max-line-length=150 --ignore=E501,W503,E402,E722`

- [x] ID: TASK-003 | Files: `loofi-fedora-tweaks/utils/install_hints.py, loofi-fedora-tweaks/ui/backup_tab.py, loofi-fedora-tweaks/utils/containers.py, loofi-fedora-tweaks/utils/state_teleport.py` | Dep: TASK-001 | Agent: backend-builder | Description: Add package-manager-aware install hint helper and integrate it into user-facing tool-not-installed flows.
  Acceptance: All touched flows produce `pkexec`-based, package-manager-aware install hints with no hardcoded `sudo dnf` text.
  Docs: none
  Tests: `tests/test_install_hints.py, tests/test_backup_tab.py, tests/test_containers_deep.py, tests/test_teleport.py`

- [x] ID: TASK-004 | Files: `loofi-fedora-tweaks/utils/errors.py, loofi-fedora-tweaks/utils/usbguard.py` | Dep: TASK-001 | Agent: backend-builder | Description: Replace remaining unsafe sudo guidance with safe operational hints for lock recovery and usbguard restart instructions.
  Acceptance: Touched messages contain no `sudo` and preserve actionable recovery guidance.
  Docs: none
  Tests: `tests/test_v10_features.py, tests/test_error_handler.py, tests/test_usbguard.py`

- [x] ID: TASK-005 | Files: `loofi-fedora-tweaks/ui/whats_new_dialog.py` | Dep: TASK-001 | Agent: backend-builder | Description: Narrow broad catch in `mark_seen()` to explicit expected exception types while preserving fail-safe behavior.
  Acceptance: `mark_seen()` still never raises for expected settings failures and no longer uses broad `except Exception`.
  Docs: none
  Tests: `tests/test_ui_tab_smoke.py`

## Phase: Test

- [x] ID: TASK-006 | Files: `tests/test_install_hints.py` | Dep: TASK-003 | Agent: test-writer | Description: Add focused tests for package-manager-aware install hint generation.
  Acceptance: Tests validate dnf and rpm-ostree hint outputs.
  Docs: none
  Tests: self

- [x] ID: TASK-007 | Files: `tests/test_backup_tab.py, tests/test_containers_deep.py, tests/test_teleport.py, tests/test_usbguard.py` | Dep: TASK-003,TASK-004 | Agent: test-writer | Description: Extend module tests to assert updated safe guidance text paths.
  Acceptance: Tests cover new runtime messages and ensure no regressions in existing behavior.
  Docs: none
  Tests: self

- [x] ID: TASK-008 | Files: `tests/test_v10_features.py, tests/test_ui_tab_smoke.py` | Dep: TASK-004,TASK-005 | Agent: test-writer | Description: Update error-hint and WhatsNew failure-path tests to match narrowed exceptions and revised lock guidance.
  Acceptance: Updated tests reflect new hints/exception handling and pass.
  Docs: none
  Tests: self

## Phase: Doc

- [x] ID: TASK-009 | Files: `CHANGELOG.md, docs/releases/RELEASE-NOTES-v45.0.0.md, docs/releases/RELEASE_NOTES.md` | Dep: TASK-006,TASK-007,TASK-008 | Agent: release-planner | Description: Document v45 scope and outcomes with a new release note and latest-index update.
  Acceptance: Changelog and release-notes index include v45.0.0 with stability/compliance/reliability UX summary.
  Docs: CHANGELOG, RELEASE-NOTES
  Tests: `python3 scripts/check_release_docs.py`

## Phase: Release

- [x] ID: TASK-010 | Files: `loofi-fedora-tweaks/version.py, pyproject.toml, loofi-fedora-tweaks.spec, .workflow/specs/.race-lock.json, .workflow/reports/test-results-v45.0.0.json, .workflow/reports/run-manifest-v45.0.0.json` | Dep: TASK-009 | Agent: release-planner | Description: Align version and workflow report artifacts to v45.0.0 release state.
  Acceptance: Version files report 45.0.0, race lock remains v45 active, and v45 report artifacts exist.
  Docs: none
  Tests: `tests/test_version.py`

- [x] ID: TASK-011 | Files: `.workflow/specs/tasks-v45.0.0.md, ROADMAP.md` | Dep: TASK-010 | Agent: project-coordinator | Description: Mark v45 implementation tasks complete and reflect deliverable completion in roadmap checklist.
  Acceptance: Task list complete and roadmap v45 deliverables marked done.
  Docs: ROADMAP
  Tests: none
