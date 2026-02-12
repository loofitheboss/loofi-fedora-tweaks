# Loofi Fedora Tweaks - User Guide

> **Version 26.0.2 "Status Bar UI Hotfix"**  
> Practical guide for daily usage, automation, and troubleshooting.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Launching and Modes](#launching-and-modes)
3. [Navigation and Shortcuts](#navigation-and-shortcuts)
4. [Permissions and Safety](#permissions-and-safety)
5. [Fedora Variant Behavior](#fedora-variant-behavior)
6. [Tab-by-Tab Guide](#tab-by-tab-guide)
7. [CLI Reference (Grouped)](#cli-reference-grouped)
8. [Plugin Marketplace](#plugin-marketplace)
9. [Daemon and Web API](#daemon-and-web-api)
10. [Files and Data Locations](#files-and-data-locations)
11. [Troubleshooting and Support](#troubleshooting-and-support)
12. [Screenshots](#screenshots)

---

## Quick Start

### Install

```bash
# Repository installer script
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

Or install an RPM directly:

```bash
pkexec dnf install ./loofi-fedora-tweaks-*.noarch.rpm
```

### First Launch

```bash
loofi-fedora-tweaks
```

On first launch, the setup wizard stores initial preferences in:

- `~/.config/loofi-fedora-tweaks/profile.json`
- `~/.config/loofi-fedora-tweaks/first_run_complete`

---

## Launching and Modes

| Mode | Command | Purpose |
|------|---------|---------|
| GUI | `loofi-fedora-tweaks` | Full desktop app |
| CLI | `loofi-fedora-tweaks --cli <command>` | Scripting and terminal workflows |
| Daemon | `loofi-fedora-tweaks --daemon` | Background automation service |
| Web API | `loofi-fedora-tweaks --web` | Headless API usage |

Optional alias:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

---

## Navigation and Shortcuts

### Sidebar and Search

- Tabs are grouped by category in the left sidebar.
- Use the sidebar search field to filter tabs quickly.
- Breadcrumb bar shows `Category > Tab > Description`.

### Keyboard Shortcuts

- `Ctrl+K`: Command Palette
- `Ctrl+Shift+K`: Quick Actions
- `Ctrl+1..9`: Jump to category
- `Ctrl+Tab`: Next tab
- `Ctrl+Shift+Tab`: Previous tab
- `F1`: Shortcut help dialog
- `Ctrl+Q`: Quit app

---

## Permissions and Safety

Loofi uses `pkexec` for privileged operations.

- You are prompted only when an action needs elevated access.
- Non-privileged actions run without elevation.
- Privileged actions are routed through utility/operations layers.

If a privileged action fails, verify:

- `pkexec` is available: `which pkexec`
- A polkit authentication agent is running in your session.

---

## Fedora Variant Behavior

Loofi automatically detects package-management mode:

- Traditional Fedora: uses `dnf`
- Atomic Fedora (Silverblue/Kinoite/etc.): uses `rpm-ostree` where applicable

Examples:

- Maintenance tab can show `Overlays` on Atomic systems.
- Update behavior and layered package handling adapt by variant.

---

## Tab-by-Tab Guide

### Dashboard

#### Home

- System overview with quick status and navigation actions.
- Use as the main entry point for daily checks.

### Automation

#### Agents

Sub-tabs:

- Dashboard
- My Agents
- Create Agent
- Activity Log

Use this tab to define autonomous routines and review their recent activity.

#### Automation

Sub-tabs:

- Scheduler
- Replicator

Use Scheduler for recurring tasks and Replicator for reproducible configuration/export workflows.

### System

#### System Info

- Host, kernel, hardware, uptime, and basic platform details.

#### System Monitor

Sub-tabs:

- Performance
- Processes

Monitor CPU/RAM/network trends and inspect/act on processes.

#### Health

- Timeline-based health metrics and trend visibility.
- Useful for capacity planning and anomaly checks.

#### Logs

- Smart journal view with filters and error-pattern summaries.
- Export logs for support or issue reporting.

### Hardware

#### Hardware

- CPU governor and power settings
- GPU and fan controls (hardware-dependent)
- Battery limits and fingerprint-related actions

#### Performance

- Auto-tuner workflow with analyze/apply/history patterns.

#### Storage

- Disk/mount overview and SMART health checks.

### Software

#### Software

Sub-tabs:

- Applications
- Repositories

Install software and manage repository setup from one place.

#### Maintenance

Sub-tabs:

- Updates
- Cleanup
- Overlays (Atomic-only)

Run updates, clean caches/journal, trim disks, and manage Atomic layers.

#### Snapshots

- Unified snapshot operations (Timeshift/Snapper/Btrfs backends).

#### Virtualization

Sub-tabs:

- VMs
- GPU Passthrough
- Disposable

Manage VM lifecycle and passthrough setup tasks.

#### Development

Sub-tabs:

- Containers
- Developer Tools

Container workflows (for example Distrobox) and toolchain setup helpers.

### Network

#### Network

Sub-tabs:

- Connections
- DNS
- Privacy
- Monitoring

Covers interface visibility, DNS switching, network privacy controls, and live stats.

#### Loofi Link

Sub-tabs:

- Devices
- Clipboard
- File Drop

Peer discovery and local network sharing workflows.

### Security

#### Security & Privacy

- Security score and audits
- Port visibility and firewall tasks
- USB/telemetry/privacy controls (where supported)

### Desktop

#### Desktop

Sub-tabs:

- Window Manager
- Theming

Desktop behavior, compositor/tiling, and theme-related settings.

#### Profiles

- Save, apply, import, and export system profiles.

#### Gaming

- Gaming-related setup and optimization helpers.

### Tools

#### AI Lab

Sub-tabs:

- Models
- Voice
- Knowledge

Manage local AI models, speech workflows, and knowledge indexing/search.

#### State Teleport

- Capture and restore workspace state packages.

#### Diagnostics

Sub-tabs:

- Watchtower
- Boot

Service diagnostics, boot analysis, and system inspection tools.

#### Community

Sub-tabs:

- Presets
- Marketplace
- Plugins

Includes preset sharing, marketplace browsing, and plugin enable/disable management.

### Settings

#### Settings

Sub-tabs:

- Appearance
- Behavior
- Advanced

Configure app behavior such as startup preferences and UI options.

---

## CLI Reference (Grouped)

All commands below assume the alias:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

### Core

```bash
loofi info
loofi health
loofi doctor
loofi hardware
loofi support-bundle
```

### Monitoring

```bash
loofi disk --details
loofi processes --sort cpu -n 15
loofi temperature
loofi netmon --connections
```

### Maintenance and Tweaks

```bash
loofi cleanup all
loofi cleanup journal --days 7
loofi tweak power --profile balanced
loofi tweak battery --limit 80
loofi advanced swappiness --value 15
```

### Network and Security

```bash
loofi network dns --provider cloudflare
loofi firewall status
loofi firewall open-port 8080/tcp
loofi security-audit
```

### Software and Services

```bash
loofi package search --query firefox --source all
loofi package install vim
loofi service list --filter failed
loofi service restart sshd
```

### Hardware, Storage, Bluetooth

```bash
loofi storage disks
loofi storage smart /dev/sda
loofi storage trim
loofi bluetooth devices
loofi bluetooth scan --timeout 10
```

### Snapshots and Tuning

```bash
loofi snapshot backends
loofi snapshot create --label before-updates
loofi tuner analyze
loofi tuner apply
loofi logs errors --since "2h ago"
```

### Profiles and Health History

```bash
loofi profile list
loofi profile apply gaming
loofi profile export-all profiles.json --include-builtins
loofi health-history show
loofi health-history export health.json
```

### Automation and Advanced Tools

```bash
loofi agent list
loofi agent create --goal "keep my system clean"
loofi vm list
loofi vfio check
loofi mesh discover
loofi teleport capture --path ~/workspace --target laptop
```

### JSON Output (Scripting)

```bash
loofi --json info
loofi --json health
loofi --json package search --query podman
```

---

## Plugin Marketplace

CLI actions:

- `search`
- `info`
- `install`
- `uninstall`
- `update`
- `list-installed`
- `reviews`
- `review-submit`
- `rating`

Examples:

```bash
loofi plugin-marketplace search --query monitor
loofi plugin-marketplace info cool-plugin
loofi plugin-marketplace install cool-plugin --accept-permissions
loofi plugin-marketplace reviews cool-plugin --limit 5
loofi plugin-marketplace review-submit cool-plugin --reviewer loofi --rating 5 --title "Great" --comment "Works well"
loofi plugin-marketplace rating cool-plugin
```

Notes:

- Some plugins declare required permissions.
- Use `--accept-permissions` for non-interactive installs.

---

## Daemon and Web API

### Daemon

```bash
loofi-fedora-tweaks --daemon
```

Use daemon mode for long-running scheduled tasks without opening the GUI.

### Web API (Headless)

```bash
loofi-fedora-tweaks --web
```

API mode is intended for controlled environments and automation scenarios.

---

## Files and Data Locations

Common paths:

- User config: `~/.config/loofi-fedora-tweaks/`
- Startup log: `~/.local/share/loofi-fedora-tweaks/startup.log`
- Runtime/app logs: typically under user journal and app config paths

When sharing diagnostics, include:

```bash
loofi-fedora-tweaks --cli support-bundle
journalctl --user --since "1 hour ago"
```

---

## Troubleshooting and Support

Start with:

1. `loofi-fedora-tweaks --cli doctor`
2. `loofi-fedora-tweaks --cli support-bundle`
3. `docs/TROUBLESHOOTING.md`

Then open an issue with:

- Fedora version and desktop environment
- Exact command or tab used
- Error output and reproduction steps
- Support bundle path (if generated)

GitHub issues: <https://github.com/loofitheboss/loofi-fedora-tweaks/issues>

---

## Screenshots

### Home Dashboard

![Home Dashboard](images/user-guide/home-dashboard.png)

### System Monitor

![System Monitor](images/user-guide/system-monitor.png)

### Maintenance (Updates)

![Maintenance Updates](images/user-guide/maintenance-updates.png)

### Security & Privacy

![Security and Privacy](images/user-guide/security-privacy.png)

### Network Overview

![Network Overview](images/user-guide/network-overview.png)

### AI Lab

![AI Lab Models](images/user-guide/ai-lab-models.png)

### Community Presets

![Community Presets](images/user-guide/community-presets.png)

### Community Marketplace

![Community Marketplace](images/user-guide/community-marketplace.png)

### Settings

![Settings Appearance](images/user-guide/settings-appearance.png)
