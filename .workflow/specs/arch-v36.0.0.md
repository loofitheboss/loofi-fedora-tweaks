# v36.0.0 "Horizon" — Architecture Spec

## Theme

UX safety, performance optimization, and navigation polish.
Hardening guide Phase 3–4 (API security, UX stabilization).
Unblocks feature-rich v37.0 "Pinnacle".

## Design Decisions

### Safe Mode

- New module: `utils/safe_mode.py`
- `SafeModeManager` with `is_safe_mode()`, `enable()`, `disable()`, `toggle()`
- Config stored in `~/.config/loofi-fedora-tweaks/safe_mode.json`
- First launch defaults to safe mode ON (read-only diagnostics)
- When ON: all mutation buttons disabled, info banners shown, CLI commands print preview only
- Toggle in Settings tab + CLI `--safe-mode` / `--no-safe-mode` flags
- `BaseTab` checks `SafeModeManager.is_safe_mode()` before `run_command()`

### Risk Classification

- New module: `utils/risk.py`
- `RiskLevel` enum: `LOW`, `MEDIUM`, `HIGH`
- `RiskRegistry` class: maps action IDs → `RiskEntry(level, description, revert_command, revert_description)`
- Pre-populated registry covering all PrivilegedCommand actions
- `get_risk(action_id) → RiskEntry`
- `get_revert_instructions(action_id) → str`
- Medium/High risk actions show revert instructions in `ConfirmActionDialog`
- `@risk_classified` decorator for auto-labeling operations

### Config Backup

- New module: `utils/config_backup.py`
- `ConfigBackupManager` with `backup_before(action_id)`, `list_backups()`, `restore(backup_id)`
- Auto-snapshots `~/.config/loofi-fedora-tweaks/` before destructive operations
- Stored in `~/.config/loofi-fedora-tweaks/backups/` with ISO timestamps
- Max 20 backups with automatic cleanup of oldest
- Integration: `ConfirmActionDialog` calls `backup_before()` for Medium/High risk actions

### API Security

- Rate limiting on auth endpoints (`/api/auth/*`): 10 requests/minute per IP
- New `--unsafe-expose` flag required for binding to non-localhost addresses
- Read-only endpoints (GET) separated from privileged endpoints (POST/PUT/DELETE)
- Read-only routes accessible without auth token
- Privileged routes require auth + audit logging
- Middleware in `api/__init__.py` for rate limiting and exposure checks

### Performance Optimization

- Startup profiling: `scripts/profile_startup.py` measuring import times and widget creation
- Target: <2s cold start on typical hardware
- Lazy import audit: identify and defer heavy imports in `main.py` and tab modules
- `utils/lazy_imports.py` helper for deferred module loading
- Memory profiling: identify retained references in tab switching
- QSS parsing: cache compiled stylesheets

### Navigation Polish

- Sidebar: smooth scrolling via `QPropertyAnimation`, hover state transitions
- Sidebar collapse animation: slide-out with easing curve
- Breadcrumb bar: improved layout with truncation for deep paths
- Category group headers: collapsible with expand/collapse animation
- Consistent spacing: audit all tab layouts for widget alignment gaps

## Module Map

```
utils/safe_mode.py          # SafeModeManager (config-based toggle)
utils/risk.py               # RiskLevel enum, RiskRegistry, risk decorators
utils/config_backup.py      # ConfigBackupManager (pre-action snapshots)
utils/lazy_imports.py       # Deferred import helpers
scripts/profile_startup.py  # Startup time profiler
api/__init__.py              # Rate limiting middleware, exposure guard
ui/base_tab.py              # Safe mode check in run_command()
ui/confirm_dialog.py        # Risk level display, revert instructions
ui/main_window.py           # Sidebar animation, breadcrumb polish
cli/main.py                 # --safe-mode, --no-safe-mode flags
```

## Dependencies

- v35.0.0 Fortress (all subprocess calls timed out, audit logging in place)
- Existing: `utils/audit.py`, `utils/commands.py`, `ui/confirm_dialog.py`, `ui/base_tab.py`
