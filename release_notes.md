# Loofi Fedora Tweaks v11.0.0 - The "Aurora" Update

A stability and extensibility release that adds plugin management, better diagnostics, and safer automation.

## Highlights

* **Plugin Manifests + Manager**: Standard `plugin.json` metadata with version gating and enable/disable support.
* **Support Bundle Export**: One-click ZIP with logs and system info for troubleshooting.
* **Automation Validation**: Validate and simulate rules before execution.

## New Features

### Plugin System v2 Foundations
* `plugin.json` manifest with version, author, description, and permissions metadata
* Enable/disable plugins without uninstalling
* CLI support: `loofi plugins list|enable|disable`

### Diagnostics Upgrade
* Support bundle ZIP export from **Diagnostics > Journal**
* CLI support: `loofi support-bundle`

### Automation Safety
* Rule validation with warnings and errors
* Dry-run simulation for rule execution

## Quality Improvements

* Unified QSS theme loading (`modern.qss`) for consistent styling
* Structured logging for Pulse, remote config, and command runner errors
* CI includes CLI smoke checks

## Installation

**Via DNF:**

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v11.0.0/loofi-fedora-tweaks-11.0.0-1.fc43.noarch.rpm
```

**Build from source:**

```bash
./build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-11.0.0-1.fc43.noarch.rpm
```

## Quick Start

```bash
# GUI
loofi-fedora-tweaks

# CLI
loofi info
loofi doctor
loofi plugins list
loofi support-bundle
```
