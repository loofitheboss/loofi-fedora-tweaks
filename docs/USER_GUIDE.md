# Loofi Fedora Tweaks - User Guide

> **Version 17.0.0 "Atlas"**
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
21. [Profiles](#profiles)
22. [Health Timeline](#health-timeline)
23. [Performance Auto-Tuner](#performance-auto-tuner)
24. [System Snapshot Timeline](#system-snapshot-timeline)
25. [Smart Log Viewer](#smart-log-viewer)
26. [Quick Actions Bar](#quick-actions-bar)
27. [Service Explorer](#service-explorer)
28. [Package Explorer](#package-explorer)
29. [Firewall Manager](#firewall-manager)
30. [Bluetooth Manager](#bluetooth-manager)
31. [Storage & Disks](#storage--disks)
32. [CLI Reference](#cli-reference)
33. [All Tabs Overview](#all-tabs-overview)
34. [Troubleshooting](#troubleshooting)

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

# Web API Mode (v20.0 preview)
loofi-fedora-tweaks --web
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

### Quick Actions Bar (v15.0)

Press **Ctrl+Shift+K** to open the Quick Actions Bar — a floating searchable palette for power users.

| Feature | Description |
|---------|-------------|
| **15+ Actions** | Across 5 categories: System, Package, Service, Monitor, Tools |
| **Fuzzy Search** | Type to filter actions instantly |
| **Recent Actions** | Recently used actions appear at the top (max 10) |
| **Plugin-Extensible** | Plugins can register custom actions via `QuickActionRegistry` |

---

## Dashboard

The **Dashboard** (Home tab) is your system health overview with live metrics:

### Live Metrics (v16.0)

| Widget | Description |
|--------|-------------|
| **CPU Sparkline** | 30-point area chart showing recent CPU usage (2s refresh) |
| **RAM Sparkline** | 30-point area chart showing memory utilization (2s refresh) |
| **Network Speed** | Real-time download/upload speed from `/proc/net/dev` |
| **Storage Breakdown** | Per-mount-point usage bars, color-coded by utilization |
| **Top Processes** | Top 5 processes by CPU usage |
| **Recent Actions** | Last 5 actions from the History log |

### Quick Actions

| Button | Action |
|--------|--------|
| **Run Cleanup** | Navigate to Maintenance tab for cleanup operations |
| **Check Updates** | Navigate to Maintenance tab for update checking |
| **Apply Preset** | Navigate to Hardware tab for hardware profiles |
| **Security Scan** | Navigate to Security & Privacy tab |

### Auto-Refresh

| Timer | Interval | Updates |
|-------|----------|--------|
| **Fast** | 2 seconds | CPU sparkline, RAM sparkline, network speed |
| **Slow** | 10 seconds | Storage breakdown, top processes, recent actions |

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

The **Network** tab (v17.0 overhaul) provides comprehensive network management with 4 sub-tabs.

### Connections Sub-Tab

| Feature | Description |
|---------|-------------|
| **WiFi Networks** | Scan and view available WiFi networks via nmcli |
| **VPN Status** | List active VPN connections |
| **Connect/Disconnect** | Connect to WiFi or VPN from the interface |

### DNS Sub-Tab

| Feature | Description |
|---------|-------------|
| **Cloudflare** | 1.1.1.1 / 1.0.0.1 |
| **Google** | 8.8.8.8 / 8.8.4.4 |
| **Quad9** | 9.9.9.9 / 149.112.112.112 |
| **AdGuard** | 94.140.14.14 / 94.140.15.15 |
| **DHCP Default** | Reset to automatic DNS |

### Privacy Sub-Tab

| Feature | Description |
|---------|-------------|
| **MAC Randomization** | Per-connection random MAC address |

### Monitoring Sub-Tab

| Feature | Description |
|---------|-------------|
| **Interface Stats** | RX/TX bytes, packets per interface |
| **Active Connections** | Current network connections via nmcli |
| **Auto-Refresh** | Periodic refresh of stats |

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

## Profiles

The **Profiles** tab (v13.0) enables quick-switching between system configurations.

### Available Profiles

| Profile | Description |
|---------|-------------|
| **Gaming** | Performance governor, compositor disabled, DND notifications, gamemode enabled |
| **Development** | Schedutil governor, Docker/Podman services enabled, all notifications |
| **Battery Saver** | Powersave governor, reduced compositor, critical notifications only, Bluetooth disabled |
| **Presentation** | Performance governor, screen timeout disabled, DND mode |
| **Server** | Performance governor, headless optimization, critical notifications |

### Profile Actions

| Feature | Description |
|---------|-------------|
| **View Profiles** | See all built-in and custom profiles with icons and descriptions |
| **Apply Profile** | One-click profile activation with confirmation |
| **Create Custom** | Define your own profile with custom CPU governor, compositor, and notification settings |
| **Capture Current** | Save current system state as a new profile |
| **Delete Custom** | Remove user-created profiles (built-in profiles cannot be deleted) |

### Profile Settings

When creating or applying a profile, the following settings can be configured:

| Setting | Options |
|---------|---------|
| **CPU Governor** | performance, powersave, schedutil, ondemand, conservative |
| **Compositor** | enabled, disabled, reduced |
| **Notifications** | all, critical, dnd (Do Not Disturb) |
| **Swappiness** | 0-100 (lower = less swap usage) |
| **Services** | Enable/disable specific systemd services |

### CLI Usage

```bash
loofi profile list              # List all profiles
loofi profile apply gaming      # Apply the gaming profile
loofi profile create myprofile  # Capture current state as "myprofile"
loofi profile delete myprofile  # Delete a custom profile
loofi --json profile list       # JSON output for scripting
```

---

## Health Timeline

The **Health Timeline** tab (v13.0) tracks system health metrics over time.

### Tracked Metrics

| Metric | Source | Unit |
|--------|--------|------|
| **CPU Temperature** | `/sys/class/thermal` or `sensors` | Degrees Celsius |
| **RAM Usage** | `/proc/meminfo` | Percentage |
| **Disk Usage** | `os.statvfs("/")` | Percentage |
| **Load Average** | `os.getloadavg()` | 1-minute average |

### Summary View

The summary shows min/max/avg statistics for each metric over the last 24 hours.

### Actions

| Feature | Description |
|---------|-------------|
| **Record Snapshot** | Capture current system metrics immediately |
| **Export Data** | Export all metrics to JSON or CSV file |
| **Prune Old Data** | Delete metrics older than 30 days |
| **Refresh** | Update summary and table displays |

### Anomaly Detection

The timeline can detect anomalies - values that deviate more than 2 standard deviations from the mean:

| Field | Description |
|-------|-------------|
| **Timestamp** | When the anomaly occurred |
| **Value** | The anomalous metric value |
| **Deviation** | How many standard deviations from the mean |
| **Mean** | The average value for this metric type |

### Table View

Filter metrics by type and time range:

| Column | Description |
|--------|-------------|
| **Timestamp** | When the metric was recorded |
| **Value** | Metric value |
| **Unit** | Unit of measurement |
| **ID** | Database row ID |

### CLI Usage

```bash
loofi health-history show             # Show 24h summary
loofi health-history record           # Record current metrics
loofi health-history export data.json # Export to JSON
loofi health-history export data.csv  # Export to CSV
loofi health-history prune            # Delete old data
loofi --json health-history show      # JSON output for scripting
```

---

## Performance Auto-Tuner

The **Performance Auto-Tuner** (v15.0) analyzes system workload and recommends optimal kernel and hardware settings.

### Workload Detection

The tuner reads CPU load, memory pressure, and I/O wait to classify the current workload:

| Workload | Detection Criteria | Description |
|----------|-------------------|-------------|
| **Idle** | CPU < 10%, Mem < 30% | System is mostly idle |
| **Desktop** | CPU < 50%, Mem < 60% | Normal desktop usage |
| **Compilation** | CPU > 70%, I/O wait high | Heavy compilation or build tasks |
| **Gaming** | CPU > 60%, Mem > 50% | Gaming or GPU-intensive workload |
| **Server** | Mem > 70%, I/O > 40% | Server or database workload |

### Recommended Settings

| Setting | Description | Range |
|---------|-------------|-------|
| **CPU Governor** | Kernel frequency scaling policy | powersave, schedutil, performance |
| **Swappiness** | How aggressively the kernel swaps | 0-100 |
| **I/O Scheduler** | Block device scheduling algorithm | mq-deadline, none, bfq |
| **THP (Transparent Huge Pages)** | Large memory page allocation | always, madvise, never |

### Tuning Presets

| Workload | Governor | Swappiness | I/O Scheduler | THP |
|----------|----------|-----------|---------------|-----|
| **Idle** | powersave | 60 | mq-deadline | always |
| **Desktop** | schedutil | 45 | mq-deadline | always |
| **Compilation** | performance | 10 | none | madvise |
| **Gaming** | performance | 10 | none | never |
| **Server** | schedutil | 30 | mq-deadline | madvise |

### Actions

| Feature | Description |
|---------|-------------|
| **Analyze** | Detect current workload and show recommendations |
| **Apply** | Apply recommendations with pkexec privilege escalation |
| **History** | View past tuning actions with timestamps |

### CLI Usage

```bash
loofi tuner analyze           # Detect workload and show recommendations
loofi tuner apply             # Apply recommended optimizations
loofi tuner history           # View tuning history
loofi --json tuner analyze    # JSON output for scripting
```

---

## System Snapshot Timeline

The **System Snapshot Timeline** (v15.0) provides unified snapshot management across multiple backends.

### Supported Backends

| Backend | Detection | Operations |
|---------|-----------|-----------|
| **Snapper** | `shutil.which("snapper")` | list, create, delete, retention |
| **Timeshift** | `shutil.which("timeshift")` | list, create, delete, retention |
| **BTRFS** | `shutil.which("btrfs")` | list subvolumes |

### Snapshot Information

Each snapshot displays:

| Field | Description |
|-------|-------------|
| **ID** | Unique snapshot identifier |
| **Description** | User-provided or auto-generated description |
| **Timestamp** | When the snapshot was created |
| **Backend** | Which tool created it (snapper/timeshift/btrfs) |
| **Cleanup** | Retention policy (timeline, number, manual) |

### Actions

| Feature | Description |
|---------|-------------|
| **List** | View all snapshots across all backends |
| **Create** | Create a new snapshot with description |
| **Delete** | Remove a snapshot by ID |
| **Backends** | Show detected backends and their status |
| **Retention** | Apply retention policies to trim old snapshots |

### CLI Usage

```bash
loofi snapshot list            # List all snapshots
loofi snapshot create          # Create a new snapshot
loofi snapshot delete <id>     # Delete a snapshot
loofi snapshot backends        # List available backends
loofi --json snapshot list     # JSON output for scripting
```

---

## Smart Log Viewer

The **Smart Log Viewer** (v15.0) analyzes systemd journal entries and detects common error patterns.

### Built-in Error Patterns

| Pattern | Severity | Description |
|---------|----------|-------------|
| **OOM Killer** | critical | Out-of-memory events killing processes |
| **Segfault** | error | Segmentation faults in applications |
| **Disk Full** | critical | Filesystem out of space |
| **Auth Failure** | warning | Failed login or authentication attempts |
| **Service Failed** | error | Systemd services failing to start |
| **USB Disconnect** | info | USB device unexpected disconnections |
| **Kernel Panic** | critical | Kernel panic or oops events |
| **NetworkManager** | warning | Network connectivity issues |
| **Thermal Throttle** | warning | CPU thermal throttling events |
| **Firmware Error** | error | Firmware/BIOS errors in dmesg |

### Filters

| Filter | Description |
|--------|-------------|
| **Unit** | Filter by systemd unit name (e.g., `sshd`, `docker`) |
| **Priority** | Filter by syslog priority (0=emergency to 7=debug) |
| **Since** | Time range (e.g., `1h`, `24h`, `7d`, `today`) |
| **Lines** | Maximum number of log entries to return |

### Actions

| Feature | Description |
|---------|-------------|
| **Show Logs** | View journal entries with optional filters |
| **Error Summary** | Get pattern-matched error overview with counts |
| **Export** | Export filtered logs to a text file |
| **Unit List** | Browse available systemd units |

### CLI Usage

```bash
loofi logs show                        # Show recent journal entries
loofi logs show --unit sshd --lines 50 # Filter by unit and limit
loofi logs show --priority 3           # Show errors and above
loofi logs show --since 1h             # Entries from last hour
loofi logs errors                      # Show error summary with patterns
loofi logs export /tmp/logs.txt        # Export filtered logs
loofi --json logs errors               # JSON output for scripting
```

---

## Quick Actions Bar

The **Quick Actions Bar** (v15.0) is a floating command palette triggered by **Ctrl+Shift+K**.

### Default Actions (15+)

| Category | Actions |
|----------|---------|
| **System** | System Update, System Cleanup, System Info |
| **Package** | Install Package, Remove Package, Search Packages |
| **Service** | Restart Service, Stop Service, Service Status |
| **Monitor** | CPU Monitor, Memory Monitor, Disk Usage |
| **Tools** | Open Terminal, File Manager, System Settings |

### Features

| Feature | Description |
|---------|-------------|
| **Fuzzy Search** | Type to filter actions by name, category, or keyword |
| **Recent Actions** | Recently used actions appear first (max 10) |
| **Category Filter** | Filter by action category |
| **Plugin Actions** | Plugins can register custom actions via `QuickActionRegistry` |

### Extending with Plugins

```python
from ui.quick_actions import QuickActionRegistry, QuickAction

registry = QuickActionRegistry()
registry.register(QuickAction(
    name="My Custom Action",
    description="Does something useful",
    category="My Plugin",
    callback=my_function,
    icon="🔧"
))
```

---

## Service Explorer

*New in v16.0*

The **Service Explorer** provides a full systemd service browser and controller, accessible from the CLI.

### Listing Services

```bash
loofi service list                        # All system services
loofi service list --filter active        # Only active
loofi service list --filter failed        # Only failed
loofi service list --search ssh           # Search by name/description
loofi service list --user                 # User-scope services
```

Output columns: Name, State (✅/❌/⬜), Enabled, Description.

### Service Control

All system-scope actions use `pkexec` for privilege escalation:

| Command | Action |
|---------|--------|
| `loofi service start <name>` | Start a service |
| `loofi service stop <name>` | Stop a service |
| `loofi service restart <name>` | Restart a service |
| `loofi service enable <name>` | Enable on boot |
| `loofi service disable <name>` | Disable on boot |
| `loofi service mask <name>` | Prevent starting entirely |
| `loofi service unmask <name>` | Allow starting again |

### Service Details & Logs

```bash
loofi service status sshd     # PID, memory, uptime, unit file path
loofi service logs sshd        # Last 50 journal lines
loofi service logs nginx --lines 200  # Custom count
```

---

## Package Explorer

*New in v16.0*

The **Package Explorer** provides unified package management across DNF/rpm-ostree and Flatpak.

### Searching

```bash
loofi package search --query vim          # Search all sources
```

Results show: Name, Version, Source (dnf/rpm-ostree/flatpak), Installed status, Summary.

### Install & Remove

```bash
loofi package install vim                 # Auto-detect source
loofi package install org.gnome.Calculator  # Detected as Flatpak
loofi package remove vim                  # Auto-detect installed source
```

Source detection logic:
- Names with 2+ dots (e.g. `org.gnome.Calculator`) → Flatpak
- On Atomic Fedora → rpm-ostree
- Otherwise → DNF

### Listing Packages

```bash
loofi package list                        # All installed packages
loofi package list --source flatpak       # Flatpak apps only
loofi package list --source dnf           # RPM packages only
loofi package list --search vim           # Filter by name/summary
loofi package recent                      # Installed in last 30 days
loofi package recent --days 7             # Custom time range
```

---

## Firewall Manager

*New in v16.0*

The **Firewall Manager** provides a CLI interface to firewalld.

### Status

```bash
loofi firewall status          # Running state, default zone, ports, services
```

### Port Management

```bash
loofi firewall ports                      # List open ports
loofi firewall open-port 8080/tcp         # Open a port (permanent + reload)
loofi firewall close-port 8080/tcp        # Close a port
```

### Service Management

```bash
loofi firewall services                   # List allowed services
```

### Zone Management

```bash
loofi firewall zones                      # List all zones with active flag
```

All write operations use `pkexec firewall-cmd` with `--permanent` and automatic reload.

---

## Bluetooth Manager

The **Bluetooth Manager** (v17.0) is integrated into the Hardware tab and provides full Bluetooth device management via `bluetoothctl`.

### Adapter Status

| Field | Description |
|-------|-------------|
| **Powered** | Whether the adapter is on |
| **Discoverable** | Whether the adapter is visible to other devices |
| **Pairable** | Whether the adapter accepts pairing requests |
| **Adapter Name** | Bluetooth adapter identifier |
| **Adapter Address** | MAC address of the adapter |

### Device Management

| Action | Description |
|--------|-------------|
| **Scan** | Discover nearby Bluetooth devices (configurable timeout) |
| **Pair** | Pair with a new device |
| **Connect** | Connect to a paired device |
| **Trust** | Mark a device as trusted (auto-connect) |
| **Block** | Block a device from connecting |
| **Unblock** | Remove a device from the block list |
| **Disconnect** | Disconnect a connected device |
| **Unpair** | Remove pairing with a device |

### Device Information

Each discovered device shows:
- **Address**: Bluetooth MAC address
- **Name**: Device display name
- **Battery**: Battery percentage (if supported)
- **Type**: audio, computer, input, phone, network, imaging, or other
- **State**: Paired, connected, trusted, blocked indicators

### CLI Usage

```bash
loofi bluetooth status         # Adapter info
loofi bluetooth devices        # List paired devices
loofi bluetooth scan           # Scan for nearby devices
loofi bluetooth pair <address> # Pair a device
loofi bluetooth connect <addr> # Connect to a device
loofi bluetooth disconnect <a> # Disconnect a device
loofi bluetooth trust <addr>   # Trust a device
loofi bluetooth power-on       # Turn adapter on
loofi bluetooth power-off      # Turn adapter off
```

---

## Storage & Disks

The **Storage & Disks** tab (v17.0) provides comprehensive disk management with the `StorageManager` backend.

### Block Devices

Lists all block devices via `lsblk`:

| Field | Description |
|-------|-------------|
| **Name** | Device name (e.g., sda, nvme0n1) |
| **Size** | Device size |
| **Type** | disk, part, rom, loop, etc. |
| **Mountpoint** | Where the device is mounted |
| **Removable** | Whether the device is removable |

### SMART Health

Reads SMART data via `smartctl`:

| Field | Description |
|-------|-------------|
| **Health Passed** | Whether the SMART health assessment passed |
| **Temperature** | Drive temperature in °C |
| **Model** | Drive model name |
| **Serial** | Drive serial number |
| **Firmware** | Firmware version |

### Mount Points

Lists mount points with usage from `df`:

| Field | Description |
|-------|-------------|
| **Source** | Device or filesystem source |
| **Target** | Mount point path |
| **Filesystem** | Filesystem type (ext4, btrfs, etc.) |
| **Size** | Total size |
| **Used** | Space used |
| **Available** | Space available |
| **Use%** | Usage percentage |

### Actions

| Action | Description |
|--------|-------------|
| **Check Filesystem** | Run fsck via pkexec (requires unmounted partition) |
| **SSD TRIM** | Run fstrim to optimize SSD performance |
| **Usage Summary** | Show aggregate disk usage overview |

### CLI Usage

```bash
loofi storage disks            # List block devices
loofi storage mounts           # List mount points with usage
loofi storage smart /dev/sda   # SMART health for a device
loofi storage trim             # Run SSD TRIM
loofi storage usage            # Disk usage summary
```

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

### Performance & Diagnostics (v15.0)

```bash
# Performance Tuner
loofi tuner analyze           # Detect workload and recommend settings
loofi tuner apply             # Apply recommended optimizations
loofi tuner history           # View tuning history

# Snapshot Management
loofi snapshot list            # List all snapshots
loofi snapshot create          # Create a new snapshot
loofi snapshot delete <id>     # Delete a snapshot
loofi snapshot backends        # List available backends

# Smart Logs
loofi logs show               # Show recent journal entries
loofi logs show --unit sshd   # Filter by systemd unit
loofi logs show --priority 3  # Filter by syslog priority
loofi logs show --since 1h    # Entries from last hour
loofi logs errors             # Show error summary with patterns
loofi logs export log.txt     # Export filtered logs
```

### Service, Package & Firewall Management (v16.0)

```bash
# Service Explorer
loofi service list             # List all systemd services
loofi service list --filter active  # Filter by state
loofi service list --search ssh     # Search by name/description
loofi service list --user      # Show user-scope services
loofi service start sshd       # Start a service (pkexec)
loofi service stop bluetooth   # Stop a service
loofi service restart nginx    # Restart a service
loofi service enable sshd      # Enable on boot
loofi service disable bluetooth  # Disable on boot
loofi service mask cups        # Prevent service from starting
loofi service unmask cups      # Allow service to start again
loofi service logs nginx       # View service journal logs
loofi service logs nginx --lines 100  # Custom line count
loofi service status sshd      # Detailed service info

# Package Explorer
loofi package search --query vim      # Search DNF + Flatpak
loofi package search --query vim --source dnf  # DNF only
loofi package install vim              # Install (auto-detect source)
loofi package install org.gnome.Calculator  # Install Flatpak
loofi package remove vim               # Remove a package
loofi package list                     # List all installed
loofi package list --source flatpak    # Flatpak only
loofi package list --search vim        # Filter installed packages
loofi package recent                   # Recently installed (30 days)
loofi package recent --days 7          # Custom time range

# Firewall Manager
loofi firewall status          # Full firewall snapshot
loofi firewall ports           # List open ports
loofi firewall open-port 8080/tcp   # Open a port (permanent)
loofi firewall close-port 8080/tcp  # Close a port
loofi firewall services        # List allowed services
loofi firewall zones           # List zones with active indicator
```

### Bluetooth & Storage (v17.0)

```bash
# Bluetooth
loofi bluetooth status         # Adapter info
loofi bluetooth devices        # List paired devices
loofi bluetooth scan           # Scan for nearby devices
loofi bluetooth pair <address> # Pair a device
loofi bluetooth connect <addr> # Connect to a device
loofi bluetooth disconnect <a> # Disconnect a device
loofi bluetooth trust <addr>   # Trust a device
loofi bluetooth power-on       # Turn adapter on
loofi bluetooth power-off      # Turn adapter off

# Storage & Disks
loofi storage disks            # List block devices
loofi storage mounts           # List mount points with usage
loofi storage smart /dev/sda   # SMART health for a device
loofi storage trim             # Run SSD TRIM
loofi storage usage            # Disk usage summary
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
| **Hardware** | Lightning | CPU, GPU, fan, power, battery, audio, fingerprint, Bluetooth |
| **Software** | Package | One-click apps + repository management |
| **Security & Privacy** | Shield | Security score, ports, USB, firewall, telemetry |
| **Network** | Globe | DNS, WiFi, VPN, MAC, monitoring (4 sub-tabs) |
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
| **Profiles** | Person | System configuration quick-switch |
| **Health** | Chart | Health timeline metrics tracking |
| **Performance** | Lightning | AutoTuner: workload detection, kernel tuning |
| **Snapshots** | Camera | Create/restore/delete snapshots |
| **Smart Logs** | Clipboard | Color-coded journal with error patterns |
| **Storage** | Disk | Block devices, SMART health, mounts, TRIM |

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

*Documentation last updated: v17.0.0 - February 2026*
