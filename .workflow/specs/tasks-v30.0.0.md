# Tasks for v30.0.0

- [x] ID: TASK-001 | Files: `scripts/build_flatpak.sh, org.loofi.FedoraTweaks.yml` | Dep: - | Agent: backend-builder | Description: Harden Flatpak packaging flow (dependency checks, deterministic output path, manifest validation, versioned artifact naming).
  Acceptance: `bash scripts/build_flatpak.sh` fails fast when required tools/manifest are missing and creates `dist/flatpak/loofi-fedora-tweaks-v<version>.flatpak` on success.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-002 | Files: `tests/test_packaging_scripts.py` | Dep: TASK-001 | Agent: test-writer | Description: Extend Flatpak packaging tests to cover success, missing dependency, missing manifest, and version parse failure paths.
  Acceptance: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_packaging_scripts.py -v` passes with Flatpak-specific assertions for artifact path and non-zero failure exits.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-003 | Files: `scripts/build_appimage.sh, loofi-fedora-tweaks.desktop` | Dep: - | Agent: backend-builder | Description: Harden AppImage packaging flow (linuxdeploy discovery, input file guards, reproducible AppDir layout, versioned artifact output).
  Acceptance: `bash scripts/build_appimage.sh` exits non-zero for missing tools/assets and creates `dist/appimage/loofi-fedora-tweaks-v<version>-x86_64.AppImage` when dependencies are available.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-004 | Files: `tests/test_packaging_scripts.py` | Dep: TASK-003 | Agent: test-writer | Description: Extend AppImage packaging tests for missing tool handling, linuxdeploy resolution branches, and successful artifact emission.
  Acceptance: AppImage-related tests pass and assert both guardrail errors and success artifact creation.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-005 | Files: `scripts/build_sdist.sh, pyproject.toml` | Dep: - | Agent: architecture-advisor | Description: Finalize sdist packaging contract (PEP 621 metadata completeness, build backend config, versioned tarball expectation, clean dist handling).
  Acceptance: `bash scripts/build_sdist.sh` produces `dist/loofi_fedora_tweaks-<version>.tar.gz` and fails with a clear error when Python build module is unavailable.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-006 | Files: `tests/test_packaging_scripts.py` | Dep: TASK-005 | Agent: test-writer | Description: Add/adjust sdist test coverage for missing build module, build invocation correctness, and expected tarball naming.
  Acceptance: sdist test cases pass and verify command behavior plus tarball existence checks.
  Docs: none
  Tests: `tests/test_packaging_scripts.py`

- [x] ID: TASK-007 | Files: `loofi-fedora-tweaks/utils/update_checker.py, loofi-fedora-tweaks/cli/main.py` | Dep: - | Agent: backend-builder | Description: Implement end-to-end auto-update flow (detect latest release, select artifact, download, checksum/signature verification, CLI entrypoint wiring).
  Acceptance: Auto-update command path returns structured success/failure results without UI subprocess calls and supports rpm/flatpak/AppImage asset preference.
  Docs: none
  Tests: `tests/test_update_checker.py`

- [x] ID: TASK-008 | Files: `tests/test_update_checker.py` | Dep: TASK-007 | Agent: test-writer | Description: Add tests for auto-update orchestration: update available/unavailable, download failure, checksum mismatch, signature failure, and success path.
  Acceptance: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_update_checker.py -v` passes with mocked network/subprocess interactions only.
  Docs: none
  Tests: `tests/test_update_checker.py`

- [x] ID: TASK-009 | Files: `loofi-fedora-tweaks/utils/update_checker.py, loofi-fedora-tweaks/utils/plugin_marketplace.py` | Dep: TASK-007 | Agent: backend-builder | Description: Implement offline mode behavior for update checker and marketplace (cached fallback, explicit offline/source flags, stable user-facing errors).
  Acceptance: Network failures return cached/offline-aware results with `offline=True` and deterministic `source` metadata instead of hard failure when cache exists.
  Docs: none
  Tests: `tests/test_update_checker.py, tests/test_plugin_marketplace.py`

- [x] ID: TASK-010 | Files: `tests/test_update_checker.py, tests/test_plugin_marketplace.py` | Dep: TASK-009 | Agent: test-writer | Description: Add offline-mode regression tests for cache hit/miss behavior and error mapping consistency across marketplace/update flows.
  Acceptance: Offline-path test cases pass and assert `offline`/`source` field correctness for both modules.
  Docs: none
  Tests: `tests/test_update_checker.py, tests/test_plugin_marketplace.py`

- [x] ID: TASK-011 | Files: `loofi-fedora-tweaks/utils/rate_limiter.py, loofi-fedora-tweaks/utils/auto_tuner.py` | Dep: - | Agent: backend-builder | Description: Apply thread-safety fixes for rate limiter waits and auto-tuner history read/write paths to prevent race conditions under concurrent callers.
  Acceptance: Concurrent invocation paths avoid deadlock/data races and preserve bounded wait behavior plus consistent history file contents.
  Docs: none
  Tests: `tests/test_rate_limiter.py, tests/test_auto_tuner.py`

- [x] ID: TASK-012 | Files: `tests/test_rate_limiter.py, tests/test_auto_tuner.py` | Dep: TASK-011 | Agent: test-writer | Description: Add concurrency-focused tests for rate limiter timeout/wait behavior and auto-tuner history lock correctness under parallel calls.
  Acceptance: New threading tests pass reliably across repeated runs and fail on intentionally unsafe lock regressions.
  Docs: none
  Tests: `tests/test_rate_limiter.py, tests/test_auto_tuner.py`

- [x] ID: TASK-013 | Files: `.github/workflows/ci.yml, .github/workflows/auto-release.yml` | Dep: TASK-002, TASK-004, TASK-006, TASK-008, TASK-010, TASK-012 | Agent: architecture-advisor | Description: Harden CI/release workflows: enforce mypy + bandit without soft-fail flags, keep Flatpak/AppImage/sdist jobs active, and gate tests at 75% coverage.
  Acceptance: Workflow definitions contain no `|| true` for type/security gates and test coverage threshold is set to `--cov-fail-under=75` in both CI and release pipelines.
  Docs: none
  Tests: `tests/test_release_doc_check.py`

- [x] ID: TASK-014 | Files: `tests/test_update_checker.py, tests/test_plugin_marketplace.py, tests/test_packaging_scripts.py, tests/test_rate_limiter.py, tests/test_auto_tuner.py` | Dep: TASK-013 | Agent: test-writer | Description: Close remaining v30 coverage gaps in touched reliability/distribution modules to hold repository-wide 75% coverage threshold.
  Acceptance: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov=loofi-fedora-tweaks --cov-fail-under=75` passes.
  Docs: none
  Tests: `tests/test_update_checker.py, tests/test_plugin_marketplace.py, tests/test_packaging_scripts.py, tests/test_rate_limiter.py, tests/test_auto_tuner.py`

- [x] ID: TASK-015 | Files: `CHANGELOG.md, README.md, docs/releases/RELEASE-NOTES-v30.0.0.md` | Dep: TASK-014 | Agent: release-planner | Description: Document v30.0 distribution/reliability outcomes (packaging scripts, auto-update, offline mode, thread safety, CI gates, coverage target).
  Acceptance: CHANGELOG, README, and v30.0.0 release notes explicitly describe delivered behavior and verification commands for users/release checks.
  Docs: CHANGELOG
  Tests: `tests/test_release_doc_check.py`
