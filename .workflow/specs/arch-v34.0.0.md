# v34.0.0 "Citadel" — Architecture Spec

## Theme

Stability, theme parity, and accessibility polish. No new features.

## Design Decisions

### Light Theme Fix

- Port all 24 missing selectors from modern.qss to light.qss with Catppuccin Latte palette
- Remove 4 dead QListWidget selectors (sidebar migrated to QTreeWidget#sidebar in v25)
- No layout or widget changes — QSS only

### CommandRunner Hardening

- Add `is_running() -> bool` via QProcess state check
- Add configurable timeout (default 300s) with QTimer auto-kill
- Add `stderr_received(str)` signal — backward-compat: still emit stderr via `output_received` too
- `stop()` escalation: terminate() → 5s grace → kill()
- Cache Flatpak detection as class-level `_is_flatpak: Optional[bool]`
- Decode with `errors='replace'` to handle non-UTF-8 output
- Check `QProcess.ExitStatus.CrashExit` and emit `error_occurred`

### Subprocess Extraction from UI

- 12 subprocess.run calls across 5 UI files → extract to utils/
- dashboard_tab.py: ps query → utils/processes.py, reboot → PrivilegedCommand.systemctl
- network_tab.py: 6 calls → utils/network.py
- software_tab.py: 1 call → utils/software.py or similar
- gaming_tab.py: 2 calls → utils/gaming.py
- main_window.py: 1 call → utils/ appropriate module

### Silent Exception Handling

- Replace 27 `except Exception: pass` with `except Exception: logger.debug(...)`
- Add `from utils.log import get_logger` and `logger = get_logger(__name__)` to affected files

### Logging

- Replace FileHandler with RotatingFileHandler(maxBytes=5MB, backupCount=3) in log.py
- Replace 17 print() calls in daemon.py with get_logger("loofi.daemon")

### Accessibility

- Wire tooltips.py constants into matching UI widgets
- Add setAccessibleName() on all interactive widgets in 20 unannotated tabs
- Add defaults in base_tab.py for output_area accessible name
