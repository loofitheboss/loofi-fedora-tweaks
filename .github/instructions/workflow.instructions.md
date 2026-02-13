---
description: Workflow pipeline rules for Loofi Fedora Tweaks development
applyTo: "**"
---

# Loofi Fedora Tweaks — Workflow-Aware AI Instructions

## 1. Workflow Pipeline

Before making code changes, verify context from `.workflow/specs/`:

- **Race Lock**: `.workflow/specs/.race-lock.json` — identifies the ACTIVE version
- **Task Spec**: `.workflow/specs/tasks-{version}.md` — canonical task list with contract markers
- **Arch Spec**: `.workflow/specs/arch-{version}.md` — architecture decisions and design rationale
- **Run Manifest**: `.workflow/reports/run-manifest-{version}.json` — phase execution log

### Task Contract Markers (v26+ rules)
Every task entry must include: `ID:`, `Files:`, `Dep:`, `Agent:`, `Description:`, `Acceptance:`, `Docs:`, `Tests:`.

### Phase Flow
`Plan → Design → Build → Test → Doc → Package → Release`
- Do NOT implement without a Design spec (`arch-{ver}.md`)
- Do NOT close a task without passing its `Tests:` field
- Do NOT release without `CHANGELOG`, `README`, and release notes

### Current State
- **Done**: v33.0.0 "Bastion"
- **Active/Next**: v33.0 (Testing & CI Hardening)
- **Source of truth**: `ROADMAP.md`

---

## 2. Architecture & Layering

Three entry modes in `loofi-fedora-tweaks/main.py`:

| Layer | Path | Role | Rule |
|-------|------|------|------|
| UI | `ui/*_tab.py` | PyQt6 widgets, inherit `BaseTab` | NO business logic, NO subprocess calls |
| Utils | `utils/*.py` | Business logic, system commands | Shared API consumed by UI + CLI |
| CLI | `cli/main.py` | Subcommands, `--json` output | Calls `utils/` directly, never `ui/` |
| Core | `core/executor/` | `BaseActionExecutor` + `ActionResult` | Subprocess abstraction layer |
| Services | `services/` | Service layer | Future expansion |
| Plugins | `plugins/`, `core/plugins/` | `LoofiPlugin` ABC, marketplace | Sandboxed extensions |

**Strict Rule**: `utils/operations.py` (and similar managers) is the API. GUI and CLI are consumers only.

---

## 3. Critical Coding Patterns

### A. Privileges & Commands
```python
from utils.commands import PrivilegedCommand
binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ALWAYS unpack — never pass tuple to subprocess
```
- Use `SystemManager.get_package_manager()` — never hardcode `dnf`
- Use `pkexec` only — never `sudo`
- `dnf()` adds `-y` internally — don't duplicate

### B. Async UI Operations
```python
from utils.command_runner import CommandRunner
self.runner = CommandRunner()
self.runner.finished.connect(self.handle_finish)
self.runner.run_command(binary, args)
```
Never block the GUI thread with synchronous subprocess calls.

### C. Error Handling
```python
from utils.errors import LoofiError, DnfLockedError, CommandFailedError
raise DnfLockedError(hint="Package manager is busy.")
```
- Each error has: `code`, `hint`, `recoverable` attributes
- Global `sys.excepthook` in `utils/error_handler.py` catches unhandled errors (v29.0)

### D. Dangerous Operations (v29.0)
```python
from ui.confirm_dialog import ConfirmActionDialog
if ConfirmActionDialog.confirm(self, "Delete all snapshots", "This cannot be undone"):
    # proceed
```

---

## 4. Testing Rules

- **Framework**: `unittest` + `unittest.mock`
- **Decorators only**: Use `@patch`, never context managers
- **Mock everything**: `subprocess.run`, `subprocess.check_output`, `shutil.which`, `os.path.exists`, `builtins.open`
- **Both paths**: Test success AND failure for every operation
- **No root**: Tests run in CI without privileges or network
- **Path setup**: `sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))`
- **Coverage target**: 75% (v29 achieved: 76.8%), 80% (v30), 85% (v31)

---

## 5. Adding Features

1. **Spec**: Create or update `.workflow/specs/arch-{ver}.md`
2. **Task**: Add entry to `.workflow/specs/tasks-{ver}.md` with contract markers
3. **Logic**: Create `utils/new_feature.py` — `@staticmethod` methods, return ops tuples
4. **UI**: Create `ui/new_feature_tab.py` — inherit `BaseTab`
5. **CLI**: Add subcommand in `cli/main.py` with `--json` support
6. **Test**: Create `tests/test_new_feature.py` — mock all system calls
7. **Register**: Add lazy loader in `MainWindow._lazy_tab()` + `add_page()` with icon
8. **Docs**: Update `CHANGELOG.md`, `README.md`, release notes

---

## 6. Versioning

Two files must stay in sync:
- `loofi-fedora-tweaks/version.py` — `__version__`, `__version_codename__`
- `loofi-fedora-tweaks.spec` — `Version:`

Workflow files to update on version bump:
- `.workflow/specs/.race-lock.json` — target version + active status
- `.workflow/specs/tasks-{ver}.md` — new task spec
- `.workflow/specs/arch-{ver}.md` — new architecture blueprint

---

## 7. Style & Conventions

- Plain English, no fluff
- Bullet lists, max 10 lines per section
- Docstrings on all public methods
- `setObjectName()` for QSS-targeted styling
- `self.tr("...")` for all user-visible strings
- Config storage: `~/.config/loofi-fedora-tweaks/`
- App catalog: `config/apps.json`
