# Loofi Fedora Tweaks v10.0.0 - The "Zenith" Update

The biggest release yet: a major consolidation and modernization of the entire application.

## Architecture Overhaul

* **25 tabs consolidated to 15** with QTabWidget sub-navigation within each consolidated tab
* **BaseTab class** (`ui/base_tab.py`) eliminates command-execution boilerplate across all tabs
* **PrivilegedCommand builder** (`utils/commands.py`) for safe pkexec operations using argument arrays
* **Error framework** (`utils/errors.py`) with typed exceptions and recovery hints
* **Hardware profiles** (`utils/hardware_profiles.py`) auto-detect hardware via DMI sysfs data

## New Features

### First-Run Wizard
On first launch, automatically detects your hardware and asks about your use case:
* HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS ZenBook auto-detection
* Use case selection: Development, Gaming, Creative Work, Office
* Profile saved to `~/.config/loofi-fedora-tweaks/profile.json`

### Command Palette (Ctrl+K)
* 60+ searchable feature entries
* Fuzzy matching with scored relevance
* Keyboard navigation (Up/Down, Enter, Escape)

### CLI Enhancements
* `--json` flag for machine-readable output on all commands
* `doctor` command checks critical and optional tool dependencies
* `hardware` command shows detected hardware profile

### CI/CD Pipeline
* GitHub Actions: lint (flake8), test (pytest), build (Fedora 43 rpmbuild)
* Tag-triggered releases with RPM artifact upload

## Consolidated Tabs

| New Tab | Merges |
|---------|--------|
| **Maintenance** | Updates + Cleanup + Overlays |
| **Software** | Apps + Repos |
| **System Monitor** | Performance + Processes |
| **Hardware** | Hardware Control + HP Tweaks (now hardware-agnostic) |
| **Security & Privacy** | Security Center + Privacy |
| **Desktop** | Director + Theming |
| **Development** | Containers + Developer Tools |
| **Community** | Presets + Marketplace |
| **Automation** | Scheduler + Replicator + Pulse |
| **Diagnostics** | Watchtower + Boot |

## New Modules

| File | Description |
|:---|:---|
| `ui/base_tab.py` | BaseTab class with CommandRunner wiring |
| `ui/maintenance_tab.py` | Consolidated maintenance (Updates + Cleanup + Overlays) |
| `ui/software_tab.py` | Consolidated software (Apps + Repos) |
| `ui/monitor_tab.py` | Consolidated system monitor (Performance + Processes) |
| `ui/diagnostics_tab.py` | Consolidated diagnostics (Watchtower + Boot) |
| `ui/desktop_tab.py` | Consolidated desktop (Director + Theming) |
| `ui/development_tab.py` | Consolidated development (Containers + Developer) |
| `ui/community_tab.py` | Consolidated community (Presets + Marketplace) |
| `ui/automation_tab.py` | Consolidated automation (Scheduler + Replicator) |
| `ui/wizard.py` | First-run wizard with hardware detection |
| `ui/command_palette.py` | Ctrl+K fuzzy-search command palette |
| `utils/errors.py` | Centralized error hierarchy |
| `utils/commands.py` | PrivilegedCommand builder |
| `utils/formatting.py` | Shared formatting utilities |
| `utils/hardware_profiles.py` | Hardware profile auto-detection |

## Bug Fixes

* **Network state detection**: Fixed Pulse `get_network_state()` incorrectly matching "disconnected" as "connected" due to substring check order

## Tests

* 225 tests passing (87+ new for v10 modules)
* Shared test fixtures in `tests/conftest.py`
* CI pipeline validates on every push

## Installation

**Via DNF:**

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v10.0.0/loofi-fedora-tweaks-10.0.0-1.fc43.noarch.rpm
```

**Build from source:**

```bash
./build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-10.0.0-1.fc43.noarch.rpm
```

## Quick Start

```bash
# GUI
loofi-fedora-tweaks

# CLI
loofi info
loofi doctor
loofi hardware
loofi --json health
```
