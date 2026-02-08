# Loofi Fedora Tweaks - User Guide

> **Version 12.0.0 "Sovereign Update"**
> Complete documentation for all features and functionality.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [First-Run Wizard (v10.0)](#first-run-wizard)
3. [Command Palette (v10.0)](#command-palette)
4. [Dashboard](#dashboard)
5. [System Monitor](#system-monitor)
6. [Maintenance](#maintenance)
7. [Hardware](#hardware)
8. [Software](#software)
9. [Security & Privacy](#security--privacy)
10. [Network](#network)
11. [Gaming](#gaming)
12. [Desktop](#desktop)
13. [Development](#development)
14. [AI Lab](#ai-lab)
15. [Automation](#automation)
16. [Community](#community)
17. [Diagnostics](#diagnostics)
18. [Virtualization](#virtualization)
19. [Loofi Link](#loofi-link)
20. [State Teleport](#state-teleport)
21. [CLI Reference](#cli-reference)
22. [All Tabs Overview](#all-tabs-overview)
23. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# One-command install
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

### Launch

```bash
# GUI Mode
loofi-fedora-tweaks

# CLI Mode
loofi info
loofi cleanup
```

---

## First-Run Wizard

On first launch, the **First-Run Wizard** guides you through initial setup:

| Step | Description |
|------|-------------|
| **System Detection** | Auto-detects hardware via DMI sysfs (HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS, etc.) |
| **Use Case Selection** | Choose your primary use case (Development, Gaming, Creative Work, Office) |
| **Apply Profile** | Saves `~/.config/loofi-fedora-tweaks/profile.json` with your preferences |

The wizard runs once and creates `~/.config/loofi-fedora-tweaks/first_run_complete` as a sentinel.

---

## Command Palette

Press **Ctrl+K** anywhere in the application to open the Command Palette.

| Feature | Description |
|---------|-------------|
| **Fuzzy Search** | Type to filter 60+ feature entries by name, category, or keyword |
| **Keyboard Navigation** | Up/Down arrows to browse, Enter to activate, Escape to close |
| **Scored Results** | Results ranked by relevance (exact > starts-with > contains > fuzzy) |
| **Tab Switching** | Select any entry to jump directly to the corresponding tab |

---

## Dashboard

The **Dashboard** (Home tab) is your system health overview:

| Card | Description |
|------|-------------|
| **CPU Usage** | Current CPU utilization percentage |
| **Memory** | RAM usage (used/total) |
| **Disk Space** | Storage utilization |

### Quick Actions

| Button | Action |
|--------|--------|
| **Run Cleanup** | Clean DNF cache, vacuum journal, TRIM SSD |
| **Check Updates** | Check for system updates |
| **Apply Preset** | Apply your saved configuration preset |

### Auto-Refresh

The dashboard auto-refreshes every 5 seconds with live system health:

| Indicator | Description |
|-----------|-------------|
| **CPU Load** | Real-time CPU usage with color-coded status (green/yellow/red) |
| **Memory** | Current RAM usage updated automatically |
| **Disk** | Disk space utilization |

---

## System Monitor

The **System Monitor** tab consolidates Performance and Process management (previously two separate tabs).

### Performance Sub-Tab

Real-time system performance graphs with 60-second rolling history:

| Graph | Data Source | Description |
|-------|------------|-------------|
| **CPU Usage** | `/proc/stat` | Per-core and total CPU utilization |
| **Memory** | `/proc/meminfo` | Used, cached, and available RAM |
| **Disk I/O** | `/proc/diskstats` | Read/write throughput in MB/s |
| **Network I/O** | `/proc/net/dev` | Upload/download bandwidth |

All data collected from `/proc` — no external dependencies required.

### Processes Sub-Tab

Monitor and manage running processes:

| Column | Description |
|--------|-------------|
| **PID** | Process ID |
| **Name** | Process name |
| **User** | Process owner |
| **CPU %** | CPU usage |
| **Memory %** | RAM percentage |
| **Memory** | Absolute memory (human-readable) |
| **State** | R=Running, S=Sleeping, Z=Zombie |

**Context Menu (Right-Click):**

| Action | Description |
|--------|-------------|
| **Kill (SIGTERM)** | Gracefully terminate |
| **Force Kill (SIGKILL)** | Forcefully terminate |
| **Renice** | Change priority (-20 to 19) |

---

## Maintenance

The **Maintenance** tab consolidates Updates, Cleanup, and Overlays (previously three separate tabs).

### Updates Sub-Tab

| Feature | Description |
|---------|-------------|
| **DNF Updates** | Check and install system package updates |
| **Flatpak Updates** | Update all Flatpak applications |
| **Atomic Updates** | rpm-ostree upgrade (on Atomic variants) |

### Cleanup Sub-Tab

| Feature | Description |
|---------|-------------|
| **DNF Cache** | Clean package manager cache |
| **Journal Vacuum** | Reduce systemd journal size |
| **SSD TRIM** | Run fstrim on SSD drives |
| **Orphan Removal** | Remove unneeded packages |

### Overlays Sub-Tab (Atomic only)

| Feature | Description |
|---------|-------------|
| **Layered Packages** | View and manage rpm-ostree overlays |
| **Add/Remove** | Install or remove layered packages |

This sub-tab is only shown on Atomic Fedora variants (Silverblue, Kinoite).

---

## Hardware

The **Hardware** tab now includes all hardware controls plus features previously in the HP Tweaks tab, made hardware-agnostic.

| Feature | Description |
|---------|-------------|
| **CPU Governor** | Toggle powersave/schedutil/performance |
| **Power Profile** | Switch power-saver/balanced/performance |
| **GPU Mode** | Integrated/Hybrid/Dedicated via envycontrol |
| **Fan Control** | Manual slider and auto mode via nbfc-linux |
| **Audio Fixes** | PulseAudio/PipeWire configuration for hardware-specific issues |
| **Battery Limit** | Set charge limit (80%/100%) with systemd persistence |
| **Fingerprint** | Fingerprint enrollment wizard via fprintd |

Hardware profiles auto-detected via DMI sysfs data. Supported profiles:

| Profile | Detection |
|---------|-----------|
| **HP EliteBook** | Product name contains "EliteBook" |
| **HP ProBook** | Product name contains "ProBook" |
| **ThinkPad** | Product name contains "ThinkPad" |
| **Dell XPS** | Product name contains "XPS" |
| **Dell Latitude** | Product name contains "Latitude" |
| **Framework** | Manufacturer contains "Framework" |
| **ASUS ZenBook** | Product name contains "ZenBook" |
| **Generic Laptop** | Chassis type 9/10 (laptop) |
| **Generic Desktop** | Fallback for unrecognized hardware |

---

## Software

The **Software** tab consolidates Apps and Repos (previously two separate tabs).

### Applications Sub-Tab

One-click installation for popular applications:

| Category | Examples |
|----------|----------|
| **Browsers** | Chrome, Firefox additions |
| **Development** | VS Code, JetBrains |
| **Communication** | Discord, Slack, Zoom |
| **Media** | Spotify, VLC, OBS Studio |

### Repositories Sub-Tab

| Feature | Description |
|---------|-------------|
| **RPM Fusion** | Enable Free/Nonfree repos |
| **Flathub** | Enable Flatpak repository |
| **Multimedia Codecs** | Install codec packages |

---

## Security & Privacy

The **Security & Privacy** tab merges the Security Center and Privacy features.

| Feature | Description |
|---------|-------------|
| **Security Score** | 0-100 health rating with recommendations |
| **Port Auditor** | Find risky open ports, block with firewall |
| **USB Guard** | Whitelist/blacklist USB devices |
| **Sandbox** | Firejail/Bubblewrap app isolation |
| **Firewall** | Manage firewalld rules |
| **Telemetry** | Disable system telemetry and trackers |
| **Security Updates** | Automatic security update configuration |

---

## Network

| Feature | Description |
|---------|-------------|
| **DNS Switcher** | Google, Cloudflare, Quad9 |
| **MAC Randomization** | Random MAC per connection |
| **Firewall Rules** | Basic firewalld management |

---

## Gaming

| Feature | Description |
|---------|-------------|
| **GameMode** | Install and configure Feral GameMode |
| **MangoHud** | FPS overlay for Vulkan/OpenGL |
| **ProtonUp-Qt** | Manage Proton-GE versions |
| **Steam Devices** | Install udev rules for controllers |

---

## Desktop

The **Desktop** tab consolidates Director (window management) and Theming.

### Window Manager Sub-Tab

| Feature | Description |
|---------|-------------|
| **Compositor Detection** | Auto-detect KDE Plasma, Hyprland, Sway |
| **Tiling Presets** | Vim (H/J/K/L) or Arrow key bindings |
| **Workspace Templates** | Development, Gaming, Creative layouts |
| **Dotfile Sync** | Git-based config backup |
| **KWin Scripts** | Custom tiling scripts for KDE Plasma |

### Theming Sub-Tab

| Feature | Description |
|---------|-------------|
| **GTK Themes** | Configure GTK application themes |
| **Qt Themes** | Configure Qt application themes |
| **Icon Packs** | Install and switch icon themes |

---

## Development

The **Development** tab consolidates Containers and Developer Tools.

### Containers Sub-Tab

| Feature | Description |
|---------|-------------|
| **Container List** | View Distrobox containers with status |
| **Create Container** | Select from popular images (Fedora, Ubuntu, Arch) |
| **Context Menu** | Enter, Stop, Delete, Open Terminal |
| **Export Apps** | Export applications from containers to host |

### Developer Tools Sub-Tab

**Language Version Managers:**

| Tool | Description |
|------|-------------|
| **PyEnv** | Multiple Python versions |
| **NVM** | Node.js version manager |
| **Rustup** | Rust toolchain installer |

**VS Code Extension Profiles:**

| Profile | Extensions |
|---------|-----------|
| **Python** | pylance, debugpy, black, jupyter, ruff |
| **C/C++** | cpptools, cmake-tools, clang-format |
| **Rust** | rust-analyzer, toml, lldb |
| **Web** | prettier, eslint, tailwindcss |

---

## AI Lab

The **AI Lab** tab has been enhanced with three sub-tabs in v12.0.

### Models Sub-Tab

| Feature | Description |
|---------|-------------|
| **Hardware Detection** | CUDA, ROCm, Intel/AMD NPU support |
| **Ollama Manager** | Install, manage, and run local AI |
| **Lite Model Library** | Curated GGUF models (Llama 3.2, Mistral, Gemma, Phi-3) |
| **RAM Recommendations** | Auto-suggest models based on available system RAM |
| **One-Click Download** | Download models with progress tracking |

### Voice Sub-Tab (v11.2)

| Feature | Description |
|---------|-------------|
| **whisper.cpp** | Local speech-to-text transcription |
| **Model Selection** | tiny/base/small/medium whisper models |
| **Microphone Check** | Verify recording device availability |
| **Record & Transcribe** | Record audio and get text transcription |

### Knowledge Sub-Tab (v11.3)

| Feature | Description |
|---------|-------------|
| **Context RAG** | TF-IDF local file indexing for AI assistance |
| **Indexable Paths** | Scans bash_history, bashrc, zshrc, config directories |
| **Security Filtering** | Skips sensitive files, binary files, enforces size limits |
| **Keyword Search** | Search your indexed files with relevance scoring |

---

## Automation

The **Automation** tab consolidates Scheduler, Replicator, and Pulse features.

### Scheduler Sub-Tab

| Feature | Description |
|---------|-------------|
| **Task Scheduling** | Create automated tasks with time or event triggers |
| **Power Triggers** | Execute on battery/AC transitions |
| **Boot Triggers** | Run tasks at login |

### Replicator Sub-Tab

| Feature | Description |
|---------|-------------|
| **Ansible Export** | Generate playbooks with packages, Flatpaks, GNOME settings |
| **Kickstart Export** | Create Anaconda .ks files for automated installs |

### Pulse Events (v9.1)

| Feature | Description |
|---------|-------------|
| **Event-Driven Automation** | React to hardware, network, and system events |
| **Focus Mode** | Domain blocking, DND, process killing |
| **Automation Profiles** | Rules that trigger actions on system events |

---

## Community

The **Community** tab consolidates Presets and Marketplace.

### My Presets Sub-Tab

| Feature | Description |
|---------|-------------|
| **Save Preset** | Save current system configuration |
| **Load Preset** | Apply a saved preset |
| **Cloud Sync** | Sync to GitHub Gist |

### Marketplace Sub-Tab

| Feature | Description |
|---------|-------------|
| **Browse** | Search community presets by category |
| **Download** | Save presets locally |
| **Drift Detection** | Track configuration changes from baseline |

### Plugins Sub-Tab

| Feature | Description |
|---------|-------------|
| **List Plugins** | View installed plugins and metadata |
| **Enable/Disable** | Toggle plugins without uninstalling |

---

## Diagnostics

The **Diagnostics** tab consolidates Watchtower and Boot management.

### Services Sub-Tab

| Feature | Description |
|---------|-------------|
| **Gaming Filter** | Show only gaming-related services |
| **Failed Filter** | Find services that failed to start |
| **Context Menu** | Start, Stop, Restart, Mask, Unmask |

### Boot Analyzer Sub-Tab

| Feature | Description |
|---------|-------------|
| **Boot Stats** | Firmware, loader, kernel, userspace timing |
| **Slow Services** | List services taking >5s to start |
| **Suggestions** | Optimization recommendations |

### Journal Viewer Sub-Tab

| Feature | Description |
|---------|-------------|
| **Quick Diagnostic** | Error count and failed services at a glance |
| **Boot Errors** | View current boot errors |
| **Panic Button** | Export forum-ready log with system info |

---

## Virtualization

The **Virtualization** tab (v11.5) provides full KVM/QEMU virtual machine management.

### VMs Sub-Tab

| Feature | Description |
|---------|-------------|
| **VM List** | View all VMs with state, RAM, and vCPU info |
| **Quick-Create Wizard** | One-click VMs from preset flavors |
| **Start/Stop Controls** | Manage VM lifecycle |
| **Delete** | Remove VMs with storage cleanup |

**Preset Flavors:**

| Flavor | Description |
|--------|-------------|
| **Windows 11** | Auto-TPM, virtio drivers, 4GB RAM, 2 vCPUs |
| **Fedora** | Latest Fedora with virtio, 2GB RAM |
| **Ubuntu** | Ubuntu LTS with virtio, 2GB RAM |
| **Kali** | Kali Linux for security testing, 2GB RAM |
| **Arch** | Minimal Arch Linux, 1GB RAM |

### GPU Passthrough Sub-Tab

| Feature | Description |
|---------|-------------|
| **Prerequisites Check** | CPU virt extensions, KVM, IOMMU verification |
| **GPU Candidates** | List GPUs available for passthrough with IOMMU groups |
| **Step-by-Step Plan** | Generated kernel args, dracut config, modprobe config |

### Disposable Sub-Tab

| Feature | Description |
|---------|-------------|
| **Base Images** | Create QCOW2 base images for disposable VMs |
| **Snapshot Overlays** | Launch throwaway VMs from overlay snapshots |
| **Auto-Cleanup** | Destroy overlay on VM shutdown |

---

## Loofi Link

The **Loofi Link** tab (v12.0) enables mesh networking between devices on the same LAN.

### Devices Sub-Tab

| Feature | Description |
|---------|-------------|
| **Device Discovery** | Find nearby devices via Avahi mDNS |
| **Device ID** | Unique identifier for this machine |
| **Peer Status** | Check if discovered peers are online |

### Clipboard Sub-Tab

| Feature | Description |
|---------|-------------|
| **Clipboard Sync** | Share clipboard content between paired devices |
| **Encryption** | AES-encrypted payload with shared pairing key |
| **Display Server** | Auto-detects X11 (xclip/xsel) or Wayland (wl-copy) |

### File Drop Sub-Tab

| Feature | Description |
|---------|-------------|
| **File Transfer** | Send files to nearby devices via local HTTP |
| **Checksum Verification** | SHA-256 integrity check on received files |
| **Filename Sanitization** | Security filtering of transferred filenames |
| **Size Limits** | Configurable transfer size limits |

---

## State Teleport

The **State Teleport** tab (v12.0) captures and restores workspace state across machines.

### Capture Section

| Feature | Description |
|---------|-------------|
| **VS Code State** | Open files, extensions, workspace settings |
| **Git State** | Branch, remote, recent commits, uncommitted changes |
| **Terminal State** | Working directory, environment variables (security-filtered) |
| **Full Capture** | One-click capture of all workspace state |

### Saved States Section

| Feature | Description |
|---------|-------------|
| **Package List** | View saved teleport packages with metadata |
| **Size Info** | Package size in bytes |
| **Source Device** | Which machine the state was captured from |

### Restore Section

| Feature | Description |
|---------|-------------|
| **Apply Teleport** | Restore workspace state from a package |
| **Security Filtering** | Filters env vars with KEY/SECRET/TOKEN/PASSWORD |
| **Selective Restore** | Choose which state components to restore |

---

## CLI Reference

### Info & Health

```bash
loofi info                    # System information
loofi health                  # System health check
loofi doctor                  # Check tool dependencies
loofi hardware                # Show detected hardware profile
```

### Monitoring

```bash
loofi disk                    # Disk usage analysis
loofi disk --details          # Include large directory listing
loofi processes               # Top 15 processes by CPU
loofi processes --sort memory # Sort by memory usage
loofi processes -n 25         # Show top 25 processes
loofi temperature             # Hardware temperature readings
loofi netmon                  # Network interface stats
loofi netmon --connections    # Include active connections
```

### Management

```bash
loofi cleanup                 # Full cleanup
loofi cleanup dnf             # DNF cache only
loofi cleanup journal         # Journal vacuum
loofi tweak power --profile performance
loofi tweak power --profile balanced
loofi tweak battery --limit 80
loofi network dns --provider cloudflare
loofi network dns --provider google
loofi advanced bbr            # Enable TCP BBR
loofi advanced swappiness 10  # Set swappiness
```

### Virtualization & Networking (v12.0)

```bash
loofi vm list                 # List virtual machines
loofi vm status myvm          # Show VM details
loofi vm start myvm           # Start a VM
loofi vm stop myvm            # Stop a VM
loofi vfio check              # Check VFIO prerequisites
loofi vfio gpus               # List GPU passthrough candidates
loofi vfio plan               # Generate VFIO setup plan
loofi mesh discover           # Discover LAN devices
loofi mesh status             # Show device ID and local IPs
loofi teleport capture        # Capture workspace state
loofi teleport list           # List saved packages
loofi teleport restore <id>   # Restore a package
loofi ai-models list          # List AI models
loofi ai-models recommend     # RAM-based model recommendation
```

### JSON Output (v10.0)

```bash
loofi --json info             # JSON system information
loofi --json health           # JSON health check
loofi --json doctor           # JSON dependency check
loofi --json hardware         # JSON hardware profile
```

### Daemon Mode

```bash
loofi-fedora-tweaks --daemon  # Run as background service
```

---

## All Tabs Overview

| Tab | Icon | Description |
|-----|------|-------------|
| **Home** | Home | Dashboard with system health |
| **System Info** | Info | Hardware specs, OS version |
| **System Monitor** | Chart | Live performance graphs + process manager |
| **Maintenance** | Wrench | Updates + cleanup + overlays |
| **Hardware** | Lightning | CPU, GPU, fan, power, battery, audio, fingerprint |
| **Software** | Package | One-click apps + repository management |
| **Security & Privacy** | Shield | Security score, ports, USB, firewall, telemetry |
| **Network** | Globe | DNS, firewall, MAC |
| **Gaming** | Controller | GameMode, MangoHud, ProtonUp |
| **Desktop** | Palette | Window management + theming |
| **Development** | Tools | Containers + developer toolchains |
| **AI Lab** | Brain | Ollama, model management |
| **Automation** | Clock | Scheduler + replicator + pulse events |
| **Community** | Globe | Presets + marketplace |
| **Diagnostics** | Telescope | Services + boot + journal |
| **Virtualization** | Desktop | VM wizard + VFIO + disposable VMs |
| **Loofi Link** | Link | Mesh discovery + clipboard + file drop |
| **State Teleport** | Satellite | Workspace capture + restore |

---

## Troubleshooting

### App Won't Launch

```bash
pip install PyQt6
python3 main.py
```

### Permission Denied

```bash
sudo dnf install polkit
```

### Check Dependencies

```bash
loofi doctor
```

The `doctor` command checks for all critical and optional tools and reports what's missing.

### Panic Log for Support

Use **Diagnostics** > **Journal** > **Export Panic Log** to generate a forum-ready diagnostic file.

### Support Bundle

Use **Diagnostics** > **Journal** > **Export Support Bundle** to generate a ZIP with logs and system info.

### Reset First-Run Wizard

```bash
rm ~/.config/loofi-fedora-tweaks/first_run_complete
```

Relaunch the app to trigger the wizard again.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/loofitheboss/loofi-fedora-tweaks/issues)
- **Releases**: [GitHub Releases](https://github.com/loofitheboss/loofi-fedora-tweaks/releases)

---

*Documentation last updated: v12.0.0 - February 2026*
