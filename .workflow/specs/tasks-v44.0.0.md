# Tasks — v44.0.0 "Review Gate"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json, .workflow/specs/tasks-v44.0.0.md` | Dep: - | Agent: project-coordinator | Description: Create v44.0.0 roadmap scope as the single ACTIVE target and initialize workflow task artifact + race lock to v44.0.0.
  Acceptance: ROADMAP has exactly one `[ACTIVE]` version for v44.0.0 and race lock targets v44.0.0 with active status.
  Docs: ROADMAP
  Tests: none

## Phase: Build

- [x] ID: TASK-002 | Files: `scripts/check_fedora_review.py` | Dep: TASK-001 | Agent: backend-builder | Description: Add lightweight Fedora review gate checker that validates tool presence and runs `fedora-review -V` and `fedora-review -d` with explicit timeout handling.
  Acceptance: Script exits 0 on success and non-zero on missing tool, command failure, or timeout.
  Docs: none
  Tests: `tests/test_check_fedora_review.py`

- [x] ID: TASK-003 | Files: `scripts/workflow_runner.py, scripts/workflow-runner.sh` | Dep: TASK-002 | Agent: backend-builder | Description: Enforce Fedora review prerequisite for write-mode package/release phases in workflow runner and document requirement in shell wrapper help output.
  Acceptance: `package` and `release` phases in write mode fail fast with blocked status when Fedora review gate fails; review mode and other phases remain unaffected.
  Docs: none
  Tests: `tests/test_workflow_runner_locks.py`

- [x] ID: TASK-004 | Files: `.github/workflows/ci.yml` | Dep: TASK-002 | Agent: backend-builder | Description: Add required `fedora_review` job to CI workflow using Fedora 43 container and checker script.
  Acceptance: CI contains non-optional Fedora review job that installs `fedora-review` and runs `python3 scripts/check_fedora_review.py`.
  Docs: none
  Tests: `tests/test_workflow_fedora_review_contract.py`

- [x] ID: TASK-005 | Files: `.github/workflows/auto-release.yml` | Dep: TASK-002 | Agent: backend-builder | Description: Add required `fedora_review` job to auto-release workflow and include it as a hard dependency for build execution.
  Acceptance: Auto-release has `fedora_review` job and `build` waits on it and requires success in the build `if` gate.
  Docs: none
  Tests: `tests/test_workflow_fedora_review_contract.py`

## Phase: Test

- [x] ID: TASK-006 | Files: `tests/test_check_fedora_review.py` | Dep: TASK-002 | Agent: test-writer | Description: Add checker tests for success, missing binary, probe failure, and timeout handling.
  Acceptance: Tests cover all checker failure classes and assert timeout + command invocation behavior.
  Docs: none
  Tests: self

- [x] ID: TASK-007 | Files: `tests/test_workflow_runner_locks.py` | Dep: TASK-003 | Agent: test-writer | Description: Extend runner tests to validate Fedora gate blocking for write-mode package/release and pass-through in review mode.
  Acceptance: New tests verify blocked metadata/error messages for failures and no gate invocation in review mode.
  Docs: none
  Tests: self

- [x] ID: TASK-008 | Files: `tests/test_workflow_fedora_review_contract.py` | Dep: TASK-004,TASK-005 | Agent: test-writer | Description: Add workflow contract tests verifying required Fedora review jobs and build dependency wiring in CI and auto-release workflows.
  Acceptance: Contract tests fail when `fedora_review` job or required build dependency/command wiring is missing.
  Docs: none
  Tests: self

## Phase: Doc

- [x] ID: TASK-009 | Files: `.github/workflow/PIPELINE.md, .github/workflow/QUICKSTART.md, .github/workflow/prompts/package.md, .github/workflow/prompts/release.md` | Dep: TASK-003,TASK-004,TASK-005 | Agent: release-planner | Description: Update workflow framework docs/prompts to define Fedora review prerequisite behavior for package and release phases.
  Acceptance: Workflow docs and prompts explicitly describe fedora-review requirement and checker gate behavior.
  Docs: PIPELINE, QUICKSTART, workflow prompts
  Tests: none

- [x] ID: TASK-010 | Files: `README.md, docs/RELEASE_CHECKLIST.md, CHANGELOG.md, docs/releases/RELEASE-NOTES-v44.0.0.md` | Dep: TASK-009 | Agent: release-planner | Description: Document Fedora review gate across user-facing CI/release docs and add v44 changelog + release notes entries.
  Acceptance: README and release checklist include fedora-review gate in pipeline narrative; changelog/release notes summarize v44 scope.
  Docs: CHANGELOG, README, RELEASE-CHECKLIST, RELEASE-NOTES
  Tests: none

## Phase: Release

- [x] ID: TASK-011 | Files: `loofi-fedora-tweaks/version.py, pyproject.toml, loofi-fedora-tweaks.spec, ROADMAP.md, .workflow/specs/.race-lock.json, .workflow/reports/test-results-v44.0.0.json, .workflow/reports/run-manifest-v44.0.0.json` | Dep: TASK-006,TASK-007,TASK-008,TASK-010 | Agent: release-planner | Description: Align version artifacts to 44.0.0 "Review Gate", register v44 roadmap state, and update workflow report artifacts for the active version.
  Acceptance: Version files are aligned to 44.0.0, v44 roadmap scope is registered as active, and v44.0.0 workflow report artifacts exist.
  Docs: ROADMAP
  Tests: `tests/test_version.py`, `python3 scripts/check_release_docs.py`
