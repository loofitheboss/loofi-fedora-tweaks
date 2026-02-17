# Release Notes — v47.0.0 "Experience"

**Release Date**: 2025-07-26
**Codename**: Experience
**Focus**: UX improvements for beginner-to-advanced users

---

## Highlights

### Experience Level System
- New `ExperienceLevelManager` with three tiers: Beginner (12 tabs), Intermediate (20 tabs), Advanced (all 28 tabs)
- Sidebar dynamically filters visible tabs based on selected experience level
- Configurable in Settings → Behavior and during first-run wizard
- Favorites always override visibility filtering

### Guided Tour
- Semi-transparent spotlight overlay (`TourOverlay`) for first-time users
- 5 built-in steps: Sidebar, Dashboard, Command Palette, Settings, Help
- Automatically launches after first-run wizard completes
- Skip button and step-by-step Next navigation

### Health Score Drill-Down
- Dashboard health gauge is now clickable (cursor changes to pointer)
- Opens `HealthDetailDialog` modal with per-component breakdown
- Progress bars for each component (Updates, Security, Storage, Performance, Backup)
- "Fix it →" buttons navigate directly to the relevant tab

### Toast Notifications
- `BaseTab` now provides `show_toast()`, `show_success()`, `show_error()`, `show_info()` convenience methods
- Automatic success/error toast on command completion via `on_command_finished`
- Wired into Software, Maintenance, and Dashboard tabs
- Non-intrusive feedback using MainWindow's existing toast system

### Quick Command Registry
- `QuickCommandRegistry` singleton with 10 built-in commands
- Commands: system update, flatpak update, cleanup, firewall check, backup, security scan, etc.
- Accessible from command palette with ⚡ prefix
- Extensible: register/unregister custom commands at runtime

### Dashboard Undo Card
- Recent actions card showing last 5 actions from `HistoryManager`
- One-click "↩ Undo" buttons for reversible actions
- Auto-refresh after undo operations
- `HistoryEntry` dataclass with UUID-based IDs

### Wizard Enhancements
- Expanded from 5 steps to 6 steps with new Experience Level selection
- Progress bar showing completion percentage
- Apply feedback label with success confirmation
- Radio buttons for Beginner/Intermediate/Advanced with descriptions

### Settings UX
- Experience Level selector added to Behavior sub-tab
- Dynamic description label updates on level change
- Help text QLabels added to Appearance and Advanced sub-tabs

---

## New Files

| File | Type | Description |
|------|------|-------------|
| `utils/experience_level.py` | Utils | Experience level enum and manager |
| `utils/health_detail.py` | Utils | Health component scores and fixes |
| `utils/guided_tour.py` | Utils | Tour step management |
| `utils/quick_commands.py` | Utils | Quick command registry |
| `ui/health_detail_dialog.py` | UI | Health drill-down modal dialog |
| `ui/tour_overlay.py` | UI | Guided tour spotlight overlay |
| `tests/test_experience_level.py` | Test | 22 tests |
| `tests/test_health_detail.py` | Test | 11 tests |
| `tests/test_guided_tour.py` | Test | 14 tests |
| `tests/test_quick_commands.py` | Test | 24 tests |
| `tests/test_dashboard_undo.py` | Test | 14 tests |
| `tests/test_base_tab_toast.py` | Test | 11 tests |
| `tests/test_settings_tab_ux.py` | Test | 5 tests |
| `tests/test_command_palette_actions.py` | Test | 6 tests |

## Modified Files

| File | Changes |
|------|---------|
| `utils/history.py` | Added `HistoryEntry` dataclass, `get_recent()`, `can_undo()`, `undo_action()` |
| `ui/base_tab.py` | Added toast methods, `_find_main_window()` |
| `ui/main_window.py` | Experience level sidebar filtering, guided tour launch |
| `ui/settings_tab.py` | Experience level combo, help text labels |
| `ui/dashboard_tab.py` | Clickable health gauge, health detail dialog, undo card, toast feedback |
| `ui/command_palette.py` | Quick command execution support |
| `ui/wizard.py` | Experience level step, progress bar, apply feedback |
| `ui/software_tab.py` | Toast notifications on command completion |
| `ui/maintenance_tab.py` | Toast notifications on command completion |

## Test Results

- **Total tests**: 6016+ (115 new)
- **Pass rate**: 100%
- **Coverage**: 82%

---

## Upgrade Notes

- No breaking changes — all new features are additive
- Experience level defaults to Advanced (all tabs visible) for existing users
- First-run wizard now has 6 steps instead of 5
- Settings → Behavior has new Experience Level selector
