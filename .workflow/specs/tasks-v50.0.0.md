# Tasks — v50.0.0 "Forge"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json, version.py, pyproject.toml, .spec` | Dep: - | Agent: project-coordinator | Description: Version bump to v50.0.0 Forge, activate roadmap entry, update race lock.
  Acceptance: Version files in sync at 50.0.0; race lock targets v50.0.0; ROADMAP has v50 as ACTIVE.
  Docs: ROADMAP
  Tests: none

## Phase: Build — Module Docstrings

- [x] ID: TASK-002 | Files: `utils/__init__.py, utils/action_executor.py, utils/action_result.py, utils/command_runner.py, utils/fingerprint.py, utils/history.py, utils/operations.py, utils/presets.py, utils/remote_config.py` | Dep: TASK-001 | Agent: code-implementer | Description: Add missing Google-style module-level docstrings to 9 utils modules.
  Acceptance: All 9 modules have module-level docstrings. No functional changes.
  Docs: none
  Tests: none

## Phase: Build — Exception Narrowing

- [x] ID: TASK-003 | Files: `utils/error_handler.py` | Dep: TASK-001 | Agent: backend-builder | Description: Narrow `except Exception` at ~L112 to specific exception types.
  Acceptance: Broad handler replaced with specific types; error handling behavior preserved.
  Docs: none
  Tests: existing tests pass

- [x] ID: TASK-004 | Files: `utils/event_bus.py` | Dep: TASK-001 | Agent: backend-builder | Description: Narrow `except Exception` at ~L174 to specific exception types.
  Acceptance: Broad handler replaced with specific types; event bus resilience preserved.
  Docs: none
  Tests: existing tests pass

- [x] ID: TASK-005 | Files: `utils/daemon.py` | Dep: TASK-001 | Agent: backend-builder | Description: Narrow `except Exception` at ~L254 to specific exception types. Preserve daemon resilience.
  Acceptance: Handler narrowed; daemon main loop remains robust against unexpected failures.
  Docs: none
  Tests: existing tests pass

- [x] ID: TASK-006 | Files: `ui/lazy_widget.py` | Dep: TASK-001 | Agent: frontend-integration-builder | Description: Narrow `except Exception` at ~L57 to specific exception types.
  Acceptance: Broad handler replaced; lazy widget loading error handling preserved.
  Docs: none
  Tests: existing tests pass

## Phase: Build — Test Coverage Expansion

- [x] ID: TASK-007 | Files: `tests/test_action_result.py` | Dep: TASK-001 | Agent: test-writer | Description: Create comprehensive test suite for `utils/action_result.py` dataclass.
  Acceptance: Dedicated test file with full coverage of ActionResult fields, equality, repr.
  Docs: none
  Tests: `tests/test_action_result.py`

- [x] ID: TASK-008 | Files: `tests/test_errors.py` | Dep: TASK-001 | Agent: test-writer | Description: Create comprehensive test suite for `utils/errors.py` error hierarchy.
  Acceptance: Tests cover all error classes, attributes (code, hint, recoverable), inheritance.
  Docs: none
  Tests: `tests/test_errors.py`

- [x] ID: TASK-009 | Files: `tests/test_event_simulator.py` | Dep: TASK-001 | Agent: test-writer | Description: Create comprehensive test suite for `utils/event_simulator.py`.
  Acceptance: Tests cover event simulation with mocked system calls.
  Docs: none
  Tests: `tests/test_event_simulator.py`

- [x] ID: TASK-010 | Files: `tests/test_presets.py` | Dep: TASK-001 | Agent: test-writer | Description: Create comprehensive test suite for `utils/presets.py`.
  Acceptance: Tests cover preset CRUD, validation, edge cases.
  Docs: none
  Tests: `tests/test_presets.py`

- [x] ID: TASK-011 | Files: `tests/test_remote_config.py` | Dep: TASK-001 | Agent: test-writer | Description: Create comprehensive test suite for `utils/remote_config.py`.
  Acceptance: Tests cover config fetching, caching, error paths with mocked network.
  Docs: none
  Tests: `tests/test_remote_config.py`

## Phase: Build — Coverage Push

- [x] ID: TASK-012 | Files: `tests/` | Dep: TASK-007,TASK-008,TASK-009,TASK-010,TASK-011 | Agent: test-writer | Description: Identify and test additional low-coverage modules to push total coverage toward 80%.
  Acceptance: Coverage at or above 80% threshold after all new tests.
  Docs: none
  Tests: new test files as identified

## Phase: Doc

- [x] ID: TASK-013 | Files: `CHANGELOG.md, ROADMAP.md, docs/releases/RELEASE-NOTES-v50.0.0.md` | Dep: TASK-012 | Agent: release-planner | Description: Finalize CHANGELOG, mark ROADMAP v50 as DONE, complete release notes.
  Acceptance: All docs complete; CHANGELOG has v50.0.0 entry; ROADMAP shows DONE.
  Docs: CHANGELOG, ROADMAP, release notes
  Tests: none

## Phase: Release

- [x] ID: TASK-014 | Files: `README.md` | Dep: TASK-013 | Agent: release-planner | Description: Update README version references and verify full test suite, lint, and build.
  Acceptance: README reflects v50.0.0; all CI gates pass.
  Docs: README
  Tests: full suite
