# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ROLE

You are Claude Code operating inside this repository.
Delegate to agents. Follow existing patterns. Minimize token usage.

## KEY REFERENCE FILES

- `ARCHITECTURE.md` — Canonical architecture, layer rules, tab layout, patterns
- `ROADMAP.md` — Version scope, status, deliverables
- `AGENTS.md` — Agent system quick reference with code style and critical rules
- `.github/instructions/system_hardening_and_stabilization_guide.md` — **MANDATORY** stabilization rules

## COMMANDS

```bash
# Dev run
./run.sh

# Run full test suite (~4349 tests, ~75s)
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short

# Run a single test file
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py -v

# Run a single test method
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py::TestPrivilegedCommandBuilders::test_dnf_install -v

# Run tests with coverage
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=term-missing --cov-fail-under=80

# Lint
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203

# Type check
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary

# Build RPM
bash scripts/build_rpm.sh

# Version bump (cascades version.py + .spec + pyproject.toml + release notes)
python scripts/bump_version.py
```

## ARCHITECTURE

PyQt6 desktop app — **Python 3.12+**, **Fedora Linux**, **28 feature tabs**, **106 utils modules**, **74% test coverage**.

Three entry modes via `main.py`: GUI (default), `--cli` (subcommands with `--json`), `--daemon` (background scheduler).

**Layer boundaries (strict):**

| Layer | Path | Key rule |
| ------- | ------ | --------- |
| UI | `ui/*_tab.py` | Inherit `BaseTab`, no `subprocess`, no business logic |
| Utils | `utils/*.py` | All `@staticmethod`, return ops tuples, no PyQt6 |
| CLI | `cli/main.py` | Argument parsing only, calls `utils/` |
| Core | `core/executor/` | `BaseActionExecutor` + `ActionResult`, no UI/CLI coupling |

`utils/operations.py` is the shared API — GUI and CLI are consumers only.

**Version sync** — three files must always match, use `scripts/bump_version.py`:

- `loofi-fedora-tweaks/version.py`
- `loofi-fedora-tweaks.spec`
- `pyproject.toml`

## CRITICAL RULES (NEVER VIOLATE)

1. **Never `sudo`** — only `pkexec` via `PrivilegedCommand`
2. **Never hardcode `dnf`** — use `SystemManager.get_package_manager()`
3. **Never `subprocess` in UI** — extract to `utils/`, call via `CommandRunner`
4. **Always unpack PrivilegedCommand** — `binary, args, desc = PrivilegedCommand.dnf(...)`
5. **Always `timeout=N`** on every `subprocess.run()` / `check_output()` call
6. **Never `shell=True`** in subprocess calls
7. **Always branch** on `SystemManager.is_atomic()` for dnf vs rpm-ostree
8. **Audit log** all privileged actions (timestamp, action, params, exit code)
9. **Never hardcode versions in tests** — use dynamic assertions; CI `docs_gate` blocks hardcoded version assertions
10. **Always scaffold release notes** — `bump_version.py` creates `docs/releases/RELEASE-NOTES-vX.Y.Z.md`

## KEY PATTERNS

```python
# PrivilegedCommand — always unpack
from utils.commands import PrivilegedCommand
binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ["pkexec", "dnf", "install", "-y", "package"]
# dnf() adds -y internally — don't duplicate

# Utils class — all @staticmethod, return ops tuples
class FeatureManager:
    @staticmethod
    def clean() -> Tuple[str, List[str], str]:
        pm = SystemManager.get_package_manager()
        if pm == "rpm-ostree":
            return ("pkexec", ["rpm-ostree", "cleanup", "--base"], "Cleaning...")
        return ("pkexec", ["dnf", "clean", "all"], "Cleaning...")

# UI tab — inherit BaseTab (gives self.output_area, self.runner, self.run_command())
from ui.base_tab import BaseTab
class MyTab(BaseTab):
    def __init__(self):
        super().__init__()

# Dangerous ops — require confirm dialog
from ui.confirm_dialog import ConfirmActionDialog
if ConfirmActionDialog.confirm(self, "Delete snapshots", "Cannot be undone"):
    # proceed

# Lazy tab registration in MainWindow._lazy_tab()
"mytab": lambda: __import__("ui.mytab_tab", fromlist=["MyTabTab"]).MyTabTab(),
```

## TESTING PATTERN

```python
"""Tests for utils/module.py"""
import sys, os, unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))
from utils.module import Manager

class TestManager(unittest.TestCase):
    @patch('utils.module.subprocess.run')
    def test_operation_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='OK')
        result = Manager.operation()
        self.assertIsNotNone(result)

    @patch('utils.module.subprocess.run')
    def test_operation_failure(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("fail")
        self.assertEqual(Manager.operation(), [])
```

- `@patch` decorators only — never context managers
- Patch the module-under-test namespace: `'utils.module.subprocess.run'`
- Test both success AND failure paths; both dnf and rpm-ostree paths where applicable
- No root needed — all system calls mocked

## CODE STYLE

- **Logging**: `from utils.log import get_logger` in utils/; `%s` formatting only, never f-strings
- **Imports**: stdlib → third-party → local, alphabetical within groups
- **Type hints**: inline on all public methods; `CommandTuple = Tuple[str, List[str], str]`
- **Docstrings**: Google-style, module-level on every file
- **Naming**: `*_tab.py` → `*Tab`; `utils/*.py` → `*Manager`/`*Ops` with `@staticmethod`

## AGENT SYSTEM

7 Claude Code agents in `.github/claude-agents/` (8 Copilot agents in `.github/agents/*.agent.md`):

- **project-coordinator** — task decomposition, dependency ordering
- **architecture-advisor** — architectural design, module structure
- **backend-builder** — `utils/` modules, system integration
- **code-implementer** — general implementation
- **frontend-integration-builder** — UI tabs, CLI commands, wiring
- **test-writer** — test creation, coverage
- **release-planner** — roadmap and release planning

For complex features: delegate to `project-coordinator`. For simple tasks: act directly.

## STABILIZATION DIRECTIVE

See `.github/instructions/system_hardening_and_stabilization_guide.md`:

- **No new major features** until Phase 1–2 stabilization is complete
- Never expand root-level capability without: validation, audit log, rollback strategy
- All privileged actions must use named actions with parameter schema validation
- If unsure, default to restrictive behavior

## RELEASE RULES

**Current version:** v44.0.0 "Review Gate"

For every vX.Y.0: update `version.py` + `.spec` + `pyproject.toml` (via `bump_version.py`), complete `CHANGELOG.md`, update `README.md`, run full test suite, build and verify RPM.

## OUTPUT FORMAT

1. **Checklist** (done/pending per phase)
2. **Agent Summary** (1 line per agent)
3. **Changes** (max 10 bullets)
4. **Commands** (shell)
5. **Files Changed** (list)

No essays. No filler. Bullet lists only. Max 10 lines per response section.

## TOKEN DISCIPLINE

- Read context files once, reference by name after
- Delegate to agents via Task tool — don't implement inline
- Never re-explain roadmap, architecture, or patterns

## MODEL ROUTING

- **haiku**: docs, formatting, version bumps, git ops, checklists
- **sonnet**: logic, tests, UI, reviews, single-module refactors
- **opus**: multi-file architecture, debugging, plugin design, planning
