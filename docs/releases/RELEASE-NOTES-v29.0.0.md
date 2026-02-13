# Release Notes — v29.0.0 "Usability & Polish"

**Release Date**: 2026-02-13
**Codename**: Usability & Polish
**Previous Version**: v28.0.0

---

## Summary

v29.0.0 reclaims the usability features originally planned for v22.0 (which was skipped) and adds cross-cutting UX polish. This release focuses on error handling, confirmation dialogs, notification toasts, sidebar enhancements, theme-awareness, CORS hardening, settings granularity, and keyboard accessibility.

---

## New Features

### Centralized Error Handler
- Global `sys.excepthook` override via `install_error_handler(app)`
- `LoofiError` subtypes display user-friendly dialogs with recovery hints
- Unknown exceptions logged to `NotificationCenter` with full traceback
- File: `utils/error_handler.py`

### Confirmation Dialog
- `ConfirmActionDialog` for dangerous operations (delete, reset, uninstall)
- Shows action description, undo hint, optional snapshot checkbox
- "Don't ask again" toggle integrated with `SettingsManager.confirm_dangerous_actions`
- Static `ConfirmActionDialog.confirm()` method for one-line usage
- File: `ui/confirm_dialog.py`

### Notification Toast
- Animated slide-in toast widget overlaid on MainWindow
- Category-based accent colors (info=blue, warning=amber, error=red, success=green)
- Configurable auto-hide timer with smooth slide animations
- Wired to `MainWindow.show_toast()` for global access
- File: `ui/notification_toast.py`

### Sidebar Enhancements
- **Search**: Now matches tab descriptions, badge data, and category in addition to names
- **Status indicators**: Live colored dots (🟢🟡🔴) on Maintenance and Storage items
  - Maintenance: update availability check
  - Storage: disk usage level
  - Refreshed every 30 seconds via QTimer
- **Keyboard focus**: Restored `StrongFocus` policy on sidebar QTreeWidget

### Settings Reset Per Group
- "↩ Reset Appearance" and "↩ Reset Behavior" buttons in Settings tab
- New `SettingsManager.reset_group(group_name)` method resets only specified keys
- Preserves other groups when resetting one

### Notification Badge
- Unread count badge on bell icon in breadcrumb bar
- Auto-refreshed every 5 seconds

---

## Changes

### Dashboard SparkLine Theme Fix
- Replaced hardcoded `#1e1e2e` background with `palette().color(backgroundRole())`
- SparkLine now renders correctly in both dark and light themes

### Web API CORS Lockdown
- CORS origins restricted from `["*"]` to `["http://localhost:8000", "http://127.0.0.1:8000"]`
- Prevents cross-origin abuse when web API is active

---

## Testing

- **95 new tests** across 5 test files
- `test_error_handler.py` — 24 tests (hook install, error routing, logging)
- `test_confirm_dialog.py` — 10 tests (accept/reject, bypass, snapshot)
- `test_notification_toast.py` — 16 tests (display, auto-hide, categories)
- `test_v29_features.py` — 17 tests (sidebar search, indicators, sparkline, keyboard)
- `test_settings_extended_v29.py` — 14 tests (group reset, key preservation)
- All 95 tests pass

---

## New Files

| File | Description |
|------|-------------|
| `utils/error_handler.py` | Centralized error handler |
| `ui/confirm_dialog.py` | Confirmation dialog widget |
| `ui/notification_toast.py` | Animated toast notifications |
| `tests/test_error_handler.py` | Error handler tests (24) |
| `tests/test_confirm_dialog.py` | Confirm dialog tests (10) |
| `tests/test_notification_toast.py` | Notification toast tests (16) |
| `tests/test_v29_features.py` | Sidebar/sparkline/keyboard tests (17) |
| `tests/test_settings_extended_v29.py` | Settings reset tests (14) |
| `.workflow/specs/tasks-v29.0.0.md` | Task specification |
| `.workflow/specs/arch-v29.0.0.md` | Architecture blueprint |

---

## Upgrade Notes

- No breaking changes. Drop-in upgrade from v28.0.0.
- Error handler auto-installs on app startup — no manual wiring needed.
- CORS change may affect external integrations using the web API from non-localhost origins.

---

## Dependencies

- v28.0.0 workflow state baseline
- Python 3.12+, PyQt6, Fedora 43+
