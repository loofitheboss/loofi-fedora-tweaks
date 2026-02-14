# Tasks — v39.0.0 "Prism"

## Phase: Build

### T1 ✅ — Migrate production deprecated imports (utils.system)
- **ID:** T1
- **Files:** `cli/main.py`, `api/routes/system.py`, `core/executor/operations.py`, `ui/maintenance_tab.py`, `ui/dashboard_tab.py`, `ui/doctor.py`, `ui/main_window.py`, `utils/commands.py`, `utils/batch_ops.py`, `utils/package_explorer.py`, `utils/package_manager.py`
- **Dep:** none
- **Agent:** CodeGen
- **Description:** Replace `from utils.system import SystemManager` with `from services.system import SystemManager` in 11 files
- **Acceptance:** Zero imports of `utils.system` in production code
- **Docs:** ARCHITECTURE.md updated
- **Tests:** Existing tests pass, no DeprecationWarning for utils.system

### T2 ✅ — Migrate production deprecated imports (utils.hardware, bluetooth, disk, temperature, processes, services)
- **ID:** T2
- **Files:** `cli/main.py`, `ui/hardware_tab.py`, `ui/monitor_tab.py`, `ui/diagnostics_tab.py`, `ui/dashboard_tab.py`, `ui/main_window.py`, `utils/arbitrator.py`, `utils/automation_profiles.py`, `utils/config_manager.py`, `utils/health_score.py`
- **Dep:** none
- **Agent:** CodeGen
- **Description:** Replace all remaining deprecated utils imports with services equivalents
- **Acceptance:** Zero deprecated utils imports in production code
- **Docs:** none
- **Tests:** Existing tests pass, no DeprecationWarning for hardware/disk/etc

### T3 ✅ — Migrate test deprecated imports
- **ID:** T3
- **Files:** `tests/test_bluetooth.py`, `tests/test_bugfixes.py`, `tests/test_services.py`, `tests/test_v10_features.py`, `tests/test_automation_profiles_deep.py`
- **Dep:** T1, T2
- **Agent:** CodeGen
- **Description:** Replace 13 deprecated imports in test files with services equivalents
- **Acceptance:** Zero DeprecationWarning in pytest output
- **Docs:** none
- **Tests:** All 4349+ tests still pass

### T4 ✅ — setStyleSheet elimination: wizard.py (17 calls)
- **ID:** T4
- **Files:** `ui/wizard.py`, `assets/modern.qss`, `assets/light.qss`
- **Dep:** none
- **Agent:** Sculptor
- **Description:** Replace 17 inline setStyleSheet calls with setObjectName + QSS rules
- **Acceptance:** Zero setStyleSheet in wizard.py
- **Docs:** none
- **Tests:** Existing wizard tests pass

### T5 ✅ — setStyleSheet elimination: monitor_tab.py (16 calls)
- **ID:** T5
- **Files:** `ui/monitor_tab.py`, `assets/modern.qss`, `assets/light.qss`
- **Dep:** none
- **Agent:** Sculptor
- **Description:** Replace 16 inline setStyleSheet calls with setObjectName + QSS rules
- **Acceptance:** Zero setStyleSheet in monitor_tab.py
- **Docs:** none
- **Tests:** Existing monitor tests pass

### T6 ✅ — setStyleSheet elimination: hardware_tab.py (16 calls)
- **ID:** T6
- **Files:** `ui/hardware_tab.py`, `assets/modern.qss`, `assets/light.qss`
- **Dep:** none
- **Agent:** Sculptor
- **Description:** Replace 16 inline setStyleSheet calls with setObjectName + QSS rules
- **Acceptance:** Zero setStyleSheet in hardware_tab.py
- **Docs:** none
- **Tests:** Existing hardware tests pass

### T7 ✅ — setStyleSheet elimination: community_tab.py (14 calls)
- **ID:** T7
- **Files:** `ui/community_tab.py`, `assets/modern.qss`, `assets/light.qss`
- **Dep:** none
- **Agent:** Sculptor
- **Description:** Replace 14 inline setStyleSheet calls with setObjectName + QSS rules
- **Acceptance:** Zero setStyleSheet in community_tab.py
- **Docs:** none
- **Tests:** Existing community tests pass

### T8 ✅ — setStyleSheet elimination: notification_panel.py (10 calls)
- **ID:** T8
- **Files:** `ui/notification_panel.py`, `assets/modern.qss`, `assets/light.qss`
- **Dep:** none
- **Agent:** Sculptor
- **Description:** Replace 10 inline setStyleSheet calls with setObjectName + QSS rules
- **Acceptance:** Zero setStyleSheet in notification_panel.py
- **Docs:** none
- **Tests:** Existing notification tests pass

### T9 ✅ — setStyleSheet elimination: remaining 10 UI files (~63 calls)
- **ID:** T9
- **Files:** `ui/maintenance_tab.py`, `ui/automation_tab.py`, `ui/profiles_tab.py`, `ui/teleport_tab.py`, `ui/development_tab.py`, `ui/desktop_tab.py`, `ui/storage_tab.py`, `ui/security_tab.py`, `ui/network_tab.py`, `ui/diagnostics_tab.py`, `assets/modern.qss`, `assets/light.qss`
- **Dep:** none
- **Agent:** Sculptor
- **Description:** Replace remaining inline setStyleSheet calls in 10 UI files
- **Acceptance:** Zero setStyleSheet in target files
- **Docs:** none
- **Tests:** All existing tests pass

### T10 ✅ — Remove deprecated utils shim modules
- **ID:** T10
- **Files:** `utils/system.py`, `utils/hardware.py`, `utils/bluetooth.py`, `utils/disk.py`, `utils/temperature.py`, `utils/processes.py`, `utils/services.py`
- **Dep:** T1, T2, T3
- **Agent:** CodeGen
- **Description:** Remove deprecated shim modules once all imports migrated
- **Acceptance:** Shim files removed, no import errors
- **Docs:** ARCHITECTURE.md updated
- **Tests:** All tests pass without shims

## Phase: Test

### T11 ✅ — Migration verification tests
- **ID:** T11
- **Files:** `tests/test_v39_prism.py`
- **Dep:** T1–T10
- **Agent:** Guardian
- **Description:** Add tests verifying zero deprecated imports, zero DeprecationWarnings, zero setStyleSheet in migrated files
- **Acceptance:** All new tests pass
- **Docs:** none
- **Tests:** New test file with migration verification

## Phase: Doc

### T12 ✅ — Update ARCHITECTURE.md import paths
- **ID:** T12
- **Files:** `ARCHITECTURE.md`
- **Dep:** T1, T2
- **Agent:** Planner
- **Description:** Update all code examples to use services.* imports
- **Acceptance:** No utils.system/hardware/etc references in examples
- **Docs:** ARCHITECTURE.md
- **Tests:** none

## Phase: Release

### T13 ✅ — CHANGELOG + README + release notes
- **ID:** T13
- **Files:** `CHANGELOG.md`, `README.md`, `docs/release_notes.md`, `docs/releases/RELEASE-NOTES-v39.0.0.md`
- **Dep:** T1–T12
- **Agent:** Planner
- **Description:** Document all v39.0 changes
- **Acceptance:** All release docs complete
- **Docs:** All release artifacts
- **Tests:** none
