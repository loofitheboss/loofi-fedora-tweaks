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
| v26.0 | Plugin Marketplace | ACTIVE | External plugins, marketplace, sandboxing |

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

## [ACTIVE] v26.0 — Plugin Marketplace

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
- [ ] Marketplace UI (browse/search/install in Community tab)
- [ ] Plugin detail dialog + permission consent dialog
- [ ] CLI commands: search, install, uninstall, update, info
- [ ] Plugin auto-update service (daemon mode)
- [x] 8 new test files (195 tests, 176 passing @ 86%)
- [ ] PLUGIN_SDK.md update
- [ ] CHANGELOG + release notes

### Phases
| Phase | Tasks | Status | Gate |
|-------|-------|--------|------|
| Foundation | T1–T8: Adapter, package, sandbox, loader, installer, integrity, marketplace API, resolver | ✅ DONE | All core modules importable, unit tests pass |
| Features | T9–T14: Marketplace UI, details dialog, CLI commands, permission dialog, auto-updater | ⚠️ PARTIAL | CLI commands pending (14 tests) |
| Stabilization | T15–T22: 8 new test files (195 tests) | ✅ DONE | 176/205 tests pass (86%), CLI stub needed |
| Release | T23–T27: Version, docs, changelog, RPM | NEXT | CLI implementation, then CI green, RPM builds |

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

## Execution Rules

1. Only ONE version is ACTIVE at a time
2. NEXT version can begin planning while ACTIVE is in final testing
3. Every version must complete release checklist (docs, tests, packaging) before tagging
4. Agents are assigned per-version — see Agent Assignment tables above
5. Status transitions: PLANNED → NEXT → ACTIVE → DONE
