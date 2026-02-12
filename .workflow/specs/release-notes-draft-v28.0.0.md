# Release Notes — Loofi Fedora Tweaks v28.0.0

> **Codename**: Workflow Contract Reset
> **Release date**: 2026-02-12
> **Status**: FINAL

---

## What's New

### Clean-Slate Workflow State

v28.0.0 resets the internal development workflow to a clean baseline after the v27.0 Marketplace Enhancement release. This is a meta-version focused on process hygiene — no application features, UI changes, or new CLI commands are introduced.

### Runner-Compatible Planning Artifacts

All v28 planning artifacts now comply with the workflow runner's contract validation rules introduced in v26. Task files include mandatory markers (`ID:`, `Files:`, `Dep:`, `Agent:`, `Description:`) and continuation fields (`Acceptance:`, `Docs:`, `Tests:`), ensuring that the automated runner can validate artifacts without manual intervention.

### Race Lock Reset

The workflow race lock has been reset to target v28.0.0 with an active status, clearing any residual state from the v27 cycle. This ensures phase execution and writer locks operate against the correct version.

### Workflow Test Coverage

Tests for task contract validation and race lock behavior have been updated to validate v28 artifacts, confirming that the runner's enforcement rules work correctly for the current cycle.

---

## Breaking Changes

### For End Users

None. The application is unchanged from v27.0.

### For Developers

No API, CLI, or UI changes. The only changes are to workflow metadata files under `.workflow/` and release documentation.

---

## Files Changed

- `.workflow/specs/tasks-v28.0.0.md` — Planning task artifact
- `.workflow/specs/.race-lock.json` — Reset to v28.0.0
- `.workflow/reports/run-manifest-v28.0.0.json` — Initialized with P1 checkpoint
- `tests/test_workflow_runner_locks.py` — Contract validation tests updated
- `docs/RELEASE_CHECKLIST.md` — v28 kickoff traceability
- `docs/releases/RELEASE-NOTES-v28.0.0.md` — Release notes placeholder
- `CHANGELOG.md` — v28 kickoff entry
- `ROADMAP.md` — v28.0 marked as ACTIVE

---

## Upgrade Notes

No upgrade steps required. This version contains no application changes — updating is equivalent to a version number bump.

---

## Known Issues

None.

---

## What's Next

v29.0 scope will be determined during the next planning cycle. Candidate themes include enhanced system monitoring, accessibility improvements, and expanded atomic Fedora support.
