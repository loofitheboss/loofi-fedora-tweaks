# Tasks for v28.0.0

- [x] ID: TASK-001 | Files: `ROADMAP.md` | Dep: - | Agent: project-coordinator | Description: Confirm v28.0.0 is the only ACTIVE roadmap target and freeze kickoff scope.
  Acceptance: ROADMAP contains exactly one ACTIVE section for v28.0.0 and clear kickoff deliverables.
  Docs: ROADMAP
  Tests: none
- [x] ID: TASK-002 | Files: `.workflow/specs/.race-lock.json` | Dep: TASK-001 | Agent: backend-builder | Description: Reset race lock metadata to v28.0.0 with active status and normalized timestamp fields.
  Acceptance: Race lock version equals v28.0.0 and status is active for new phase execution.
  Docs: none
  Tests: none
- [x] ID: TASK-003 | Files: `.workflow/reports/run-manifest-v28.0.0.json` | Dep: TASK-001 | Agent: backend-builder | Description: Initialize v28.0.0 run manifest using workflow runner-compatible schema.
  Acceptance: Manifest includes version, assistant, owner, mode, started_at, updated_at, and phases list.
  Docs: none
  Tests: none
- [x] ID: TASK-004 | Files: `.workflow/specs/tasks-v28.0.0.md` | Dep: TASK-001 | Agent: project-coordinator | Description: Define dependency-safe kickoff plan tasks with explicit acceptance/docs/tests fields.
  Acceptance: Every task entry satisfies task contract markers and continuation fields.
  Docs: none
  Tests: none
- [x] ID: TASK-005 | Files: `scripts/workflow_runner.py`, `.github/workflow/prompts/plan.md` | Dep: TASK-002, TASK-003, TASK-004 | Agent: architecture-advisor | Description: Verify workflow runner and planning prompt contracts remain aligned for v28 planning cycle.
  Acceptance: Task artifact format and phase metadata map cleanly to runner validation checks.
  Docs: none
  Tests: `tests/test_workflow_runner_locks.py`
- [x] ID: TASK-006 | Files: `tests/test_workflow_runner_locks.py` | Dep: TASK-005 | Agent: test-writer | Description: Add or update tests for task contract validation and race lock behavior against v28 artifacts.
  Acceptance: Tests cover valid contract entries and block malformed task artifacts.
  Docs: none
  Tests: `tests/test_workflow_runner_locks.py`
- [x] ID: TASK-007 | Files: `docs/RELEASE_CHECKLIST.md`, `docs/releases/RELEASE-NOTES-v28.0.0.md`, `CHANGELOG.md` | Dep: TASK-005 | Agent: release-planner | Description: Add v28 kickoff traceability notes for workflow-state reset and planning baseline.
  Acceptance: Release docs describe v28 kickoff intent and artifact expectations without implementation claims.
  Docs: CHANGELOG
  Tests: none
- [x] ID: TASK-008 | Files: `.workflow/reports/run-manifest-v28.0.0.json` | Dep: TASK-006, TASK-007 | Agent: project-coordinator | Description: Record planning checkpoint entry to mark v28 kickoff baseline ready for design/build phases.
  Acceptance: Manifest phases include a successful plan checkpoint for v28.0.0.
  Docs: none
  Tests: none
