# Tasks for v30.0

- [x] ID: TASK-001 | Files: `scripts/build_flatpak.sh, build_flatpak.sh, org.loofi.FedoraTweaks.yml` | Dep: - | Agent: backend-builder | Description: Implement Flatpak packaging scripts with deterministic build, validation checks, and artifact output.
  Acceptance: Running `bash scripts/build_flatpak.sh` performs prerequisite checks, builds Flatpak, and exits 0 with bundle/repo artifacts when tools are present.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-002 | Files: `scripts/build_appimage.sh` | Dep: - | Agent: backend-builder | Description: Implement AppImage packaging script for Loofi with dependency checks, AppDir/AppImage generation, and predictable output naming.
  Acceptance: Running `bash scripts/build_appimage.sh` validates required tooling and produces a versioned `.AppImage` file in the configured output directory.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-003 | Files: `scripts/build_sdist.sh, pyproject.toml` | Dep: - | Agent: architecture-advisor | Description: Implement source distribution packaging flow and add `pyproject.toml` build-system/project metadata required for sdist creation.
  Acceptance: Running `bash scripts/build_sdist.sh` creates a source tarball under `dist/` via standard Python build tooling.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-004 | Files: `loofi-fedora-tweaks/utils/update_checker.py` | Dep: - | Agent: backend-builder | Description: Extend update checker to support full auto-update flow: detect latest release, select downloadable asset, download artifact, and verify integrity/signature before install handoff.
  Acceptance: Update API returns structured update metadata and exposes download+verify methods that fail closed on network, checksum, or signature errors.
  Docs: none
  Tests: `tests/test_update_checker.py`

- [x] ID: TASK-005 | Files: `loofi-fedora-tweaks/utils/plugin_marketplace.py, loofi-fedora-tweaks/utils/update_checker.py` | Dep: TASK-004 | Agent: backend-builder | Description: Add offline-mode behavior for marketplace and update checker with explicit network-unavailable handling and cache-first fallback.
  Acceptance: When offline is detected or network calls fail, marketplace/update operations return stable offline results without raising unhandled exceptions.
  Docs: none
  Tests: `tests/test_plugin_marketplace_cdn.py, tests/test_update_checker.py`

- [x] ID: TASK-006 | Files: `loofi-fedora-tweaks/utils/rate_limiter.py` | Dep: - | Agent: backend-builder | Description: Fix rate limiter thread coordination using `threading.Event` to avoid busy-wait loops and ensure safe wake/sleep behavior across concurrent callers.
  Acceptance: Concurrent waits do not spin excessively, respect timeout boundaries, and remain race-free under parallel acquire/wait calls.
  Docs: none
  Tests: `tests/test_rate_limiter.py`

- [x] ID: TASK-007 | Files: `loofi-fedora-tweaks/utils/auto_tuner.py` | Dep: - | Agent: backend-builder | Description: Add thread-safety guard(s) for auto-tuner mutable state and history writes to prevent data races during concurrent detect/recommend/apply/history operations.
  Acceptance: Concurrent auto-tuner operations keep history/settings consistent and avoid partial writes or runtime race errors.
  Docs: none
  Tests: `tests/test_auto_tuner.py`

- [x] ID: TASK-008 | Files: `tests/test_packaging_scripts.py` | Dep: TASK-001, TASK-002, TASK-003 | Agent: test-writer | Description: Add/expand packaging tests that mock shell/tooling interactions and validate success/failure paths for Flatpak/AppImage/sdist scripts.
  Acceptance: Test suite verifies prerequisite validation, command composition, and non-zero exits for missing dependencies across all 3 packaging scripts.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-009 | Files: `tests/test_update_checker.py, tests/test_plugin_marketplace_cdn.py` | Dep: TASK-005 | Agent: test-writer | Description: Add regression tests for auto-update download/verify pipeline and offline-mode fallback behavior in update checker and marketplace APIs.
  Acceptance: Tests cover online success, offline fallback, invalid checksum/signature, and network exception paths with deterministic mocked responses.
  Docs: none
  Tests: `tests/test_update_checker.py, tests/test_plugin_marketplace_cdn.py`

- [x] ID: TASK-010 | Files: `tests/test_rate_limiter.py, tests/test_auto_tuner.py` | Dep: TASK-006, TASK-007 | Agent: test-writer | Description: Add concurrency-focused tests for rate limiter and auto-tuner to validate thread safety, timeout guarantees, and state consistency.
  Acceptance: Repeated parallel test runs pass without flakes and assert bounded wait times and consistent shared-state outcomes.
  Docs: none
  Tests: `tests/test_rate_limiter.py, tests/test_auto_tuner.py`

- [x] ID: TASK-011 | Files: `.github/workflows/ci.yml` | Dep: TASK-001, TASK-002, TASK-003, TASK-008, TASK-009, TASK-010 | Agent: architecture-advisor | Description: Harden CI by adding Flatpak/AppImage build jobs, enforcing mypy and bandit as blocking checks, and raising test coverage gate to 75%.
  Acceptance: CI workflow has no `continue-on-error` for mypy/bandit, includes packaging jobs, and test job fails below 75% coverage.
  Docs: none
  Tests: `tests/test_workflow_runner_locks.py`

- [x] ID: TASK-012 | Files: `CHANGELOG.md, README.md, docs/releases/RELEASE-NOTES-v30.0.0.md` | Dep: TASK-011 | Agent: release-planner | Description: Document v30.0 distribution/reliability changes, new packaging paths, offline behavior, and CI quality gates in release artifacts.
  Acceptance: Docs describe delivered v30.0 scope, user-facing behavior changes, and verification steps for packaging/update/CI updates.
  Docs: CHANGELOG|README|RELEASE-NOTES
  Tests: `tests/test_release_doc_check.py`
