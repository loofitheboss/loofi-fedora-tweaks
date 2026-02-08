# Contributing to Loofi Fedora Tweaks

Thank you for considering contributing! Here's how you can help.

## Reporting Bugs

1. Search [existing issues](https://github.com/loofitheboss/loofi-fedora-tweaks/issues) to avoid duplicates.
2. Open a new issue with:
    * **Title**: Short and descriptive.
    * **Steps to Reproduce**: What did you do?
    * **Expected Behavior**: What should have happened?
    * **Actual Behavior**: What happened instead?
    * **Environment**: Fedora version, KDE Plasma version, Python version.

## Feature Requests

Open an issue with the **enhancement** label. Describe:

* The problem you're trying to solve.
* Your proposed solution.

## Pull Requests

1. **Fork** the repository.
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make changes** and commit: `git commit -m "Add your feature"`
4. **Push**: `git push origin feature/your-feature-name`
5. **Open a Pull Request** on GitHub.

### Code Style

* Python: Follow PEP 8.
* Use meaningful variable names.
* Comment complex logic.
* Wrap all user-visible strings with `self.tr("...")` for i18n.
* New tabs should inherit from `BaseTab` (see `ui/base_tab.py`).
* System commands go in `utils/` modules, never directly in UI code.

## Project Structure (v10.0)

```
loofi-fedora-tweaks/
├── loofi-fedora-tweaks/       # Main application source
│   ├── main.py               # Entry point (GUI/CLI/Daemon)
│   ├── version.py            # Version source of truth
│   ├── ui/                   # PyQt6 UI components
│   │   ├── main_window.py    # Main window with sidebar (15 tabs)
│   │   ├── base_tab.py       # BaseTab class (shared by all tabs)
│   │   ├── dashboard_tab.py  # Dashboard (Home)
│   │   ├── monitor_tab.py    # System Monitor (Performance + Processes)
│   │   ├── maintenance_tab.py # Maintenance (Updates + Cleanup + Overlays)
│   │   ├── software_tab.py   # Software (Apps + Repos)
│   │   ├── hardware_tab.py   # Hardware (CPU/GPU/Fan/Battery/Audio/Fingerprint)
│   │   ├── security_tab.py   # Security & Privacy
│   │   ├── desktop_tab.py    # Desktop (Director + Theming)
│   │   ├── development_tab.py # Development (Containers + Developer)
│   │   ├── automation_tab.py # Automation (Scheduler + Replicator)
│   │   ├── community_tab.py  # Community (Presets + Marketplace)
│   │   ├── diagnostics_tab.py # Diagnostics (Watchtower + Boot)
│   │   ├── wizard.py         # First-run wizard
│   │   ├── command_palette.py # Ctrl+K command palette
│   │   └── lazy_widget.py    # Lazy tab loading
│   ├── utils/                # Business logic and system commands
│   │   ├── commands.py       # PrivilegedCommand builder (safe pkexec)
│   │   ├── errors.py         # Error hierarchy (LoofiError, etc.)
│   │   ├── formatting.py     # Shared formatting utilities
│   │   ├── hardware_profiles.py # Hardware auto-detection via DMI
│   │   ├── command_runner.py # Async QProcess wrapper
│   │   ├── operations.py     # Shared operations layer
│   │   ├── system.py         # System detection (Atomic/Traditional)
│   │   ├── pulse.py          # Event-driven automation engine
│   │   ├── focus_mode.py     # Focus mode / distraction blocking
│   │   └── ...               # Other utility modules
│   ├── cli/                  # CLI entry point
│   │   └── main.py           # CLI with --json support
│   ├── assets/               # Icons, QSS themes
│   │   ├── modern.qss        # Dark theme
│   │   └── loofi-fedora-tweaks.png
│   ├── config/               # Default configs
│   └── plugins/              # Third-party extensions
├── tests/                    # Unit tests (225+ tests)
│   ├── conftest.py           # Shared fixtures
│   ├── test_v10_features.py  # v10 foundation module tests
│   ├── test_cli_enhanced.py  # CLI tests
│   └── ...
├── docs/                     # Documentation
│   ├── USER_GUIDE.md
│   ├── RELEASE_CHECKLIST.md
│   └── CONTRIBUTING.md       # This file
├── .github/
│   ├── workflows/ci.yml      # CI pipeline (lint, test, build)
│   ├── workflows/release.yml # Tag-triggered releases
│   └── copilot-instructions.md
├── build_rpm.sh              # Build script
├── loofi-fedora-tweaks.spec  # RPM spec file
├── requirements.txt          # Python dependencies
└── README.md                 # Project overview
```

## Key Patterns for Contributors

### BaseTab Class

All new tabs that execute system commands should inherit from `BaseTab`:

```python
from ui.base_tab import BaseTab

class MyNewTab(BaseTab):
    def __init__(self):
        super().__init__()
        # BaseTab provides: self.output_area, self.runner, self.run_command()
```

### PrivilegedCommand Builder

Use `PrivilegedCommand` for safe pkexec operations:

```python
from utils.commands import PrivilegedCommand

cmd = PrivilegedCommand.dnf("install", "-y", "package-name")
# Returns: ["pkexec", "dnf", "install", "-y", "package-name"]
```

### Error Framework

Use typed exceptions from `utils/errors.py`:

```python
from utils.errors import CommandFailedError, PrivilegeError
```

### Lazy Tab Registration

Register new tabs in `MainWindow._lazy_tab()` loaders dict:

```python
"mytab": lambda: __import__("ui.mytab_tab", fromlist=["MyTabTab"]).MyTabTab(),
```

## Running Tests

```bash
PYTHONPATH=loofi-fedora-tweaks python3 -m pytest tests/ -v
# 225 tests passing
```

## Building the RPM

```bash
./build_rpm.sh
# Output: rpmbuild/RPMS/noarch/loofi-fedora-tweaks-11.0.0-1.fc43.noarch.rpm
```

## CI/CD

Pull requests automatically run:
1. **Lint** (flake8) - Code style checks
2. **Test** (pytest) - Full test suite
3. **Build** (rpmbuild) - RPM package build in Fedora 43 container

---

Thanks for contributing!
