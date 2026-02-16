# Release Notes -- v42.0.0 "Sentinel"

**Release Date:** 2026-02-16
**Codename:** Sentinel
**Theme:** Hardening & Polish — exception narrowing, dnf elimination, UX improvements

## Summary

v42.0.0 "Sentinel" closes the remaining stabilization gaps from Phases 5-6 of the
hardening guide. All `except Exception` handlers have been narrowed to specific types,
hardcoded `dnf` references eliminated across 15 files, and the daemon service unit
hardened with systemd sandboxing directives. UX polish includes a software tab search
bar, Focus Mode discoverability, tooltip expansion, and a high-contrast theme.

## Highlights

- **106 exception handlers narrowed** across 30 files — 33 justified boundaries retained with audit comments
- **25+ hardcoded `dnf` references eliminated** — all use `PrivilegedCommand.dnf()` or `SystemManager.get_package_manager()`
- **Daemon systemd hardening** — `NoNewPrivileges`, `ProtectSystem=strict`, `SystemCallFilter`
- **Software tab search/filter** — case-insensitive filtering by name/description
- **High-contrast theme** — new `high-contrast.qss` with settings toggle
- **5860 tests passing**, 82% coverage, 0 failures

## Changes

### Changed

- Narrowed 106 `except Exception` handlers to specific types: `(subprocess.SubprocessError, OSError)` for subprocess, `(json.JSONDecodeError, ValueError)` for JSON, `(ImportError, AttributeError)` for imports
- Replaced 25+ hardcoded `dnf` commands with `PrivilegedCommand.dnf()`, `SystemManager.get_package_manager()`, or `shutil.which("dnf")` guards
- Moved `subprocess.run()` call from `ui/software_tab.py` to `utils/software_utils.py`
- Daemon task actions validated against `TaskAction` enum before execution

### Added

- Software tab search bar with case-insensitive filtering
- Focus Mode status card on dashboard Quick Actions
- "Toggle Focus Mode" entry in command palette (Ctrl+K)
- Tooltips for Dashboard, Software, Maintenance, Desktop, and Development tabs
- High-contrast theme (`assets/high-contrast.qss`) with settings toggle
- Systemd sandboxing directives: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome=read-only`, `ProtectKernelTunables`, `RestrictSUIDSGID`, `SystemCallFilter=@system-service`
- Plugin `min_app_version`/`max_app_version` compatibility gates
- Plugin auto-update setting (default: off)

### Fixed

- Subprocess timeout enforcement for 17 remaining calls in `services/hardware/` and `services/system/`
- Test pollution from module-level stub installation in `test_maintenance_tab.py` and `test_community_tab.py`
- 15+ test exception type mismatches from narrowing
- `AgentScheduler` test references updated for `_stop_event` refactor

## Stats

- **Tests:** 5860 passed, 35 skipped, 0 failed
- **Lint:** 0 errors
- **Coverage:** 82%

## Upgrade Notes

No user-facing breaking changes. Daemon service unit gains stricter sandboxing — restart
the service after upgrade (`systemctl --user restart loofi-fedora-tweaks.service`).
