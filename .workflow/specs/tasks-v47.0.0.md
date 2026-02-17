# Tasks — v47.0.0 "Experience"

## Phase: Plan/State

- [x] ID: TASK-001 | Files: `ROADMAP.md, .workflow/specs/.race-lock.json` | Dep: - | Agent: project-coordinator | Description: Transition active roadmap target and race lock to v47.0.0 Experience.
  Acceptance: Roadmap includes v47 as `[ACTIVE]` and race lock targets `v47.0.0`.
  Docs: ROADMAP
  Tests: none

## Phase: Build

- [ ] ID: TASK-002 | Files: `loofi-fedora-tweaks/utils/experience.py` | Dep: TASK-001 | Agent: backend-builder | Description: Create experience level manager with beginner/intermediate/advanced profiles and profile persistence.
  Acceptance: ExperienceManager reads/writes level to profile.json; all methods are @staticmethod.
  Docs: none
  Tests: `tests/test_experience.py`

- [ ] ID: TASK-003 | Files: `loofi-fedora-tweaks/utils/feedback.py` | Dep: TASK-001 | Agent: backend-builder | Description: Create actionable feedback utility that generates structured next-step suggestions from error/status contexts.
  Acceptance: FeedbackManager returns structured hints with action, description, and severity.
  Docs: none
  Tests: `tests/test_feedback.py`

- [ ] ID: TASK-004 | Files: `loofi-fedora-tweaks/utils/health_detail.py` | Dep: TASK-001 | Agent: backend-builder | Description: Create health drill-down utility providing per-category health breakdowns.
  Acceptance: HealthDetailManager returns category-level scores and remediation links.
  Docs: none
  Tests: `tests/test_health_detail.py`

- [ ] ID: TASK-005 | Files: `loofi-fedora-tweaks/utils/guided_tour.py` | Dep: TASK-001 | Agent: backend-builder | Description: Create guided tour state manager for first-run walkthrough persistence.
  Acceptance: GuidedTourManager tracks tour completion state in profile.json.
  Docs: none
  Tests: `tests/test_guided_tour.py`

## Phase: Test

- [ ] ID: TASK-006 | Files: `tests/test_experience.py, tests/test_feedback.py, tests/test_health_detail.py, tests/test_guided_tour.py` | Dep: TASK-002,TASK-003,TASK-004,TASK-005 | Agent: test-writer | Description: Create comprehensive test suites for all v47 utility modules.
  Acceptance: All tests pass with mocked system calls; coverage meets 80% threshold.
  Docs: none
  Tests: self

## Phase: Doc

- [ ] ID: TASK-007 | Files: `CHANGELOG.md, docs/releases/RELEASE-NOTES-v47.0.0.md` | Dep: TASK-006 | Agent: release-planner | Description: Document v47 experience release scope and outcomes.
  Acceptance: Docs and changelog reflect v47 features and release summary.
  Docs: CHANGELOG, RELEASE-NOTES
  Tests: none

## Phase: Release

- [ ] ID: TASK-008 | Files: `loofi-fedora-tweaks/version.py, pyproject.toml, loofi-fedora-tweaks.spec, .workflow/specs/.race-lock.json` | Dep: TASK-007 | Agent: release-planner | Description: Align version artifacts and workflow reports to v47.0.0 release state.
  Acceptance: Version files and race lock are aligned to v47.0.0.
  Docs: none
  Tests: `tests/test_version.py`
