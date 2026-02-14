# Release Notes — v40.0.0 "Foundation"

**Release Date:** 2026-02-14
**Codename:** Foundation
**Theme:** Correctness and safety hardening — timeouts, logging, privilege escalation, shell injection elimination

## Summary

v40.0 "Foundation" is a pure hardening release. Every subprocess call now
has an explicit timeout, every logger call uses `%s` formatting, every
`pkexec sh -c` invocation has been refactored to atomic commands, and all
hardcoded `dnf` references now route through `PrivilegedCommand.dnf()` or
`SystemManager.get_package_manager()` for Fedora Atomic compatibility.

## Highlights

- **Zero `sh -c` patterns** — all 10 `pkexec sh -c` calls refactored to atomic subprocess commands
- **Zero hardcoded `dnf`** — 13 references across 10 utils files replaced with `SystemManager.get_package_manager()` or `PrivilegedCommand.dnf()`
- **Zero f-string logger calls** — 21 calls across 7 files converted to `%s` formatting
- **Zero bare exception handlers** — 141 silent `except` blocks across 52 files now log with `logger.debug()`
- **Subprocess timeout enforcement** — explicit `timeout=` on all remaining subprocess calls
- **AdvancedOps return types** — 4 methods now return `OperationResult` dataclass instead of raw tuples

## Changes

### Security

- Added explicit `timeout=` parameters to all remaining subprocess calls in `core/executor/operations.py` and `utils/safety.py`
- Refactored all 10 `pkexec sh -c` calls to atomic commands across `operations.py`, `security_tab.py`, `software_tab.py`, and `battery.py`
- Replaced all user-facing `sudo dnf` messages with `pkexec dnf` in `utils/ai.py` (4 places) and `utils/ansible_export.py` (2 places)

### Changed

- 21 f-string logger calls converted to `%s` formatting across 7 files
- 13 hardcoded `"dnf"` references replaced with `SystemManager.get_package_manager()` or `PrivilegedCommand.dnf()` across 10 utils files
- `package_manager.py`: 3 of 4 install/remove methods now route through `PrivilegedCommand.dnf()` (rpm-ostree --apply-live path intentionally preserved for its unique fallback logic)
- 4 `AdvancedOps` methods in `core/executor/operations.py` now return `OperationResult` instead of raw command tuples
- CLI handler updated to match new `OperationResult` return types

### Fixed

- 141 silent exception blocks across 52 files now capture and log exceptions
- 3 files with syntax corruption (merged return statements) repaired: `services/system/services.py`, `utils/health_score.py`, `utils/boot_analyzer.py`
- Stale `utils.system` and `utils.disk` imports in `dashboard_tab.py`, `doctor.py`, `main_window.py` migrated to `services.system` and `services.hardware.disk`
- Removed stale release-gate tests (`test_v38_clarity.py`, `test_v39_prism.py`) that hardcoded old version numbers
- Updated `test_clarity_update.py` version assertions to match v40.0.0

## Stats

- **Tests:** 4309 passed, 35 skipped, 0 failed
- **Lint:** 0 errors (flake8)
- **Typecheck:** 0 errors (mypy)
- **Coverage:** 74%

## Upgrade Notes

No user-facing changes. Internal hardening only.
All changes are backward compatible — no plugin or configuration changes required.
