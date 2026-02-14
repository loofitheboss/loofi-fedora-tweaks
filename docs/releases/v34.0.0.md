# v34.0.0 "Citadel" — Release Notes

**Release date**: 2025-07-18
**Codename**: Citadel
**Focus**: Light theme fix, stability hardening, accessibility

---

## What's New

v34.0.0 "Citadel" is a polish-only release — no new features, only fixes, stability improvements, and accessibility enhancements.

### Light Theme Fix

The light theme (`light.qss`) has been completely rewritten:

- Removed 4 dead `QListWidget` selectors that targeted non-existent widgets
- Added 24+ new selectors covering the sidebar tree, disabled buttons, focus rings, combobox dropdowns, scrollbar hover states, table/tree items, and status labels
- All colours now use the Catppuccin Latte palette for consistency with the dark theme's Catppuccin Mocha palette
- Font family updated to match `modern.qss`

### Stability Hardening

**CommandRunner** (`utils/command_runner.py`) received 7 improvements:
- Configurable timeout (default 5 min) with automatic cleanup
- `stop()` method with terminate → kill escalation (5s grace period)
- `is_running()` status check
- Crash detection via `QProcess.ExitStatus.CrashExit`
- New `stderr_received` signal for separate error stream handling
- Flatpak detection cached at class level (was re-checked every call)
- `errors='replace'` on byte decoding to prevent crashes on invalid output

**Exception handling** — 21 silent `except: pass` blocks across 9 UI files now log properly with `logger.debug(..., exc_info=True)`.

**Subprocess extraction** — Zero `subprocess` imports remain in the UI layer. All system commands go through proper utility modules:
- `utils/network_utils.py` — WiFi scanning, VPN, DNS, hostname privacy
- `utils/software_utils.py` — Package/command existence checks
- `utils/gaming_utils.py` — GameMode status detection
- `utils/desktop_utils.py` — System colour scheme detection
- `utils/system_info_utils.py` — Hostname, kernel, release, CPU, RAM, disk, uptime, battery queries
- `ui/development_tab.py` — Terminal launching via `QProcess.startDetached()` instead of `subprocess.Popen`
- `ui/dashboard_tab.py` — Reboot via `QProcess.startDetached()` instead of `subprocess.run`

**Logging** — `RotatingFileHandler` replaces `FileHandler` (5 MB cap, 3 backups). Daemon's 17 `print()` calls replaced with structured logger calls.

### Accessibility

- 314 `setAccessibleName()` calls across all 27 tab files — every interactive widget (buttons, checkboxes, combos, inputs, spinboxes, sliders) has a screen reader label
- 3 tooltip constants wired from `ui/tooltips.py` to Hardware and Network tabs

### Testing

- 85 new tests for the 5 new utility modules
- Full suite: **4061 passed**, 0 failed

---

## Files Changed

| Area | Files |
|------|-------|
| Theme | `assets/light.qss` |
| Core stability | `utils/command_runner.py`, `utils/log.py`, `utils/daemon.py` |
| New utils | `utils/network_utils.py`, `utils/software_utils.py`, `utils/gaming_utils.py`, `utils/desktop_utils.py`, `utils/system_info_utils.py` |
| UI cleanup | `ui/dashboard_tab.py`, `ui/network_tab.py`, `ui/software_tab.py`, `ui/gaming_tab.py`, `ui/main_window.py`, `ui/system_info_tab.py`, `ui/development_tab.py` |
| Exception logging | `ui/confirm_dialog.py`, `ui/hardware_tab.py`, `ui/logs_tab.py`, `ui/monitor_tab.py`, `ui/performance_tab.py`, `ui/system_info_tab.py`, `ui/whats_new_dialog.py` |
| Accessibility | All 27 `ui/*_tab.py` files |
| Tests | `tests/test_network_utils.py`, `tests/test_software_utils.py`, `tests/test_gaming_utils.py`, `tests/test_desktop_utils.py`, `tests/test_system_info_utils.py` |
| Version | `version.py`, `pyproject.toml`, `loofi-fedora-tweaks.spec` |

## Upgrade

Standard upgrade path — no breaking changes, no migration needed.
