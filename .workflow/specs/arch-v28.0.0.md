# Architecture Blueprint — v28.0.0 Workflow Contract Reset

> **Version**: v28.0.0
> **Phase**: P2 DESIGN
> **Date**: 2026-02-12
> **Agent**: architecture-advisor
> **Status**: Implementation-ready

---

## Overview

v28.0.0 is a meta-version: no application code changes. Its purpose is to establish a clean-slate workflow state after v27.0 completion and validate that all planning artifacts satisfy the `workflow_runner.py` contract. This blueprint documents the artifact structure, validation rules, and phase sequencing that govern the v28 cycle.

---

## Resolved Open Questions

### Q1: Should v28 introduce new workflow runner features?
**Decision: NO.**
v28 resets state and validates existing contracts. No runner code changes. The runner already enforces task contract markers (`ID:`, `Files:`, `Dep:`, `Agent:`, `Description:`) and continuation fields (`Acceptance:`, `Docs:`, `Tests:`) for versions ≥ v26. v28 artifacts must comply with those rules.

**Rationale**: Mixing workflow-state reset with runner feature work creates unnecessary coupling. Runner changes belong in a future version if needed.

### Q2: Should the race lock schema change?
**Decision: NO.**
The existing schema (`version`, `started_at`, `status`) is sufficient. The `started_at` field uses `YYYYMMDD_HHMMSS` format matching `get_timestamp()` in the runner. No additional fields are needed.

### Q3: Should the run manifest include failure metadata?
**Decision: EXISTING SCHEMA SUFFICIENT.**
The manifest `phases` array already supports `status: "success" | "failure"` per entry. No schema extension needed for v28.

---

## Artifact Structure

### File Layout

```
.workflow/
├── specs/
│   ├── .race-lock.json              # Active version lock
│   ├── tasks-v28.0.0.md             # P1 task artifact (contract-compliant)
│   ├── arch-v28.0.0.md              # THIS FILE (P2 blueprint)
│   └── release-notes-draft-v28.0.0.md  # P2 pre-doc draft
└── reports/
    └── run-manifest-v28.0.0.json    # Phase execution log
```

### Race Lock Schema

```json
{
  "version": "v28.0.0",
  "started_at": "20260212_210000",
  "status": "active"
}
```

- `version`: Normalized version tag (must start with `v`)
- `started_at`: Timestamp from `get_timestamp()` — `YYYYMMDD_HHMMSS`
- `status`: `"active"` while version is in progress

### Run Manifest Schema

```json
{
  "version": "v28.0.0",
  "assistant": "copilot",
  "owner": "agents",
  "mode": "write",
  "issue": null,
  "started_at": "2026-02-12T21:00:00Z",
  "updated_at": "2026-02-12T21:00:00Z",
  "phases": [
    {
      "phase": "plan",
      "phase_name": "P1 PLAN",
      "status": "success",
      "timestamp": "2026-02-12T21:00:00Z",
      "artifacts": [".workflow/specs/tasks-v28.0.0.md"]
    }
  ]
}
```

- `phases`: Append-only array. Each entry records phase name, status, timestamp, and output artifacts.
- `updated_at`: Set to current UTC on each phase append.

### Task Contract Format

Each task line in `tasks-vXX.md` must contain these markers (enforced by `validate_task_contract()`):

**Line markers** (all on the task line):
- `ID:` — unique task identifier (e.g., `TASK-001`)
- `Files:` — affected file paths
- `Dep:` — dependency task IDs (or `-` for none)
- `Agent:` — responsible agent name
- `Description:` — what the task does

**Continuation fields** (within 4 lines after task line):
- `Acceptance:` — completion criteria
- `Docs:` — documentation deliverables
- `Tests:` — test file references

---

## Phase Sequencing

The workflow runner enforces this phase order:

```
P1 PLAN → P2 DESIGN → P3 BUILD → P4 TEST → P5 DOC → P6 PACKAGE → P7 RELEASE
```

For v28.0.0 specifically:
- **P1 PLAN** ✅ — Task decomposition, race lock reset, manifest init
- **P2 DESIGN** — Architecture blueprint + release notes draft (this phase)
- **P3 BUILD** — No app code; validate all artifacts are structurally sound
- **P4 TEST** — Run existing tests, confirm no regressions from v27
- **P5 DOC** — Finalize release notes, CHANGELOG, checklist
- **P6 PACKAGE** — Version bump in `version.py` + `.spec`, RPM build
- **P7 RELEASE** — Tag, publish, archive workflow state

---

## Validation Rules

### Contract Enforcement

`validate_task_contract()` in `workflow_runner.py` enforces:
1. Task file must exist
2. At least one task entry with `ID:` field
3. All 5 line markers present on each task line
4. All 3 continuation fields within 4-line window after each task
5. Enforcement applies to versions ≥ v26 (`should_enforce_task_contract()`)

### Race Lock Guards

- Only one version may be `"active"` at a time
- Phase execution checks lock version matches target version
- Writer lock (`.writer-lock.json`) prevents concurrent writes

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Stale race lock from v27 blocking v28 | Low | TASK-002 already reset lock to v28.0.0 |
| Task contract drift from runner expectations | Low | TASK-005 verified alignment; TASK-006 added tests |
| Manifest schema mismatch | Low | Uses same schema as v27; no changes needed |
| Phase ordering violation | None | Runner enforces `PHASE_ORDER` list |

No architecture risks identified. v28 is a state-management version with no application code changes.

---

## Implementation Notes

### P3 BUILD Scope

Since v28 has no application code, P3 should:
1. Verify all 8 P1 tasks are marked `[x]` in the task artifact
2. Confirm race lock, manifest, and task file all target `v28.0.0`
3. Run `validate_task_contract()` against `tasks-v28.0.0.md`
4. No new modules, no new UI, no new CLI commands

### P4 TEST Scope

1. Run full test suite (`pytest tests/ -v`) — expect 0 regressions
2. Run `test_workflow_runner_locks.py` specifically for contract validation
3. No new test files needed beyond what TASK-006 already delivered

### Version Bump Values (P6)

```python
# version.py
__version__ = "28.0.0"
__version_codename__ = "Workflow Contract Reset"
```

```spec
# loofi-fedora-tweaks.spec
Version: 28.0.0
```

---

## Dependencies

- v27.0 completion (DONE)
- `scripts/workflow_runner.py` contract rules (stable, no changes needed)
- `tests/test_workflow_runner_locks.py` (updated in TASK-006)
