# Tasks for v23.0 — Architecture Hardening

> Machine-parseable task list. Agent-to-layer assignments with dependencies.

## Task List

| # | Task | Agent | Layer | Size | Status | Depends | Files |
|---|------|-------|-------|------|--------|---------|-------|
| 1 | Create BaseActionExecutor ABC | backend-builder | core | S | ✅ DONE | - | core/executor/base.py |
| 2 | Create ActionResult dataclass | backend-builder | core | S | ✅ DONE | 1 | core/executor/result.py |
| 3 | Create service layer structure | architecture-advisor | services | S | ✅ DONE | - | services/__init__.py, services/*/base.py |
| 4 | Implement import validation tests | test-writer | tests | M | ✅ DONE | 3 | tests/test_architecture_imports.py |
| 5 | Create GitHub Actions CI workflow | release-planner | .github | M | ✅ DONE | - | .github/workflows/ci.yml |
| 6 | Implement BaseWorker QThread wrapper | backend-builder | core | M | ✅ DONE | 1,2 | core/workers/base_worker.py |
| 7 | Create CommandRunner→BaseWorker adapter | backend-builder | core | M | ✅ DONE | 6 | core/workers/command_worker.py |
| 8 | Test BaseWorker integration | test-writer | tests | M | ✅ DONE | 6,7 | tests/test_base_worker.py |
| 9 | Implement PackageService | backend-builder | services | L | ✅ DONE | 6,7 | services/package/service.py |
| 10 | Implement SystemService | backend-builder | services | M | ✅ DONE | 6,7 | services/system/service.py |
| 11 | Test service implementations | test-writer | tests | L | ✅ DONE | 9,10 | tests/test_services.py |
| 12 | Migrate one tab to services | frontend-integration-builder | ui | L | ⏸️ PENDING | 9,10 | ui/maintenance_tab.py |
| 13 | Update CHANGELOG.md | release-planner | docs | S | ✅ DONE | 6-12 | CHANGELOG.md |
| 14 | Update README.md | release-planner | docs | S | ✅ DONE | 6-12 | README.md |
| 15 | Create release notes | release-planner | docs | S | ✅ DONE | 13,14 | RELEASE-NOTES-v23.0.0.md |

## Size Legend
- **S** (Small): 1-50 lines, single file
- **M** (Medium): 50-200 lines, 1-3 files
- **L** (Large): 200+ lines, 3+ files

## Status Legend
- **✅ DONE**: Completed and verified
- **🔄 ACTIVE**: Currently in progress
- **⏸️ PENDING**: Blocked by dependencies

---

## Task Details

### Task 6: Implement BaseWorker QThread wrapper
**Acceptance Criteria:**
- [ ] BaseWorker extends QThread or QRunnable
- [ ] Signals: started, progress, finished, error
- [ ] Cancel mechanism (thread-safe)
- [ ] Error propagation via ActionResult
- [ ] Used by CommandWorker

**Agent:** backend-builder (model: sonnet)

---

### Task 7: Create CommandRunner→BaseWorker adapter
**Acceptance Criteria:**
- [ ] CommandWorker extends BaseWorker
- [ ] Wraps existing CommandRunner (preserve compatibility)
- [ ] Maps CommandRunner signals to BaseWorker protocol
- [ ] Returns ActionResult on completion
- [ ] BaseTab can use either CommandRunner or CommandWorker
- [ ] No breaking changes to existing tabs

**Agent:** backend-builder (model: sonnet)
**Strategy:** Adapter pattern — gradual migration, preserve CommandRunner for existing code

---

### Task 8: Test BaseWorker integration
**Acceptance Criteria:**
- [ ] Test signal emission (started, finished, error)
- [ ] Test cancel mechanism
- [ ] Test thread lifecycle
- [ ] Mock subprocess calls
- [ ] 80%+ coverage on workers

**Agent:** test-writer (model: sonnet)

---

### Task 9: Implement PackageService
**Acceptance Criteria:**
- [ ] Abstract base in services/package/base.py (interface only)
- [ ] DnfPackageService implementation
- [ ] RpmOstreePackageService implementation
- [ ] Factory: auto-detection via SystemManager.get_package_manager()
- [ ] Delegates to existing utils for actual work
- [ ] Uses CommandWorker for async ops
- [ ] Returns ActionResult
- [ ] No breaking changes to existing package_manager.py

**Agent:** backend-builder (model: sonnet)
**Strategy:** Abstraction layer over existing utils — composition, not replacement

---

### Task 10: Implement SystemService
**Acceptance Criteria:**
- [ ] Abstract base in services/system/base.py (interface only)
- [ ] SystemService implementation in services/system/service.py
- [ ] Methods: reboot, shutdown, update_grub, suspend
- [ ] Delegates to existing SystemManager where appropriate
- [ ] Uses CommandWorker for async ops
- [ ] Returns ActionResult
- [ ] No rename/refactor of existing SystemManager (preserve imports)

**Agent:** backend-builder (model: sonnet)
**Strategy:** Abstraction layer — SystemService wraps/uses SystemManager, no breaking changes

---

### Task 11: Test service implementations
**Acceptance Criteria:**
- [ ] Test PackageService factory pattern
- [ ] Test DnfPackageService operations
- [ ] Test RpmOstreePackageService operations
- [ ] Test SystemService methods
- [ ] Mock all subprocess calls
- [ ] 80%+ coverage

**Agent:** test-writer (model: sonnet)

---

### Task 12: Migrate one tab to services
**Acceptance Criteria:**
- [ ] MaintenanceTab uses PackageService
- [ ] Replace direct subprocess calls
- [ ] Use CommandWorker for async OR preserve CommandRunner
- [ ] Update UI on worker signals
- [ ] No regressions in functionality
- [ ] BaseTab API compatibility maintained

**Agent:** frontend-integration-builder (model: sonnet)
**Strategy:** Demonstrate service layer adoption without breaking existing patterns

---

### Task 13-15: Documentation
**Acceptance Criteria:**
- [ ] CHANGELOG.md lists all v23.0 changes
- [ ] README.md reflects new architecture
- [ ] Release notes highlight service layer + CI
- [ ] Version string updated in version.py

**Agent:** release-planner (model: haiku)

---

## Dependency Graph

```
1 (BaseActionExecutor) ──────┐
                              ├──> 6 (BaseWorker) ───┐
2 (ActionResult) ─────────────┘                      │
                                                     ├──> 7 (CommandWorker) ──┐
3 (Service structure) ───────────────────────────────┘                        │
                                                                               │
                                                                               ├──> 9 (PackageService) ──┐
                                                                               │                          │
                                                                               └──> 10 (SystemService) ───┤
                                                                                                          │
4 (Import tests) [independent]                                                                            │
5 (CI workflow) [independent]                                                                             │
                                                                                                          │
8 (Worker tests) <── 6,7                                                                                  │
11 (Service tests) <── 9,10                                                                               │
12 (Tab migration) <─────────────────────────────────────────────────────────────────────────────────────┘
                                                                                                          │
13 (CHANGELOG) <──────────────────────────────────────────────────────────────────────────────────────────┤
14 (README) <──────────────────────────────────────────────────────────────────────────────────────────────┤
15 (Release notes) <── 13,14 ─────────────────────────────────────────────────────────────────────────────┘
```

---

## Progress Summary

**Complete:** 14/15 tasks (93%)
**Active:** 0/15 tasks (0%)
**Pending:** 1/15 tasks (7%)

**Next action:** Complete task 12 (migrate one tab to services)

---

## Notes

- Tasks 1-5 completed in early development
- Tasks 6-7 are critical path for remaining work
- Service layer (9-10) blocks tab migration (12)
- Documentation (13-15) must wait for all features
- Target completion: Before v22.0 planning
