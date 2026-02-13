# Tasks for v31.0.0 — Smart UX

| # | ID | Task | Agent | Layer | Size | Dep | Files | Done |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | T1 | Health score backend | backend-builder | utils | M | - | utils/health_score.py | [x] |
| 2 | T2 | Health score dashboard widget | frontend-integration-builder | ui | M | T1 | ui/dashboard_tab.py | [x] |
| 3 | T3 | i18n infrastructure | backend-builder | utils | M | - | utils/i18n.py, resources/translations/ | [x] |
| 4 | T4 | Batch operations backend | backend-builder | utils | S | - | utils/batch_ops.py | [x] |
| 5 | T5 | Batch operations UI (Software tab) | frontend-integration-builder | ui | M | T4 | ui/software_tab.py | [x] |
| 6 | T6 | Report exporter backend | backend-builder | utils | M | - | utils/report_exporter.py | [x] |
| 7 | T7 | Export report UI (System Info tab) | frontend-integration-builder | ui | S | T6 | ui/system_info_tab.py | [x] |
| 8 | T8 | Plugin template script | code-implementer | scripts | S | - | scripts/create_plugin.sh | [x] |
| 9 | T9 | Favorites backend | backend-builder | utils | S | - | utils/favorites.py | [x] |
| 10 | T10 | Favorites sidebar UI | frontend-integration-builder | ui | M | T9 | ui/main_window.py | [x] |
| 11 | T11 | Quick actions config backend | backend-builder | utils | S | - | utils/quick_actions_config.py | [x] |
| 12 | T12 | Configurable quick actions UI | frontend-integration-builder | ui | M | T11 | ui/dashboard_tab.py | [x] |
| 13 | T13 | Accessibility level 2 pass | frontend-integration-builder | ui | L | - | ui/*.py | [x] |
| 14 | T14 | Tests for v31 modules | test-writer | tests | L | T1-T12 | tests/test_health_score.py, tests/test_i18n.py, tests/test_batch_ops.py, tests/test_report_exporter.py, tests/test_favorites.py, tests/test_quick_actions_config.py | [x] |
| 15 | T15 | Version bump, CHANGELOG, docs | release-planner | docs | M | T1-T14 | version.py, CHANGELOG.md, README.md, docs/release_notes.md | [x] |

## Task Contract Details

### T1: Health score backend

- **ID:** T1
- **Files:** utils/health_score.py
- **Dep:** -
- **Agent:** backend-builder
- **Description:** Create HealthScoreManager with weighted scoring from CPU, RAM, disk, updates, uptime
- **Acceptance:** HealthScore dataclass returns score 0-100, grade A-F, components dict, recommendations list
- **Docs:** Docstrings on all public methods
- **Tests:** tests/test_health_score.py

### T2: Health score dashboard widget

- **ID:** T2
- **Files:** ui/dashboard_tab.py
- **Dep:** T1
- **Agent:** frontend-integration-builder
- **Description:** Add HealthScoreWidget card to Dashboard between header and live metrics
- **Acceptance:** Circular gauge shows score, grade, color; refreshes every 30s
- **Docs:** Widget docstring
- **Tests:** tests/test_dashboard_health.py (smoke)

### T3: i18n infrastructure

- **ID:** T3
- **Files:** utils/i18n.py, resources/translations/en.ts, resources/translations/sv.ts
- **Dep:** -
- **Agent:** backend-builder
- **Description:** Qt Linguist workflow: translator loading, locale detection, .ts/.qm files
- **Acceptance:** I18nManager.set_locale() installs QTranslator, available_locales() returns list
- **Docs:** resources/translations/README.md
- **Tests:** tests/test_i18n.py

### T4: Batch operations backend

- **ID:** T4
- **Files:** utils/batch_ops.py
- **Dep:** -
- **Agent:** backend-builder
- **Description:** BatchOpsManager with batch_install, batch_remove, batch_update methods
- **Acceptance:** Returns proper operation tuples, respects Atomic branching
- **Docs:** Docstrings
- **Tests:** tests/test_batch_ops.py

### T5: Batch operations UI

- **ID:** T5
- **Files:** ui/software_tab.py
- **Dep:** T4
- **Agent:** frontend-integration-builder
- **Description:** Add checkboxes to package list, batch action buttons
- **Acceptance:** "Install Selected" and "Remove Selected" buttons invoke BatchOpsManager
- **Docs:** -
- **Tests:** tests/test_software_batch.py (smoke)

### T6: Report exporter backend

- **ID:** T6
- **Files:** utils/report_exporter.py
- **Dep:** -
- **Agent:** backend-builder
- **Description:** Export system info as Markdown or HTML
- **Acceptance:** export_markdown() and export_html() return formatted strings
- **Docs:** Docstrings
- **Tests:** tests/test_report_exporter.py

### T7: Export report UI

- **ID:** T7
- **Files:** ui/system_info_tab.py
- **Dep:** T6
- **Agent:** frontend-integration-builder
- **Description:** Add "Export Report" button with format dropdown
- **Acceptance:** Button saves report to user-chosen location
- **Docs:** -
- **Tests:** tests/test_system_info_export.py (smoke)

### T8: Plugin template script

- **ID:** T8
- **Files:** scripts/create_plugin.sh
- **Dep:** -
- **Agent:** code-implementer
- **Description:** Scaffold new plugin with plugin.py, metadata.json, README.md, test file
- **Acceptance:** Running script creates valid plugin directory structure
- **Docs:** --help flag
- **Tests:** Manual verification

### T9: Favorites backend

- **ID:** T9
- **Files:** utils/favorites.py
- **Dep:** -
- **Agent:** backend-builder
- **Description:** FavoritesManager with JSON persistence for pinned tabs
- **Acceptance:** add/remove/get/is_favorite methods work with JSON file
- **Docs:** Docstrings
- **Tests:** tests/test_favorites.py

### T10: Favorites sidebar UI

- **ID:** T10
- **Files:** ui/main_window.py
- **Dep:** T9
- **Agent:** frontend-integration-builder
- **Description:** Pin icon in sidebar, favorites section at top, right-click context menu
- **Acceptance:** Pinned tabs appear in favorites section, persist across restarts
- **Docs:** -
- **Tests:** tests/test_favorites_ui.py (smoke)

### T11: Quick actions config backend

- **ID:** T11
- **Files:** utils/quick_actions_config.py
- **Dep:** -
- **Agent:** backend-builder
- **Description:** QuickActionsConfig with JSON persistence for dashboard quick actions
- **Acceptance:** get/set/default_actions methods work, defaults match current hardcoded actions
- **Docs:** Docstrings
- **Tests:** tests/test_quick_actions_config.py

### T12: Configurable quick actions UI

- **ID:** T12
- **Files:** ui/dashboard_tab.py
- **Dep:** T11
- **Agent:** frontend-integration-builder
- **Description:** Dashboard reads quick actions from config, add Configure button
- **Acceptance:** Quick actions grid is dynamic, config dialog allows reordering
- **Docs:** -
- **Tests:** tests/test_dashboard_quick_actions.py (smoke)

### T13: Accessibility level 2

- **ID:** T13
- **Files:** ui/*.py (all tab files)
- **Dep:** -
- **Agent:** frontend-integration-builder
- **Description:** Add setAccessibleName/setAccessibleDescription to all interactive widgets
- **Acceptance:** All buttons, inputs, combos have accessible names
- **Docs:** -
- **Tests:** tests/test_accessibility.py

### T14: Tests for v31 modules

- **ID:** T14
- **Files:** tests/test_health_score.py, tests/test_i18n.py, tests/test_batch_ops.py, tests/test_report_exporter.py, tests/test_favorites.py, tests/test_quick_actions_config.py
- **Dep:** T1-T12
- **Agent:** test-writer
- **Description:** Comprehensive unit tests for all new v31 utils modules
- **Acceptance:** All tests pass, mocked system calls, both success and failure paths
- **Docs:** -
- **Tests:** Self-referential

### T15: Version bump, CHANGELOG, docs

- **ID:** T15
- **Files:** version.py, CHANGELOG.md, README.md, docs/release_notes.md
- **Dep:** T1-T14
- **Agent:** release-planner
- **Description:** Finalize version, update all documentation
- **Acceptance:** Version sync between version.py and .spec, complete CHANGELOG entry
- **Docs:** All updated
- **Tests:** -
