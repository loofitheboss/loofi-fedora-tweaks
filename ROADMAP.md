# Loofi Fedora Tweaks — Roadmap

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

## Execution Rules

1. Only ONE version is ACTIVE at a time
2. NEXT version can begin planning while ACTIVE is in final testing
3. Every version must complete release checklist (docs, tests, packaging) before tagging
4. Agents are assigned per-version — see Agent Assignment tables above
5. Status transitions: PLANNED → NEXT → ACTIVE → DONE
