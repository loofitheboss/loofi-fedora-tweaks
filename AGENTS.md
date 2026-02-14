# Loofi Fedora Tweaks — Agent Instructions

> PyQt6 desktop app for Fedora Linux system customization.
> Python 3.12+ | 28 feature tabs | 174 test files (4349 tests, 74% coverage) | 105 utils modules
> Canonical references: `ARCHITECTURE.md` (structure), `ROADMAP.md` (scope), `.github/copilot-instructions.md` (patterns)

## Build, Lint, Test Commands

```bash
# Run full test suite
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short

# Run a single test file
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py -v

# Run a single test method
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py::TestPrivilegedCommandBuilders::test_dnf_install -v

# Run tests with coverage
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov=loofi-fedora-tweaks --cov-report=term-missing --cov-fail-under=75

# Lint
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722

# Type check
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary

# Build RPM
bash scripts/build_rpm.sh

# Dev run
./run.sh
```

## Project Layout

```
loofi-fedora-tweaks/          # Source root (set as PYTHONPATH)
├── ui/*_tab.py               # PyQt6 tabs (inherit BaseTab)
├── ui/base_tab.py            # BaseTab: shared CommandRunner, output_area
├── utils/*.py                # Business logic (@staticmethod, operations tuples)
├── utils/commands.py         # PrivilegedCommand builder (pkexec)
├── utils/errors.py           # LoofiError hierarchy (code, hint, recoverable)
├── core/executor/            # BaseActionExecutor + ActionResult
├── cli/main.py               # CLI entry (calls utils/, never ui/)
├── config/                   # apps.json, polkit policy, systemd
└── version.py                # __version__, __version_codename__
tests/                        # unittest + mock, @patch decorators, no root
scripts/                      # build_rpm.sh, MCP servers, workflow tools
.github/agents/               # 8 VS Code Copilot agents (canonical)
.github/claude-agents/        # 7 Claude agents (adapters)
.github/instructions/         # AI instructions + hardening guide
```

## Code Style

### Imports
Ordered: stdlib, blank line, third-party, blank line, local. Alphabetical within groups.
```python
import logging
import subprocess
from typing import List, Optional, Tuple

from PyQt6.QtWidgets import QVBoxLayout, QLabel

from utils.commands import PrivilegedCommand
from utils.errors import LoofiError
```

### Logging
```python
from utils.log import get_logger       # preferred (in utils/)
logger = get_logger(__name__)

import logging                          # acceptable (in ui/)
logger = logging.getLogger(__name__)
```
Use `%s` formatting in log calls, never f-strings: `logger.debug("Failed: %s", e)`

### Type Hints
- Inline annotations on all public methods (PEP 484)
- `Tuple[str, List[str], str]` for operations tuples (aliased as `CommandTuple`)
- `Optional[X]` or `X | None` (both accepted, PEP 604 preferred for new code)
- Return type on every public function

### Docstrings
Google-style. Module-level docstring on every file.
```python
"""One-line summary.

Args:
    param: Description.

Returns:
    Description of return value.
"""
```

### Naming Conventions
| Element | Convention | Example |
|---------|-----------|---------|
| Files | `snake_case.py` | `network_utils.py` |
| Tab files | `*_tab.py` | `hardware_tab.py` |
| Test files | `test_*.py` | `test_commands.py` |
| Classes | `PascalCase` | `NetworkUtils`, `BaseTab` |
| Exceptions | `PascalCase` + `Error` | `DnfLockedError` |
| Methods | `snake_case` | `scan_wifi()` |
| Private | `_leading_underscore` | `_derive_action_name()` |
| Constants | `UPPER_SNAKE_CASE` | `POLKIT_MAP` |
| Type aliases | `PascalCase` | `CommandTuple` |
| Test classes | `Test` + `PascalCase` | `TestScanWifi` |
| Test methods | `test_what_scenario` | `test_dnf_install` |

### Error Handling
```python
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
except (subprocess.SubprocessError, OSError) as e:
    logger.debug("Descriptive msg: %s", e)
    return []  # safe default: [], "", None, False
```
Use typed exceptions from `utils/errors.py`. Each has `code`, `hint`, `recoverable`.

## Critical Rules (Never Violate)

1. **Never `sudo`** — only `pkexec` via `PrivilegedCommand`
2. **Never hardcode `dnf`** — use `SystemManager.get_package_manager()`
3. **Never subprocess in UI** — extract to `utils/`, call via `CommandRunner`
4. **Always unpack PrivilegedCommand** — `binary, args, desc = PrivilegedCommand.dnf(...)`
5. **Always `timeout=N`** on every `subprocess.run()` / `check_output()` call
6. **Always branch on `SystemManager.is_atomic()`** for dnf vs rpm-ostree
7. **Version sync** — `version.py`, `.spec`, and `pyproject.toml` must match (use `scripts/bump_version.py`)
8. **Audit log** privileged actions (timestamp, action, params, exit code)
9. **Stabilization gate** — no new major features until Phase 1-2 complete
10. **Never `shell=True`** in subprocess calls
11. **Never hardcode versions in tests** — use dynamic assertions (non-empty, semver format); CI `docs_gate` blocks hardcoded version/codename assertions
12. **Always scaffold release notes** — run `bump_version.py` which creates `docs/releases/RELEASE-NOTES-vX.Y.Z.md`

## Key Patterns

```python
# PrivilegedCommand — always unpack the tuple
from utils.commands import PrivilegedCommand
binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ["pkexec", "dnf", "install", "-y", "package"]

# Utils class — all @staticmethod, no instance state
class FeatureManager:
    @staticmethod
    def operation() -> Tuple[str, List[str], str]:
        return ("pkexec", ["dnf", "clean", "all"], "Cleaning...")

# UI tab — inherit BaseTab
from ui.base_tab import BaseTab
class MyTab(BaseTab):
    def __init__(self):
        super().__init__()  # gives self.output_area, self.runner, self.run_command()

# Atomic detection
pm = SystemManager.get_package_manager()  # "dnf" or "rpm-ostree"
```

## Testing Rules

```python
"""Tests for utils/module.py"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.module import Manager

class TestManager(unittest.TestCase):
    """Tests for Manager operations."""

    @patch('utils.module.subprocess.run')
    def test_operation_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='OK')
        result = Manager.operation()
        self.assertIsNotNone(result)
        mock_run.assert_called_once()

    @patch('utils.module.subprocess.run')
    def test_operation_failure(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("fail")
        result = Manager.operation()
        self.assertEqual(result, [])  # safe default
```

- **`@patch` decorators only** — never context managers
- Patch the module-under-test namespace: `'utils.module.subprocess.run'`
- Mock: `subprocess.run`, `subprocess.check_output`, `shutil.which`, `os.path.exists`, `builtins.open`
- Test both success AND failure paths
- Test both dnf and rpm-ostree paths where applicable
- No root needed — all system calls mocked

## Agent System

For complex multi-step tasks, delegate to agents in `.github/claude-agents/`:
- **project-coordinator** — task decomposition, dependency ordering
- **architecture-advisor** — design, module structure
- **backend-builder** — utils/ modules, system integration
- **code-implementer** — general implementation
- **frontend-integration-builder** — UI tabs, CLI commands
- **test-writer** — test creation, coverage
- **release-planner** — roadmap, releases

VS Code equivalents in `.github/agents/`: Arkitekt, Builder, CodeGen, Guardian, Manager, Planner, Sculptor, Test.

## Stabilization Directive

See `.github/instructions/system_hardening_and_stabilization_guide.md`:
- No new major features until Phase 1-2 hardening complete
- Refactor before expanding. Safety over velocity.
- Never expand root-level capability without: validation, audit log, rollback strategy
- If unsure, default to restrictive behavior
