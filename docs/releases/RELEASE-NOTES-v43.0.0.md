# Release Notes -- v43.0.0 "Stabilization-Only"

**Release Date:** 2026-02-16
**Codename:** Stabilization-Only
**Theme:** Strict compliance hardening -- policy enforcement, runtime cleanup, CI gate tightening

## Summary

v43.0.0 is a stabilization-only release that formalizes hardening rules as an
enforced policy gate. Runtime paths now comply with timeout requirements, UI
subprocess boundaries, package-manager abstraction requirements, and explicit
broad-exception boundaries.

## Highlights

- Added `scripts/check_stabilization_rules.py` (AST checker) for timeout, UI subprocess, hardcoded executable `dnf`, and broad-exception allowlist rules
- Enforced stabilization checker in CI, coverage-gate, and auto-release workflows
- Standardized all workflow coverage thresholds to **80**
- Extracted First-Run Wizard health checks to `utils/wizard_health.py` (UI now has zero subprocess logic for health checks)
- Removed remaining executable hardcoded `dnf` command paths from package/update/health/export stacks
- Narrowed broad exception handlers to explicit types, with boundary wrappers documented in checker allowlist

## Changes

### Added

- `scripts/check_stabilization_rules.py`
- `loofi-fedora-tweaks/utils/wizard_health.py`
- `tests/test_check_stabilization_rules.py`
- `tests/test_wizard_health.py`
- `tests/test_v43_stabilization.py`
- `tests/test_version.py`

### Changed

- `.github/workflows/ci.yml`: added stabilization checker job; coverage threshold set to `80`
- `.github/workflows/auto-release.yml`: added stabilization checker job; coverage threshold set to `80`
- `.github/workflows/coverage-gate.yml`: added stabilization checker step; coverage threshold set to `80`
- `loofi-fedora-tweaks/services/hardware/disk.py`: added missing subprocess timeout
- `loofi-fedora-tweaks/ui/wizard.py`: now consumes `WizardHealth` utility output
- Multiple services/utils modules refactored to use `SystemManager.get_package_manager()` for dnf/rpm-ostree awareness

### Fixed

- Regression path where `utils/drift.py` referenced `SystemManager` without import (flake8 failure)
- Compatibility tests for `MainWindow` status indicators now mock `UpdateChecker.check_for_updates()`
- Boundary fallback behavior restored for error notification and "What's New" seen-state persistence

## Stats

- **Tests:** 5878 passed, 35 skipped, 0 failed
- **Coverage:** 82.33% (gate: 80%)
- **Lint:** passed (`flake8` with project config ignores)
- **Type check:** passed (`mypy --ignore-missing-imports`)
- **Policy checker:** passed (`scripts/check_stabilization_rules.py`)

## Upgrade Notes

No intentional breaking changes to CLI surface or UI feature flow.
This release is focused on hardening and policy enforcement only.
