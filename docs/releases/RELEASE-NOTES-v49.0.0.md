# Release Notes — v49.0.0 "Shield"

**Release Date**: 2026-02-19
**Theme**: Test Coverage Expansion & Quality Hardening

## Summary

v49.0 "Shield" hardens project quality by expanding test coverage for the four lowest-covered modules: `formatting.py` (0%), `battery.py` (24%), `update_manager.py` (27%), and `adapter.py` (30%). A total of 120 tests across 4 files now cover all success and failure paths, including edge cases for subprocess timeouts, OSError handling, and atomic/traditional Fedora branching.

## What's New

### Test Coverage Expansion

| Module                         | Before | Tests Added | Key Coverage                                                          |
| ------------------------------ | ------ | ----------- | --------------------------------------------------------------------- |
| `utils/formatting.py`          | 0%     | 26 tests    | `bytes_to_human`, `seconds_to_human`, `percent_bar`, `truncate`       |
| `services/hardware/battery.py` | 24%    | 13 tests    | `set_limit` success, failure steps, OSError, SubprocessError, timeout |
| `utils/update_manager.py`      | 27%    | 28 total    | DNF/rpm-ostree paths, shutil.which, OSError, TimeoutExpired           |
| `core/plugins/adapter.py`      | 30%    | 53 total    | Lifecycle, slugify, version compat, CLI commands, manifest checks     |

### Quality Improvements

- All test mocks follow `@patch` decorator pattern with module-under-test namespace
- All subprocess mocks include `timeout` enforcement verification
- Deduplicated stale test methods with incomplete mock patterns
- Covers both `dnf` and `rpm-ostree` paths where applicable

## Upgrade Notes

No breaking changes. This is a test-only release with no functional code changes.

## Test Results

- **Total tests**: 6300+ passing
- **Coverage**: 82%+
- **CI**: All 14 jobs green
