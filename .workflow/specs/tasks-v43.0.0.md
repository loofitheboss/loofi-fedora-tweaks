# Tasks — v43.0.0 "Stabilization-Only"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json` | Dep: - | Agent: project-coordinator | Description: Add v43.0.0 as ACTIVE in roadmap with strict stabilization deliverables and set race lock target to v43.0.0.
  Acceptance: Exactly one ACTIVE version exists and race lock target_version is v43.0.0.
  Docs: ROADMAP
  Tests: none

## Phase: Build

- [x] ID: TASK-002 | Files: `scripts/check_stabilization_rules.py` | Dep: - | Agent: backend-builder | Description: Implement AST-based stabilization checker for timeout enforcement, UI subprocess ban, executable hardcoded dnf calls, and broad-exception allowlist.
  Acceptance: Script exits non-zero on violations and prints file:line entries per violation.
  Docs: none
  Tests: `tests/test_check_stabilization_rules.py`

- [x] ID: TASK-003 | Files: `.github/workflows/ci.yml, .github/workflows/auto-release.yml, .github/workflows/coverage-gate.yml` | Dep: TASK-002 | Agent: backend-builder | Description: Wire stabilization checker into CI/release workflows and raise all coverage thresholds from 79 to 80.
  Acceptance: Checker runs in all listed workflows and all COVERAGE_THRESHOLD values equal 80.
  Docs: none
  Tests: none

- [x] ID: TASK-004 | Files: `loofi-fedora-tweaks/services/hardware/disk.py` | Dep: - | Agent: backend-builder | Description: Add missing timeout to DiskManager.get_all_mount_points subprocess call.
  Acceptance: No untimed subprocess.run/check_output/call calls remain in services/hardware/disk.py.
  Docs: none
  Tests: `tests/test_services_hardware_manager.py`

- [x] ID: TASK-005 | Files: `loofi-fedora-tweaks/ui/wizard.py, loofi-fedora-tweaks/utils/wizard_health.py` | Dep: - | Agent: frontend-integration-builder | Description: Extract wizard health-check subprocess logic into utils and consume via UI.
  Acceptance: ui/wizard.py has zero subprocess calls and health checks preserve behavior for disk/package/firewall/backup/SELinux.
  Docs: none
  Tests: `tests/test_wizard_health.py`

- [x] ID: TASK-006 | Files: `loofi-fedora-tweaks/services/package/service.py` | Dep: - | Agent: backend-builder | Description: Refactor package service execution paths to avoid literal executable dnf arrays using package-manager abstraction and PrivilegedCommand for privileged actions.
  Acceptance: install/remove/update/search/info/list codepaths avoid executable hardcoded dnf usage and tests pass.
  Docs: none
  Tests: `tests/test_package_service.py`

- [x] ID: TASK-007 | Files: `loofi-fedora-tweaks/utils/update_manager.py, loofi-fedora-tweaks/utils/scheduler.py` | Dep: - | Agent: backend-builder | Description: Refactor update and history command paths to package-manager-aware helpers for dnf/rpm-ostree.
  Acceptance: No executable hardcoded dnf subprocess calls remain in the two modules; behavior remains intact for traditional and atomic systems.
  Docs: none
  Tests: `tests/test_update_manager.py, tests/test_scheduler.py, tests/test_scheduler_deep.py, tests/test_maintenance_updates_regression.py`

- [x] ID: TASK-008 | Files: `loofi-fedora-tweaks/utils/health_score.py, loofi-fedora-tweaks/utils/agent_runner.py, loofi-fedora-tweaks/utils/ai.py` | Dep: - | Agent: backend-builder | Description: Remove executable hardcoded dnf subprocess usage from health/update/AI checks using package-manager abstraction.
  Acceptance: Modules support both dnf and rpm-ostree paths without direct executable dnf subprocess calls.
  Docs: none
  Tests: `tests/test_health_score.py, tests/test_agent_runner_extended.py, tests/test_ai.py, tests/test_ai_polish.py`

- [x] ID: TASK-009 | Files: `loofi-fedora-tweaks/utils/ansible_export.py, loofi-fedora-tweaks/utils/config_manager.py, loofi-fedora-tweaks/utils/drift.py, loofi-fedora-tweaks/utils/kickstart.py` | Dep: - | Agent: backend-builder | Description: Refactor repoquery/repolist package inventory commands to package-manager-aware execution with atomic-safe fallback.
  Acceptance: Target files contain no executable hardcoded dnf subprocess calls and preserve output schemas.
  Docs: none
  Tests: `tests/test_ansible_export.py, tests/test_config_manager.py, tests/test_drift_extended.py, tests/test_kickstart_deep.py`

- [x] ID: TASK-010 | Files: `loofi-fedora-tweaks/main.py, loofi-fedora-tweaks/cli/main.py, loofi-fedora-tweaks/utils/error_handler.py` | Dep: - | Agent: code-implementer | Description: Narrow broad exception handlers in app/CLI entry and error-handler paths while preserving explicit boundary catches.
  Acceptance: Generic catches are replaced by specific exception classes except justified boundary wrappers.
  Docs: none
  Tests: `tests/test_main_entry.py, tests/test_cli_main_extended.py, tests/test_cli_extended_handlers.py, tests/test_cli_uncovered_handlers.py`

- [x] ID: TASK-011 | Files: `loofi-fedora-tweaks/utils/agent_runner.py, loofi-fedora-tweaks/utils/agent_scheduler.py, loofi-fedora-tweaks/utils/api_server.py, loofi-fedora-tweaks/utils/daemon.py` | Dep: - | Agent: code-implementer | Description: Narrow broad exceptions in scheduler/daemon/agent runtime flows while preserving resilient error reporting.
  Acceptance: Non-boundary generic catches are removed and runtime logging behavior remains stable.
  Docs: none
  Tests: `tests/test_agent_runner_extended.py`

- [x] ID: TASK-012 | Files: `loofi-fedora-tweaks/ui/agents_tab.py, loofi-fedora-tweaks/ui/community_tab.py, loofi-fedora-tweaks/ui/mesh_tab.py, loofi-fedora-tweaks/ui/lazy_widget.py, loofi-fedora-tweaks/ui/development_tab.py, loofi-fedora-tweaks/ui/whats_new_dialog.py, loofi-fedora-tweaks/ui/system_info_tab.py, loofi-fedora-tweaks/ui/confirm_dialog.py, loofi-fedora-tweaks/ui/virtualization_tab.py` | Dep: - | Agent: frontend-integration-builder | Description: Narrow broad exceptions in UI codepaths with known failure modes while preserving non-crashing fallbacks.
  Acceptance: Generic catches are reduced and user-safe fallback behavior remains.
  Docs: none
  Tests: `tests/test_development_tab.py, tests/test_community_tab.py, tests/test_confirm_dialog.py, tests/test_virtualization.py`

- [x] ID: TASK-013 | Files: `loofi-fedora-tweaks/core/plugins/adapter.py, loofi-fedora-tweaks/core/plugins/resolver.py, loofi-fedora-tweaks/core/workers/base_worker.py, loofi-fedora-tweaks/utils/event_bus.py` | Dep: - | Agent: backend-builder | Description: Formalize exception-boundary allowlist in plugin/callback/worker wrappers and narrow non-boundary catches.
  Acceptance: Only justified boundary catches remain generic and checker allowlist matches code.
  Docs: none
  Tests: `tests/test_plugins.py, tests/test_plugins_v2.py, tests/test_base_worker.py, tests/test_event_bus.py`

## Phase: Test

- [x] ID: TASK-014 | Files: `tests/test_v43_stabilization.py, tests/test_check_stabilization_rules.py, tests/test_package_service.py, tests/test_update_manager.py, tests/test_scheduler.py, tests/test_health_score.py, tests/test_agent_runner_extended.py, tests/test_ansible_export.py, tests/test_config_manager.py, tests/test_drift_extended.py, tests/test_kickstart_deep.py, tests/test_ai.py, tests/test_ai_polish.py` | Dep: TASK-004,TASK-005,TASK-006,TASK-007,TASK-008,TASK-009,TASK-010,TASK-011,TASK-012,TASK-013 | Agent: test-writer | Description: Update existing tests for refactors and add v43 stabilization compliance tests and allowlist behavior checks.
  Acceptance: Updated/new tests pass and fail correctly when policy invariants regress.
  Docs: none
  Tests: self

## Phase: Release

- [x] ID: TASK-015 | Files: `CHANGELOG.md, README.md, docs/releases/RELEASE-NOTES-v43.0.0.md, loofi-fedora-tweaks/version.py, pyproject.toml, loofi-fedora-tweaks.spec, ROADMAP.md, .workflow/reports/test-results-v43.0.json, .workflow/reports/run-manifest-v43.0.json` | Dep: TASK-003,TASK-014 | Agent: release-planner | Description: Complete v43 version/docs/release artifacts and transition roadmap ACTIVE to DONE after all validation passes.
  Acceptance: Version files aligned to 43.0.0, release notes scaffolded, roadmap and workflow reports updated.
  Docs: CHANGELOG, README, RELEASE-NOTES, ROADMAP
  Tests: `tests/test_version.py`
  Note: standard `build_rpm.sh` command needs host `python3-devel`; package validation completed with `rpmbuild --nodeps` fallback in this environment.
