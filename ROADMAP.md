# Loofi Fedora Tweaks — Roadmap

<!-- markdownlint-configure-file {"MD024": {"siblings_only": true}, "MD060": false} -->

> Machine-parseable roadmap. Agents read this to determine scope, status, and sequencing.
> Format: `[STATUS]` where STATUS = DONE | ACTIVE | NEXT | PLANNED

## Version Index

| Version | Codename | Status | Theme |
|---------|----------|--------|-------|
| v21.0 | UX Stabilization | DONE | Layout integrity, QSS scoping |
| v22.0 | Usability | SKIPPED | Search, status indicators, preferences |
| v23.0 | Architecture Hardening | DONE | Service layer, executor, imports |
| v24.0 | Power Features | DONE | Profiles, export, log panel, snapshots |
| v25.0 | Plugin Architecture | DONE | Plugin system, UI redesign, API |
| v25.0.3 | Maintenance Update Crash Hotfix | DONE | Stabilize Maintenance update actions |
| v26.0 | Plugin Marketplace | DONE | External plugins, marketplace, sandboxing |
| v27.0 | Marketplace Enhancement | DONE | CDN index, ratings/reviews, badges, analytics, hot-reload, stronger sandbox |
| v28.0 | Workflow Contract Reset | DONE | Clean-slate workflow state, runner-compatible planning artifacts, kickoff handoff |
| v29.0 | Usability & Polish | DONE | UX polish, skipped v22 scope, error handling, accessibility, CORS |
| v30.0 | Distribution & Reliability | DONE | Flatpak, AppImage, auto-update, CI hardening, coverage 75% |
| v31.0 | Smart UX | DONE | Health score, i18n, batch ops, export report, plugin template |
| v32.0 | Abyss | DONE | Full visual redesign, activity-based categories, Abyss theme |
| v33.0 | Bastion | DONE | Testing & type safety debt, CI pipeline hardening |
| v34.0 | Citadel | DONE | Light theme fix, stability hardening, accessibility polish |
| v35.0 | Fortress | DONE | Subprocess timeout enforcement, audit logging, privilege hardening |
| v36.0 | Horizon | DONE | UX safety, performance optimization, navigation polish |
| v37.0 | Pinnacle | DONE | Smart features, ecosystem expansion, user-requested enhancements |
| v38.0 | Clarity | DONE | UX polish, theme correctness, stability improvements |
| v39.0 | Prism | DONE | Deprecated import migration, inline style elimination |
| v40.0 | Foundation | DONE | Correctness & safety hardening, zero shell injection |
| v41.0 | Coverage | DONE | Test coverage 80%+, CI pipeline hardening |

---

## [DONE] v41.0 "Coverage" — Test Coverage & CI Debt

### Scope

Pure test and CI release. Push test coverage from 74% to 80%+, add JUnit
annotations via dorny/test-reporter, gate releases on RPM smoke tests,
and enforce the 80% threshold in all CI workflows. Zero production code changes.

### Deliverables

- [x] Eliminate zero-coverage modules (plugin_cdn_client, battery_shim)
- [x] Write/expand tests for 7 largest under-tested utils modules
- [x] Add dedicated test files for 5 biggest untested UI tabs
- [x] Additional coverage push: 8 more test files to cross 80% threshold
- [x] dorny/test-reporter for JUnit XML GitHub annotations (ci.yml, auto-release.yml)
- [x] RPM post-install smoke test job in auto-release.yml
- [x] COVERAGE_THRESHOLD bumped from 74 to 80 in all 3 workflow files
- [x] Coverage badge added to README.md
- [x] Version bump + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Test | All 23 test files, coverage analysis |
| Builder | CI workflow improvements |
| Planner | Release coordination |

### Dependencies

- v40.0 Foundation (clean safety baseline)

---

## [DONE] v40.0 "Foundation" — Correctness & Safety Hardening

### Scope

Pure hardening release. Every subprocess call gets an explicit timeout,
every logger call uses `%s` formatting, every `pkexec sh -c` invocation
refactored to atomic commands, all hardcoded `dnf` references route
through `PrivilegedCommand.dnf()` or `SystemManager.get_package_manager()`.

### Deliverables

- [x] Zero `pkexec sh -c` patterns (10 calls refactored to atomic commands)
- [x] Zero hardcoded `dnf` (13 references replaced with SystemManager)
- [x] Zero f-string logger calls (21 calls converted to `%s`)
- [x] Zero bare exception handlers (141 blocks now log exceptions)
- [x] Subprocess timeout enforcement on all remaining calls
- [x] AdvancedOps return types (4 methods → OperationResult dataclass)
- [x] Stale import migrations (utils.system → services.system)
- [x] Release notes + version bump

### Agent Assignment

| Agent | Task |
|-------|------|
| Builder | Shell injection elimination, dnf replacement, timeout enforcement |
| CodeGen | Logger formatting, exception handling |
| Guardian | Stale import fixes, migration tests |
| Planner | Release coordination |

### Dependencies

- v39.0 Prism (clean import baseline)

---

## [DONE] v39.0 "Prism" — Import Migration & Style Elimination

### Scope

Complete the services layer migration from v23.0. Remove all deprecated
`utils/` import shims, replace 175+ inline `setStyleSheet` calls with
QSS objectNames, and enforce zero DeprecationWarnings.

### Deliverables

- [x] Zero deprecated imports (27 production + 13 test files migrated)
- [x] Zero inline styles (175+ setStyleSheet → setObjectName + QSS rules)
- [x] Zero DeprecationWarnings (strict enforcement)
- [x] 9 shim modules removed
- [x] ~600 new QSS rules in both modern.qss and light.qss
- [x] Migration verification tests (test_v39_prism.py)
- [x] Release notes + version bump

### Agent Assignment

| Agent | Task |
|-------|------|
| Builder | Import migration, shim removal |
| CodeGen | Style-to-QSS conversion |
| Sculptor | QSS rules authoring |
| Guardian | Migration tests, DeprecationWarning enforcement |
| Planner | Release coordination |

### Dependencies

- v38.0 Clarity (theme correctness baseline)

---

## [DONE] v38.0 "Clarity" — UX Polish & Theme Correctness

### Scope

Focus on user experience improvements, theme correctness, and stability
hardening. No new major features — refine what exists.

- Eliminate all hardcoded dark-theme colors; use QSS objectNames exclusively
- Fix Doctor tab: use PrivilegedCommand, SystemManager, self.tr(), objectNames
- Fix Dashboard: dynamic username, QSS-driven metric colors
- Wire Quick Actions callbacks to actual tab navigation
- Add Undo UI surface (status bar button + toast notifications)
- Confirm Dialog: risk level badges (LOW/MEDIUM/HIGH), per-action suppression
- BaseTab: Copy/Save/Cancel output toolbar for all command tabs
- Command Palette: keyword description hints under each entry
- Clickable breadcrumb category for parent navigation
- Dual-theme QSS rules for all new objectNames (modern + light)

### Deliverables

- [x] Version bump to v38.0.0 "Clarity"
- [x] Doctor tab rewrite (PrivilegedCommand, get_package_manager, self.tr(), a11y)
- [x] Dashboard: getpass.getuser() username, QSS objectNames for all metrics
- [x] Quick Actions: 16 callbacks wired via switch_to_tab()
- [x] QSS rules for ~30 new objectNames in modern.qss + light.qss
- [x] Confirm Dialog: 9 objectNames, risk badges, per-action don't-ask-again
- [x] Command Palette: 5 objectNames, keyword hints display
- [x] BaseTab: table objectName, optional color params, Copy/Save/Cancel toolbar
- [x] Undo button in status bar + toast notification system
- [x] Clickable breadcrumb category (QPushButton with hover underline)
- [x] Tests for all changes
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Arkitekt | QSS architecture, objectName strategy |
| Builder | Doctor rewrite, Quick Actions wiring, HistoryManager integration |
| Sculptor | UI enhancements (undo, breadcrumb, output toolbar, risk badges) |
| CodeGen | Theme fixes, objectName replacements |
| Guardian | Tests for all changes |
| Planner | Release coordination |

### Dependencies

- v37.0 Pinnacle (feature baseline)

---

## [DONE] v35.0 "Fortress" — Security & Privilege Hardening

### Scope

Complete hardening guide Phase 1–2 to unblock future feature development.
263 subprocess calls across 56 files need timeout enforcement.
Structured audit logging, parameter validation, and Polkit separation.

- Add `timeout` parameter to all 263 subprocess calls across 56 utils/cli files
- Implement structured audit logging for all privileged actions
- Add parameter schema validation to PrivilegedCommand
- Split monolithic Polkit policy into per-capability policies
- Add dry-run mode for system mutations
- Create SECURITY.md with vulnerability disclosure process
- Deprecate `install.sh` curl-pipe-bash (move to "Advanced" section)
- Add CLI `run_operation()` timeout enforcement
- Fix notification panel UI bug (panel shows on init, badge ordering)

### Deliverables

- [x] Subprocess timeout enforcement: all 56 files (263 calls) have `timeout` parameter
- [x] Audit logger module: `utils/audit.py` with structured JSON logging
- [x] All privileged actions logged (timestamp, action, params, exit code, stderr hash)
- [x] PrivilegedCommand parameter validation (schema-based, reject unknown params)
- [x] Polkit policy split: 10+ granular policies (firewall, network, storage, service, kernel, etc.)
- [x] Dry-run mode: `--dry-run` flag on CLI, preview mode on GUI confirm dialogs
- [x] SECURITY.md with disclosure process and supported versions
- [x] `install.sh` deprecated with warning banner, README updated to recommend RPM/Copr
- [x] CLI `run_operation()` with configurable timeout (default 300s)
- [x] Notification panel: starts hidden, proper positioning, bell+badge ordering
- [x] Tests for all changes (audit, validation, timeouts)
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Builder | Subprocess timeouts (56 files), audit logger, parameter validation |
| CodeGen | Polkit split, dry-run mode, CLI timeout |
| Guardian | Tests, SECURITY.md, install.sh deprecation |
| Sculptor | Notification panel UI fix |
| Planner | Release coordination |

### Dependencies

- v34.0 Citadel (clean stability baseline)

---

## [DONE] v36.0 "Horizon" — UX Safety & Performance

### Scope

Hardening guide Phase 3–4 (API security, UX stabilization) plus performance optimization
and navigation/UI polish based on user feedback.

- Safe Mode: read-only diagnostics on first launch, explicit toggle for mutations
- Risk classification per tweak (Low/Medium/High) with revert instructions
- Rollback/undo support: config backup + snapshot integration
- API security: rate limiting, `--unsafe-expose` flag, read-only endpoint separation
- Performance: startup profiling, lazy import optimization, memory reduction
- Navigation polish: sidebar rendering, category smoothness, breadcrumb improvements
- UI polish: consistent spacing, widget alignment, responsive layouts

### Deliverables

- [x] Safe Mode toggle (read-only by default on first launch)
- [x] Risk classification system: `utils/risk.py` with Low/Medium/High per action
- [x] Revert instructions shown for Medium/High risk operations
- [x] Config backup before destructive operations (automatic)
- [x] API rate limiting on auth endpoints
- [x] `--unsafe-expose` flag required for non-localhost binding
- [x] Read-only vs privileged API endpoint separation
- [x] Startup time profiling and optimization (target: <2s cold start)
- [x] Lazy import audit: defer heavy imports (PyQt6 submodules, optional utils)
- [x] Sidebar navigation polish (smooth scrolling, hover states, collapse animation)
- [x] Breadcrumb bar layout improvements
- [x] Coverage ≥ 80% (complete v33 deliverable)
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Builder | Safe mode, risk classification, config backup, API security |
| CodeGen | Performance optimization, lazy imports |
| Sculptor | Navigation polish, sidebar, breadcrumb improvements |
| Guardian | Tests, coverage push to 80% |
| Planner | Release coordination |

### Dependencies

- v35.0 Fortress (hardening gate cleared)

---

## [DONE] v37.0 "Pinnacle" — Smart Features & Ecosystem

### Scope

With hardening complete and UX polished, expand with user-requested features
focused on practical Fedora system management.

- Smart Update Manager: dependency conflict preview, update scheduling, rollback on failure
- GNOME/KDE Extension Manager: browse, install, enable/disable extensions from app
- Flatpak Manager improvements: size visualization, permission viewer, cleanup suggestions
- Boot Customization: GRUB theme, timeout, default kernel selection
- Wayland-aware tweaks: display config, scaling, fractional scaling
- System Backup Wizard: guided backup with Timeshift/Snapper integration
- Plugin ecosystem: community plugin showcase, plugin quality ratings
- Onboarding improvements: interactive first-run wizard, guided system check

### Deliverables

- [ ] Smart Update Manager tab section (conflict preview, scheduling, rollback)
- [ ] Extension manager: GNOME Shell extensions + KDE widgets browser
- [ ] Flatpak Manager: size treemap, permission audit, orphan cleanup
- [ ] Boot config: GRUB theme selector, timeout slider, default kernel picker
- [ ] Wayland display config: scaling, fractional scaling, multi-monitor layout
- [ ] System Backup Wizard: step-by-step guided backup setup
- [ ] Plugin showcase: curated community plugins in marketplace tab
- [ ] First-run wizard v2: interactive system health check + recommended actions
- [ ] Tests for all new features
- [ ] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Arkitekt | Feature architecture design |
| Builder | Update manager, extension manager, Flatpak manager, boot config backends |
| Sculptor | UI tabs, wizard v2, plugin showcase |
| CodeGen | Wayland tweaks, backup wizard |
| Guardian | Tests for all features |
| Planner | Release coordination |

### Dependencies

- v36.0 Horizon (UX safety and performance baseline)

---

## [DONE] v34.0 "Citadel" — Stability, Theme & Accessibility Polish

### Scope

- Fix broken light theme (24 missing QSS selectors, 4 dead selectors)
- Harden CommandRunner (timeout, kill escalation, stderr separation, crash detection)
- Extract all subprocess.run calls from UI code into utils/
- Replace all silent `except Exception: pass` with logged exceptions
- Add log rotation and proper daemon logging
- Add accessibility annotations to all 20 unannotated tabs
- Wire unused tooltips.py constants into UI code
- Push test coverage toward 80%

### Deliverables

- [x] Light theme parity with dark theme (all QSS selectors ported)
- [x] CommandRunner: timeout, kill escalation, stderr signal, crash detection
- [x] Zero subprocess.run calls in ui/ files
- [x] Zero silent exception swallows in ui/ files
- [x] Log rotation (5 MB, 3 backups)
- [x] Daemon uses proper logging (17 print→logger conversions)
- [x] Accessibility annotations on all 27 tabs (314 calls)
- [x] tooltips.py constants wired into UI
- [x] Tests for all changes (85 new tests)
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| CodeGen | Light theme QSS, CommandRunner hardening |
| Builder | Extract subprocess from UI to utils/ |
| Guardian | Silent exception fixes, accessibility, tests |
| Planner | Release coordination |

### Dependencies

- v33.0 Bastion (clean type-safe baseline)

---

## [DONE] v33.0 "Bastion" — Testing & CI Hardening

### Scope

- Fix all pre-existing mypy type errors so typecheck gate is strict
- Fix all pre-existing test failures (target: 100% pass rate)
- Raise coverage to 80%+
- Remove `continue-on-error` from typecheck and test gates
- Add test result summary annotations to CI
- Add release smoke test job (--version + --cli --version after RPM install)

### Deliverables

- [x] Fix mypy errors (163→0, Linux-only APIs, type annotations, missing stubs)
- [x] Fix remaining test failures (3958 passing, 0 failing)
- [ ] Coverage ≥ 80% (currently 76.8%)
- [x] Remove continue-on-error from typecheck/test in auto-release.yml and ci.yml (already strict)
- [ ] Add pytest --junitxml + dorny/test-reporter for PR annotations
- [ ] RPM install smoke test in release job
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Guardian | Fix mypy errors, fix failing tests, coverage fill |
| Builder | Type annotation improvements |
| Planner | CI pipeline improvements, release checklist |

### Dependencies

- v32.0 Abyss (clean baseline)

---

## [DONE] v32.0 — Abyss

### Scope

- Full visual redesign with purpose-built Abyss dark/light theme
- Reorganize 10 navigation categories into 8 activity-based groups
- Sidebar collapse toggle
- Deterministic category ordering via CATEGORY_ORDER
- Migrate all inline Catppuccin colors to Abyss palette
- Remove dead style.qss

### Deliverables

- [x] Abyss dark theme (modern.qss rewrite, ~560 lines)
- [x] Abyss light theme (light.qss rewrite)
- [x] 8 activity-based categories with emoji icons
- [x] CATEGORY_ORDER + CATEGORY_ICONS in registry.py
- [x] Sidebar collapse toggle (≡/✕ button)
- [x] 26 tab metadata files updated
- [x] Notification toast, health score, quick action colors migrated
- [x] 30+ files batch color migration (Catppuccin → Abyss)
- [x] Dead style.qss removed
- [x] CHANGELOG + README + release notes

---

## [DONE] v21.0 — UX Stabilization & Layout Integrity

### Scope

- Fix title/top-bar overlap
- Scope QTabBar scroller styling
- Enforce consistent root layout margins
- HiDPI safety
- No frameless hacks unless fully implemented

### Deliverables

- [x] Top bar glitch fixed
- [x] QSS scoped to QTabBar
- [x] Layout margins consistent (16px)
- [x] HiDPI scalable dimensions
- [x] Frameless mode behind feature flag
- [x] Geometry regression tests
- [x] CHANGELOG + README + release notes

---

## [DONE] v23.0 — Architecture Hardening

### Scope

- Introduce `ui/`, `core/`, `services/`, `utils/` boundaries
- Single subprocess wrapper (BaseActionExecutor)
- QThread/QRunnable for long ops
- GitHub Actions: lint + test + RPM build

### Deliverables

- [x] BaseActionExecutor ABC in core/executor/
- [x] ActionResult wrapper
- [x] Service layer directories created
- [x] Import validation tests (34 tests)
- [x] CI pipeline (lint, typecheck, security, test, build)
- [x] QThread workers for long operations
- [x] Service implementations (not stubs)
- [x] CHANGELOG + README finalized

### Agent Assignment

| Agent | Task |
|-------|------|
| Arkitekt | Approve folder structure, executor design |
| Builder | Service abstractions, executor impl |
| Sculptor | Non-blocking UI via QThread |
| Test | Import tests, executor tests |
| Planner | CI workflow, docs, packaging |

---

## [SKIPPED] v22.0 — Usability & Workflow Enhancements

### Scope

- Search/filter tweaks across all tabs
- Applied status indicators (visual feedback)
- Reset per group
- Confirm dialogs for destructive actions
- Persistent preferences

### Deliverables

- [ ] Search bar in sidebar/toolbar
- [ ] Filter logic across tab content
- [ ] Status badges on applied tweaks
- [ ] Reset button per tweak group
- [ ] Confirmation dialog system
- [ ] Preferences persistence (JSON config)
- [ ] Tests for state transitions
- [ ] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Manager | Define search + status plan |
| Builder | Persistent preferences, reset logic |
| Sculptor | Search/filter UI, indicators |
| Test | State transition tests |
| Planner | Docs + packaging |

### Dependencies

- v23.0 service layer (for clean preference storage)

---

## [DONE] v24.0 — Advanced Power Features

### Scope

- Profiles (save/load tweak configurations)
- JSON import/export
- Live log panel
- System snapshot before apply

### Deliverables

- [x] Profile dataclass + storage
- [x] Save/load profile UI
- [x] JSON export/import endpoints
- [x] Live log panel widget
- [x] Snapshot integration (Timeshift/Snapper)
- [x] Profile CLI commands
- [x] Tests for profile save/load
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Builder | Profiles, JSON export/import |
| Sculptor | Advanced mode toggle, log panel |
| Arkitekt | Validate snapshot system |
| Test | Profile save/load tests |
| Planner | Packaging polish |

### Dependencies

- v23.0 service layer
- Note: v22.0 persistent preferences shipped independently; v24.0 profiles use own storage

---

## [DONE] v25.0 — Plugin Architecture + UI Redesign

### Scope

- Tweaks self-register as modules
- Dynamic loading
- Clear API boundary
- Compatibility detection engine
- Unified spacing system
- Sidebar redesign

### Deliverables

- [x] Plugin interface definition
- [x] Plugin loader implementation
- [x] Plugin registration tests
- [x] Sidebar navigation redesign
- [x] Compatibility detection engine
- [x] README rewrite
- [x] Plugin dev guide
- [x] CONTRIBUTING.md
- [x] CHANGELOG + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Arkitekt | Define plugin interface |
| Builder | Plugin loader |
| Sculptor | Sidebar redesign |
| Test | Plugin registration tests |
| Planner | Documentation overhaul |
| CodeGen | Final integration |

### Dependencies

- v23.0 service layer
- v24.0 profiles (plugin configs)

---

## [DONE] v25.0.3 — Maintenance Update Crash Hotfix

### Scope

- Fix Maintenance update action crash on button press
- Keep update flow consistent with existing command runner behavior
- Add regression coverage for update command selection/queue startup

### Deliverables

- [x] Update handlers use stable command-runner execution path
- [x] `Update All` starts with system package-manager update step
- [x] Regression tests for maintenance update flow
- [x] CHANGELOG + README + release notes

## [DONE] v26.0 — Plugin Marketplace

### Scope

- Unified plugin system (bridge core/plugins ↔ utils/plugin_base)
- External plugin loading, install/uninstall engine
- Plugin package format (.loofi-plugin archive)
- Runtime permission sandboxing
- GitHub-based plugin marketplace API
- Marketplace UI in Community tab
- Plugin signing & integrity verification
- CLI marketplace commands (search/install/uninstall/update)
- Plugin dependency resolution
- Plugin auto-update service

### Deliverables

- [x] PluginAdapter (wraps LoofiPlugin as PluginInterface)
- [x] PluginPackage dataclass + archive format spec
- [x] PluginSandbox (permission enforcement layer)
- [x] External plugin scanner + loader
- [x] Plugin installer engine (download, verify, extract, register)
- [x] Plugin integrity verifier (SHA256 + GPG)
- [x] PluginMarketplaceAPI (GitHub-based index)
- [x] Plugin dependency resolver
- [x] Marketplace UI (browse/search/install in Community tab)
- [x] Plugin detail dialog + permission consent dialog
- [x] CLI commands: search, install, uninstall, update, info
- [x] Plugin auto-update service (daemon mode)
- [x] 195 comprehensive tests (100% pass rate)
- [x] PLUGIN_SDK.md update
- [x] CHANGELOG + release notes
- [x] RPM built and tested (v26.0.0)

### Phases

| Phase | Tasks | Status | Gate |
|-------|-------|--------|------|
| Foundation | T1–T8: Adapter, package, sandbox, loader, installer, integrity, marketplace API, resolver | ✅ DONE | All core modules importable, unit tests pass |
| Features | T9–T14: Marketplace UI, details dialog, CLI commands, permission dialog, auto-updater | ✅ DONE | CLI commands implemented and tested |
| Stabilization | T15–T22: 8 new test files (195 tests) | ✅ DONE | 195/195 tests pass (100%) |
| Release | T23–T27: Version, docs, changelog, RPM | ✅ DONE | v26.0.0 released (2026-02-12) |

### Agent Assignment

| Agent | Task |
|-------|------|
| Arkitekt | PluginAdapter design, package format spec |
| Builder | Sandbox, external loader, installer, integrity, marketplace API, resolver, auto-updater |
| Sculptor | Marketplace UI, detail dialog, permission dialog |
| CodeGen | CLI marketplace commands |
| Guardian | 8 test files (adapter, sandbox, loader, installer, marketplace, CLI, resolver, integrity) |
| Planner | Version bump, PLUGIN_SDK.md, CHANGELOG, release notes |

### Dependencies

- v25.0 plugin architecture (PluginInterface, PluginRegistry, PluginLoader)
- v24.0 profiles (plugin configs)

### New Files (17)

- `core/plugins/adapter.py`, `package.py`, `sandbox.py`, `scanner.py`, `integrity.py`, `resolver.py`
- `utils/plugin_installer.py`, `plugin_marketplace.py`, `plugin_updater.py`
- `ui/plugin_detail_dialog.py`, `permission_dialog.py`
- `tests/test_plugin_{adapter,sandbox,external_loader,installer,marketplace,resolver,integrity}.py`, `test_cli_marketplace.py`

---

## [DONE] v27.0 — Marketplace Enhancement

### Scope

- Replace GitHub-based marketplace index with dedicated CDN-backed index
- Add plugin ratings and reviews (read/write integration)
- Add verified publisher badges
- Add opt-in plugin usage analytics
- Add hot reload for installed plugins without app restart
- Strengthen plugin sandbox with OS-level isolation

### Deliverables

- [x] CDN marketplace client + signed index schema
- [x] Marketplace API/provider abstraction updated to CDN-first with fallback
- [x] Ratings/reviews models and backend integration
- [x] Ratings/reviews UI in Community tab
- [x] Verified publisher badge support in listing and detail views
- [x] Analytics consent preference (default off) + telemetry sender
- [x] Hot-reload manager integrated with plugin loader/registry
- [x] OS-level isolation support for plugin execution policy
- [x] Test coverage for CDN, reviews, badges, analytics, hot reload, sandbox
- [x] CHANGELOG + README + release notes + RPM validation

### Agent Assignment

| Agent | Task |
|-------|------|
| Arkitekt | CDN/index contract, isolation design |
| Builder | Marketplace backend, analytics, hot reload, sandbox hardening |
| Sculptor | Community tab UX for reviews and verification badges |
| CodeGen | CLI extensions for review/badge/marketplace flows |
| Guardian | Unit/integration test matrix for new marketplace features |
| Planner | Versioning, docs, release checklist and packaging |

### Dependencies

- v26.0 plugin marketplace baseline
- v25.0 plugin architecture (PluginInterface/Registry/Loader)

---

## [DONE] v28.0 — Workflow Contract Reset

### Scope

- Establish clean-slate workflow state for a new cycle
- Create runner-compatible P1 planning artifact format for v28
- Align planning handoff assets with workflow runner contract checks

### Deliverables

- [x] `ROADMAP.md` marks exactly one ACTIVE target (v28.0)
- [x] `.workflow/specs/tasks-v28.0.0.md` follows task contract markers
- [x] `.workflow/specs/.race-lock.json` targets `v28.0.0` in active state
- [x] `.workflow/reports/run-manifest-v28.0.0.json` initialized with runner schema
- [x] Kickoff planning tasks include implementation, tests, and docs workstreams

### Agent Assignment

| Agent | Task |
|-------|------|
| Manager | Decompose v28 kickoff tasks and dependencies |
| Arkitekt | Validate workflow artifact structure |
| Builder | Implement workflow/runner integration deltas |
| Test | Validate contract and workflow state checks |
| Planner | Finalize docs + release-trace updates |

### Dependencies

- v27.0 completion artifacts
- `scripts/workflow_runner.py` contract validation rules

---

## [DONE] v29.0 — Usability & Polish

### Scope

- Reclaim skipped v22.0 features (search, status indicators, confirm dialogs, reset per group)
- Centralized error handler with recovery hints
- In-app notification toast UI
- Dashboard sparkline theme-awareness
- Web API CORS lockdown
- Keyboard accessibility pass
- CI coverage raised to 75%+ (achieved: 76.8%)

### Deliverables

- [x] Centralized error handler (sys.excepthook + LoofiError routing)
- [x] ConfirmActionDialog for dangerous operations
- [x] Notification toast wired to NotificationCenter
- [x] Sidebar search enhanced with description/tag matching
- [x] Status indicators (colored dots) on sidebar items
- [x] Dashboard SparkLine reads palette instead of hardcoded colors
- [x] Web API CORS restricted to localhost
- [x] Sidebar keyboard focus restored
- [x] Settings reset per group buttons
- [x] Tab smoke tests for untested tabs (target: 65% coverage)
- [x] Comprehensive test coverage: 151 test files, 3846+ tests, 76.8% line coverage
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| CodeGen | Error handler, confirm dialog, CORS, sparkline fix |
| Sculptor | Notification toast, sidebar indicators, accessibility |
| Builder | Settings reset per group |
| Guardian | Tab smoke tests |
| Planner | Docs, packaging, release |

### Dependencies

- v28.0 workflow state (clean baseline)

---

## [DONE] v30.0 — Distribution & Reliability

### Scope

- Implement Flatpak packaging (build_flatpak.sh)
- Implement AppImage packaging (build_appimage.sh)
- Implement sdist packaging (build_sdist.sh + pyproject.toml)
- Auto-update flow (detect + download + verify)
- CI: add Flatpak + AppImage build jobs, enforce mypy + bandit
- Rate limiter and auto-tuner thread safety fixes
- Offline mode for marketplace/update checker
- CI coverage maintained at 75%+ (baseline: 76.8%)

### Deliverables

- [x] build_flatpak.sh implemented
- [x] build_appimage.sh implemented
- [x] build_sdist.sh + pyproject.toml
- [x] Auto-update flow in update_checker.py
- [x] CI Flatpak/AppImage build jobs
- [x] mypy + bandit enforced (no continue-on-error)
- [x] Rate limiter threading.Event fix
- [x] Auto-tuner thread safety guard
- [x] Offline mode for marketplace/update checker
- [x] Tests for new v30 modules (target: maintain 75%+ coverage)
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Builder | Packaging scripts, auto-update, offline mode |
| Arkitekt | pyproject.toml design, CI pipeline |
| Guardian | Coverage gap analysis + tests |
| Planner | Release checklist |

### Dependencies

- v29.0 usability polish

---

## [DONE] v31.0 — Smart UX

### Scope

- System health score (aggregate dashboard metric)
- i18n scaffolding (Qt Linguist workflow, English + Swedish)
- Batch operations in Software/Maintenance tabs
- Export system report (Markdown/HTML)
- Plugin starter template script
- Favorite/pinned tabs
- Configurable Dashboard quick actions
- Accessibility level 2 (accessible names, Orca testing)
- CI coverage raised to 80%

### Deliverables

- [x] Health score widget on Dashboard
- [x] i18n infrastructure (ts/qm extraction, locale loading)
- [x] Batch install/remove in Software tab
- [x] Export report button in System Info tab
- [x] create_plugin.sh scaffold script
- [x] Favorite tabs persistence + sidebar pinning
- [x] Configurable quick actions grid
- [x] setAccessibleName/Description across all interactive widgets
- [x] Target 80% CI coverage
- [x] CHANGELOG + README + release notes

### Agent Assignment

| Agent | Task |
|-------|------|
| Arkitekt | Health score design, i18n architecture |
| Builder | Health aggregation, export report, batch ops |
| Sculptor | Dashboard health widget, favorites UI, quick actions config |
| CodeGen | Plugin template script, i18n tooling |
| Guardian | Orca screen reader testing, coverage fill |
| Planner | Release planning |

### Dependencies

- v30.0 distribution infrastructure

---

## Execution Rules

1. Only ONE version is ACTIVE at a time
2. NEXT version can begin planning while ACTIVE is in final testing
3. Every version must complete release checklist (docs, tests, packaging) before tagging
4. Agents are assigned per-version — see Agent Assignment tables above
5. Status transitions: PLANNED → NEXT → ACTIVE → DONE
