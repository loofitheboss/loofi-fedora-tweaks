# Release Notes — v1.0.0 "Foundation"

**Release Date**: 2026-02-20
**Theme**: Version Renormalization & Stable Baseline

## Summary

v1.0.0 "Foundation" marks the project's graduation to proper semantic versioning and
production-stable status. The project resets from experimental v50.0.0 numbering to
SemVer 1.0.0, establishing a canonical stable reference point for all future development.

This release also includes two new test suites, a test fix, and a Windows compatibility
bug fix in the workflow reports script.

## What's New

### Version Renormalization

The project versioning has been reset from v50.0.0 to v1.0.0 under proper SemVer:
- **Codename**: Foundation
- **Status**: Production/Stable (promoted from Beta)
- All version files synchronized: `version.py`, `pyproject.toml`, `.spec`

### Test Expansion

| Module | Tests Added | Key Coverage |
| --- | --- | --- |
| `test_log.py` | New suite | Centralized logging configuration, XDG path handling, root logger setup |
| `test_monitor.py` | New suite | `bytes_to_human`, `get_memory_info`, `get_cpu_info`, system health checks |

### Test Fix

- `test_plugins_v2.py`: Added `@patch` decorator for `APP_VERSION` in version compatibility test, decoupling from runtime version.

### Bug Fix

- `generate_workflow_reports.py`: Replaced Unicode checkmark/cross characters with ASCII equivalents to fix `UnicodeEncodeError` on Windows (cp1252 console encoding).

## What's Included

- 29 feature tabs (GUI mode)
- CLI, Daemon, and WebAPI entry modes
- Plugin-based architecture with SDK
- 82% test coverage (~5,936 tests)
- Hardware-aware defaults
- Atomic Fedora (rpm-ostree) support
- RPM packaging via `.spec` file

## Upgrade Notes

This is a version renormalization release. If upgrading from v50.0.0:
- No functional changes — safe to upgrade in place
- Version comparisons should treat v1.0.0 as the successor to v50.0.0
- Future versions will follow SemVer: v1.1.0, v1.2.0, v2.0.0, etc.

## Known Issues

None.
