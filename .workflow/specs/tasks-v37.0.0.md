# v37.0.0 "Pinnacle" — Task Spec

## Tasks

### Phase 1: Backend — Update & Extension Management

- [x] T1: Implement UpdateManager backend
  - ID: T1
  - Files: `utils/update_manager.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `UpdateManager` with `check_updates()`, `preview_conflicts()`, `schedule_update()`, `rollback_last()`. Dataclasses: `UpdateEntry`, `ConflictEntry`, `ScheduledUpdate`. Branches on Atomic vs Traditional.
  - Acceptance: Returns update list, conflict preview works, rollback returns valid command tuple
  - Docs: CHANGELOG
  - Tests: `tests/test_update_manager.py`

- [x] T2: Implement ExtensionManager backend
  - ID: T2
  - Files: `utils/extension_manager.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `ExtensionManager` with `list_installed()`, `list_available()`, `install()`, `enable()`, `disable()`, `remove()`. Dataclass: `ExtensionEntry`. Detect GNOME vs KDE via `$XDG_CURRENT_DESKTOP`.
  - Acceptance: List installed works, install/enable/disable return valid command tuples, graceful fallback if no DE detected
  - Docs: CHANGELOG
  - Tests: `tests/test_extension_manager.py`

- [x] T3: Implement FlatpakManager backend
  - ID: T3
  - Files: `utils/flatpak_manager.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `FlatpakManager` with `get_flatpak_sizes()`, `get_flatpak_permissions()`, `find_orphan_runtimes()`, `cleanup_unused()`. Dataclass: `FlatpakSizeEntry`.
  - Acceptance: Sizes parsed from flatpak output, permissions listed, orphans detected, cleanup returns valid command tuple
  - Docs: CHANGELOG
  - Tests: `tests/test_flatpak_manager.py`

- [x] T4: Implement BootConfigManager backend
  - ID: T4
  - Files: `utils/boot_config.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `BootConfigManager` with `get_grub_config()`, `set_timeout()`, `set_default_kernel()`, `set_theme()`, `list_kernels()`, `list_themes()`, `apply_grub_changes()`. Dataclasses: `GrubConfig`, `KernelEntry`.
  - Acceptance: Parses /etc/default/grub, lists kernels via grubby, apply uses pkexec
  - Docs: CHANGELOG
  - Tests: `tests/test_boot_config.py`

### Phase 2: Backend — Display, Backup, Plugin

- [x] T5: Implement WaylandDisplayManager backend
  - ID: T5
  - Files: `utils/wayland_display.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `WaylandDisplayManager` with `get_displays()`, `set_scaling()`, `set_position()`. Dataclass: `DisplayInfo`. GNOME uses gsettings, KDE uses kscreen-doctor. Gate by `$XDG_SESSION_TYPE`.
  - Acceptance: Displays listed, scaling applied via gsettings/kscreen-doctor, X11 returns unsupported message
  - Docs: CHANGELOG
  - Tests: `tests/test_wayland_display.py`

- [x] T6: Implement BackupWizard backend
  - ID: T6
  - Files: `utils/backup_wizard.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `BackupWizard` with `detect_backup_tool()`, `create_snapshot()`, `list_snapshots()`, `restore_snapshot()`. Dataclasses: `SnapshotEntry`, `SnapshotResult`. Wraps Timeshift and Snapper.
  - Acceptance: Tool detection works, snapshot creation returns result, list parses output correctly
  - Docs: CHANGELOG
  - Tests: `tests/test_backup_wizard.py`

- [x] T7: Extend plugin marketplace with curated showcase
  - ID: T7
  - Files: `utils/plugin_marketplace.py`
  - Dep: none
  - Agent: Builder
  - Description: Add `get_curated_plugins()`, `get_plugin_quality()`. Dataclasses: `CuratedPlugin`, `QualityReport`. Featured plugins from CDN index with rating and download counts.
  - Acceptance: Curated list returns featured plugins, quality report includes rating and download count
  - Docs: CHANGELOG
  - Tests: `tests/test_plugin_marketplace.py`

### Phase 3: UI Tabs — New Tabs

- [x] T8: Create ExtensionsTab UI
  - ID: T8
  - Files: `ui/extensions_tab.py`
  - Dep: T2
  - Agent: Sculptor
  - Description: New `ExtensionsTab(BaseTab)` with search bar, installed/available toggle, extension cards with enable/disable/install/remove buttons. Desktop-aware (GNOME vs KDE label).
  - Acceptance: Tab renders, shows installed extensions, search filters results, toggle buttons work
  - Docs: CHANGELOG
  - Tests: `tests/test_extensions_tab.py`

- [x] T9: Create BackupTab UI (wizard flow)
  - ID: T9
  - Files: `ui/backup_tab.py`
  - Dep: T6
  - Agent: Sculptor
  - Description: New `BackupTab(BaseTab)` with `QStackedWidget` wizard flow. Step 1: detect tool, Step 2: configure, Step 3: create snapshot, Step 4: verify result. List existing snapshots with restore button.
  - Acceptance: Wizard flow works end-to-end, snapshot list shows entries, restore prompts confirmation
  - Docs: CHANGELOG
  - Tests: `tests/test_backup_tab.py`

### Phase 4: UI Extensions — Existing Tabs

- [x] T10: Add Smart Update section to MaintenanceTab
  - ID: T10
  - Files: `ui/maintenance_tab.py`
  - Dep: T1
  - Agent: Sculptor
  - Description: Add expandable "Smart Updates" section with update check button, conflict preview table, schedule picker, and rollback button. Uses `UpdateManager` backend.
  - Acceptance: Update check populates table, conflicts shown with warning, rollback triggers command
  - Docs: CHANGELOG
  - Tests: `tests/test_maintenance_tab.py`

- [x] T11: Add Flatpak section to SoftwareTab
  - ID: T11
  - Files: `ui/software_tab.py`
  - Dep: T3
  - Agent: Sculptor
  - Description: Add "Flatpak Manager" sub-tab with size visualization (horizontal bars), permission audit list, orphan runtime cleanup button.
  - Acceptance: Sizes shown as bar chart, permissions listed per app, cleanup button works
  - Docs: CHANGELOG
  - Tests: `tests/test_software_tab.py`

- [x] T12: Add Boot Config section to HardwareTab
  - ID: T12
  - Files: `ui/hardware_tab.py`
  - Dep: T4
  - Agent: Sculptor
  - Description: Add "Boot Configuration" sub-tab with GRUB timeout slider, default kernel dropdown, theme selector. Apply button runs grub2-mkconfig via pkexec.
  - Acceptance: Config loads, changes apply, kernel list populated
  - Docs: CHANGELOG
  - Tests: `tests/test_hardware_tab.py`

- [x] T13: Add Wayland Display section to DesktopTab
  - ID: T13
  - Files: `ui/desktop_tab.py`
  - Dep: T5
  - Agent: Sculptor
  - Description: Add "Display Configuration" section to DesktopTab. Scaling slider (100%–200%), fractional scaling toggle, multi-monitor arrangement. Gated by Wayland session check.
  - Acceptance: Scaling slider works, fractional toggle applies, hidden on X11
  - Docs: CHANGELOG
  - Tests: `tests/test_desktop_tab.py`

- [x] T14: Add plugin showcase to marketplace tab
  - ID: T14
  - Files: `ui/community_tab.py`
  - Dep: T7
  - Agent: Sculptor
  - Description: Add "Featured Plugins" section at top of marketplace tab with curated grid, rating badges, download counts, and one-click install.
  - Acceptance: Featured plugins shown, ratings displayed, install button works
  - Docs: CHANGELOG
  - Tests: `tests/test_community_tab.py`

### Phase 5: Wizard & CLI

- [x] T15: Upgrade first-run wizard v2
  - ID: T15
  - Files: `ui/wizard.py`
  - Dep: T1, T6
  - Agent: Sculptor
  - Description: Add system health check page (disk space, package state, firewall, backup status). Add recommended actions page with one-click apply buttons and risk badges. Store completion in `wizard_v2.json`.
  - Acceptance: Health check page runs diagnostics, recommendations are actionable, completion persisted
  - Docs: CHANGELOG
  - Tests: `tests/test_wizard.py`

- [x] T16: Add CLI subcommands for new features
  - ID: T16
  - Files: `cli/main.py`
  - Dep: T1, T2, T3, T4, T5, T6
  - Agent: CodeGen
  - Description: Add subcommands: `update check/schedule/rollback`, `extensions list/install/enable/disable/remove`, `flatpak sizes/permissions/cleanup`, `boot config/kernels/timeout`, `backup create/list/restore`. All with `--json` output support.
  - Acceptance: All subcommands execute, --json returns valid JSON, help text accurate
  - Docs: CHANGELOG
  - Tests: `tests/test_cli.py`

- [x] T17: Register new tabs in MainWindow
  - ID: T17
  - Files: `ui/main_window.py`
  - Dep: T8, T9
  - Agent: Sculptor
  - Description: Add lazy loaders for `ExtensionsTab` and `BackupTab` in `_lazy_tab()`. Add `add_page()` entries with appropriate icons and category placement.
  - Acceptance: Tabs appear in sidebar, lazy-load on first click, correct category grouping
  - Docs: CHANGELOG
  - Tests: `tests/test_main_window.py`

### Phase 6: Risk Registry & Safe Mode Updates

- [x] T18: Register new actions in RiskRegistry
  - ID: T18
  - Files: `utils/risk.py`
  - Dep: T1, T2, T3, T4, T5, T6
  - Agent: CodeGen
  - Description: Add risk entries for all new privileged actions: update rollback (HIGH), GRUB changes (HIGH), extension install/remove (MEDIUM), flatpak cleanup (LOW), snapshot create (LOW), snapshot restore (HIGH).
  - Acceptance: All new actions have risk entries, revert instructions for Medium/High
  - Docs: CHANGELOG
  - Tests: `tests/test_risk.py`

### Phase 7: Testing

- [x] T19: Tests for UpdateManager
  - ID: T19
  - Files: `tests/test_update_manager.py`
  - Dep: T1
  - Agent: Guardian
  - Description: Comprehensive tests for update check, conflict preview, scheduling, rollback. Mock subprocess calls. Test both DNF and rpm-ostree paths.
  - Acceptance: 100% coverage on UpdateManager, both paths tested
  - Docs: none
  - Tests: Self

- [x] T20: Tests for ExtensionManager
  - ID: T20
  - Files: `tests/test_extension_manager.py`
  - Dep: T2
  - Agent: Guardian
  - Description: Tests for list/install/enable/disable/remove. Mock GNOME and KDE command outputs. Test desktop detection and fallback.
  - Acceptance: Both GNOME and KDE paths tested, fallback tested
  - Docs: none
  - Tests: Self

- [x] T21: Tests for FlatpakManager
  - ID: T21
  - Files: `tests/test_flatpak_manager.py`
  - Dep: T3
  - Agent: Guardian
  - Description: Tests for size parsing, permission listing, orphan detection, cleanup. Mock flatpak command outputs.
  - Acceptance: All operations tested with realistic mock data
  - Docs: none
  - Tests: Self

- [x] T22: Tests for BootConfigManager
  - ID: T22
  - Files: `tests/test_boot_config.py`
  - Dep: T4
  - Agent: Guardian
  - Description: Tests for GRUB config parsing, kernel listing, timeout/theme/default changes, apply command. Mock file reads and subprocess.
  - Acceptance: Config parsing tested, all setters tested, apply uses pkexec
  - Docs: none
  - Tests: Self

- [x] T23: Tests for WaylandDisplayManager
  - ID: T23
  - Files: `tests/test_wayland_display.py`
  - Dep: T5
  - Agent: Guardian
  - Description: Tests for display listing, scaling, positioning. Mock gsettings and kscreen-doctor. Test X11 fallback.
  - Acceptance: Both GNOME and KDE paths tested, X11 graceful degradation tested
  - Docs: none
  - Tests: Self

- [x] T24: Tests for BackupWizard
  - ID: T24
  - Files: `tests/test_backup_wizard.py`
  - Dep: T6
  - Agent: Guardian
  - Description: Tests for tool detection, snapshot create/list/restore. Mock both Timeshift and Snapper. Test no-tool-found fallback.
  - Acceptance: Both tools tested, edge cases covered, restore confirmation tested
  - Docs: none
  - Tests: Self

- [x] T25: Tests for new UI tabs and sections
  - ID: T25
  - Files: `tests/test_extensions_tab.py`, `tests/test_backup_tab.py`
  - Dep: T8, T9
  - Agent: Guardian
  - Description: Tests for new tab rendering, widget initialization, signal connections. Mock backend calls.
  - Acceptance: Tabs instantiate without errors, buttons connected to correct handlers
  - Docs: none
  - Tests: Self

- [x] T26: Tests for CLI subcommands
  - ID: T26
  - Files: `tests/test_cli.py`
  - Dep: T16
  - Agent: Guardian
  - Description: Tests for all new CLI subcommands. Mock backend calls. Test --json output format.
  - Acceptance: All subcommands tested, JSON output validated
  - Docs: none
  - Tests: Self

### Phase 8: Release

- [x] T27: CHANGELOG + README + release notes
  - ID: T27
  - Files: `CHANGELOG.md`, `README.md`, `docs/release_notes.md`
  - Dep: T1-T26
  - Agent: Planner
  - Description: Write v37.0.0 changelog entry, update README feature list (tab count, coverage), create release notes with feature highlights.
  - Acceptance: All changes documented, version references updated, tab count accurate
  - Docs: Self
  - Tests: `scripts/check_release_docs.py`
