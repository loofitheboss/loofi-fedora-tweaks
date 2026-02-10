# Loofi Fedora Tweaks — Agent Instructions

> PyQt6 desktop app for Fedora Linux system customization.
> 25 UI tabs, 55 test files, 52+ utils modules, CLI + GUI + Daemon modes.

## Architecture

```
loofi-fedora-tweaks/
├── ui/*_tab.py       # PyQt6 tabs (inherit BaseTab)
├── utils/*.py        # Business logic (@staticmethod, operations tuples)
├── core/executor/    # BaseActionExecutor + ActionResult
├── services/         # Service layer (WIP)
├── cli/main.py       # CLI (calls utils/, never ui/)
├── config/           # apps.json, polkit policy, systemd
└── version.py        # __version__, __version_codename__
tests/                # unittest + mock, @patch decorators, no root
scripts/              # build_rpm.sh, workflow-runner.sh
```

## Critical Rules

1. **Never use `sudo`** — only `pkexec` via `PrivilegedCommand`
2. **Never hardcode `dnf`** — use `SystemManager.get_package_manager()`
3. **Never put subprocess calls in UI code** — extract to `utils/`
4. **Always mock system calls in tests** — use `@patch` decorators
5. **Always unpack PrivilegedCommand tuples** before `subprocess.run()`
6. **Version sync**: `version.py` and `.spec` must match

## Key Patterns

```python
# PrivilegedCommand (ALWAYS unpack)
from utils.commands import PrivilegedCommand
binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args  # ["pkexec", "dnf", "install", "-y", "package"]

# BaseTab for UI
from ui.base_tab import BaseTab
class MyTab(BaseTab):
    def __init__(self): super().__init__()

# Operations tuple from utils
@staticmethod
def clean_cache() -> Tuple[str, List[str], str]:
    return ("pkexec", ["dnf", "clean", "all"], "Cleaning...")

# Atomic Fedora detection
pm = SystemManager.get_package_manager()  # "dnf" or "rpm-ostree"
```

## Automated Pipeline

Every version follows 7 phases. Prompts in `.claude/workflow/prompts/`.

```
PLAN → DESIGN → IMPLEMENT → TEST → DOCUMENT → PACKAGE → RELEASE
```

- **ROADMAP.md** — Version scope, status (DONE/ACTIVE/NEXT/PLANNED)
- **`.claude/workflow/PIPELINE.md`** — Phase definitions with entry/exit criteria
- **`.claude/workflow/model-router.md`** — Model selection for cost
- **`scripts/workflow-runner.sh`** — CLI: `./scripts/workflow-runner.sh 23.0.0 validate`

## Testing

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov-fail-under=80
```

- `@patch` decorators, never context managers
- Mock: `subprocess.run`, `subprocess.check_output`, `shutil.which`, `os.path.exists`
- Both success AND failure paths
- No root needed

## Build

```bash
bash scripts/build_rpm.sh        # Build RPM
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722
```

## Style

- Concise. No essays. Bullet lists.
- Max 10 lines per response section
- Minimal diffs — only change what's needed
- Existing patterns over new abstractions
