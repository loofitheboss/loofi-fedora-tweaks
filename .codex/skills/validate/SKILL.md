---
name: validate
description: Check release readiness — version alignment, tests, lint, docs, packaging.
---

# Validate Release Readiness

## Run
```bash
bash scripts/workflow-runner.sh {VERSION} validate
```

## Manual Checks
1. Version alignment:
   - `python -c "import sys; sys.path.insert(0,'loofi-fedora-tweaks'); from version import __version__; print(__version__)"`
   - `grep '^Version:' loofi-fedora-tweaks.spec | awk '{print $2}'`
2. Tests pass: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q`
3. Lint clean: `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722`
4. CHANGELOG has version entry
5. README version references correct
6. Build scripts executable
