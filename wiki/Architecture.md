# Architecture

Technical architecture and design patterns for Loofi Fedora Tweaks.

---

## Project Directory Structure

```text
loofi-fedora-tweaks/          # Application root (on PYTHONPATH)
├── main.py                   # Entry point — GUI (default), CLI (--cli), Daemon (--daemon)
├── version.py                # __version__, __version_codename__, __app_name__
├── ui/                       # PyQt6 widgets — 28 feature tabs + base class
│   ├── base_tab.py           # BaseTab ABC — shared CommandRunner wiring, output area
│   ├── *_tab.py              # Feature tabs (inherit BaseTab for command tabs)
│   ├── main_window.py        # MainWindow with sidebar + lazy-loaded tab stack
│   ├── lazy_widget.py        # Lazy tab loader
│   ├── wizard.py             # First-run wizard
│   ├── doctor.py             # DependencyDoctor startup check
│   ├── command_palette.py    # Ctrl+K command palette
│   └── confirm_dialog.py     # ConfirmActionDialog for dangerous ops
├── utils/                    # Business logic — 105 modules
│   ├── commands.py           # PrivilegedCommand builder (pkexec, never sudo)
│   ├── command_runner.py     # CommandRunner (QProcess async wrapper)
│   ├── system.py             # SystemManager (is_atomic, get_package_manager)
│   ├── operations.py         # Shared operations layer (API for GUI + CLI)
│   ├── errors.py             # Error hierarchy (LoofiError, DnfLockedError, etc.)
│   ├── safety.py             # SafetyManager — snapshot prompts before risky ops
│   ├── history.py            # HistoryManager — action logging with undo
│   ├── hardware_profiles.py  # Auto-detect hardware via /sys/class/dmi/
│   ├── daemon.py             # Background scheduler (--daemon mode)
│   └── remote_config.py      # Remote config fetch with local fallback
├── cli/
│   └── main.py               # CLI subcommands with --json output (calls utils/)
├── core/
│   ├── executor/             # BaseActionExecutor + ActionResult
│   └── plugins/              # Plugin engine (LoofiPlugin ABC)
├── services/                 # Service layer (future expansion)
├── config/                   # apps.json, polkit policy, systemd unit
├── assets/                   # modern.qss, icons, resources
├── agents/                   # Agent runtime (in-app AI orchestration)
├── api/                      # REST API server
├── web/                      # Web dashboard
├── plugins/                  # Third-party plugin directory
└── resources/                # Static resources

tests/                        # 174 test files, 4349 tests (74% coverage)
scripts/                      # Build, workflow, CI scripts
config/                       # Global config templates
docs/                         # User guide, release notes, checklists
.github/                      # CI, agents, instructions, workflows
.workflow/                    # Pipeline specs, reports, race-lock
.codex/                       # Codex skills (plan, implement, test, release, validate)
completions/                  # Shell completions (bash, zsh)
```

---

## Layer Rules (STRICT)

These rules **must never be violated** to maintain clean separation of concerns:

| Layer | Path | Allowed | Forbidden |
|-------|------|---------|-----------|
| **UI** | `ui/*_tab.py` | PyQt6 widgets, signals, BaseTab | `subprocess`, business logic, direct system calls |
| **Utils** | `utils/*.py` | Business logic, subprocess, system calls | `import PyQt6`, UI references |
| **CLI** | `cli/main.py` | Argument parsing, calls utils/ | `import ui`, PyQt6 |
| **Core** | `core/executor/` | Action abstraction | Direct UI/CLI coupling |

**Key rule**: `utils/operations.py` is the shared API. GUI and CLI are consumers only.

---

## Three Entry Modes

| Mode | Flag | Module | Purpose |
|------|------|--------|---------|
| **GUI** | (default) | `main.py` → `MainWindow` | PyQt6 desktop app with 28 lazy-loaded tabs |
| **CLI** | `--cli` | `cli/main.py` | Subcommands with `--json` output |
| **Daemon** | `--daemon` | `utils/daemon.py` | Background scheduler |

---

## Critical Code Patterns

### 1. PrivilegedCommand Builder

**Always unpack the tuple before passing to subprocess:**

```python
from utils.commands import PrivilegedCommand

# Returns: ("pkexec", ["dnf", "install", "-y", "package"], "Installing...")
binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ["pkexec", "dnf", "install", "-y", "package"]

# ⚠️ NEVER pass the raw tuple to subprocess.run()
subprocess.run(cmd, timeout=60)  # ✅ Correct
subprocess.run((binary, args, desc), timeout=60)  # ❌ Wrong — will crash
```

**Features:**
- Auto-detects Atomic (rpm-ostree) vs Traditional (dnf)
- `dnf()` adds `-y` internally — don't duplicate
- Returns `Tuple[str, List[str], str]` — binary, args, description

### 2. Operations Tuple Pattern

Most operations return `Tuple[str, List[str], str]`:

```python
@staticmethod
def clean_cache() -> Tuple[str, List[str], str]:
    pm = SystemManager.get_package_manager()
    if pm == "rpm-ostree":
        return ("pkexec", ["rpm-ostree", "cleanup", "--base"], "Cleaning...")
    return ("pkexec", ["dnf", "clean", "all"], "Cleaning...")
```

CLI executes these via `run_operation()`. GUI tabs use `CommandRunner`.

### 3. BaseTab Class for UI Tabs

All command-executing tabs inherit from `BaseTab`:

```python
from ui.base_tab import BaseTab

class MyTab(BaseTab):
    def __init__(self):
        super().__init__()
        # Provides: self.output_area, self.runner (CommandRunner),
        # self.run_command(), self.append_output(), self.add_section()
```

### 4. CommandRunner (Async GUI)

Never block the GUI thread with synchronous subprocess calls:

```python
from utils.command_runner import CommandRunner

self.runner = CommandRunner()
self.runner.finished.connect(self.on_done)
self.runner.run_command("pkexec", ["dnf", "update", "-y"])
```

**Features:**
- Signals: `output_received`, `finished`, `error_occurred`, `progress_update`
- Auto-detects Flatpak sandbox and wraps with `flatpak-spawn --host`
- Configurable timeout (default 5 minutes)
- Terminate → kill escalation

### 5. Error Framework

Use typed exceptions from `utils/errors.py`:

```python
from utils.errors import LoofiError, DnfLockedError, CommandFailedError

raise DnfLockedError(hint="Package manager is busy.")

# Each error has: code, hint, recoverable attributes
```

**Available errors:**
- `LoofiError` — Base error class
- `DnfLockedError` — Package manager locked
- `CommandFailedError` — Command execution failed
- `PrivilegeError` — Privilege escalation failed
- `ValidationError` — Parameter validation failed
- `CommandTimeoutError` — Operation timed out

### 6. Confirm Dialog for Dangerous Ops

```python
from ui.confirm_dialog import ConfirmActionDialog

if ConfirmActionDialog.confirm(self, "Delete snapshots", "Cannot be undone"):
    # User confirmed, proceed with action
```

**Features:**
- Risk badges (LOW/MEDIUM/HIGH)
- Command preview section
- Per-action "don't ask again" option

### 7. Atomic Fedora Detection

**Never hardcode `dnf`** — always use package manager detection:

```python
from utils.system import SystemManager

pm = SystemManager.get_package_manager()  # "dnf" or "rpm-ostree"

if SystemManager.is_atomic():
    # Use rpm-ostree commands
else:
    # Use dnf commands
```

### 8. Privilege Escalation

**Only `pkexec`** — never `sudo`:

```python
# ✅ Correct
PrivilegedCommand.systemctl("restart", "service")

# ❌ Wrong
["sudo", "systemctl", "restart", "service"]
```

Polkit policies are in `config/` directory (7 purpose-scoped files).

### 9. Lazy Tab Loading

Tabs load on first view via `ui/lazy_widget.py`:

```python
# In MainWindow._lazy_tab():
"mytab": lambda: __import__("ui.mytab_tab", fromlist=["MyTabTab"]).MyTabTab(),
```

Only `DashboardTab` and `SystemInfoTab` are eagerly imported.

### 10. Safety & History

```python
from utils.safety import SafetyManager
from utils.history import HistoryManager

# Prompt for snapshot before risky operation
SafetyManager.confirm_action("delete_logs", requires_snapshot=True)

# Log action with undo command
HistoryManager.log_change(
    action="delete_logs",
    description="Deleted system logs",
    undo_commands=[("restore_logs", [], "Restore logs")]
)
```

---

## Naming Conventions

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

---

## Version Management

**Three files must stay in sync** (use `scripts/bump_version.py` to update all):

1. `loofi-fedora-tweaks/version.py` — `__version__`, `__version_codename__`
2. `loofi-fedora-tweaks.spec` — `Version:`
3. `pyproject.toml` — `version`

**Never edit these files manually** — use the version bump script.

---

## Build & Run Commands

```bash
# Run from source (development)
./run.sh

# Run tests
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v

# Lint
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203

# Type check
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary

# Security scan
bandit -r loofi-fedora-tweaks/ -ll -ii --skip B103,B104,B108,B310,B404,B603,B602

# Build RPM
bash scripts/build_rpm.sh
```

---

## Configuration & Conventions

- **Config directory**: `~/.config/loofi-fedora-tweaks/`
- **App catalog**: `config/apps.json` (fetched remotely via `utils/remote_config.py`)
- **QSS themes**: `assets/modern.qss` (dark), `assets/light.qss` (light)
- **i18n**: `self.tr("...")` for all user-visible strings
- **Plugins**: Extend `LoofiPlugin` ABC from `utils/plugin_base.py`
- **Tab registration**: `MainWindow._lazy_tab()` loaders + `add_page()` with emoji icon

---

## Adding a New Feature

Follow this 6-step checklist:

1. **Logic**: Create `utils/new_feature.py` — `@staticmethod` methods returning operations tuples
2. **UI**: Create `ui/new_feature_tab.py` — inherit `BaseTab`, use `self.run_command()`
3. **CLI**: Add subcommand in `cli/main.py` with `--json` support
4. **Tests**: Create `tests/test_new_feature.py` — mock all system calls, test both paths
5. **Register**: Add lazy loader in `MainWindow._lazy_tab()` + `add_page()` with icon
6. **Docs**: Update `CHANGELOG.md`, `README.md`, release notes

---

## Plugin Architecture

Plugins live in `plugins/<name>/` with this structure:

```
plugins/
  my-plugin/
    __init__.py
    plugin.json      # Manifest
    plugin.py        # LoofiPlugin subclass
```

**Plugin manifest** (`plugin.json`):

```json
{
  "name": "My Plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Plugin description",
  "permissions": ["network", "filesystem"],
  "min_app_version": "40.0.0",
  "icon": "🔌"
}
```

**Plugin class**:

```python
from utils.plugin_base import LoofiPlugin

class MyPlugin(LoofiPlugin):
    @property
    def info(self):
        return PluginInfo(name="My Plugin", version="1.0.0", ...)
    
    def create_widget(self):
        # Return QWidget for tab
    
    def get_cli_commands(self):
        # Return dict of CLI commands
    
    def on_load(self):
        # Initialize
    
    def on_unload(self):
        # Cleanup
```

See [Plugin Development](Plugin-Development) for full guide.

---

## Next Steps

- [Plugin Development](Plugin-Development) — Build custom plugins
- [Security Model](Security-Model) — Understand privilege system
- [Contributing](Contributing) — Development workflow and standards
- [Testing](Testing) — Test suite structure and patterns
