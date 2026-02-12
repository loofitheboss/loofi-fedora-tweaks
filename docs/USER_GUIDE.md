# Loofi Fedora Tweaks - Detailed User Guide

> **Version 26.0.2 "Status Bar UI Hotfix"**  
> A practical, detailed guide to using Loofi Fedora Tweaks effectively and safely.

---

## Table of Contents

1. [What This App Does](#what-this-app-does)
2. [Install and First Launch](#install-and-first-launch)
3. [How the App Works Internally](#how-the-app-works-internally)
4. [UI Layout and Navigation](#ui-layout-and-navigation)
5. [Recommended Daily/Weekly Workflows](#recommended-dailyweekly-workflows)
6. [Detailed Tab Guide](#detailed-tab-guide)
7. [Plugin Marketplace and Community Features](#plugin-marketplace-and-community-features)
8. [CLI Guide by Task](#cli-guide-by-task)
9. [Configuration and Data Locations](#configuration-and-data-locations)
10. [Troubleshooting and Support](#troubleshooting-and-support)
11. [Screenshot Gallery](#screenshot-gallery)

---

## What This App Does

Loofi Fedora Tweaks is an all-in-one Fedora operations console with three key goals:

- Expose system controls in a structured GUI.
- Provide the same operations in CLI form for automation.
- Keep risky operations safer with privilege prompts and confirmations.

At the time of writing, the app ships with **26 built-in tabs** grouped by category:

- Dashboard
- Automation
- System
- Hardware
- Software
- Network
- Security
- Desktop
- Tools
- Settings

It supports both:

- Traditional Fedora systems (`dnf` based)
- Atomic Fedora variants (`rpm-ostree` based)

---

## Install and First Launch

### Install

```bash
# Repository installer script
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

Or install a release RPM directly:

```bash
pkexec dnf install ./loofi-fedora-tweaks-*.noarch.rpm
```

### Launch

```bash
loofi-fedora-tweaks
```

### First-Run Wizard

On first launch, the setup wizard helps with:

- Hardware profile detection
- Use-case selection (Gaming, Development, Daily Driver, Server, Minimal)
- Initial profile persistence

It writes:

- `~/.config/loofi-fedora-tweaks/profile.json`
- `~/.config/loofi-fedora-tweaks/first_run_complete`

---

## How the App Works Internally

### Runtime Modes

| Mode | Command | Purpose |
|------|---------|---------|
| GUI | `loofi-fedora-tweaks` | Full desktop app |
| CLI | `loofi-fedora-tweaks --cli <command>` | Scriptable operations |
| Daemon | `loofi-fedora-tweaks --daemon` | Background automation |
| Web API | `loofi-fedora-tweaks --web` | Headless remote integration |

Optional convenience alias:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

### Startup Flow (GUI)

High-level flow:

1. `main.py` checks PyQt6 availability.
2. Loads stylesheet and translations.
3. Opens `MainWindow`.
4. `MainWindow` uses plugin registry/loader to populate sidebar tabs dynamically.
5. Each tab is wrapped in a lazy widget and initialized when first shown.

What this means in practice:

- Faster startup than initializing every tab immediately.
- Better compatibility checks per tab/plugin.
- A clean place to add future external plugins.

### Command Execution Flow

Most action tabs follow the same command pattern:

1. UI triggers a utility function or operation tuple.
2. A command runner executes asynchronously.
3. Output is streamed into the tab’s Output Log.
4. Exit code and errors are surfaced in the UI.

### Privilege and Safety Model

- Privileged operations use `pkexec` prompts.
- Some risky actions show safety confirmations.
- Snapshot prompts may appear before dangerous system changes where supported.

### Package Manager Awareness

The app detects platform mode automatically:

- `dnf` on traditional Fedora
- `rpm-ostree` on Atomic variants

This affects behavior in Maintenance and package/update flows.

---

## UI Layout and Navigation

### Main UI Regions

- Left sidebar: categories and tabs
- Top breadcrumb: `Category > Tab > Description`
- Center content area: active tab view
- Bottom status bar: quick shortcut hints + version

### Keyboard Shortcuts

- `Ctrl+K` - Command Palette (feature/tab search)
- `Ctrl+Shift+K` - Quick Actions dialog
- `Ctrl+1..9` - Jump category
- `Ctrl+Tab` - Next tab
- `Ctrl+Shift+Tab` - Previous tab
- `F1` - Shortcut help
- `Ctrl+Q` - Quit

### Home Screen Example

![Home Dashboard](images/user-guide/home-dashboard.png)

The Home tab gives a quick operational overview and links to frequent actions.

---

## Recommended Daily/Weekly Workflows

### Daily Health Check (2-3 minutes)

1. Open **Home** and check CPU/RAM/network trends.
2. Open **System Monitor -> Processes** for runaway processes.
3. Open **Security & Privacy** and refresh security score if needed.

### Weekly Maintenance Cycle

1. Open **Maintenance -> Updates**.
2. Run **Update All** (or run updates individually).
3. Open **Maintenance -> Cleanup** and run:
   - DNF cache clean
   - Journal vacuum
   - SSD trim
4. Optionally create/refresh snapshots in **Snapshots**.

### Security Baseline Pass

1. Open **Security & Privacy**.
2. Refresh score.
3. Run port scan.
4. Verify firewall status.
5. Check telemetry and USB guard sections if relevant to your setup.

### Before Risky Changes

1. Create a snapshot in **Snapshots**.
2. Export profile bundle in **Profiles**.
3. Export support bundle from CLI:

```bash
loofi support-bundle
```

---

## Detailed Tab Guide

## Dashboard Category

### Home

Key capabilities:

- Live CPU and RAM sparkline metrics
- Storage usage bars
- Top process summary
- Recent actions view
- Quick action buttons for common navigation

Notes:

- Fast metrics refresh about every 2 seconds.
- Heavier sections refresh about every 10 seconds.
- Quick actions mainly route you to relevant tabs for execution.

## Automation Category

### Agents

Sub-tabs:

- Dashboard
- My Agents
- Create Agent
- Activity Log

What you can do:

- View active/enabled/error counts
- Start/stop scheduler
- Enable/disable/run existing agents
- Create agents from a natural-language goal

### Automation

Sub-tabs:

- Scheduler
- Replicator

Scheduler features:

- Create scheduled tasks (cleanup/update/sync/preset actions)
- Enable/disable/run/delete tasks
- Manage background service state

Replicator features:

- Preview and export Ansible playbooks
- Preview and export Kickstart files

## System Category

### System Info

- Host, OS, kernel, and hardware details in one place.

### System Monitor

Sub-tabs:

- Performance
- Processes

What to use it for:

- Real-time usage and I/O trends
- Process filtering and quick refresh
- Process-level operational triage

![System Monitor](images/user-guide/system-monitor.png)

### Health

- Timeline-style health metrics for trend tracking over time.
- Useful for detecting gradual degradations.

### Logs

Key features:

- Error summary panel
- Pattern detection table
- Live log mode
- Filtered log browsing and export

Best practice:

- Use `errors` view first, then browse raw logs when needed.

## Hardware Category

### Hardware

Key sections include:

- CPU governor control
- Power profile switching
- GPU mode switching (where supported)
- Fan controls (where tooling exists)
- Audio service restart helper
- Battery charge limits (80/100)
- Fingerprint enrollment dialog
- Bluetooth power/scan controls

Behavior notes:

- Hardware capabilities vary by machine model and installed tools.
- Missing toolchains show install/help actions instead of hidden controls.

### Performance

Auto-tuner workflow:

1. Detect current workload.
2. Review recommendation.
3. Apply recommendation.
4. Review tuning history.

This is ideal when balancing battery life vs. responsiveness for changing workloads.

### Storage

Capabilities:

- Physical disk and mount overview
- SMART health view
- TRIM execution
- Filesystem check trigger

Use this tab weekly if you do heavy I/O or maintain large local datasets.

## Software Category

### Software

Sub-tabs:

- Applications
- Repositories

Applications:

- Curated installer buttons and install-state refresh.

Repositories:

- RPM Fusion enablement
- Flathub enablement
- Codec setup helpers
- COPR helper actions

### Maintenance

Sub-tabs:

- Updates
- Cleanup
- Overlays (Atomic-only)

Updates section:

- Update all queue (system + flatpak + firmware)
- Individual update controls
- Kernel list/remove helpers

Cleanup section:

- DNF cache cleanup
- Remove unused packages
- Journal vacuum
- SSD trim
- RPM DB rebuild

Overlays section (Atomic):

- Layered package list
- Remove selected package
- Reset to base image
- Reboot prompt for pending deployment

![Maintenance Updates](images/user-guide/maintenance-updates.png)

### Snapshots

Unified snapshot management across available backends:

- Detects backend availability
- Create snapshot
- Delete selected snapshot
- Refresh timeline list

### Virtualization

Sub-tabs:

- VMs
- GPU Passthrough
- Disposable

VM operations:

- List/start/stop/delete VMs
- Quick-create flow from ISO

GPU passthrough:

- Prerequisite checks
- Candidate GPU detection
- Setup plan generation

Disposable:

- Base image management
- Launch short-lived VM instances

### Development

Sub-tabs:

- Containers
- Developer Tools

Containers:

- Distrobox-aware container list/create/enter/stop/delete

Developer Tools:

- Install/version-check: PyEnv, NVM, Rustup
- VS Code extension profile actions

## Network Category

### Network

Sub-tabs:

- Connections
- DNS
- Privacy
- Monitoring

Capabilities:

- Active interface and Wi-Fi visibility
- DNS provider switching and DNS resolution testing
- MAC randomization toggle
- Hostname privacy toggle
- Bandwidth and active connection summary

![Network Overview](images/user-guide/network-overview.png)

### Loofi Link

Sub-tabs:

- Devices
- Clipboard
- File Drop

Common uses:

- Discover peers on local network
- Sync clipboard to selected peer
- Send files and handle incoming transfer decisions

## Security Category

### Security & Privacy

Main functional areas:

- Security score card
- Port auditor (scan + block)
- USB guard controls
- App sandbox controls
- Firewall actions
- Telemetry package removal helper
- Security update checks

![Security and Privacy](images/user-guide/security-privacy.png)

Operational tip:

- Run a score refresh after major system updates or network/profile changes.

## Desktop Category

### Desktop

Sub-tabs:

- Window Manager
- Theming

Typical uses:

- Compositor/window behavior adjustments
- Theme and desktop consistency controls

### Profiles

Common tasks:

- Apply built-in profile
- Create custom profile from current state
- Export/import single profiles
- Export/import profile bundles

Use profiles when moving between battery-saving and performance-heavy contexts.

### Gaming

- Gaming-focused optimization shortcuts and helper actions.

## Tools Category

### AI Lab

Sub-tabs:

- Models
- Voice
- Knowledge

Models:

- View installed models
- Download from catalog
- Check RAM fit

Voice:

- Record and transcribe flow

Knowledge:

- Build/clear index
- Scan indexable files
- Query indexed content

![AI Lab Models](images/user-guide/ai-lab-models.png)

### State Teleport

- Capture workspace state packages
- List captured packages
- Restore selected package

### Diagnostics

Sub-tabs:

- Watchtower
- Boot

Watchtower:

- Service status/actions
- Boot-time summary
- Error and failure overview
- Support bundle export

Boot:

- Kernel parameter management
- ZRAM controls
- Secure Boot/MOK workflows

### Community

Sub-tabs:

- Presets
- Marketplace
- Plugins

Presets:

- Save/load/delete local presets
- Import/export and gist sync

Marketplace:

- Search/filter community presets
- Download and apply presets
- Drift detection against baseline

Plugins:

- View loaded plugins
- Enable/disable installed plugins

![Community Presets](images/user-guide/community-presets.png)

![Community Marketplace](images/user-guide/community-marketplace.png)

## Settings Category

### Settings

Sub-tabs:

- Appearance
- Behavior
- Advanced

What persists:

- Theme mode
- Start minimized
- Desktop notifications
- Dangerous action confirmations
- Restore last tab
- Log level
- Update checks on startup

Settings are stored in `~/.config/loofi-fedora-tweaks/settings.json`.

![Settings Appearance](images/user-guide/settings-appearance.png)

---

## Plugin Marketplace and Community Features

There are two related but different concepts:

- **Community preset marketplace** (inside Community tab): configuration presets.
- **Plugin marketplace** (`plugin-marketplace` CLI): installable plugins.

### Plugin Marketplace CLI Actions

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
loofi plugin-marketplace reviews cool-plugin --limit 10
loofi plugin-marketplace rating cool-plugin
```

Tip:

- Use `--accept-permissions` for non-interactive install flows.

---

## CLI Guide by Task

All examples below assume:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

### System Overview and Diagnostics

```bash
loofi info
loofi health
loofi doctor
loofi hardware
loofi support-bundle
```

### Monitoring and Investigation

```bash
loofi disk --details
loofi processes --sort cpu -n 15
loofi temperature
loofi netmon --connections
loofi logs show --since "1h ago" --lines 200
loofi logs errors --since "24h ago"
```

### Updates and Cleanup

```bash
loofi cleanup all
loofi cleanup dnf
loofi cleanup journal --days 7
loofi cleanup trim
```

### Hardware and Performance

```bash
loofi tweak power --profile balanced
loofi tweak battery --limit 80
loofi advanced swappiness --value 15
loofi tuner analyze
loofi tuner apply
```

### Service and Package Administration

```bash
loofi service list --filter failed
loofi service restart sshd
loofi service logs sshd --lines 100
loofi package search --query podman --source all
loofi package install vim
```

### Security and Network

```bash
loofi security-audit
loofi firewall status
loofi firewall open-port 8080/tcp
loofi network dns --provider cloudflare
```

### Storage, Bluetooth, and Snapshots

```bash
loofi storage disks
loofi storage smart /dev/sda
loofi storage trim
loofi bluetooth devices
loofi bluetooth scan --timeout 10
loofi snapshot backends
loofi snapshot create --label before-major-change
```

### Automation and Power Features

```bash
loofi agent list
loofi agent create --goal "keep my system clean"
loofi vm list
loofi vfio check
loofi mesh discover
loofi teleport capture --path ~/workspace --target laptop
```

### JSON Output for Scripts

```bash
loofi --json info
loofi --json health
loofi --json package search --query firefox
```

---

## Configuration and Data Locations

Main user paths:

- `~/.config/loofi-fedora-tweaks/profile.json`
- `~/.config/loofi-fedora-tweaks/first_run_complete`
- `~/.config/loofi-fedora-tweaks/settings.json`
- `~/.local/share/loofi-fedora-tweaks/startup.log`

For support/debug captures:

```bash
loofi support-bundle
journalctl --user --since "1 hour ago"
```

---

## Troubleshooting and Support

Recommended escalation order:

1. Run diagnostics:
   - `loofi doctor`
   - `loofi info`
2. Export support bundle:
   - `loofi support-bundle`
3. Check detailed troubleshooting:
   - `docs/TROUBLESHOOTING.md`
4. Open GitHub issue with:
   - Fedora version + desktop environment
   - exact tab/command used
   - expected vs actual result
   - logs/support bundle details

Issue tracker: <https://github.com/loofitheboss/loofi-fedora-tweaks/issues>

---

## Screenshot Gallery

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
