# Tasks for v24.0

| # | Task | Agent | Layer | Size | Depends | Files | Done |
|---|------|-------|-------|------|---------|-------|------|
| 1 | Define profile schema/types (`ProfileRecord`, `ProfileBundle`) and compatibility contract | architecture-advisor | core | S | - | core/profiles/models.py, core/profiles/__init__.py | [x] |
| 2 | Implement profile storage engine + migration-safe serialization in core; wire through ProfileManager facade | backend-builder | core | L | 1 | core/profiles/storage.py, utils/profiles.py | [x] |
| 3 | Add unit tests for dataclass validation, storage CRUD, legacy JSON read compatibility | test-writer | tests | M | 2 | tests/test_profile_storage.py, tests/test_profiles.py | [x] |
| 4 | Implement Profiles tab save/load + import/export actions using new ProfileManager APIs | frontend-integration-builder | ui | M | 2 | ui/profiles_tab.py | [x] |
| 5 | Add UI workflow tests for Profiles tab save/load/import/export flows with mocks | test-writer | tests | M | 4 | tests/test_profiles_tab.py | [x] |
| 6 | Add FastAPI profile endpoints (single + bundle import/export + apply/list) | backend-builder | api | M | 2 | api/routes/profiles.py, utils/api_server.py | [x] |
| 7 | Add API tests (auth dependency, success/failure payloads, overwrite behavior) | test-writer | tests | M | 6 | tests/test_api_profiles.py | [x] |
| 8 | Extend CLI `profile` command with import/export + bundle actions and flags | backend-builder | cli | M | 2 | cli/main.py, utils/profiles.py | [x] |
| 9 | Add CLI tests for new profile actions (single, bundle, overwrite, errors) | test-writer | tests | M | 8 | tests/test_cli_profile.py | [x] |
| 10 | Implement live-log polling API in SmartLogViewer (incremental fetch + dedupe cursor/key) | backend-builder | utils | M | - | utils/smart_logs.py | [x] |
| 11 | Add live log panel widget to existing Logs tab (start/stop, rate, bounded buffer) | frontend-integration-builder | ui | M | 10 | ui/logs_tab.py | [x] |
| 12 | Add tests for live-log polling logic and Logs tab live panel wiring | test-writer | tests | M | 11 | tests/test_smart_logs.py, tests/test_logs_tab.py | [x] |
| 13 | Integrate snapshot-before-apply in profile workflows (UI/CLI/API path) with graceful fallback | backend-builder | utils | M | 2 | utils/profiles.py, cli/main.py | [x] |
| 14 | Add tests for snapshot integration: backend available, unavailable, and failure-continue behavior | test-writer | tests | M | 13 | tests/test_profiles.py | [x] |
| 15 | Update release docs and roadmap status for v24 scope completion | release-planner | docs | S | 3,5,7,9,12,14 | CHANGELOG.md, README.md, RELEASE-NOTES-v24.0.0.md, ROADMAP.md | [x] |
