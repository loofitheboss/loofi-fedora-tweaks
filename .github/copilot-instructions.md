# Loofi Fedora Tweaks — AI Coding Instructions

> **Version**: v33.0.0 "Bastion" | **Python**: 3.12+ | **Framework**: PyQt6 | **Platform**: Fedora Linux
> See `ARCHITECTURE.md` for canonical architecture, layer rules, tab layout, and critical patterns.
> See `ROADMAP.md` for active development phase.

## Architecture

PyQt6 desktop app for Fedora system management with three entry modes (`loofi-fedora-tweaks/main.py`):
- **GUI** (default): `MainWindow` sidebar with 26 lazy-loaded tabs
- **CLI** (`--cli`): Subcommands in `cli/main.py` with `--json` output support
- **Daemon** (`--daemon`): Background scheduler via `utils/daemon.py`

### Layer Structure
```
ui/*_tab.py      -> GUI tabs (PyQt6 widgets, inherit BaseTab for command tabs)
ui/base_tab.py   -> BaseTab class (shared CommandRunner wiring, output area)
utils/*.py       -> Business logic (100+ modules), system commands, all reusable ops
utils/commands.py -> PrivilegedCommand builder (safe pkexec, no shell strings)
utils/errors.py  -> Error hierarchy (LoofiError, DnfLockedError, etc.)
cli/main.py      -> CLI that calls into utils/ (never into ui/)
config/          -> apps.json (app catalog), polkit policy, systemd service
plugins/         -> Third-party extensions via LoofiPlugin ABC
```

**Key rule:** `utils/operations.py` is the shared operations layer. Both GUI and CLI call into it. Never put `subprocess` calls directly in UI code — always extract to a `utils/` module.

## Tab Layout (26 tabs)

See `ARCHITECTURE.md` § Tab Layout for the full 26-tab table.
Consolidated tabs use `QTabWidget` for sub-navigation within the tab.

## Critical Patterns

### BaseTab Class (v10.0)
All command-executing tabs should inherit from `BaseTab`:
```python
from ui.base_tab import BaseTab

class MyTab(BaseTab):
    def __init__(self):
        super().__init__()
        # Provides: self.output_area, self.runner (CommandRunner),
        # self.run_command(), self.append_output(), self.add_section(),
        # self.add_output_section()
```

### PrivilegedCommand Builder (v10.0)
Use `PrivilegedCommand` for safe pkexec operations — returns a `Tuple[str, List[str], str]` (binary, args, description). **Always unpack before passing to subprocess.run()**:
```python
from utils.commands import PrivilegedCommand

# Returns: ("pkexec", ["dnf", "install", "-y", "package"], "Installing package...")
binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ["pkexec", "dnf", "install", "-y", "package"]

# Returns: ("pkexec", ["systemctl", "restart", "service"], "Restart system service...")
binary, args, _ = PrivilegedCommand.systemctl("restart", "service")
cmd = [binary] + args  # ["pkexec", "systemctl", "restart", "service"]
```
⚠️ **Never pass the raw tuple to subprocess.run()** — it will crash with TypeError.
Auto-detects Atomic vs Traditional for dnf/rpm-ostree.
`dnf()` already adds `-y` internally — do not pass `-y` as a package arg.

### Error Framework (v10.0)
Use typed exceptions from `utils/errors.py`:
```python
from utils.errors import LoofiError, DnfLockedError, PrivilegeError, CommandFailedError

# Each has: code, hint, recoverable attributes
raise DnfLockedError()  # code="DNF_LOCKED", hint="Wait for other package operations..."
```

### Hardware Profiles (v10.0)
`utils/hardware_profiles.py` auto-detects hardware via /sys/class/dmi/id/:
```python
from utils.hardware_profiles import detect_hardware_profile, get_profile_label
profile = detect_hardware_profile()  # e.g., "hp-elitebook"
label = get_profile_label(profile)   # e.g., "HP EliteBook"
```

### Operations Tuple
Most operations return `Tuple[str, List[str], str]` — (command, args, description). Example:
```python
# In utils/operations.py
@staticmethod
def clean_dnf_cache() -> Tuple[str, List[str], str]:
    pm = SystemManager.get_package_manager()
    if pm == "rpm-ostree":
        return ("pkexec", ["rpm-ostree", "cleanup", "--base"], "Cleaning rpm-ostree base...")
    return ("pkexec", ["dnf", "clean", "all"], "Cleaning DNF cache...")
```
CLI executes these via `run_operation()` in `cli/main.py`. GUI tabs use `CommandRunner` (see below).

### Atomic/Immutable Fedora Support
`SystemManager.is_atomic()` detects OSTree systems (Silverblue, Kinoite). All package operations must branch:
- Traditional: `dnf install -y ...`
- Atomic: `rpm-ostree install ...`

Always use `SystemManager.get_package_manager()` from `utils/system.py` — never hardcode `dnf`.

### Privilege Escalation
Use `pkexec` (Polkit) for root operations — **never `sudo`**. Policy at `config/org.loofi.fedora-tweaks.policy`. Prefer `PrivilegedCommand` builder over raw command arrays.

### CommandRunner (Async GUI Commands)
`utils/command_runner.py` wraps `QProcess` for non-blocking command execution in UI tabs. Signals: `output_received`, `finished`, `error_occurred`, `progress_update`. Auto-detects Flatpak sandbox (`/.flatpak-info`) and wraps commands with `flatpak-spawn --host`. Usage pattern in tabs:
```python
from utils.command_runner import CommandRunner
self.runner = CommandRunner()
self.runner.finished.connect(self.on_done)
self.runner.run_command("pkexec", ["dnf", "update", "-y"])
```

### Lazy Tab Loading
Tabs load on first view via `ui/lazy_widget.py`. Register in `MainWindow._lazy_tab()` loaders dict:
```python
"mytab": lambda: __import__("ui.mytab_tab", fromlist=["MyTabTab"]).MyTabTab(),
```
Only `DashboardTab` and `SystemInfoTab` are eagerly imported.

### Safety & History
- `utils/safety.py` `SafetyManager.confirm_action()` prompts snapshot creation (Timeshift/Snapper) before risky ops
- `utils/history.py` `HistoryManager.log_change()` records actions with undo commands (max 50)
- Always offer snapshot + log undo commands for destructive operations

## Adding a New Feature

1. Create `utils/newthing.py` — all business logic, `@staticmethod` methods returning operations tuples
2. Create `ui/newthing_tab.py` — inherit from `BaseTab`, use `self.run_command()` for async ops
3. Register in `MainWindow._lazy_tab()` loaders dict + `add_page()` with emoji icon
4. Add CLI subcommand in `cli/main.py` calling utils directly (with `--json` support)
5. Use `self.tr("...")` for all user-visible strings (i18n)
6. Add tests in `tests/` using `@patch` decorators, mock all system calls
7. Use `PrivilegedCommand` for any pkexec operations
8. Use typed errors from `utils/errors.py` for error handling

## Version Management

Two files must stay in sync when bumping version:
- `loofi-fedora-tweaks/version.py` — `__version__`, `__version_codename__` (source of truth)
- `loofi-fedora-tweaks.spec` — `Version:`

`build_rpm.sh` reads version dynamically from `version.py`.

## Build & Run

```bash
./run.sh                                              # Dev run (needs .venv with PyQt6)
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v  # Run tests (3953 passing)
./build_rpm.sh                                        # Build RPM -> rpmbuild/RPMS/noarch/
```

## Testing Conventions

- Framework: `unittest` + `unittest.mock` (158 test files, 3953+ tests)
- **All system calls must be mocked** — tests run without root, without real packages
- See `ARCHITECTURE.md` § Testing Rules for full details
- Use `@patch` decorators, not context managers
- Verify both success and failure paths

## CI/CD

- `.github/workflows/ci.yml` — Runs on every push/PR: lint (flake8), test (pytest), build (rpmbuild in Fedora 43 container)
- `.github/workflows/auto-release.yml` — Single release publisher: master auto-tag + tag release publish

## Conventions

- **Naming:** `ui/*_tab.py` -> `*Tab` class; `utils/*.py` -> `*Manager`/`*Ops` with `@staticmethod`
- **QSS theming:** `assets/modern.qss`; use `setObjectName()` for targeted styling
- **Config storage:** User data at `~/.config/loofi-fedora-tweaks/`
- **App catalog:** `config/apps.json` — entries have `name`, `desc`, `cmd`, `args`, `check_cmd` fields; fetched remotely via `utils/remote_config.py` with local fallback
- **Plugin system:** Extend `LoofiPlugin` ABC from `utils/plugin_base.py`, place in `plugins/<name>/plugin.py`
- **Dependencies:** `DependencyDoctor` (`ui/doctor.py`) runs at startup to check for critical tools (`dnf`, `pkexec`)
- **First-run:** `ui/wizard.py` runs on first launch, saves profile to `~/.config/loofi-fedora-tweaks/profile.json`
- **Command palette:** `ui/command_palette.py` activated via Ctrl+K shortcut

## MCP Server Integration

The repository uses GitHub's MCP (Model Context Protocol) server for AI-assisted workflows:

- **VS Code config**: `.vscode/mcp.json`
- **Copilot CLI config**: `.copilot/mcp-config.json`
- **Toolsets**: `pull_requests`, `code_security`, `secret_protection`, `issues`, `repos`

### Automated Bot Workflows

| Workflow | Trigger | What It Does |
|----------|---------|--------------|
| `pr-security-bot.yml` | PR to master | Bandit + pip-audit + Trivy + detect-secrets scan, posts summary comment |
| `bot-automation.yml` | PR/Issue opened, weekly cron | Auto-label by file path/keywords, stale cleanup |
| `auto-merge-dependabot.yml` | Dependabot PR | Auto-approve + auto-merge patch-level dependency updates |

### Security Scan Details

- Bandit skips: B404, B603, B602 (subprocess-related, handled by PrivilegedCommand pattern)
- Scan scope: `loofi-fedora-tweaks/` directory only
- Reports uploaded as workflow artifacts on every PR
