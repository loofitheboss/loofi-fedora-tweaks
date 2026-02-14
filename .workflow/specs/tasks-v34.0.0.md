# v34.0.0 "Citadel" — Task Spec

## Tasks

### Phase 1: Light Theme Fix

- [x] T1: Remove dead QListWidget selectors from light.qss
  - ID: T1
  - Files: `assets/light.qss`
  - Dep: none
  - Agent: CodeGen
  - Description: Remove 4 dead QListWidget selectors (L13, L22, L30, L35)
  - Acceptance: No QListWidget selectors remain in light.qss
  - Docs: CHANGELOG
  - Tests: Visual verification

- [x] T2: Add QTreeWidget#sidebar selectors to light.qss
  - ID: T2
  - Files: `assets/light.qss`
  - Dep: T1
  - Agent: CodeGen
  - Description: Port sidebar selectors from modern.qss with Catppuccin Latte colors
  - Acceptance: Sidebar renders correctly in light theme
  - Docs: CHANGELOG
  - Tests: Visual verification

- [x] T3: Add remaining missing selectors to light.qss
  - ID: T3
  - Files: `assets/light.qss`
  - Dep: T2
  - Agent: CodeGen
  - Description: Port all 20+ missing selectors (buttons, focus, scrollbar, table, objectName targets)
  - Acceptance: All selectors from modern.qss have light.qss equivalents
  - Docs: CHANGELOG
  - Tests: Visual verification

### Phase 2: Stability & Error Handling

- [x] T4: Harden CommandRunner
  - ID: T4
  - Files: `utils/command_runner.py`
  - Dep: none
  - Agent: CodeGen
  - Description: Add timeout, kill escalation, stderr signal, is_running, crash detection, Flatpak cache, decode safety
  - Acceptance: All 7 improvements implemented, backward-compatible
  - Docs: CHANGELOG
  - Tests: `tests/test_command_runner.py`

- [x] T5: Extract subprocess.run from UI files
  - ID: T5
  - Files: `ui/dashboard_tab.py`, `ui/network_tab.py`, `ui/software_tab.py`, `ui/gaming_tab.py`, `ui/main_window.py`, `ui/system_info_tab.py`, `ui/development_tab.py`
  - Dep: none
  - Agent: Builder
  - Description: Move all subprocess calls from UI code into utils/ modules or QProcess
  - Acceptance: `grep -rn "import subprocess" loofi-fedora-tweaks/ui/` returns 0 hits
  - Docs: CHANGELOG
  - Tests: Tests for new utils functions

- [x] T6: Fix silent exception swallows
  - ID: T6
  - Files: 11 UI files
  - Dep: none
  - Agent: Guardian
  - Description: Replace 27 `except Exception: pass` with `except Exception: logger.debug(...)`
  - Acceptance: `grep -rn "except Exception.*pass" loofi-fedora-tweaks/ui/` returns 0 bare swallows
  - Docs: CHANGELOG
  - Tests: existing tests still pass

- [x] T7: Add log rotation to log.py
  - ID: T7
  - Files: `utils/log.py`
  - Dep: none
  - Agent: Builder
  - Description: Replace FileHandler with RotatingFileHandler(maxBytes=5MB, backupCount=3)
  - Acceptance: Log rotation active, old handler removed
  - Docs: CHANGELOG
  - Tests: `tests/test_log.py`

- [x] T8: Convert daemon.py print() to logging
  - ID: T8
  - Files: `utils/daemon.py`
  - Dep: T7
  - Agent: Builder
  - Description: Replace 17 print() calls with get_logger("loofi.daemon")
  - Acceptance: `grep -n "print(" utils/daemon.py` returns 0 hits
  - Docs: CHANGELOG
  - Tests: `tests/test_daemon.py`

### Phase 3: Accessibility

- [x] T9: Wire tooltips.py into UI tabs
  - ID: T9
  - Files: `ui/tooltips.py`, affected tab files
  - Dep: none
  - Agent: Guardian
  - Description: Import and apply tooltip constants to matching widgets
  - Acceptance: tooltips.py imported by relevant tabs, constants in use
  - Docs: CHANGELOG
  - Tests: existing tests

- [x] T10: Add accessibility annotations to all tabs
  - ID: T10
  - Files: All 27 UI tab files, `ui/base_tab.py`
  - Dep: none
  - Agent: Guardian
  - Description: Add setAccessibleName on interactive widgets in all tabs (314 calls total)
  - Acceptance: Every QPushButton/QCheckBox/QComboBox has accessible name across all 27 tabs
  - Docs: CHANGELOG
  - Tests: existing tests

### Phase 4: Testing

- [x] T11: Add tests for CommandRunner changes
  - ID: T11
  - Files: `tests/test_command_runner.py`
  - Dep: T4
  - Agent: Test
  - Description: Test timeout, kill escalation, stderr signal, crash detection, Flatpak caching
  - Acceptance: All new methods have test coverage
  - Docs: none
  - Tests: self

- [x] T12: Add tests for extracted subprocess functions
  - ID: T12
  - Files: `tests/test_network_utils.py`, `tests/test_software_utils.py`, `tests/test_gaming_utils.py`, `tests/test_desktop_utils.py`, `tests/test_system_info_utils.py`
  - Dep: T5
  - Agent: Test
  - Description: Test new utils functions extracted from UI code (85 tests total)
  - Acceptance: New functions covered
  - Docs: none
  - Tests: self

### Phase 5: Documentation

- [x] T13: Update CHANGELOG, README, release notes
  - ID: T13
  - Files: `CHANGELOG.md`, `README.md`, `docs/releases/RELEASE-NOTES-v34.0.0.md`
  - Dep: T1-T12
  - Agent: Planner
  - Description: Document all v34.0.0 changes
  - Acceptance: CHANGELOG has v34.0.0 section, release notes updated
  - Docs: self
  - Tests: none
