# Release Notes -- v41.0.0 "Coverage"

**Release Date:** 2026-02-15
**Codename:** Coverage
**Theme:** Test coverage push from 74% to 80%+ and CI pipeline hardening

## Summary

Pure test and CI release with zero production code changes. Adds 23 new or
expanded test files covering utils modules, UI tabs, CLI, and core services.
CI pipeline gains JUnit annotations, an RPM smoke-test gate, and an 80%
coverage threshold enforced across all workflows.

## Highlights

- Coverage raised from 74% to 80%+ (30 653 stmts, 6 125 missed)
- 23 test files created or expanded (~1 900 new tests)
- `dorny/test-reporter` renders JUnit XML as GitHub check annotations
- RPM post-install smoke test gates every release build
- Coverage threshold bumped from 74 to 80 in ci.yml, auto-release.yml, coverage-gate.yml
- Coverage badge added to README.md

## Changes

### Changed

- `COVERAGE_THRESHOLD` raised from 74 to 80 in ci.yml, auto-release.yml, coverage-gate.yml
- `permissions` in ci.yml and auto-release.yml now include `checks: write` for test-reporter

### Added

- 23 test files: test_plugin_cdn_client, test_battery_shim, test_file_drop, test_context_rag, test_agent_planner_dedicated, test_vm_manager_dedicated, test_ansible_export (expanded), test_network_monitor_extended, test_agent_runner_extended, test_community_tab, test_network_tab, test_monitor_tab, test_diagnostics_tab, test_maintenance_tab, test_operations_extended, test_services_system_extended, test_safety_extended, test_main_window, test_backup_tab, test_hardware_tab, test_development_tab, test_cli_main_extended, test_pulse_extended
- `dorny/test-reporter@v1` step in ci.yml and auto-release.yml test jobs
- `rpm_smoke_test` job in auto-release.yml (installs RPM, runs --version and --cli --help)
- Coverage badge (shields.io) in README.md

### Fixed

- `test_hardware_tab.py` sys.modules pollution (added setUpModule/tearDownModule cleanup)

## Stats

- **Tests:** 5 797 passed, 61 skipped, 36 failed (all pre-existing)
- **Lint:** 0 errors
- **Coverage:** 80.02%

## Upgrade Notes

No user-facing changes. This is a test-only release.
