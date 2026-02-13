# ARCHITECTURE.md — Loofi Fedora Tweaks

> **Canonical architecture reference.** All agent and instruction files MUST reference this document
> instead of duplicating architecture details. This file is updated when structure changes.
>
> **Version**: 33.0.0 "Bastion" | **Python**: 3.12+ | **Framework**: PyQt6 | **Platform**: Fedora Linux

## Project Structure

```
loofi-fedora-tweaks/          # Application root (on PYTHONPATH)
├── main.py                   # Entry point — GUI (default), CLI (--cli), Daemon (--daemon)
├── version.py                # __version__, __version_codename__, __app_name__
├── ui/                       # PyQt6 widgets — 26 tabs
│   ├── base_tab.py           # BaseTab ABC — shared CommandRunner wiring, output area
│   ├── *_tab.py              # Feature tabs (inherit BaseTab for command tabs)
│   ├── main_window.py        # MainWindow with sidebar + lazy-loaded tab stack
│   ├── lazy_widget.py        # Lazy tab loader
│   ├── wizard.py             # First-run wizard
│   ├── doctor.py             # DependencyDoctor startup check
│   ├── command_palette.py    # Ctrl+K command palette
│   └── confirm_dialog.py     # ConfirmActionDialog for dangerous ops
├── utils/                    # Business logic — 100+ modules
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

tests/                        # 158 test files, 3953+ tests (76.8% coverage)
scripts/                      # Build, workflow, CI scripts
config/                       # Global config templates
docs/                         # User guide, release notes, checklists
.github/                      # CI, agents, instructions, workflows
.workflow/                    # Pipeline specs, reports, race-lock
.codex/                       # Codex skills (plan, implement, test, release, validate)
completions/                  # Shell completions (bash, zsh)
```

## Three Entry Modes

| Mode | Flag | Module | Purpose |
|------|------|--------|---------|
| **GUI** | (default) | `main.py` → `MainWindow` | PyQt6 desktop app with 26 lazy-loaded tabs |
| **CLI** | `--cli` | `cli/main.py` | Subcommands with `--json` output |
| **Daemon** | `--daemon` | `utils/daemon.py` | Background scheduler |

## Layer Rules (STRICT)

| Layer | Path | Allowed | Forbidden |
|-------|------|---------|-----------|
| **UI** | `ui/*_tab.py` | PyQt6 widgets, signals, BaseTab | `subprocess`, business logic, `import utils` for ops |
| **Utils** | `utils/*.py` | Business logic, subprocess, system calls | `import PyQt6`, UI references |
| **CLI** | `cli/main.py` | Argument parsing, calls utils/ | `import ui`, PyQt6 |
| **Core** | `core/executor/` | Action abstraction | Direct UI/CLI coupling |

**Key rule**: `utils/operations.py` is the shared API. GUI and CLI are consumers only.

## Tab Layout (26 Tabs)

| # | Tab | File | Consolidates |
|---|-----|------|-------------|
| 1 | Home | `dashboard_tab.py` | Dashboard |
| 2 | System Info | `system_info_tab.py` | System details |
| 3 | System Monitor | `monitor_tab.py` | Performance + Processes |
| 4 | Maintenance | `maintenance_tab.py` | Updates + Cleanup + Overlays |
| 5 | Hardware | `hardware_tab.py` | Hardware + HP Tweaks + Bluetooth |
| 6 | Software | `software_tab.py` | Apps + Repos |
| 7 | Security & Privacy | `security_tab.py` | Security + Privacy |
| 8 | Network | `network_tab.py` | Connections + DNS + Privacy + Monitoring |
| 9 | Gaming | `gaming_tab.py` | Gaming setup |
| 10 | Desktop | `desktop_tab.py` | Director + Theming |
| 11 | Development | `development_tab.py` | Containers + Developer tools |
| 12 | AI Lab | `ai_enhanced_tab.py` | AI features |
| 13 | Automation | `automation_tab.py` | Scheduler + Replicator + Pulse |
| 14 | Community | `community_tab.py` | Presets + Marketplace |
| 15 | Diagnostics | `diagnostics_tab.py` | Watchtower + Boot |
| 16 | Virtualization | `virtualization_tab.py` | VMs + VFIO + Disposable |
| 17 | Loofi Link | `mesh_tab.py` | Mesh + Clipboard + File Drop |
| 18 | State Teleport | `teleport_tab.py` | Workspace Capture/Restore |
| 19 | Performance | `performance_tab.py` | Auto-Tuner |
| 20 | Snapshots | `snapshot_tab.py` | Snapshot Timeline |
| 21 | Logs | `logs_tab.py` | Smart Log Viewer |
| 22 | Storage | `storage_tab.py` | Disks + Mounts + SMART |
| 23 | Health Timeline | `health_timeline_tab.py` | System health over time |
| 24 | Profiles | `profiles_tab.py` | User profiles management |
| 25 | Agents | `agents_tab.py` | AI agent management |
| 26 | Settings | `settings_tab.py` | App settings |

Consolidated tabs use `QTabWidget` for sub-navigation within the tab.

## Critical Patterns

### 1. PrivilegedCommand (ALWAYS unpack)

```python
from utils.commands import PrivilegedCommand

binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ["pkexec", "dnf", "install", "-y", "package"]
# ⚠️ Never pass the raw tuple to subprocess.run()
```

- Returns `Tuple[str, List[str], str]` — binary, args, description
- Auto-detects Atomic (rpm-ostree) vs Traditional (dnf)
- `dnf()` adds `-y` internally — don't duplicate

### 2. BaseTab for UI Tabs

```python
from ui.base_tab import BaseTab

class MyTab(BaseTab):
    def __init__(self):
        super().__init__()
        # Provides: self.output_area, self.runner (CommandRunner),
        # self.run_command(), self.append_output(), self.add_section()
```

### 3. CommandRunner (Async GUI)

```python
from utils.command_runner import CommandRunner
self.runner = CommandRunner()
self.runner.finished.connect(self.on_done)
self.runner.run_command("pkexec", ["dnf", "update", "-y"])
```

Never block the GUI thread with synchronous subprocess calls.

### 4. Operations Tuple Pattern

```python
@staticmethod
def clean_cache() -> Tuple[str, List[str], str]:
    pm = SystemManager.get_package_manager()
    if pm == "rpm-ostree":
        return ("pkexec", ["rpm-ostree", "cleanup", "--base"], "Cleaning...")
    return ("pkexec", ["dnf", "clean", "all"], "Cleaning...")
```

### 5. Error Framework

```python
from utils.errors import LoofiError, DnfLockedError, CommandFailedError
raise DnfLockedError(hint="Package manager is busy.")
# Each error has: code, hint, recoverable attributes
```

### 6. Confirm Dialog (Dangerous Ops)

```python
from ui.confirm_dialog import ConfirmActionDialog
if ConfirmActionDialog.confirm(self, "Delete snapshots", "Cannot be undone"):
    # proceed
```

### 7. Atomic Fedora

```python
pm = SystemManager.get_package_manager()  # "dnf" or "rpm-ostree"
if SystemManager.is_atomic():
    # rpm-ostree path
```

Always use `SystemManager.get_package_manager()` — **never hardcode `dnf`**.

### 8. Privilege Escalation

**Only `pkexec`** — never `sudo`. Policy: `config/org.loofi.fedora-tweaks.policy`.

### 9. Lazy Tab Loading

```python
# In MainWindow._lazy_tab():
"mytab": lambda: __import__("ui.mytab_tab", fromlist=["MyTabTab"]).MyTabTab(),
```

### 10. Safety & History

- `SafetyManager.confirm_action()` — snapshot prompt before risky ops
- `HistoryManager.log_change()` — action log with undo commands (max 50)

## Testing Rules

- **Framework**: `unittest` + `unittest.mock`
- **Decorators only**: `@patch`, never context managers
- **Mock everything**: `subprocess.run`, `check_output`, `shutil.which`, `os.path.exists`, `builtins.open`
- **Both paths**: Test success AND failure
- **No root**: Tests run in CI without privileges
- **Path setup**: `sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))`
- **Coverage**: 76.8% current, 80% target (v33)

## Adding a Feature

1. **Logic**: `utils/new_feature.py` — `@staticmethod`, return ops tuples
2. **UI**: `ui/new_feature_tab.py` — inherit `BaseTab`
3. **CLI**: Subcommand in `cli/main.py` with `--json`
4. **Test**: `tests/test_new_feature.py` — mock all system calls
5. **Register**: `MainWindow._lazy_tab()` + `add_page()` with icon
6. **Docs**: `CHANGELOG.md`, `README.md`

## Version Management

Two files MUST stay in sync:

- `loofi-fedora-tweaks/version.py` — `__version__`, `__version_codename__`
- `loofi-fedora-tweaks.spec` — `Version:`

## Build & Run

```bash
./run.sh                                                    # Dev run
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v   # Tests
bash scripts/build_rpm.sh                                   # Build RPM
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722
```

## Config & Conventions

- **Config dir**: `~/.config/loofi-fedora-tweaks/`
- **App catalog**: `config/apps.json`
- **QSS**: `assets/modern.qss` — use `setObjectName()` for targeting
- **i18n**: `self.tr("...")` for all user-visible strings
- **Naming**: `ui/*_tab.py` → `*Tab`; `utils/*.py` → `*Manager`/`*Ops` with `@staticmethod`
- **Plugins**: Extend `LoofiPlugin` ABC, place in `plugins/<name>/plugin.py`
