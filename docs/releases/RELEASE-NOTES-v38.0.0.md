# Release Notes — v38.0.0 "Clarity"

**Release date**: 2025-07-22
**Codename**: Clarity
**Type**: UX polish & theme correctness

---

## Highlights

v38.0.0 "Clarity" eliminates all hardcoded dark-theme colors, fixes the Doctor tab to follow project patterns, wires Quick Actions to real tab navigation, and adds an undo/toast notification system. No new major features — this release refines what exists.

---

## Doctor Tab Rewrite

- Uses `PrivilegedCommand.dnf()` instead of raw dnf strings
- Respects `SystemManager.get_package_manager()` for Atomic Fedora
- All strings wrapped in `self.tr()` for i18n readiness
- `setObjectName()` on all key widgets for QSS styling
- `setAccessibleName()` on interactive elements for screen readers

---

## Dashboard Fixes

- Dynamic username via `getpass.getuser()` instead of hardcoded "Loofi"
- All metric labels and values use QSS objectNames instead of inline `setStyleSheet`

---

## Quick Actions Wiring

- All 16 action callbacks wired to `main_window.switch_to_tab()` via `_nav()` helper
- Previously callbacks were silently no-ops

---

## Theme Correctness

- **Confirm Dialog**: 9 inline `setStyleSheet` blocks replaced with objectNames
- **Command Palette**: 5 inline `setStyleSheet` blocks replaced with objectNames; keyword hints displayed as second line under each entry
- **BaseTab**: Removed hardcoded `QPalette` colors from `configure_table()`; table uses `setObjectName("baseTable")`; `make_table_item()` and `set_table_empty_state()` color params now optional (QSS handles styling)
- **~200 new QSS rules** in `modern.qss` (dark theme) for all new objectNames
- **~200 new QSS rules** in `light.qss` (Catppuccin Latte) matching all new objectNames

---

## New UI Features

| Feature | Location | Description |
|---------|----------|-------------|
| Undo button | Status bar | `MainWindow.show_undo_button()` with `HistoryManager` integration |
| Toast notifications | Status bar | `MainWindow.show_toast()` for transient success/error feedback |
| Output toolbar | BaseTab | Copy (📋), Save (💾), Cancel (⏹) buttons for all command output sections |
| Risk badges | Confirm Dialog | Color-coded LOW/MEDIUM/HIGH labels with QSS `[level=...]` property selectors |
| Per-action suppression | Confirm Dialog | "Don't ask again" saves per `action_key` via SettingsManager |
| Keyword hints | Command Palette | Second line under each entry showing keyword descriptions |
| Clickable breadcrumb | MainWindow | Category label changed from `QLabel` to clickable `QPushButton` for parent navigation |

---

## Files Changed

| File | Change |
|------|--------|
| `ui/doctor.py` | Full rewrite — PrivilegedCommand, SystemManager, tr(), objectNames, a11y |
| `ui/dashboard_tab.py` | getpass username, QSS objectNames for metrics |
| `ui/quick_actions.py` | 16 callbacks wired via switch_to_tab() |
| `ui/confirm_dialog.py` | 9 objectNames, risk badges, per-action suppression |
| `ui/command_palette.py` | 5 objectNames, keyword hints |
| `ui/base_tab.py` | Table objectName, optional color params, Copy/Save/Cancel toolbar |
| `ui/main_window.py` | Undo button, toast system, breadcrumb click |
| `assets/modern.qss` | ~200 new rules for v38 objectNames |
| `assets/light.qss` | ~200 new rules matching v38 objectNames |
| `version.py` | v38.0.0 "Clarity" |

---

## Test Suite

- **40 new tests** in `tests/test_v38_clarity.py` covering all v38 changes
- **4349 tests passing** (up from 4061), 0 failures

---

## Upgrade Notes

- No configuration changes required
- QSS themes updated — custom theme overrides may need adjustment for new objectNames
- "Don't ask again" confirmations can be reset in Settings tab
