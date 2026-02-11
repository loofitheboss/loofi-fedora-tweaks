# Workflow Quickstart (State-File)

## Run Pipeline with Python Runner

```bash
# Single phase
python3 scripts/workflow_runner.py --phase plan --target-version v24.0

# Full pipeline
python3 scripts/workflow_runner.py --phase all --target-version v24.0

# Preview commands without execution
python3 scripts/workflow_runner.py --phase design --target-version v24.0 --dry-run
```

## Artifact Locations

- Specs: `.workflow/specs/`
- Reports: `.workflow/reports/`
- Prompts: `.github/workflow/prompts/`

## Need-to-Know Rule

- P3 Build reads only architecture + tasks artifacts.
- P3 Build does not read `ROADMAP.md`.

## Legacy Runner

- `scripts/workflow-runner.sh` remains available for manual/legacy flow.
