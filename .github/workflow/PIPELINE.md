# Future-Proof Workflow Pipeline

> This pipeline uses a Race Lock to guarantee version integrity.
> It keeps active specs in a hot workspace and archives prior runs as cold history.

## Race Lock
When you run `--phase plan`, the runner creates `.workflow/specs/.race-lock.json`.
- Purpose: prevent version mixing (example: running `v25.0` design in a `v25.0` race).
- Enforcement: non-plan phases must match the lock version exactly.
- Reset: starting a new `plan` archives current specs and creates a fresh lock.

## Directory Structure
```text
.workflow/
├── specs/                      # HOT: current race artifacts
│   ├── .race-lock.json         # Active race metadata
│   ├── tasks-v25.0.md
│   ├── arch-v25.0.md
│   └── release-notes-draft-v25.0.md
├── reports/
│   └── test-results-v25.0.json
└── archive/                    # COLD: previous race snapshots
    ├── v23.0_20260210_101010/
    └── v23.1_20260315_090001/
```

## Phase Flow
`P1 Plan -> P2 Design -> P3 Build -> P4 Test -> P5 Doc -> P6 Package -> P7 Release`

## How To Run
1. Start a new race (archives old specs, writes new lock):
```bash
python3 scripts/workflow_runner.py --phase plan --target-version v25.0
```
2. Continue same race:
```bash
python3 scripts/workflow_runner.py --phase design --target-version v25.0
python3 scripts/workflow_runner.py --phase build --target-version v25.0
python3 scripts/workflow_runner.py --phase test --target-version v25.0
python3 scripts/workflow_runner.py --phase doc --target-version v25.0
python3 scripts/workflow_runner.py --phase package --target-version v25.0
python3 scripts/workflow_runner.py --phase release --target-version v25.0
```
3. Run full sequence:
```bash
python3 scripts/workflow_runner.py --phase all --target-version v25.0
```

## Version Mismatch Behavior
If lock is `v25.0` and you run `--target-version v25.0` on non-plan phases, execution stops with a mismatch error.
To switch versions safely, start a new plan for the new version.
