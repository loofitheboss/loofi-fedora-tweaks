# Release Notes — v33.0.0 "Bastion"

**Release date:** 2025-07-17

## Overview

v33.0.0 is a testing and CI hardening release. All pre-existing mypy type errors have been
eliminated (163 → 0), all test failures resolved (3958 tests passing), and CI gates made strict.

## Highlights

### Zero Type Errors

- Fixed 163 mypy type errors across 40+ source files.
- Added `from __future__ import annotations` for modern union syntax.
- Proper `dict[str, Any]` annotations, `cast()` calls for Qt types, `Optional` wrappers.
- Establishes a clean type-safety baseline for future development.

### All Tests Passing

- 3958 tests passing, 0 failing (was 5 pre-existing failures).
- Fixed `SecurityTab` static method calls — was using `self.make_table_item()` on a
  non-`BaseTab` class, now correctly uses `BaseTab.make_table_item()`.
- Fixed `pulse.py` upower parsing — `get_power_state()` whitespace handling with
  `split(":", 1)[1].strip()`.
- Fixed test isolation issues in `test_packaging_scripts.py`, `test_frameless_mode_flag.py`,
  `test_main_window_geometry.py`, and `test_workflow_runner_locks.py`.

### CI Gates Strict

- Verified `continue-on-error` was already removed from typecheck and test jobs.
- All CI gates now enforced — no silent failures.

## Changed Files

- `loofi-fedora-tweaks/version.py` — 33.0.0 "Bastion"
- `loofi-fedora-tweaks.spec` — Version 33.0.0
- 40+ source files — type annotation fixes
- `ui/security_tab.py` — static method call fixes
- `utils/pulse.py` — upower parsing fix
- `tests/test_packaging_scripts.py` — PATH isolation fix
- `tests/test_frameless_mode_flag.py` — QApplication lifecycle fix
- `tests/test_main_window_geometry.py` — QApplication lifecycle fix
- `tests/test_workflow_runner_locks.py` — missing keyword argument fix
- `tests/test_v17_cli.py` — string assertion fix

## Compatibility

- Fedora 43+
- Python 3.12+
- PyQt6 6.x
- No new dependencies added
- Fully backward-compatible; no migration required
