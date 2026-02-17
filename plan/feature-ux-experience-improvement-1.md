---
goal: Improve UX for beginner-to-advanced users with guided onboarding, actionable feedback, and progressive disclosure
version: 1.0
date_created: 2026-02-17
last_updated: 2026-02-17
owner: Loofi Fedora Tweaks
status: 'Completed'
tags: [feature, ux, onboarding, feedback, stability, beginner-mode, notifications]
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

Comprehensive UX improvement plan for Loofi Fedora Tweaks v47.0 focused on making the app intuitive for first-time Fedora users while preserving full power for advanced users. The plan prioritizes three pillars: **progressive disclosure** (show the right features at the right skill level), **actionable feedback** (every action produces visible confirmation), and **guided discovery** (help users find and understand features without reading docs). All changes align with the stabilization guide — no new privileged capabilities, no subprocess additions in UI, and all existing safety gates preserved.

## 1. Requirements & Constraints

- **REQ-001**: Implement a user experience level system (Beginner / Intermediate / Advanced) that filters sidebar tab visibility and dashboard quick actions
- **REQ-002**: Add toast notification feedback for all user-initiated actions (install, configure, toggle) with success/error/info states
- **REQ-003**: Make health score clickable with per-component breakdown modal showing CPU, RAM, Disk, Uptime, Updates scores
- **REQ-004**: Add contextual help tooltips on all settings explaining their impact and showing default values
- **REQ-005**: Enhance onboarding wizard with progress indicators, estimated time, and "what's included" expandable profiles
- **REQ-006**: Add interactive "Getting Started" tour that highlights key features on first launch after wizard
- **REQ-007**: Make command palette actionable — support running quick commands, not just navigating tabs
- **REQ-008**: Add "Undo Last Action" button to dashboard with visible recent change indicator
- **REQ-009**: Show non-default settings with visual badges so users know what they've customized
- **SEC-001**: No new privileged capabilities — all changes are UI/UX layer only
- **SEC-002**: User experience level stored in config, never affects security boundaries
- **CON-001**: Must preserve all 28 existing tabs — beginner mode hides but does not remove them
- **CON-002**: All new UI must use `self.tr("...")` for i18n readiness
- **CON-003**: No business logic in UI layer — all new logic goes to `utils/`
- **CON-004**: Stabilization guide compliance — no new subprocess calls, no privilege expansion
- **GUD-001**: Follow existing BaseTab / PluginInterface patterns for any new tab components
- **GUD-002**: Use existing `notification_toast.py` and `notification_panel.py` for feedback — extend, don't replace
- **GUD-003**: Configuration stored via `SettingsManager` / `ConfigManager` — no new config files
- **PAT-001**: Utils modules use `@staticmethod`, return operations tuples, no PyQt6 imports
- **PAT-002**: All tests use `@patch` decorators with full mocking of system calls

## 2. Implementation Steps

### Implementation Phase 1 — Experience Level System & Progressive Disclosure

- GOAL-001: Create a user experience level system that allows beginner users to see a simplified interface while advanced users see everything. The level selector integrates into Settings and the first-run wizard.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create `utils/experience_level.py` — Define `ExperienceLevel` enum (BEGINNER, INTERMEDIATE, ADVANCED) with `@staticmethod` methods: `get_level() -> ExperienceLevel`, `set_level(level)`, `get_visible_tabs(level) -> List[str]` returning tab IDs appropriate for each level. BEGINNER shows ~12 core tabs (Dashboard, System Info, Software, Hardware, Network, Security, Backup, Settings, Storage, Performance, Desktop, Maintenance). INTERMEDIATE adds Development, Extensions, Gaming, Profiles, Virtualization. ADVANCED shows all 28 tabs. Store in `~/.config/loofi-fedora-tweaks/settings.json` via `SettingsManager`. | | |
| TASK-002 | Update `ui/main_window.py` `_build_sidebar_from_registry()` — After building the full tab tree, filter out tabs not in `ExperienceLevel.get_visible_tabs()`. Add a "Show All Tabs" toggle at bottom of sidebar that temporarily reveals hidden tabs (with dimmed styling). Preserve favorites — favorited tabs always visible regardless of level. | | |
| TASK-003 | Update `ui/settings_tab.py` — Add "Experience Level" combo box to the Behavior sub-tab with Beginner/Intermediate/Advanced options. Include description label that updates on selection: Beginner = "Simplified view with essential tools", Intermediate = "Core tools plus development & customization", Advanced = "Full access to all 28 tabs and features". On change, emit signal to `MainWindow` to rebuild sidebar. | | |
| TASK-004 | Update `ui/wizard.py` — Add experience level selection as Step 2 (after hardware detection, before use-case profile). Show 3 radio buttons with visual cards explaining each level. Default selection based on hardware profile: Server → Advanced, Development → Intermediate, Daily/Minimal → Beginner, Gaming → Intermediate. | | |
| TASK-005 | Create `tests/test_experience_level.py` — Test all `ExperienceLevel` methods: level persistence, tab visibility per level, default fallback, favorites override. Mock `SettingsManager` and file I/O. | | |

### Implementation Phase 2 — Actionable Feedback & Notifications

- GOAL-002: Ensure every user-initiated action produces visible feedback via toast notifications and the notification panel. Integrate existing `notification_toast.py` with `BaseTab` so all tabs can show success/error toasts without custom wiring.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Update `ui/base_tab.py` — Add `show_toast(title, message, category)` convenience method that finds the `MainWindow` ancestor and calls its toast notification system. Add `show_success(msg)`, `show_error(msg)`, `show_info(msg)` shorthand methods. Wire `command_finished` to automatically show success/error toast based on exit code. | | |
| TASK-007 | Update `ui/main_window.py` — Expose `show_toast(title, message, category)` public method that delegates to the existing `NotificationToast` widget. Ensure toasts stack properly when multiple fire in sequence (queue with 500ms delay between dismissals). | | |
| TASK-008 | Update high-traffic tabs to use toast feedback — Add `show_success()`/`show_error()` calls to `software_tab.py` (after package install/remove), `maintenance_tab.py` (after cleanup), `backup_tab.py` (after backup/restore), `security_tab.py` (after firewall toggle), `network_tab.py` (after connection changes). Only add to `command_finished` handlers — no logic changes. | | |
| TASK-009 | Update `ui/dashboard_tab.py` quick actions — After each quick action completes, show toast with result. Add animation pulse to the Quick Actions card when an action is running (simple border color change via QSS). | | |
| TASK-010 | Create `tests/test_base_tab_toast.py` — Test toast integration in BaseTab: success/error/info toast methods, MainWindow lookup, category mapping. Mock `NotificationToast`. | | |

### Implementation Phase 3 — Health Score Drill-Down

- GOAL-003: Make the dashboard health score interactive — clicking the score gauge opens a detailed breakdown modal showing per-component scores, trends, and actionable fix suggestions with direct navigation links.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-011 | Create `utils/health_detail.py` — `HealthDetailManager` with `@staticmethod` methods: `get_component_scores() -> Dict[str, ComponentScore]` returning individual CPU, RAM, Disk, Uptime, Updates scores with thresholds, current values, and recommendations. `get_actionable_fixes() -> List[HealthFix]` returning fixes with `tab_id` navigation targets (e.g., "High CPU" → `monitor` tab). Define `ComponentScore` and `HealthFix` dataclasses. | | |
| TASK-012 | Create `ui/health_detail_dialog.py` — Modal dialog showing: header with overall grade + score, 5-row component table (component name, score bar, status icon, recommendation text), and "Fix it" buttons that emit `navigate_to_tab(tab_id)` signal. Use existing QSS styling patterns. Inherits QDialog, not BaseTab. | | |
| TASK-013 | Update `ui/dashboard_tab.py` — Make health score gauge clickable (override `mousePressEvent` on the gauge widget). On click, open `HealthDetailDialog`. Pass component scores from `HealthDetailManager`. Connect `navigate_to_tab` signal to `MainWindow.navigate_to_tab()`. | | |
| TASK-014 | Create `tests/test_health_detail.py` — Test `HealthDetailManager`: component score calculation, fix generation, tab ID mapping. Mock `psutil`/subprocess calls. Test both healthy and degraded system states. | | |

### Implementation Phase 4 — Settings UX Enhancement

- GOAL-004: Make every setting self-explanatory with inline help text, default value indicators, and save confirmation feedback. Users should never wonder what a setting does or whether their change was saved.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-015 | Update `ui/settings_tab.py` Appearance sub-tab — Add `QLabel` help text below each control: Theme selector ("Controls the overall color scheme. Default: Dark"), Follow system ("Automatically matches your desktop theme. Default: Off"). Add "(Default)" suffix to default option in combo boxes. Show toast on save. | | |
| TASK-016 | Update `ui/settings_tab.py` Behavior sub-tab — Add help text to: Minimize to tray, Show notifications, Confirm dangerous actions, Restore last tab, Update checking. Highlight non-default values with subtle left-border accent (2px colored bar via QSS `objectName`). | | |
| TASK-017 | Update `ui/settings_tab.py` Advanced sub-tab — Add help text to log level selector ("Controls how much detail appears in logs. Default: INFO. Use DEBUG only for troubleshooting."). Add "Settings Export" and "Settings Import" buttons that call `ConfigManager.export_config()` / `import_config()`. Show file dialog for export path. | | |
| TASK-018 | Create `tests/test_settings_tab_ux.py` — Test settings tab UX: help text presence, default indicators, non-default highlighting logic, export/import button wiring. Mock `SettingsManager`, `ConfigManager`, `QFileDialog`. | | |

### Implementation Phase 5 — Enhanced Onboarding & First-Run Experience

- GOAL-005: Improve the first-run wizard with progress indicators, time estimates, and profile comparison. Add a post-wizard "Getting Started" tour that highlights key UI elements.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Update `ui/wizard.py` — Add step progress bar at top of wizard (Step 1/5, Step 2/5...) with step names. Add estimated time label ("~2 minutes to complete"). For each use-case profile radio button, add expandable "What's included" section listing the tweaks that profile enables. | | |
| TASK-020 | Update `ui/wizard.py` Apply step — Add progress spinner/bar during apply phase. Show per-recommendation status as it completes (✅/❌). After all recommendations applied, show "Setup Complete" success screen with 3 suggested next steps: "Explore Dashboard", "Check System Health", "Browse Available Tweaks". | | |
| TASK-021 | Create `utils/guided_tour.py` — `GuidedTourManager` with `@staticmethod` methods: `needs_tour() -> bool` (checks if tour has been shown), `mark_tour_complete()`, `get_tour_steps() -> List[TourStep]` returning ordered steps with target widget names and descriptions. Define `TourStep` dataclass with `widget_name`, `title`, `description`, `position`. | | |
| TASK-022 | Create `ui/tour_overlay.py` — Semi-transparent overlay widget that highlights a target widget with a spotlight cutout and shows a tooltip-style card with step title, description, and Next/Skip buttons. Implements `GuidedTourManager` steps sequentially. Steps: (1) Sidebar navigation, (2) Dashboard health score, (3) Command palette (Ctrl+K), (4) Quick Actions, (5) Settings. | | |
| TASK-023 | Update `ui/main_window.py` — After first-run wizard completes, check `GuidedTourManager.needs_tour()` and launch `TourOverlay` if needed. Add "Restart Tour" option in Help menu / command palette. | | |
| TASK-024 | Create `tests/test_guided_tour.py` — Test `GuidedTourManager`: tour state persistence, step ordering, completion marking. Mock file I/O. | | |

### Implementation Phase 6 — Command Palette Enhancement

- GOAL-006: Extend the command palette from navigation-only to action-capable. Users should be able to run common operations directly from Ctrl+K without navigating to a tab first.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-025 | Create `utils/quick_commands.py` — Define `QuickCommand` dataclass with `id`, `name`, `description`, `category`, `action_callable`, `keywords`. Create `QuickCommandRegistry` with `@staticmethod` methods to register/list/execute commands. Include 10 built-in commands: Toggle Focus Mode, Run System Cleanup, Check for Updates, Export Config, View Health Score, Toggle Dark/Light Theme, Open Settings, Show Notification Panel, Undo Last Action, Refresh Dashboard. | | |
| TASK-026 | Update `ui/command_palette.py` — Add "Actions" section above "Navigation" section in search results. Actions show a ▶ icon prefix. When an action is selected, execute `QuickCommandRegistry.execute(command_id)` instead of navigating. Add category filter chips at top of palette: All | Navigate | Actions. Show recent commands section when search is empty. | | |
| TASK-027 | Create `tests/test_quick_commands.py` — Test `QuickCommandRegistry`: command registration, listing, execution, category filtering, keyword search. Mock all action callables. | | |

### Implementation Phase 7 — Dashboard Undo & Recent Changes

- GOAL-007: Surface the existing undo capability (from `utils/history.py`) in the dashboard UI so users have visible rollback access and can see what changed recently.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-028 | Update `ui/dashboard_tab.py` — Add "Recent Changes" card below Quick Actions showing last 3 actions from `HistoryManager` with timestamps, descriptions, and individual "Undo" buttons. Add prominent "Undo Last Action" button in the dashboard header area (only visible when undo is available). Style undo buttons with caution color (amber). | | |
| TASK-029 | Update `utils/history.py` — Add `can_undo() -> bool` and `get_recent(count=3) -> List[HistoryEntry]` methods. Define `HistoryEntry` dataclass if not already present. Add `undo_action(action_id)` for targeted undo of specific actions (not just the last one). | | |
| TASK-030 | Create `tests/test_dashboard_undo.py` — Test undo button visibility logic, recent changes display, undo action execution. Mock `HistoryManager`. Test edge cases: empty history, failed undo, no undo command available. | | |

### Implementation Phase 8 — Documentation & Version Alignment

- GOAL-008: Update all documentation, version artifacts, and release notes for the v47.0 UX improvement release.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-031 | Update `CHANGELOG.md` — Add v47.0.0 section with all UX improvements organized by category: Experience Level System, Feedback & Notifications, Health Score Drill-Down, Settings UX, Onboarding, Command Palette, Dashboard Undo. | | |
| TASK-032 | Update `README.md` — Add UX features section: experience levels, guided tour, actionable health score, enhanced command palette. Update screenshots if applicable. | | |
| TASK-033 | Update `ROADMAP.md` — Add v47.0 entry with scope, deliverables, agent assignments, and dependencies. Mark v46.0 as DONE. | | |
| TASK-034 | Run `scripts/bump_version.py` to align `version.py`, `pyproject.toml`, `.spec` to 47.0.0. Create `docs/releases/RELEASE-NOTES-v47.0.0.md`. | | |
| TASK-035 | Update `ARCHITECTURE.md` — Document new modules: `utils/experience_level.py`, `utils/health_detail.py`, `utils/guided_tour.py`, `utils/quick_commands.py`. Add Experience Level System to Architecture Overview. | | |

## 3. Alternatives

- **ALT-001**: Instead of a 3-tier experience level, use a single "Simplified Mode" toggle (on/off). Rejected because intermediate users would see either too few or too many tabs — 3 tiers matches the user spectrum better.
- **ALT-002**: Build health drill-down as a new tab instead of a dialog. Rejected because it adds sidebar clutter and the information is contextual to the dashboard.
- **ALT-003**: Implement guided tour using a third-party library (e.g., PyQt tour widget). Rejected because it adds a dependency and custom implementation allows tighter integration with the existing icon system and QSS theming.
- **ALT-004**: Make command palette actions separate from navigation entirely (two different shortcuts). Rejected because having one universal Ctrl+K surface is more discoverable and matches common app patterns (VS Code, Spotlight).
- **ALT-005**: Store experience level per-session instead of persisted. Rejected because users expect their preference to persist across restarts.

## 4. Dependencies

- **DEP-001**: `utils/settings.py` — `SettingsManager` for experience level persistence
- **DEP-002**: `utils/config_manager.py` — `ConfigManager` for settings export/import
- **DEP-003**: `utils/health_score.py` — `HealthScoreManager` for component scores (extended by `health_detail.py`)
- **DEP-004**: `utils/history.py` — `HistoryManager` for undo functionality
- **DEP-005**: `ui/notification_toast.py` — Existing toast system (extended to BaseTab)
- **DEP-006**: `ui/notification_panel.py` — Existing notification panel
- **DEP-007**: `core/plugins/registry.py` — `PluginRegistry` for tab filtering
- **DEP-008**: `ui/base_tab.py` — `BaseTab` for toast integration
- **DEP-009**: `ui/command_palette.py` — Existing palette (extended with actions)
- **DEP-010**: `ui/wizard.py` — Existing wizard (enhanced with progress/level)
- **DEP-011**: v46.0 Navigator must be complete (category taxonomy baseline)

## 5. Files

- **FILE-001**: `utils/experience_level.py` — NEW — Experience level enum, tab visibility logic
- **FILE-002**: `utils/health_detail.py` — NEW — Per-component health scores and actionable fixes
- **FILE-003**: `utils/guided_tour.py` — NEW — Tour state management and step definitions
- **FILE-004**: `utils/quick_commands.py` — NEW — Quick command registry for command palette actions
- **FILE-005**: `ui/health_detail_dialog.py` — NEW — Health score breakdown modal dialog
- **FILE-006**: `ui/tour_overlay.py` — NEW — Guided tour spotlight overlay widget
- **FILE-007**: `ui/main_window.py` — MODIFIED — Toast exposure, sidebar filtering, tour launch
- **FILE-008**: `ui/base_tab.py` — MODIFIED — Toast convenience methods
- **FILE-009**: `ui/settings_tab.py` — MODIFIED — Experience level, help text, default indicators
- **FILE-010**: `ui/wizard.py` — MODIFIED — Progress bar, time estimate, level selection
- **FILE-011**: `ui/dashboard_tab.py` — MODIFIED — Clickable health score, undo card, toast feedback
- **FILE-012**: `ui/command_palette.py` — MODIFIED — Action support, category filters, recent commands
- **FILE-013**: `utils/history.py` — MODIFIED — `can_undo()`, `get_recent()`, targeted undo
- **FILE-014**: `ui/software_tab.py` — MODIFIED — Toast feedback on package operations
- **FILE-015**: `ui/maintenance_tab.py` — MODIFIED — Toast feedback on cleanup
- **FILE-016**: `ui/backup_tab.py` — MODIFIED — Toast feedback on backup/restore
- **FILE-017**: `ui/security_tab.py` — MODIFIED — Toast feedback on firewall toggles
- **FILE-018**: `ui/network_tab.py` — MODIFIED — Toast feedback on network changes
- **FILE-019**: `tests/test_experience_level.py` — NEW — Experience level tests
- **FILE-020**: `tests/test_base_tab_toast.py` — NEW — BaseTab toast integration tests
- **FILE-021**: `tests/test_health_detail.py` — NEW — Health detail manager tests
- **FILE-022**: `tests/test_settings_tab_ux.py` — NEW — Settings UX enhancement tests
- **FILE-023**: `tests/test_guided_tour.py` — NEW — Guided tour manager tests
- **FILE-024**: `tests/test_quick_commands.py` — NEW — Quick command registry tests
- **FILE-025**: `tests/test_dashboard_undo.py` — NEW — Dashboard undo integration tests
- **FILE-026**: `CHANGELOG.md` — MODIFIED — v47.0.0 release entry
- **FILE-027**: `README.md` — MODIFIED — UX features documentation
- **FILE-028**: `ROADMAP.md` — MODIFIED — v47.0 entry, v46.0 marked DONE
- **FILE-029**: `ARCHITECTURE.md` — MODIFIED — New module documentation

## 6. Testing

- **TEST-001**: `tests/test_experience_level.py` — Level persistence, tab visibility per level, default fallback, favorites override, level upgrade/downgrade
- **TEST-002**: `tests/test_base_tab_toast.py` — Toast convenience methods on BaseTab, MainWindow ancestor lookup, category mapping, success/error/info variants
- **TEST-003**: `tests/test_health_detail.py` — Component score calculation (healthy/degraded/critical), fix generation with correct tab targets, score boundaries, mock psutil
- **TEST-004**: `tests/test_settings_tab_ux.py` — Help text presence for all settings, default indicator rendering, non-default highlight logic, export/import button wiring
- **TEST-005**: `tests/test_guided_tour.py` — Tour state persistence, step count/ordering, completion marking, restart capability, sentinel file handling
- **TEST-006**: `tests/test_quick_commands.py` — Command registration, listing, execution, category filtering, keyword search, deduplication, error handling on failed actions
- **TEST-007**: `tests/test_dashboard_undo.py` — Undo button visibility when history empty/non-empty, recent changes display, undo execution success/failure, targeted vs last undo
- **TEST-008**: Existing test suite must pass with 0 regressions — run `just verify` after each phase

## 7. Risks & Assumptions

- **RISK-001**: Experience level filtering may confuse users who expect to see all tabs — mitigated by "Show All Tabs" toggle and Settings visibility
- **RISK-002**: Guided tour overlay may not render correctly on all display configurations (HiDPI, multi-monitor) — mitigated by using relative positioning and testing at multiple DPI
- **RISK-003**: Command palette actions that trigger system changes (e.g., "Run System Cleanup") need confirmation dialogs — mitigated by reusing existing `ConfirmActionDialog` for dangerous actions
- **RISK-004**: Toast notification stacking could become noisy during batch operations — mitigated by queue with delay and max visible count
- **RISK-005**: Health score drill-down modal may show stale data if system state changes while dialog is open — mitigated by refresh button in dialog
- **ASSUMPTION-001**: v46.0 Navigator category taxonomy is finalized and stable before this work begins
- **ASSUMPTION-002**: Existing `NotificationToast` widget is functional and tested — no rework needed
- **ASSUMPTION-003**: `HistoryManager.undo_last_action()` works reliably for stored undo commands
- **ASSUMPTION-004**: Users will discover the experience level selector through the wizard or Settings tab — no additional onboarding needed for the feature itself
- **ASSUMPTION-005**: 12 tabs is the right number for Beginner mode — may need user feedback to adjust

## 8. Related Specifications / Further Reading

- [ARCHITECTURE.md](../ARCHITECTURE.md) — Layer rules, tab patterns, plugin interface
- [ROADMAP.md](../ROADMAP.md) — Version history and scope tracking
- [System Hardening Guide](../.github/instructions/system_hardening_and_stabilization_guide.md) — Stabilization compliance rules
- [Existing tab reorganization plan](./refactor-tab-category-reorganization-1.md) — v46.0 category taxonomy (prerequisite)
- [utils/health_score.py](../loofi-fedora-tweaks/utils/health_score.py) — Current health scoring implementation
- [ui/notification_toast.py](../loofi-fedora-tweaks/ui/notification_toast.py) — Existing toast notification system
- [utils/history.py](../loofi-fedora-tweaks/utils/history.py) — Action history and undo mechanism
