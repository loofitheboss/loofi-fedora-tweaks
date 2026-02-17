# Loofi Fedora Tweaks — Copilot Instructions

> **Python 3.12+** | **PyQt6** | **Fedora Linux**
> Canonical references: `ARCHITECTURE.md` (structure + layer rules), `ROADMAP.md` (scope)

## Build, Test, Lint

```bash
# Preferred: use Justfile (install: sudo dnf install just)
just test                    # Full test suite
just test-file test_commands # Single test file
just test-method test_commands.py::TestPrivilegedCommandBuilders::test_dnf_install  # Single method
just test-coverage           # Tests + coverage (min 75%)
just lint                    # flake8 (max-line-length=150, ignore E501,W503,E402,E722,E203)
just typecheck               # mypy
just verify                  # lint + typecheck + tests + coverage
just run                     # Dev run (GUI)
just build-rpm               # Build RPM package

# Without just (always set PYTHONPATH):
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py -v
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py::TestPrivilegedCommandBuilders::test_dnf_install -v
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary
```

## Architecture

PyQt6 desktop app for Fedora system management with three entry modes (`loofi-fedora-tweaks/main.py`):
- **GUI** (default): `MainWindow` sidebar with 28 lazy-loaded tabs
- **CLI** (`--cli`): Subcommands in `cli/main.py` with `--json` output
- **Daemon** (`--daemon`): Background scheduler via `utils/daemon.py`

### Layer Boundaries (strict — enforced by CI)

| Layer | Path | Allowed | Forbidden |
|-------|------|---------|-----------|
| **UI** | `ui/*_tab.py` | PyQt6 widgets, inherit `BaseTab` | `subprocess`, business logic |
| **Utils** | `utils/*.py` | Business logic, `@staticmethod`, subprocess | `import PyQt6` |
| **CLI** | `cli/main.py` | Argument parsing, calls `utils/` | `import ui`, PyQt6 |
| **Core** | `core/executor/` | `BaseActionExecutor` + `ActionResult` | Direct UI/CLI coupling |

`utils/operations.py` is the shared API — GUI and CLI are consumers only.

## Critical Rules

1. **Never `sudo`** — only `pkexec` via `PrivilegedCommand`
2. **Never hardcode `dnf`** — use `SystemManager.get_package_manager()`
3. **Never subprocess in UI** — extract to `utils/`, call via `CommandRunner`
4. **Always unpack PrivilegedCommand** — `binary, args, desc = PrivilegedCommand.dnf(...)`; never pass the raw tuple to `subprocess.run()`
5. **Always `timeout=N`** on every `subprocess.run()` / `check_output()`
6. **Never `shell=True`** in subprocess calls
7. **Always branch on `SystemManager.is_atomic()`** for dnf vs rpm-ostree
8. **Audit log** all privileged actions (timestamp, action, params, exit code)
9. **Never hardcode versions in tests** — use dynamic assertions; CI `docs_gate` blocks hardcoded version assertions
10. **Version sync** — `version.py`, `.spec`, `pyproject.toml` must match (use `scripts/bump_version.py`)

## Key Patterns

### PrivilegedCommand
```python
from utils.commands import PrivilegedCommand

binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ["pkexec", "dnf", "install", "-y", "package"]
# dnf() adds -y internally — don't duplicate
# Auto-detects Atomic (rpm-ostree) vs Traditional (dnf)

binary, args, _ = PrivilegedCommand.systemctl("restart", "service")
```

### Utils Module Pattern
```python
class FeatureManager:
    @staticmethod
    def operation() -> Tuple[str, List[str], str]:
        pm = SystemManager.get_package_manager()
        if pm == "rpm-ostree":
            return ("pkexec", ["rpm-ostree", "cleanup", "--base"], "Cleaning...")
        return ("pkexec", ["dnf", "clean", "all"], "Cleaning...")
```

### UI Tab Pattern
```python
from ui.base_tab import BaseTab

class MyTab(BaseTab):
    def __init__(self):
        super().__init__()
        # Provides: self.output_area, self.runner (CommandRunner),
        # self.run_command(), self.append_output(), self.add_section()
```

### Error Handling
```python
from utils.errors import LoofiError, DnfLockedError, CommandFailedError
# Each has: code, hint, recoverable attributes
raise DnfLockedError()  # code="DNF_LOCKED", hint="Wait for other package operations..."

# Subprocess error pattern:
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
except (subprocess.SubprocessError, OSError) as e:
    logger.debug("Descriptive msg: %s", e)
    return []  # safe default: [], "", None, False
```

### CommandRunner (Async GUI Commands)
`utils/command_runner.py` wraps `QProcess` for non-blocking execution. Signals: `output_received`, `finished`, `error_occurred`. Auto-detects Flatpak sandbox.
```python
self.runner = CommandRunner()
self.runner.finished.connect(self.on_done)
self.runner.run_command("pkexec", ["dnf", "update", "-y"])
```

### Lazy Tab Loading
Register in `MainWindow._lazy_tab()` loaders dict:
```python
"mytab": lambda: __import__("ui.mytab_tab", fromlist=["MyTabTab"]).MyTabTab(),
```

## Code Style

- **Imports**: stdlib → third-party → local (alphabetical within groups, blank line between)
- **Logging**: `from utils.log import get_logger` in utils/; `%s` formatting only (never f-strings in log calls)
- **Type hints**: inline on all public methods; `CommandTuple = Tuple[str, List[str], str]`
- **Docstrings**: Google-style, module-level docstring on every file
- **Naming**: `*_tab.py` → `*Tab` class; `utils/*.py` → `*Manager`/`*Ops` with `@staticmethod`; test classes `Test*`; test methods `test_what_scenario`

## Testing

Framework: `unittest` + `unittest.mock` (~4349 tests, 200 files, min 75% coverage).

```python
"""Tests for utils/module.py"""
import unittest, sys, os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))
from utils.module import Manager

class TestManager(unittest.TestCase):
    @patch('utils.module.subprocess.run')
    def test_operation_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='OK')
        result = Manager.operation()
        self.assertIsNotNone(result)
```

- **`@patch` decorators only** — never context managers
- Patch the module-under-test namespace: `'utils.module.subprocess.run'`
- Test both success AND failure paths; both dnf and rpm-ostree where applicable
- All system calls mocked — no root needed

## Adding a New Feature

1. `utils/newthing.py` — business logic, `@staticmethod`, return operations tuples
2. `ui/newthing_tab.py` — inherit `BaseTab`, use `self.run_command()`
3. Register in `MainWindow._lazy_tab()` + `add_page()` with emoji icon
4. CLI subcommand in `cli/main.py` (with `--json` support)
5. `self.tr("...")` for all user-visible strings (i18n)
6. Tests in `tests/` with `@patch`, mock all system calls
7. `PrivilegedCommand` for pkexec ops, typed errors from `utils/errors.py`
8. Dangerous ops: use `ConfirmActionDialog.confirm()` + `SafetyManager` snapshot prompt

## Version Management

Three files must stay in sync — use `scripts/bump_version.py` (also scaffolds release notes):
- `loofi-fedora-tweaks/version.py` (source of truth)
- `loofi-fedora-tweaks.spec`
- `pyproject.toml`

## CI/CD

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR | flake8 + pytest + rpmbuild (Fedora 43 container) |
| `auto-release.yml` | Master push / tag | Auto-tag + release publish |
| `pr-security-bot.yml` | PR to master | Bandit (skips B404/B603/B602) + pip-audit + detect-secrets |
| `copr-publish.yml` | Release | SRPM → Fedora COPR |

## Conventions

- **Config storage**: `~/.config/loofi-fedora-tweaks/`
- **QSS theming**: `assets/modern.qss`; use `setObjectName()` for targeted styling
- **App catalog**: `config/apps.json` with remote fetch + local fallback
- **Plugins**: Extend `LoofiPlugin` ABC, place in `plugins/<name>/plugin.py`
- **First-run**: `ui/wizard.py` saves profile to `~/.config/loofi-fedora-tweaks/profile.json`
- **Command palette**: `ui/command_palette.py` via Ctrl+K
- **Privilege escalation**: `pkexec` with polkit policy at `config/org.loofi.fedora-tweaks.policy`
- **Atomic Fedora**: `SystemManager.is_atomic()` detects OSTree (Silverblue, Kinoite); all package ops must branch

## Agent System

For complex multi-step tasks, delegate to specialized agents. Copilot agents (`.github/agents/`) and Claude agents (`.github/claude-agents/`) mirror each other:

| Copilot Agent | Claude Agent | Role |
|---------------|-------------|------|
| **Arkitekt** | architecture-advisor | Feature design, code organization, module structure |
| **Builder** | backend-builder | `utils/` modules, dataclasses, system integration |
| **CodeGen** | code-implementer | General implementation, bug fixes |
| **Sculptor** | frontend-integration-builder | UI tabs, CLI commands, MainWindow wiring |
| **Guardian / Test** | test-writer | Test creation, mock strategy, coverage |
| **Manager** | project-coordinator | Task decomposition, multi-step orchestration |
| **Planner** | release-planner | Release coordination, version bumps, roadmap |

**Agent memory** persists in `.github/agent-memory/<agent>/MEMORY.md` — accumulated architectural decisions and patterns.

**Delegation order for new features:** Arkitekt (design) → Builder (utils) → Sculptor (UI/CLI) → Test (tests) → Manager (coordination)

## Workflow Pipeline

7-phase release pipeline managed by `scripts/workflow_runner.py`:

```
Plan → Design → Build → Test → Doc → Package → Release
```

```bash
# Single phase
python3 scripts/workflow_runner.py --phase plan --target-version v45.0

# Full pipeline
python3 scripts/workflow_runner.py --phase all --target-version v45.0

# Dry run
python3 scripts/workflow_runner.py --phase design --target-version v45.0 --dry-run
```

- **Race lock** (`.workflow/specs/.race-lock.json`): prevents version mixing across phases
- **Writer lock**: single-writer mutations across AI assistants (`--mode write` vs `--mode review`)
- **Artifacts**: specs in `.workflow/specs/`, reports in `.workflow/reports/`
- **Model routing**: `.github/workflow/model-router.toml` routes tasks to haiku/sonnet/opus
- **Agent sync**: `scripts/sync_ai_adapters.py` keeps Claude/Copilot agent adapters in sync with canonical `.github/` definitions

### Model Routing

`.github/workflow/model-router.toml` maps phases to intelligence tiers:

| Tier | Model | Phases |
|------|-------|--------|
| **Brain** | gpt-5.3-codex / opus | Plan, Design (bad decisions are expensive) |
| **Labor** | gpt-4o / sonnet | Build, Test (strong coding/testing) |
| **Labor-Light** | gpt-4o-mini / haiku | Doc, Package, Release (low-risk text) |

### Phase Prompts

Per-phase prompt templates in `.github/workflow/prompts/`:
- `plan.md` — Task decomposition (coordinator role)
- `design.md` — Architecture blueprint + pattern enforcement
- `build.md` — Implementation in dependency order
- `test.md` — unittest + @patch, 80%+ coverage target
- `document.md` — CHANGELOG, README, release notes
- `package.md` — Version alignment validation, build verification
- `release.md` — Pre-flight checklist, git tag/branch commands

## Skills (Codex)

Reusable skill definitions in `.codex/skills/` map 1:1 to workflow phases. Each `SKILL.md` contains steps, output format, rules, and verification commands:

| Skill | Phase | Purpose |
|-------|-------|---------|
| `plan` | P1 | Decompose ACTIVE version from ROADMAP.md into atomic tasks |
| `design` | P2 | Create architecture specs before implementation |
| `implement` | P3 | Execute tasks in dependency order, mark done |
| `test` | P4 | Write/run tests for all changed files (80%+ coverage) |
| `validate` | — | Check release readiness (version, tests, lint, docs) |
| `doc` | P5 | Update CHANGELOG, README, release notes |
| `package` | P6 | Build and verify RPM/Flatpak/AppImage/sdist |
| `release` | P5-P7 | Full release execution (doc + package + tag) |

### Codex Profiles (`.codex/config.toml`)

| Profile | Model | Use case |
|---------|-------|----------|
| `fast` | gpt-4o-mini | Docs, formatting, version bumps |
| `balanced` | gpt-4o | Logic, tests, UI, reviews |
| `power` | gpt-5.3-codex | Multi-file architecture, debugging |
| `planner` | gpt-5.3-codex | Planning/architecture artifacts |
| `builder` | gpt-4o | Implementation tasks |
| `scribe` | gpt-4o-mini | Release documentation |

### Adapter Manifest

`.codex/adapter-manifest.json` tracks canonical source locations:
- Canonical agents: `.github/` (copilot agents + claude agents)
- Workflow prompts: `.github/workflow/prompts/`
- Runtime artifacts: `.workflow/` (specs, reports, archive)
- Sync tool: `scripts/sync_ai_adapters.py` propagates changes from canonical → adapters

## MCP Servers

Configured in `.copilot/mcp-config.json` for Copilot CLI, `.vscode/mcp.json` for VS Code, `.mcp.json` for other tools:

| Server | Purpose |
|--------|---------|
| **github** | GitHub API (PRs, issues, security, repos) |
| **context7** | Library documentation lookup |
| **fetch** | Web page fetching |
| **loofi-workflow** | Workflow pipeline management (plan/build/test/release phases) |
| **loofi-agent-sync** | Agent adapter synchronization across AI tools |
