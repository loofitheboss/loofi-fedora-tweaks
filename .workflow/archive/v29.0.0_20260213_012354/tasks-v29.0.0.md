# Tasks for v29.0.0

- [x] ID: TASK-001 | Files: `utils/error_handler.py` | Dep: - | Agent: code-implementer | Description: Implement centralized error handler with sys.excepthook override, LoofiError-aware dialog routing, and NotificationCenter logging.
  Acceptance: Global excepthook installed via install_error_handler(). LoofiError subtypes show hint dialogs. Unknown exceptions log to NotificationCenter with traceback.
  Docs: CHANGELOG
  Tests: `tests/test_error_handler.py`
- [x] ID: TASK-002 | Files: `ui/confirm_dialog.py` | Dep: - | Agent: code-implementer | Description: Create ConfirmActionDialog with action description, undo hint, optional snapshot checkbox, and "don't ask again" toggle.
  Acceptance: ConfirmActionDialog.confirm() static method returns bool. Integrates with SettingsManager.confirm_dangerous_actions preference.
  Docs: CHANGELOG
  Tests: `tests/test_confirm_dialog.py`
- [x] ID: TASK-003 | Files: `ui/notification_toast.py` | Dep: - | Agent: frontend-integration-builder | Description: Implement animated slide-in toast widget with category-based accent colors, auto-hide timer, and smooth animations.
  Acceptance: Toast slides in from top-right, auto-hides after configurable delay, wired to MainWindow.show_toast().
  Docs: CHANGELOG
  Tests: `tests/test_notification_toast.py`
- [x] ID: TASK-004 | Files: `ui/main_window.py` | Dep: - | Agent: frontend-integration-builder | Description: Enhance sidebar search to match tab descriptions, badge data, and category in addition to names.
  Acceptance: Search input filters sidebar items by name, description, badge, and category. Empty search restores all items.
  Docs: CHANGELOG
  Tests: `tests/test_v29_features.py`
- [x] ID: TASK-005 | Files: `ui/main_window.py` | Dep: - | Agent: frontend-integration-builder | Description: Add live colored status indicator dots on sidebar items for Maintenance and Storage tabs.
  Acceptance: _refresh_status_indicators() runs on 30s QTimer. Maintenance shows update availability. Storage shows disk usage level.
  Docs: CHANGELOG
  Tests: `tests/test_v29_features.py`
- [x] ID: TASK-006 | Files: `ui/dashboard_tab.py` | Dep: - | Agent: code-implementer | Description: Fix SparkLine widget to use palette-based colors instead of hardcoded dark theme colors.
  Acceptance: SparkLine uses palette().color(backgroundRole()) for background. Renders correctly in both dark and light themes.
  Docs: CHANGELOG
  Tests: `tests/test_v29_features.py`
- [x] ID: TASK-007 | Files: `utils/api_server.py` | Dep: - | Agent: backend-builder | Description: Lock down Web API CORS origins from wildcard to localhost only.
  Acceptance: CORS origins restricted to ["http://localhost:8000", "http://127.0.0.1:8000"]. Wildcard no longer accepted.
  Docs: CHANGELOG
  Tests: `tests/test_api_server.py`
- [x] ID: TASK-008 | Files: `ui/settings_tab.py`, `utils/settings.py` | Dep: - | Agent: backend-builder | Description: Add per-group reset buttons in Settings tab and SettingsManager.reset_group() method.
  Acceptance: "Reset Appearance" and "Reset Behavior" buttons reset only their group keys. SettingsManager.reset_group() accepts group name string.
  Docs: CHANGELOG
  Tests: `tests/test_settings_extended_v29.py`
- [x] ID: TASK-009 | Files: `ui/main_window.py` | Dep: - | Agent: frontend-integration-builder | Description: Restore keyboard accessibility on sidebar with StrongFocus policy and keyboard shortcut setup.
  Acceptance: Sidebar QTreeWidget has FocusPolicy.StrongFocus. Tab/arrow key navigation works. Keyboard shortcuts registered.
  Docs: CHANGELOG
  Tests: `tests/test_v29_features.py`
- [x] ID: TASK-010 | Files: `tests/test_error_handler.py`, `tests/test_confirm_dialog.py`, `tests/test_notification_toast.py`, `tests/test_v29_features.py`, `tests/test_settings_extended_v29.py` | Dep: TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009 | Agent: test-writer | Description: Create 95 comprehensive tests across 5 test files covering all v29 features.
  Acceptance: All 95 tests pass. Coverage includes success/failure paths, edge cases, and integration with existing modules.
  Docs: none
  Tests: self-referential
- [x] ID: TASK-011 | Files: `README.md` | Dep: TASK-001 through TASK-010 | Agent: release-planner | Description: Update README.md with v29.0.0 version, features, and release badge.
  Acceptance: README title, badges, and "What Is New" section reflect v29.0.0 changes.
  Docs: README
  Tests: none
- [x] ID: TASK-012 | Files: `docs/releases/RELEASE-NOTES-v29.0.0.md` | Dep: TASK-011 | Agent: release-planner | Description: Create release notes document for v29.0.0.
  Acceptance: Release notes cover all deliverables, new files, and upgrade notes.
  Docs: release notes
  Tests: none
