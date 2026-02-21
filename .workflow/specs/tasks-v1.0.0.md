# Tasks — v1.0.0 "Foundation"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json, version.py, pyproject.toml, .spec` | Dep: - | Agent: project-coordinator | Description: Version renormalization from v50.0.0 to v1.0.0 Foundation. Reset SemVer, update race lock, promote to Production/Stable.
  Acceptance: Version files in sync at 1.0.0; race lock targets v1.0.0; pyproject classifiers show Production/Stable.
  Docs: CHANGELOG, README
  Tests: none

## Phase: Build — Test Expansion

- [x] ID: TASK-002 | Files: `tests/test_log.py` | Dep: TASK-001 | Agent: code-implementer | Description: Add unit test suite for centralized logging configuration, XDG path handling, and root logger setup.
  Acceptance: test_log.py passes with full coverage of log module initialization paths.
  Docs: none
  Tests: test_log.py

- [x] ID: TASK-003 | Files: `tests/test_monitor.py` | Dep: TASK-001 | Agent: code-implementer | Description: Add unit test suite for SystemMonitor — bytes_to_human, get_memory_info, get_cpu_info, system health checks.
  Acceptance: test_monitor.py passes with coverage of all SystemMonitor public methods.
  Docs: none
  Tests: test_monitor.py

## Phase: Build — Test Fix

- [x] ID: TASK-004 | Files: `tests/test_plugins_v2.py` | Dep: TASK-001 | Agent: code-implementer | Description: Fix plugin version compatibility test to decouple from runtime APP_VERSION using @patch decorator.
  Acceptance: test_plugins_v2.py passes regardless of current version value.
  Docs: none
  Tests: existing tests pass

## Phase: Build — Bug Fix

- [x] ID: TASK-005 | Files: `scripts/generate_workflow_reports.py` | Dep: TASK-001 | Agent: code-implementer | Description: Fix Unicode encoding crash (cp1252) on Windows by replacing Unicode checkmark/cross with ASCII equivalents in check_only output.
  Acceptance: generate_workflow_reports.py --check runs without UnicodeEncodeError on Windows.
  Docs: none
  Tests: none

## Phase: Doc

- [x] ID: TASK-006 | Files: `CHANGELOG.md, README.md, CLAUDE.md, docs/releases/RELEASE-NOTES-v1.0.0.md` | Dep: TASK-001..TASK-005 | Agent: project-coordinator | Description: Finalize CHANGELOG entry, update README header/badges, update CLAUDE.md version, write release notes.
  Acceptance: All documentation reflects v1.0.0 Foundation; release notes complete.
  Docs: CHANGELOG, README, RELEASE-NOTES
  Tests: none

## Phase: Release

- [x] ID: TASK-007 | Files: - | Dep: TASK-006 | Agent: project-coordinator | Description: Tag v1.0.0, push, create GitHub release with artifacts (RPM, sdist, AppImage).
  Acceptance: GitHub release live at v1.0.0 with all package artifacts attached.
  Docs: none
  Tests: none
