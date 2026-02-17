# Release Notes -- v45.0.0 "Housekeeping"

**Release Date:** 2026-02-17
**Codename:** Housekeeping
**Theme:** Stability fixes, safer guidance, and reliability UX consistency

## Summary

v45.0.0 is a stability-first release that resolves lint blockers, removes unsafe
runtime guidance text, and standardizes package-install hints across key flows.
It also tightens one UI exception boundary while keeping behavior fail-safe.

## Highlights

- Fixed runtime lint blockers in:
  - `utils/network_monitor.py`
  - `utils/performance.py`
- Added `utils/install_hints.py` for package-manager-aware install guidance.
- Replaced hardcoded `sudo` guidance in runtime user-facing messaging with safer hints.
- Narrowed `WhatsNewDialog.mark_seen()` exception handling to expected failure types.
- Aligned release artifacts to `45.0.0`.

## Changes

### Added

- `loofi-fedora-tweaks/utils/install_hints.py`
- `tests/test_install_hints.py`

### Changed

- `ui/backup_tab.py` now shows package-manager-aware `pkexec` install hints for missing backup tools.
- `utils/containers.py` now returns package-manager-aware install guidance when Distrobox is missing.
- `utils/state_teleport.py` now returns package-manager-aware install guidance when VS Code is missing.
- `utils/usbguard.py` restart guidance now uses `pkexec systemctl` wording.
- `utils/errors.py` lock recovery hint no longer suggests destructive sudo lockfile deletion.
- `ui/whats_new_dialog.py` narrowed exception handling in `mark_seen()`.

### Fixed

- Flake8 `E203` violations in network/performance utility modules.

## Validation

- Targeted tests added/updated for guidance messaging and exception behavior.
- Version alignment updated to `45.0.0` across `version.py`, `.spec`, and `pyproject.toml`.

## Upgrade Notes

No migration steps required. This release is backward-compatible and focused on
stability and safety messaging improvements.
