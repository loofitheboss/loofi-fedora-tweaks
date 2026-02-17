---
description: "Run pytest with coverage, discover uncovered lines, and increase coverage to target threshold"
---

# Pytest Coverage Improvement

The goal is to increase test coverage toward the 80% CI threshold.

## Workflow

1. Generate a coverage report:

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=annotate:cov_annotate --cov-report=term-missing -v --tb=short
```

2. For a specific module:

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_mymodule.py --cov=loofi-fedora-tweaks/utils/mymodule.py --cov-report=annotate:cov_annotate -v
```

3. Open the `cov_annotate` directory. Each file corresponds to a source file. Files at 100% coverage can be skipped.

4. For files below 100%, find lines starting with `!` (exclamation mark) — these are uncovered.

5. Add tests following project conventions:
   - Use `@patch` decorators only (never context managers)
   - Patch module-under-test namespace: `'utils.module.subprocess.run'`
   - Mock all system calls — tests must run without root
   - Test both success AND failure paths
   - Test both dnf and rpm-ostree paths for package operations

6. Keep running tests and improving coverage until the target is met.

7. Clean up: `rm -rf cov_annotate`
