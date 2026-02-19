# Architecture Spec - v49.0.0 "Shield"

## Design Rationale

v49.0.0 is a test coverage expansion and quality hardening release. The objective is to
bring the lowest-covered modules (formatting, battery, update_manager, plugin_adapter)
from 0–30% to 60%+ coverage with comprehensive edge case testing. No architectural
changes — pure quality-focused delivery.

## Scope

1. `test_formatting.py` — 26 new tests for pure formatting utilities (was 0% coverage).
2. `test_battery_service.py` — 13 new tests for BatteryManager.set_limit with all failure paths (was 24% coverage).
3. `test_update_manager.py` — Enhanced with proper `shutil.which` + `SystemManager` mocking, deduplicated stale tests (28 tests, was 27% coverage).
4. `test_plugin_adapter.py` — Expanded with lifecycle, slugify, version compat, CLI commands, check_compat (53 tests, was 30% coverage).

## Key Decisions

### Test-Only Release

No new features, no architectural changes. All work is test creation and expansion
following existing project patterns (decorators, module-under-test patching, both
dnf/rpm-ostree paths).

### Module Selection Criteria

Modules selected by lowest coverage percentages: formatting (0%), battery (24%),
update_manager (27%), plugin_adapter (30%). All are critical system-facing modules
that benefit most from increased test coverage.

### Mock Patterns

All new tests follow `@patch` decorators (never context managers), patch the
module-under-test namespace, include timeout enforcement verification on subprocess
mocks, and cover both success and failure paths.

## Risks

- None. Test-only changes with no production code modifications.
