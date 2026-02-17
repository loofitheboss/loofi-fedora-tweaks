# Workflow Quickstart (State-File)

## Run Pipeline with Python Runner

```bash
# Single phase
python3 scripts/workflow_runner.py --phase plan --target-version v24.0

# Full pipeline
python3 scripts/workflow_runner.py --phase all --target-version v24.0

# Preview commands without execution
python3 scripts/workflow_runner.py --phase design --target-version v24.0 --dry-run

# Explicit assistant write mode
python3 scripts/workflow_runner.py --phase build --target-version v24.0 --assistant codex --mode write --issue 42

# Review-only mode (no writer lock)
python3 scripts/workflow_runner.py --phase test --target-version v24.0 --assistant claude --mode review --issue 42
```

## Artifact Locations

- Specs: `.workflow/specs/`
- Reports: `.workflow/reports/`
- Prompts: `.github/workflow/prompts/`
- Model routing: `.github/workflow/model-router.toml`

## Need-to-Know Rule

- P3 Build reads only architecture + tasks artifacts.
- P3 Build does not read `ROADMAP.md`.
- In write mode, `package` and `release` require Fedora review tooling:
  - `python3 scripts/check_fedora_review.py`
  - install prerequisite: `dnf install -y fedora-review`

## Legacy Runner

- `scripts/workflow-runner.sh` remains available for manual/legacy flow.
- `scripts/sync_ai_adapters.py` syncs Claude/Copilot/Codex adapter files from canonical `.github/`.
