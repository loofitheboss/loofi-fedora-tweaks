# Release Notes: v28.0.0 "Workflow Contract Reset"

**Release Date:** 2026-02-12  
**Codename:** Workflow Contract Reset  
**Theme:** Clean-slate workflow state, runner-compatible planning artifacts, version bump

---

## Overview

v28.0.0 establishes a clean baseline for the next development cycle by resetting workflow state artifacts, validating task contract alignment, and bumping all version references. This is a meta-version — no application features, UI changes, or CLI commands are introduced.

---

## Meta Changes

### Workflow State Reset
- **Race Lock:** Reset to v28.0.0 with active status and normalized timestamp fields
- **Run Manifest:** Initialized with runner-compatible schema including version, assistant, owner, mode, and phases list
- **Task Artifact:** Created dependency-safe kickoff plan with explicit acceptance/docs/tests fields per task

### Contract Validation
- **Task Markers:** Verified required markers (ID, Files, Dep, Agent, Description) align with workflow_runner.py validation
- **Continuation Fields:** Confirmed acceptance criteria, documentation scope, and test expectations encoded in task artifact
- **Planning Prompt:** Validated `.github/workflow/prompts/plan.md` format matches runner expectations

### Planning Checkpoint
- **Phase Entry:** Recorded successful PLAN phase completion in run manifest
- **Artifact Tracking:** Linked `.workflow/specs/tasks-v28.0.0.md` as phase output
- **Handoff Ready:** Baseline prepared for design/build/test phase progression

---

## Testing

- Added/updated `tests/test_workflow_runner_locks.py` for task contract validation and race lock behavior
- All 1514+ existing tests pass without regression

---

## Documentation

- Updated `CHANGELOG.md` with v28.0.0 kickoff traceability notes
- Added kickoff context to `docs/RELEASE_CHECKLIST.md`
- Created this release notes document for v28 baseline

---

## Next Steps

v29.0 scope will be determined during the next planning cycle.

---

## Contributors

- Workflow automation system
- Project coordinator agent
- Backend builder agent
- Test writer agent
- Release planner agent
