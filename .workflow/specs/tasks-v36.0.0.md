# v36.0.0 "Horizon" — Task Spec

## Tasks

### Phase 1: UX Safety (Safe Mode + Risk Classification)

- [ ] T1: Implement SafeModeManager
  - ID: T1
  - Files: `utils/safe_mode.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `SafeModeManager` with `is_safe_mode()`, `enable()`, `disable()`, `toggle()`. Config stored in `~/.config/loofi-fedora-tweaks/safe_mode.json`. First launch defaults to safe mode ON.
  - Acceptance: SafeModeManager persists state, first-run returns True, toggle works
  - Docs: CHANGELOG
  - Tests: `tests/test_safe_mode.py`

- [ ] T2: Implement RiskRegistry and RiskLevel
  - ID: T2
  - Files: `utils/risk.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `RiskLevel` enum (LOW/MEDIUM/HIGH), `RiskEntry` dataclass, `RiskRegistry` with pre-populated action→risk mappings. Include `get_risk()`, `get_revert_instructions()`.
  - Acceptance: All PrivilegedCommand actions have risk entries, revert instructions for Medium/High
  - Docs: CHANGELOG
  - Tests: `tests/test_risk.py`

- [ ] T3: Implement ConfigBackupManager
  - ID: T3
  - Files: `utils/config_backup.py`
  - Dep: none
  - Agent: Builder
  - Description: Create `ConfigBackupManager` with `backup_before()`, `list_backups()`, `restore()`. Auto-snapshot config dir before destructive ops. Max 20 backups with rotation.
  - Acceptance: Backup creates timestamped copy, restore works, old backups cleaned up
  - Docs: CHANGELOG
  - Tests: `tests/test_config_backup.py`

- [ ] T4: Wire safe mode into BaseTab
  - ID: T4
  - Files: `ui/base_tab.py`
  - Dep: T1
  - Agent: Sculptor
  - Description: Add safe mode check in `run_command()` — if safe mode ON, show info message instead of executing. Add safe mode banner widget to BaseTab layout.
  - Acceptance: Commands blocked in safe mode, banner visible, non-command tabs unaffected
  - Docs: CHANGELOG
  - Tests: `tests/test_base_tab.py`

- [ ] T5: Wire risk + backup into ConfirmActionDialog
  - ID: T5
  - Files: `ui/confirm_dialog.py`
  - Dep: T2, T3
  - Agent: Sculptor
  - Description: Show risk level badge (color-coded) and revert instructions for Medium/High risk actions. Call `ConfigBackupManager.backup_before()` on confirm for Medium/High.
  - Acceptance: Risk badge shown, revert instructions visible, backup created before High risk
  - Docs: CHANGELOG
  - Tests: `tests/test_confirm_dialog.py`

- [ ] T6: Add safe mode CLI flags
  - ID: T6
  - Files: `cli/main.py`
  - Dep: T1
  - Agent: CodeGen
  - Description: Add `--safe-mode` and `--no-safe-mode` flags. In safe mode, CLI commands print preview instead of executing. Add `safe-mode` subcommand to check/toggle status.
  - Acceptance: `--safe-mode` prevents execution, `--cli safe-mode status` shows current state
  - Docs: CHANGELOG
  - Tests: `tests/test_cli.py`

### Phase 2: API Security

- [ ] T7: Add rate limiting to auth endpoints
  - ID: T7
  - Files: `api/__init__.py`
  - Dep: none
  - Agent: Builder
  - Description: Add rate limiting middleware (10 req/min per IP) on `/api/auth/*` endpoints. Use existing `TokenBucketRateLimiter` pattern or simple in-memory counter with TTL.
  - Acceptance: 11th request within 1 minute returns 429, counter resets after window
  - Docs: CHANGELOG
  - Tests: `tests/test_api_server.py`

- [ ] T8: Add --unsafe-expose flag
  - ID: T8
  - Files: `api/__init__.py`, `cli/main.py`
  - Dep: none
  - Agent: CodeGen
  - Description: API server refuses to bind to non-localhost addresses unless `--unsafe-expose` flag is passed. Default bind: `127.0.0.1`.
  - Acceptance: Non-localhost bind without flag raises error, with flag proceeds with warning
  - Docs: CHANGELOG
  - Tests: `tests/test_api_server.py`

- [ ] T9: Separate read-only vs privileged API endpoints
  - ID: T9
  - Files: `api/routes/system.py`, `api/routes/profiles.py`, `api/routes/executor.py`
  - Dep: T7
  - Agent: Builder
  - Description: GET endpoints accessible without auth. POST/PUT/DELETE require auth token. Add audit logging for privileged API calls.
  - Acceptance: GET works unauthenticated, POST without token returns 401, privileged calls audit-logged
  - Docs: CHANGELOG
  - Tests: `tests/test_api_server.py`

### Phase 3: Performance Optimization

- [ ] T10: Create startup profiler script
  - ID: T10
  - Files: `scripts/profile_startup.py`
  - Dep: none
  - Agent: CodeGen
  - Description: Script that profiles import times and widget creation using `cProfile` + custom import hook. Reports top 20 slowest imports and total startup time.
  - Acceptance: Script runs, produces ranked import time report
  - Docs: CHANGELOG
  - Tests: Manual verification

- [ ] T11: Lazy import audit and optimization
  - ID: T11
  - Files: `utils/lazy_imports.py`, `loofi-fedora-tweaks/main.py`
  - Dep: T10
  - Agent: CodeGen
  - Description: Create `lazy_imports.py` with `lazy_import()` helper. Audit main.py and heavy modules for imports that can be deferred. Target: <2s cold start.
  - Acceptance: `profile_startup.py` shows measurable improvement, no functional regression
  - Docs: CHANGELOG
  - Tests: `tests/test_lazy_imports.py`

- [ ] T12: QSS stylesheet caching
  - ID: T12
  - Files: `ui/main_window.py`
  - Dep: none
  - Agent: CodeGen
  - Description: Cache parsed QSS stylesheets to avoid re-reading from disk on theme switches. Store compiled stylesheets in memory dict keyed by theme name + file mtime.
  - Acceptance: Second theme switch is faster, cache invalidated on file change
  - Docs: CHANGELOG
  - Tests: `tests/test_main_window.py`

### Phase 4: Navigation & UI Polish

- [ ] T13: Sidebar smooth scrolling
  - ID: T13
  - Files: `ui/main_window.py`
  - Dep: none
  - Agent: Sculptor
  - Description: Add smooth scroll animation to sidebar `QTreeWidget` using `QPropertyAnimation`. Scroll to selected item with easing curve.
  - Acceptance: Sidebar scrolls smoothly to selected tab, no visual jitter
  - Docs: CHANGELOG
  - Tests: `tests/test_main_window.py`

- [ ] T14: Sidebar hover states and collapse animation
  - ID: T14
  - Files: `ui/main_window.py`, `assets/modern.qss`
  - Dep: T13
  - Agent: Sculptor
  - Description: Add hover highlight transitions on sidebar items. Add collapse/expand animation for sidebar panel (slide animation with easing).
  - Acceptance: Hover shows smooth highlight, collapse is animated
  - Docs: CHANGELOG
  - Tests: Visual verification

- [ ] T15: Breadcrumb bar improvements
  - ID: T15
  - Files: `ui/main_window.py`
  - Dep: none
  - Agent: Sculptor
  - Description: Improve breadcrumb layout with path truncation for long names, separator styling, and consistent font sizing.
  - Acceptance: Breadcrumb handles long tab names gracefully, consistent styling
  - Docs: CHANGELOG
  - Tests: `tests/test_main_window.py`

- [ ] T16: Tab layout spacing audit
  - ID: T16
  - Files: Multiple `ui/*_tab.py` files
  - Dep: none
  - Agent: Sculptor
  - Description: Audit and fix inconsistent spacing, margins, and widget alignment across tabs. Standardize: 12px section margins, 8px widget spacing, 4px inner padding.
  - Acceptance: All tabs use consistent spacing values, no visual misalignment
  - Docs: CHANGELOG
  - Tests: Visual verification

### Phase 5: Testing & Coverage

- [ ] T17: Tests for safe mode, risk, config backup
  - ID: T17
  - Files: `tests/test_safe_mode.py`, `tests/test_risk.py`, `tests/test_config_backup.py`
  - Dep: T1, T2, T3
  - Agent: Guardian
  - Description: Comprehensive tests for all Phase 1 modules. Mock filesystem operations. Test first-run defaults, toggle, persistence, risk lookups, backup rotation.
  - Acceptance: 100% coverage on new modules, both success and failure paths
  - Docs: none
  - Tests: Self

- [ ] T18: Tests for API security changes
  - ID: T18
  - Files: `tests/test_api_server.py`
  - Dep: T7, T8, T9
  - Agent: Guardian
  - Description: Tests for rate limiting (429 response), unsafe-expose guard, read-only vs privileged endpoint separation.
  - Acceptance: Rate limiting, exposure guard, and auth separation all tested
  - Docs: none
  - Tests: Self

- [ ] T19: Tests for lazy imports and performance
  - ID: T19
  - Files: `tests/test_lazy_imports.py`
  - Dep: T11
  - Agent: Guardian
  - Description: Tests for lazy_import helper, deferred module loading, cache invalidation.
  - Acceptance: Lazy imports tested for deferred loading and error handling
  - Docs: none
  - Tests: Self

- [ ] T20: Coverage push toward 80%
  - ID: T20
  - Files: Multiple test files
  - Dep: T17, T18, T19
  - Agent: Guardian
  - Description: Identify lowest-coverage modules and add targeted tests. Target: ≥80% overall coverage.
  - Acceptance: `pytest --cov` reports ≥80%
  - Docs: CHANGELOG
  - Tests: Self

### Phase 6: Release

- [ ] T21: CHANGELOG + README + release notes
  - ID: T21
  - Files: `CHANGELOG.md`, `README.md`, `docs/release_notes.md`
  - Dep: T1-T20
  - Agent: Planner
  - Description: Write v36.0.0 changelog entry, update README feature list, create release notes.
  - Acceptance: All changes documented, version references updated
  - Docs: Self
  - Tests: `scripts/check_release_docs.py`
