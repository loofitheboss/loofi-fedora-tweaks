---
name: test
description: Write and run tests for all changed files in the current version.
---

# Test Phase (P4)

## Steps
1. Read `.workflow/specs/tasks-v{VERSION}.md` for changed files
2. For each changed module, write/update tests:
   - Success path
   - Failure path (CalledProcessError, FileNotFoundError)
   - Edge cases
3. Run full suite
4. Fix failures or report if implementation issue

## Run Tests
```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short --cov=loofi-fedora-tweaks --cov-report=term-missing --cov-fail-under=80
```

## Testing Rules
- `@patch` decorators only (no context managers)
- Mock: `subprocess.run`, `subprocess.check_output`, `shutil.which`, `os.path.exists`, `builtins.open`
- No root required
- Use existing `tests/conftest.py` fixtures
- Minimum 80% coverage on changed files
- Reference `.github/workflow/prompts/test.md` for full prompt
