# Architecture Blueprint — v29.0.0 Usability & Polish

> **Version**: v29.0.0
> **Phase**: P2 DESIGN
> **Date**: 2026-02-13
> **Agent**: architecture-advisor
> **Status**: Implementation-ready

---

## Overview

v29.0.0 reclaims the skipped v22.0 usability scope and adds cross-cutting UX polish. Changes span error handling, confirmation dialogs, notification toasts, sidebar enhancements, theme-awareness, CORS hardening, settings reset, and keyboard accessibility.

No new architectural layers are introduced. All changes integrate into existing patterns.

---

## Design Decisions

### D1: Error Handler Integration Point
**Decision: sys.excepthook override in main.py startup.**
`install_error_handler(app)` installs a global hook. `LoofiError` subtypes display dialogs with `hint` text. Unknown exceptions log to `NotificationCenter` and stderr. No new exception classes — reuses `utils/errors.py` hierarchy.

**Rationale**: Catches all unhandled exceptions without requiring try/catch wrappers in every tab.

### D2: Confirmation Dialog as Static Method
**Decision: `ConfirmActionDialog.confirm()` returns bool.**
Static factory pattern matches existing dialog patterns in the codebase (e.g., `QMessageBox.question`). Integrates with `SettingsManager.confirm_dangerous_actions` to allow global bypass.

**Rationale**: Minimal API surface. Callers need one line to add confirmation.

### D3: Notification Toast Positioning
**Decision: Top-right corner, overlaid on MainWindow.**
Toast slides in from right edge with QPropertyAnimation. Stacking handled by MainWindow — only one toast visible at a time (latest replaces previous).

**Rationale**: Standard desktop notification position. Doesn't interfere with sidebar or content area.

### D4: Sidebar Search Scope
**Decision: Match against name, description, badge, and category.**
`_filter_sidebar()` iterates all top-level and child items, checking case-insensitive substring match against stored item data (roles `Qt.UserRole+1` through `Qt.UserRole+3`).

**Rationale**: Users search by function ("network") not tab name ("Loofi Link").

### D5: Status Indicators Implementation
**Decision: Inline colored dots in sidebar item text.**
`_refresh_status_indicators()` prepends emoji dots (🟢🟡🔴) to item text on a 30-second timer. Maintenance checks `utils/system.py` update availability. Storage checks `utils/storage.py` disk usage.

**Rationale**: Lightweight, no custom painting. Timer interval balances freshness vs resource usage.

### D6: CORS Scope
**Decision: Restrict to localhost origins only.**
`["http://localhost:8000", "http://127.0.0.1:8000"]` replaces `["*"]`. The web API is intended for local development and integration only.

**Rationale**: Prevents cross-origin requests from external domains in production scenarios.

### D7: Settings Reset Granularity
**Decision: Per-group reset (Appearance, Behavior), not per-key.**
`SettingsManager.reset_group(group_name)` accepts a group string and resets all keys in that group to defaults. More useful than per-key reset, less destructive than full reset.

**Rationale**: Users typically want to undo a category of changes, not individual settings.

---

## File Impact Map

| File | Change Type | Description |
|------|------------|-------------|
| `utils/error_handler.py` | **NEW** | Global excepthook, LoofiError routing |
| `ui/confirm_dialog.py` | **NEW** | ConfirmActionDialog with static confirm() |
| `ui/notification_toast.py` | **NEW** | Animated slide-in toast |
| `ui/main_window.py` | MODIFIED | Search, indicators, keyboard focus, toast wiring |
| `ui/dashboard_tab.py` | MODIFIED | SparkLine palette fix |
| `ui/settings_tab.py` | MODIFIED | Reset per group buttons |
| `utils/settings.py` | MODIFIED | reset_group() method |
| `utils/api_server.py` | MODIFIED | CORS lockdown |

---

## Testing Strategy

5 test files, 95 tests total:
- `test_error_handler.py` (24) — Hook installation, LoofiError routing, unknown errors, logging
- `test_confirm_dialog.py` (10) — Dialog accept/reject, bypass, snapshot checkbox
- `test_notification_toast.py` (16) — Toast display, auto-hide, categories, animations
- `test_v29_features.py` (17) — Sidebar search, indicators, sparkline, keyboard focus
- `test_settings_extended_v29.py` (14) — Group reset, key preservation, edge cases

All tests use `@patch` decorators. No real system calls. QApplication mocked where needed via `QT_QPA_PLATFORM=offscreen`.

---

## Dependencies

- v28.0.0 workflow state (clean baseline)
- Existing `utils/errors.py` error hierarchy
- Existing `utils/notifications.py` NotificationCenter
- Existing `utils/settings.py` SettingsManager
