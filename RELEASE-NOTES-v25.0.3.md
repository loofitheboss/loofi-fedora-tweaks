# Release Notes — v25.0.3 "Maintenance Update Crash Hotfix"

Release date: 2026-02-11

## Summary
v25.0.3 is a focused hotfix release that stabilizes the Maintenance update actions.

## Highlights
- Fixed crash path when clicking `Update System` from `Software > Maintenance > Updates`.
- Fixed crash path when clicking `Update All (DNF + Flatpak + Firmware)`.
- Unified system update execution with the existing `CommandRunner` path used by other maintenance actions.
- Ensured `Update All` starts with the system update step before Flatpak and firmware.
- Added regression tests for maintenance update command selection and update-all queue startup.

## Upgrade notes
- No migration steps required.
- Existing settings and profiles are unaffected.
