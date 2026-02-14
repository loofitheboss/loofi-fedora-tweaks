# Release Notes — v39.0.0 "Prism"

**Release Date:** 2026-02-14
**Codename:** Prism
**Theme:** Deprecated import migration, inline style elimination, service layer completion

## Summary

v39.0 "Prism" completes the services layer migration started in v23.0.
All deprecated `utils/` import shims have been removed, 175+ inline
`setStyleSheet` calls replaced with QSS objectNames, and the test suite
runs with zero DeprecationWarnings under strict enforcement.

## Highlights

- **Zero deprecated imports** — 27 production + 13 test file imports migrated from `utils.*` to `services.*`
- **Zero inline styles** — 175+ `setStyleSheet` calls replaced with `setObjectName` + QSS rules across 31 UI files
- **Zero DeprecationWarnings** — test suite passes with `-W error::DeprecationWarning`
- **9 shim modules removed** — `utils/system.py`, `utils/hardware.py`, `utils/bluetooth.py`, `utils/disk.py`, `utils/temperature.py`, `utils/processes.py`, `utils/services.py`, `utils/hardware_profiles.py`, `services/system/process.py`
- **~600 new QSS rules** in both `modern.qss` (dark) and `light.qss` (Catppuccin Latte)

## Changes

### Changed
- 14 production files: `from utils.(system|hardware|bluetooth|disk|temperature|processes|services|hardware_profiles)` → `from services.(system|hardware)`
- 12 test files: 127+ `@patch('utils.*')` decorators → `services.*` paths
- 31 UI files: inline `setStyleSheet` → `setObjectName` + QSS property selectors
- Dynamic styling uses `setProperty("state", value)` + `unpolish/polish` pattern

### Removed
- 9 deprecated shim modules (see Highlights)
- 175+ inline `setStyleSheet` calls

### Added
- `tests/test_v39_prism.py` — 18 migration verification tests
- ~600 QSS rules in `modern.qss` for v39.0 Prism objectNames
- ~600 QSS rules in `light.qss` for v39.0 Prism objectNames

### Fixed
- httpx deprecation in `test_api_server.py` (`data=` → `content=b"..."`)
- Forward-compatible version assertions in `test_v38_clarity.py`
- `services/system/__init__.py` CommandRunner import (bypasses deleted shim)

## Stats

- **Tests:** 4367 passed, 35 skipped, 0 failed
- **Lint:** 0 errors (flake8)
- **DeprecationWarnings:** 0 (strict enforcement)
- **setStyleSheet calls remaining:** 1 (intentional global theme loader in main_window.py)

## Upgrade Notes

No user-facing changes. Internal refactoring only.
If you have custom plugins importing from deprecated `utils.*` paths,
update them to use `services.system` or `services.hardware` equivalents.
