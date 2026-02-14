# v35.0.0 "Fortress" — Task Spec

## Tasks

### Phase 1: Subprocess Timeout Enforcement (Critical — 263 calls, 56 files)

- [ ] T1: Add timeouts to high-count files (10+ calls each)
  - ID: T1
  - Files: `utils/firewall_manager.py` (19), `utils/ai.py` (14), `utils/automation_profiles.py` (13), `utils/package_explorer.py` (12), `utils/ports.py` (10)
  - Dep: none
  - Agent: Builder
  - Description: Add `timeout=` to all subprocess calls in the 5 highest-count files (68 calls total). Use category-appropriate timeouts per arch spec.
  - Acceptance: `grep -E 'subprocess\.(run|check_output|Popen|call)\(' <file> | grep -v timeout` returns 0 for each file
  - Docs: CHANGELOG
  - Tests: Existing tests still pass; new timeout tests for critical paths

- [ ] T2: Add timeouts to medium-count files (6-9 calls each)
  - ID: T2
  - Files: `utils/journal.py` (9), `utils/vm_manager.py` (8), `utils/agent_runner.py` (8), `utils/focus_mode.py` (7), `utils/package_manager.py` (7), `utils/pulse.py` (7), `utils/scheduler.py` (7), `utils/usbguard.py` (7), `utils/clipboard_sync.py` (6), `utils/kwin_tiling.py` (6), `utils/profiles.py` (6), `utils/secureboot.py` (6), `utils/containers.py` (6), `utils/network_utils.py` (6)
  - Dep: none
  - Agent: Builder
  - Description: Add `timeout=` to all subprocess calls in 14 medium-count files (96 calls total)
  - Acceptance: Zero untimed subprocess calls in listed files
  - Docs: CHANGELOG
  - Tests: Existing tests still pass

- [ ] T3: Add timeouts to standard-count files (3-5 calls each)
  - ID: T3
  - Files: `utils/ansible_export.py` (5), `utils/devtools.py` (5), `utils/kickstart.py` (5), `utils/service_explorer.py` (5), `utils/state_teleport.py` (5), `utils/storage.py` (5), `utils/tiling.py` (5), `utils/vscode.py` (5), `utils/disposable_vm.py` (4), `utils/drift.py` (4), `utils/kernel.py` (4), `utils/voice.py` (4), `utils/zram.py` (4), `utils/snapshot_manager.py` (4), `utils/boot_analyzer.py` (3), `utils/presets.py` (3), `utils/sandbox.py` (3)
  - Dep: none
  - Agent: Builder
  - Description: Add `timeout=` to all subprocess calls in 17 standard-count files (74 calls total)
  - Acceptance: Zero untimed subprocess calls in listed files
  - Docs: CHANGELOG
  - Tests: Existing tests still pass

- [ ] T4: Add timeouts to low-count files (1-2 calls each)
  - ID: T4
  - Files: `utils/mesh_discovery.py` (2), `utils/ai_models.py` (2), `utils/config_manager.py` (2), `utils/safety.py` (2), `utils/smart_logs.py` (2), `utils/gaming_utils.py` (2), `utils/update_checker.py` (1), `utils/agent_planner.py` (1), `utils/fingerprint.py` (1), `utils/health_timeline.py` (1), `utils/history.py` (1), `utils/network_monitor.py` (1), `utils/notifications.py` (1), `utils/vfio.py` (1), `utils/virtualization.py` (1), `utils/daemon.py` (1), `utils/health_score.py` (1), `utils/software_utils.py` (1), `utils/desktop_utils.py` (1)
  - Dep: none
  - Agent: Builder
  - Description: Add `timeout=` to all subprocess calls in 19 low-count files (25 calls total)
  - Acceptance: Zero untimed subprocess calls in listed files
  - Docs: CHANGELOG
  - Tests: Existing tests still pass

- [ ] T5: Add timeout to CLI run_operation()
  - ID: T5
  - Files: `cli/main.py`
  - Dep: none
  - Agent: Builder
  - Description: Add `timeout=300` default to `run_operation()`, add `--timeout` CLI flag
  - Acceptance: `run_operation()` has timeout parameter, CLI flag works
  - Docs: CHANGELOG
  - Tests: `tests/test_cli.py`

- [ ] T6: Add CommandTimeoutError to error hierarchy
  - ID: T6
  - Files: `utils/errors.py`
  - Dep: none
  - Agent: Builder
  - Description: Add `CommandTimeoutError(LoofiError)` with code="COMMAND_TIMEOUT", hint, recoverable=True
  - Acceptance: Error class exists and can be raised/caught
  - Docs: none
  - Tests: `tests/test_errors.py`

### Phase 2: Audit Logging

- [ ] T7: Create audit logger module
  - ID: T7
  - Files: `utils/audit.py`
  - Dep: none
  - Agent: Builder
  - Description: Implement `AuditLogger` with JSON Lines output, rotation (10 MB, 5 backups), structured entries (ts, action, params, exit_code, stderr_hash, user)
  - Acceptance: `AuditLogger.log()` writes valid JSONL entries, rotation works
  - Docs: CHANGELOG
  - Tests: `tests/test_audit.py`

- [ ] T8: Integrate audit logging into PrivilegedCommand
  - ID: T8
  - Files: `utils/commands.py`
  - Dep: T7
  - Agent: Builder
  - Description: Auto-log all `PrivilegedCommand` method calls via audit logger. Log action name, sanitized params, exit code.
  - Acceptance: Every PrivilegedCommand execution produces an audit log entry
  - Docs: CHANGELOG
  - Tests: `tests/test_commands.py`

- [ ] T9: Add CLI audit-log command
  - ID: T9
  - Files: `cli/main.py`
  - Dep: T7
  - Agent: CodeGen
  - Description: Add `--audit-log` subcommand to dump recent audit entries, support `--json` output
  - Acceptance: `loofi --cli audit-log` outputs recent entries
  - Docs: CHANGELOG
  - Tests: `tests/test_cli.py`

### Phase 3: Parameter Validation & Polkit

- [ ] T10: Add parameter schema validation to PrivilegedCommand
  - ID: T10
  - Files: `utils/commands.py`
  - Dep: T7
  - Agent: Builder
  - Description: Add `@validated_action` decorator with schema dict (types, constraints). Reject unknown params, empty strings, path traversal. Log failures.
  - Acceptance: Invalid params raise `ValidationError`, audit-logged
  - Docs: CHANGELOG
  - Tests: `tests/test_commands.py`

- [ ] T11: Split Polkit policy into granular files
  - ID: T11
  - Files: `config/org.loofi.fedora-tweaks.*.policy`
  - Dep: none
  - Agent: CodeGen
  - Description: Create 6 new Polkit policy files (firewall, network, storage, service-manage, kernel, security). Keep existing 5 policies. Update RPM spec to install all.
  - Acceptance: 11 policy files exist with correct XML structure
  - Docs: CHANGELOG
  - Tests: XML validation

- [ ] T12: Map PrivilegedCommand actions to Polkit policy IDs
  - ID: T12
  - Files: `utils/commands.py`
  - Dep: T11
  - Agent: Builder
  - Description: Add `POLKIT_MAP` dict mapping PrivilegedCommand methods to Polkit action IDs. Future: use `pkexec --action-id` when available.
  - Acceptance: Every PrivilegedCommand method has a corresponding Polkit policy ID
  - Docs: none
  - Tests: `tests/test_commands.py`

### Phase 4: Dry-Run Mode

- [ ] T13: Add dry-run support to CLI
  - ID: T13
  - Files: `cli/main.py`
  - Dep: T7
  - Agent: CodeGen
  - Description: Add `--dry-run` global flag. When set, `run_operation()` prints command without executing, logs to audit with `dry_run: true`.
  - Acceptance: `loofi --cli --dry-run cleanup` shows command without running it
  - Docs: CHANGELOG
  - Tests: `tests/test_cli.py`

- [ ] T14: Add preview mode to GUI confirm dialogs
  - ID: T14
  - Files: `ui/confirm_dialog.py`
  - Dep: none
  - Agent: Sculptor
  - Description: Add "Preview" button to `ConfirmActionDialog` that shows the exact command that will run
  - Acceptance: Preview button shows command text, does not execute
  - Docs: CHANGELOG
  - Tests: `tests/test_confirm_dialog.py`

### Phase 5: Security Documentation & Install Deprecation

- [ ] T15: Create SECURITY.md
  - ID: T15
  - Files: `SECURITY.md`
  - Dep: none
  - Agent: Guardian
  - Description: Create vulnerability disclosure policy with GitHub Security Advisories link, supported versions (v34+), responsible disclosure timeline (90 days), security contact
  - Acceptance: SECURITY.md exists at project root with all required sections
  - Docs: self
  - Tests: none

- [ ] T16: Deprecate install.sh
  - ID: T16
  - Files: `install.sh`, `README.md`
  - Dep: none
  - Agent: Guardian
  - Description: Add warning banner to install.sh, require `--i-know-what-i-am-doing` flag. Update README to recommend RPM/Copr as primary install.
  - Acceptance: `bash install.sh` shows warning and exits without flag
  - Docs: README
  - Tests: none

### Phase 6: UI Bug Fixes

- [ ] T17: Fix notification panel visibility and positioning
  - ID: T17
  - Files: `ui/notification_panel.py`, `ui/main_window.py`
  - Dep: none
  - Agent: Sculptor
  - Description: Panel starts hidden, proper background/border styling, bell→badge ordering, edge-clipping prevention, dynamic height cap
  - Acceptance: Panel invisible on startup, no clipping in top-right corner
  - Docs: CHANGELOG
  - Tests: `tests/test_notification_*.py`

### Phase 7: Testing & Validation

- [ ] T18: Add timeout enforcement integration tests
  - ID: T18
  - Files: `tests/test_timeout_enforcement.py`
  - Dep: T1-T5
  - Agent: Test
  - Description: Create script that scans all utils/ and cli/ for subprocess calls without timeout. Add as pytest test that fails if any untimed calls exist.
  - Acceptance: Test passes (zero untimed subprocess calls)
  - Docs: none
  - Tests: self

- [ ] T19: Add audit logger tests
  - ID: T19
  - Files: `tests/test_audit.py`
  - Dep: T7
  - Agent: Test
  - Description: Test log creation, rotation, JSONL format, field validation, audit integration with PrivilegedCommand
  - Acceptance: Full coverage of AuditLogger class
  - Docs: none
  - Tests: self

- [ ] T20: Add parameter validation tests
  - ID: T20
  - Files: `tests/test_commands.py`
  - Dep: T10
  - Agent: Test
  - Description: Test schema validation, rejection of invalid params, path traversal detection, audit logging of failures
  - Acceptance: Both valid and invalid inputs tested
  - Docs: none
  - Tests: self

### Phase 8: Documentation

- [ ] T21: Update CHANGELOG, README, release notes
  - ID: T21
  - Files: `CHANGELOG.md`, `README.md`, `docs/releases/RELEASE-NOTES-v35.0.0.md`
  - Dep: T1-T20
  - Agent: Planner
  - Description: Document all v35.0.0 changes including timeout enforcement stats, audit system, Polkit changes, security improvements
  - Acceptance: CHANGELOG has complete v35.0.0 section, release notes cover all changes
  - Docs: self
  - Tests: none
