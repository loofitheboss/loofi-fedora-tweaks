# Loofi Fedora Tweaks v14.0.0 - The "Quantum Leap" Update

A reliability and polish release introducing automatic update checking, a What's New dialog for post-upgrade highlights, full configuration backup/restore/factory-reset management, and plugin lifecycle events.

## Highlights

* **Update Checker**: Automatic update notifications from GitHub releases API.
* **What's New Dialog**: Post-upgrade dialog showing release highlights.
* **Factory Reset**: Full backup/restore/reset management for all config files.
* **Plugin Lifecycle Events**: `on_app_start`, `on_app_quit`, `on_tab_switch` hooks for plugins.

## New Features

### Update Checker
* Fetches latest release from GitHub releases API
* Compares installed version against latest release tag
* `UpdateInfo` dataclass with version comparison and download URL
* Configurable timeout for network requests

### What's New Dialog
* Shows after every version upgrade
* Remembers last-seen version via `SettingsManager`
* Scrollable view with current + previous version notes
* "Don't show again" checkbox

### Factory Reset & Backup Management
* `create_backup()` — snapshot all JSON config files with manifest
* `list_backups()` — enumerate available backups with metadata
* `restore_backup()` — restore config from a named backup
* `delete_backup()` — remove old backups
* `reset_config()` — factory reset with automatic pre-reset backup
* Preserves plugins by default during reset

### Plugin Lifecycle Events
* `on_app_start` — called when the application starts
* `on_app_quit` — called before application exits
* `on_tab_switch` — called when user switches tabs
* `on_settings_changed` — notified when settings change
* `get_settings_schema` — plugins can declare configurable settings

## New Files

| File | Description |
|------|-------------|
| `utils/update_checker.py` | GitHub releases API update checker |
| `utils/factory_reset.py` | Backup/restore/reset management |
| `ui/whats_new_dialog.py` | Post-upgrade What's New dialog |
| `tests/test_factory_reset.py` | Factory reset unit tests (22 tests) |
| `tests/test_update_checker.py` | Update checker unit tests (8 tests) |

## Test Coverage

* **1130+ tests** passing (up from 1060 in v13.5.0)
* 72 new tests for factory reset and update checker

## Installation

```bash
# From RPM (Fedora)
sudo dnf install loofi-fedora-tweaks-14.0.0-1.fc43.noarch.rpm

# From source
./run.sh
```

## Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for the complete version history.
loofi ai-models recommend     # Get RAM-based model recommendation
```

## Installation

**Via DNF:**

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v12.0.0/loofi-fedora-tweaks-12.0.0-1.fc43.noarch.rpm
```

**Build from source:**

```bash
./build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-12.0.0-1.fc43.noarch.rpm
```

## Quick Start

```bash
# GUI
loofi-fedora-tweaks

# CLI
loofi info
loofi doctor
loofi vm list
loofi mesh discover
loofi teleport capture
loofi ai-models list
```
