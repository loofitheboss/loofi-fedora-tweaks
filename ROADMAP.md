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
| v25.0 | Plugin Architecture | NEXT | Plugin system, UI redesign, API |

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
| architecture-advisor | Approve folder structure, executor design |
| backend-builder | Service abstractions, executor impl |
| frontend-integration-builder | Non-blocking UI via QThread |
| test-writer | Import tests, executor tests |
| release-planner | CI workflow, docs, packaging |

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
| project-coordinator | Define search + status plan |
| backend-builder | Persistent preferences, reset logic |
| frontend-integration-builder | Search/filter UI, indicators |
| test-writer | State transition tests |
| release-planner | Docs + packaging |

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
| backend-builder | Profiles, JSON export/import |
| frontend-integration-builder | Advanced mode toggle, log panel |
| architecture-advisor | Validate snapshot system |
| test-writer | Profile save/load tests |
| release-planner | Packaging polish |

### Dependencies

- v23.0 service layer
- Note: v22.0 persistent preferences shipped independently; v24.0 profiles use own storage

---

## [NEXT] v25.0 — Plugin Architecture + UI Redesign

### Scope
- Tweaks self-register as modules
- Dynamic loading
- Clear API boundary
- Compatibility detection engine
- Unified spacing system
- Sidebar redesign

### Deliverables
- [ ] Plugin interface definition
- [ ] Plugin loader implementation
- [ ] Plugin registration tests
- [ ] Sidebar navigation redesign
- [ ] Compatibility detection engine
- [ ] README rewrite
- [ ] Plugin dev guide
- [ ] CONTRIBUTING.md
- [ ] CHANGELOG + release notes

### Agent Assignment
| Agent | Task |
|-------|------|
| architecture-advisor | Define plugin interface |
| backend-builder | Plugin loader |
| frontend-integration-builder | Sidebar redesign |
| test-writer | Plugin registration tests |
| release-planner | Documentation overhaul |
| code-implementer | Final integration |

### Dependencies

- v23.0 service layer
- v24.0 profiles (plugin configs)

---

## Execution Rules

1. Only ONE version is ACTIVE at a time
2. NEXT version can begin planning while ACTIVE is in final testing
3. Every version must complete the [Release Checklist](.claude/workflow/PIPELINE.md#release-checklist) before tagging
4. Agents are assigned per-version — see Agent Assignment tables above
5. Status transitions: PLANNED → NEXT → ACTIVE → DONE
