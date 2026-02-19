---
description: "Review and refactor code according to project instructions and coding standards"
---

# Review and Refactor

## Role

You're a senior Python/PyQt6 engineer maintaining the Loofi Fedora Tweaks project.

## Task

1. Review all coding guidelines in `.github/instructions/*.md` and `.github/copilot-instructions.md`.
2. Review the target code carefully and refactor if needed, ensuring:
   - Layer boundaries are respected (no subprocess in UI, no PyQt6 in utils)
   - PrivilegedCommand tuples are always unpacked
   - All subprocess calls have `timeout=N` and no `shell=True`
   - Error handling uses typed exceptions from `utils/errors.py`
   - Logging uses `%s` formatting, never f-strings
   - Atomic Fedora paths are handled where applicable
3. Keep existing files intact — do not split code into new files.
4. Run tests after changes: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short`
5. Run lint: `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203`
