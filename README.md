# Loofi Fedora Tweaks v17.0.0 "Atlas"

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>Complete Fedora System Management — Consolidated, Modern, Hardware-Aware</strong><br>
  <em>Auto-detects HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS | Supports Atomic Variants | Developer-Focused</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v17.0.0">
    <img src="https://img.shields.io/badge/Release-v17.0.0-blue?style=for-the-badge&logo=github" alt="Release v17.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Tests-1514%20passing-brightgreen?style=for-the-badge" alt="Tests"/>
</p>

---

## What's New in v17.0.0 "Atlas"

### Atlas — Hardware & Visibility Release

Four new dedicated tabs bring v15 features to the GUI, plus a Bluetooth manager, storage & disk health tools, and a completely overhauled Network tab.

**Performance Tab** (AutoTuner GUI)
* Workload detection with real-time CPU/memory classification
* Kernel settings display (governor, swappiness, I/O scheduler, THP)
* One-click apply with pkexec, tuning history table, 30s auto-refresh

**Snapshots Tab**
* Create, restore, and delete snapshots across Timeshift/Snapper/BTRFS
* Backend auto-detection, retention policies, timeline view

**Smart Logs Tab**
* Color-coded journal viewer with 10 built-in error patterns
* Pattern analysis table, unit/priority/time filters, export

**Storage & Disks Tab**
* Block device inventory (lsblk), SMART health monitoring
* Mount point listing with usage stats, filesystem check (fsck), SSD TRIM

**Network Tab Overhaul**
* 4 sub-tabs: Connections (WiFi/VPN), DNS, Privacy (MAC), Monitoring
* WiFi scanning, VPN status, interface stats with auto-refresh

**Bluetooth Manager** (Hardware tab)
* Adapter status, device scanning, pair/connect/trust/block
* Battery level display, device type classification

**CLI: bluetooth & storage** — 2 new subcommands with full action support

**1514 Tests** — 94 new tests across 4 test files, 25 total tabs

---

## Previous: v16.0.0 "Horizon"

**Service Explorer** — Full systemd service browser with lifecycle control

**Package Explorer** — Unified DNF/rpm-ostree/Flatpak search, install, remove

**Firewall Manager** — firewalld zones, ports, services, rich rules

**Dashboard v2** — Live sparkline graphs, network speed, storage breakdown

---

## Previous: v15.0.0 "Nebula"

**Performance Auto-Tuner** — Workload detection + CPU governor, swappiness, I/O scheduler optimization

**System Snapshot Timeline** — Unified Timeshift/Snapper/BTRFS snapshot management

**Smart Log Viewer** — Journal analysis with 10 built-in error patterns

**Quick Actions Bar** — `Ctrl+Shift+K` floating command palette with 15+ actions

---

## Previous: v14.0.0 "Quantum Leap"

**Update Checker** — Automatic update notifications from GitHub releases API

**What's New Dialog** — Post-upgrade dialog showing release highlights

**Factory Reset** — Full backup/restore/reset management for all config files

**Plugin Lifecycle Events** — `on_app_start`, `on_app_quit`, `on_tab_switch` hooks

---

## Previous: v13.5.0 "Nexus Update" (UX Polish)

**System Profiles**
* **5 Built-in Profiles**: Gaming, Development, Battery Saver, Presentation, Server
* **Quick-Switch**: One-click profile application with CPU governor, services, and notifications
* **Custom Profiles**: Create and save your own configurations
* **Profile Capture**: Capture current system state as a new profile

**Health Timeline**
* **Metrics Tracking**: SQLite-based logging of CPU temp, RAM, disk usage, load average
* **Anomaly Detection**: Flag values that deviate from the norm (2+ std devs)
* **Export Options**: JSON and CSV export for external analysis
* **Data Pruning**: Configurable retention with automatic cleanup

**Plugin SDK v2**
* **Permissions Model**: Plugins declare required permissions (network, filesystem, etc.)
* **Update Checking**: Plugins can check for updates via remote manifest
* **Dependency Validation**: Manifest-based dependency resolution

**Mesh Networking Enhancements**
* **Improved Peer Discovery**: Better mDNS integration
* **Clipboard Sync**: Enhanced encrypted clipboard sharing
* **File Drop**: Improved file transfer reliability

**CLI Enhancements**
* **profile**: list, apply, create, delete system profiles
* **health-history**: show, record, export, prune health metrics
* **Shell Completions**: Bash, Zsh, and Fish completion scripts

**Architecture**
* **20-Tab Layout**: Added Profiles and Health tabs
* **839+ Tests**: Comprehensive test coverage

---

## Documentation

* **[User Guide](docs/USER_GUIDE.md)** — Complete documentation for all features
* **[Contributing](docs/CONTRIBUTING.md)** — Development setup, code style, PR workflow
* **[Changelog](CHANGELOG.md)** — Full version history
* **[Plugin SDK](docs/PLUGIN_SDK.md)** — Build third-party plugins

---

## Feature Overview

### Tabs (v17.0 — 25 tabs)

| Tab | Contains | Description |
|-----|----------|-------------|
| **Home** | Dashboard | System health overview with quick actions |
| **System Info** | Hardware/OS | CPU, RAM, disk, battery, OS information |
| **System Monitor** | Performance + Processes | Live graphs, process manager with kill/renice |
| **Maintenance** | Updates + Cleanup + Overlays | DNF/Flatpak updates, cache cleaning, rpm-ostree layers |
| **Hardware** | Hardware + Tweaks + Bluetooth | CPU governor, GPU, fan, power, audio, fingerprint, Bluetooth |
| **Software** | Apps + Repos | One-click app install, repository management |
| **Security & Privacy** | Security + Privacy | Security score, port audit, USB guard, firewall, telemetry |
| **Network** | Connections + DNS + Privacy + Monitoring | WiFi/VPN, DNS switcher, MAC randomization, interface stats |
| **Gaming** | Gaming | GameMode, MangoHud, ProtonUp, Steam |
| **Desktop** | Director + Theming | Window management, compositor, GTK/Qt themes |
| **Development** | Containers + Developer | Distrobox GUI, PyEnv, NVM, Rustup, VS Code |
| **AI Lab** | AI Enhanced | Lite models, voice mode, context RAG |
| **Automation** | Scheduler + Replicator + Pulse | Task scheduling, IaC export, event-driven automation |
| **Community** | Presets + Marketplace | Save/load presets, browse community presets |
| **Diagnostics** | Watchtower + Boot | Services, boot analyzer, journal viewer |
| **Virtualization** | VMs + VFIO + Disposable | VM wizard, GPU passthrough, disposable VMs |
| **Loofi Link** | Mesh + Clipboard + File Drop | Device discovery, clipboard sync, file transfer |
| **State Teleport** | Workspace Capture/Restore | Save and restore workspace state across devices |
| **Profiles** | System Profiles | Quick-switch between gaming, dev, battery saver, etc. |
| **Health** | Health Timeline | Track and analyze system metrics over time |
| **Performance** | Auto-Tuner | Workload detection, kernel tuning, apply & history |
| **Snapshots** | Snapshot Timeline | Create/restore/delete snapshots (Timeshift/Snapper/BTRFS) |
| **Smart Logs** | Log Viewer | Color-coded journal with 10 error patterns |
| **Storage** | Disks + Mounts | Block devices, SMART health, mounts, fsck, TRIM |
| **Quick Actions** | Command Palette | `Ctrl+Shift+K` floating command palette |

### New in v15.0

| Feature | Description |
|---------|-------------|
| **Performance Auto-Tuner** | Workload detection + CPU governor, swappiness, I/O scheduler, THP optimization |
| **Snapshot Timeline** | Unified Timeshift / Snapper / BTRFS snapshot management with retention |
| **Smart Log Viewer** | Journal analysis with 10 built-in error patterns and suggested fixes |
| **Quick Actions Bar** | `Ctrl+Shift+K` floating command palette with 15+ actions |
| **CLI: tuner** | `analyze`, `apply`, `history` subcommands |
| **CLI: snapshot** | `list`, `create`, `delete`, `backends` subcommands |
| **CLI: logs** | `show`, `errors`, `export` with `--unit`, `--priority`, `--since` filters |

### New in v17.0

| Feature | Description |
|---------|-------------|
| **Performance Tab** | AutoTuner GUI — workload detection, kernel tuning, apply & history |
| **Snapshots Tab** | SnapshotManager GUI — create/restore/delete across backends |
| **Smart Logs Tab** | SmartLogViewer GUI — color-coded journal with pattern analysis |
| **Storage & Disks Tab** | Block devices, SMART health, mounts, fsck, SSD TRIM |
| **Network Overhaul** | 4 sub-tabs: Connections, DNS, Privacy, Monitoring |
| **Bluetooth Manager** | Scan, pair, connect, trust, block via bluetoothctl |
| **CLI: bluetooth** | `status`, `devices`, `scan`, `pair`, `connect`, `power-on/off` |
| **CLI: storage** | `disks`, `mounts`, `smart`, `trim`, `usage` |

### New in v16.0

| Feature | Description |
|---------|-------------|
| **Service Explorer** | Full systemd service browser with lifecycle control |
| **Package Explorer** | Unified DNF/rpm-ostree/Flatpak search, install, remove |
| **Firewall Manager** | firewalld zones, ports, services, rich rules management |
| **Dashboard v2** | Live sparkline graphs, network speed, storage breakdown, top processes |

### Previous Feature Highlights

* **System Profiles** (v13.0): 5 built-in profiles with quick-switch
* **Health Timeline** (v13.0): SQLite-based metrics tracking with anomaly detection
* **Update Checker** (v14.0): Automatic update notifications from GitHub releases API
* **What's New Dialog** (v14.0): Post-upgrade dialog showing release highlights
* **Factory Reset** (v14.0): Full backup/restore/reset management
* **Plugin Lifecycle** (v14.0): `on_app_start`, `on_app_quit`, `on_tab_switch` hooks
* **Pulse Engine** (v9.1): Event-driven automation with DBus listener
* **Focus Mode** (v9.1): Distraction blocking with domain blocking and DND
* **Live Graphs** (v9.2): Real-time CPU, RAM, Disk I/O, Network I/O
* **Process Manager** (v9.2): Sortable process table with kill/renice
* **Director** (v9.0): Window management for KDE, Hyprland, Sway
* **Security Center** (v8.5): Security score, port audit, USB guard, sandbox
* **AI Lab** (v8.1): Ollama management, CUDA/ROCm/NPU detection
* **Replicator** (v8.0): Ansible playbook and Kickstart export

---

## Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

### Direct RPM Download

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v17.0.0/loofi-fedora-tweaks-17.0.0-1.noarch.rpm
```

### Run from Source

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks/loofi-fedora-tweaks
pip install -r ../requirements.txt
python3 main.py
```

### Build RPM from Source

```bash
./build_rpm.sh
# Output: rpmbuild/RPMS/noarch/loofi-fedora-tweaks-17.0.0-1.noarch.rpm
```

---

## CLI Usage

```bash
# Launch GUI
loofi-fedora-tweaks

# System info and health
loofi info                    # System information
loofi health                  # System health check
loofi doctor                  # Check tool dependencies
loofi hardware                # Show detected hardware profile

# Monitoring
loofi disk                    # Disk usage analysis
loofi processes               # Top processes by CPU
loofi temperature             # Hardware temperatures
loofi netmon                  # Network interface stats

# Management
loofi cleanup                 # Run full cleanup
loofi tweak power --profile performance
loofi network dns --provider cloudflare
loofi plugins list            # List available plugins
loofi support-bundle          # Export support bundle ZIP

# Virtualization (v12.0)
loofi vm list                 # List virtual machines
loofi vm start myvm           # Start a VM
loofi vfio check              # Check VFIO prerequisites
loofi vfio gpus               # List GPU passthrough candidates

# Mesh Networking (v12.0)
loofi mesh discover           # Discover LAN devices
loofi mesh status             # Show device ID and local IPs

# State Teleport (v12.0)
loofi teleport capture        # Capture workspace state
loofi teleport list           # List saved packages
loofi teleport restore <id>   # Restore a package

# AI Models (v12.0)
loofi ai-models list          # List installed and recommended models
loofi ai-models recommend     # Get RAM-based model recommendation

# Profiles (v13.0)
loofi profile list            # List all profiles
loofi profile apply gaming    # Apply a profile
loofi profile create myprofile  # Create from current state
loofi profile delete myprofile  # Delete a custom profile

# Health History (v13.0)
loofi health-history show     # Show 24h metrics summary
loofi health-history record   # Record current metrics
loofi health-history export health.json  # Export to JSON
loofi health-history prune    # Delete old data

# Performance Tuning (v15.0)
loofi tuner analyze           # Detect workload and recommend settings
loofi tuner apply             # Apply recommended optimizations
loofi tuner history           # View tuning history

# Snapshot Management (v15.0)
loofi snapshot list            # List all snapshots
loofi snapshot create          # Create a new snapshot
loofi snapshot delete <id>     # Delete a snapshot
loofi snapshot backends        # List available backends

# Smart Logs (v15.0)
loofi logs show               # Show recent journal entries
loofi logs errors             # Show error summary with patterns
loofi logs export log.txt     # Export filtered logs

# Service Management (v16.0)
loofi service list             # List all systemd services
loofi service list --filter active   # Filter by state
loofi service start sshd       # Start a service
loofi service stop bluetooth   # Stop a service
loofi service logs nginx       # View service journal logs
loofi service status sshd      # Detailed service info

# Package Management (v16.0)
loofi package search --query vim   # Search DNF + Flatpak
loofi package install vim          # Install a package
loofi package remove vim           # Remove a package
loofi package list                 # List installed packages
loofi package list --source flatpak  # Filter by source
loofi package recent               # Recently installed packages

# Firewall Management (v16.0)
loofi firewall status          # Full firewall status
loofi firewall ports           # List open ports
loofi firewall open-port 8080/tcp   # Open a port
loofi firewall close-port 8080/tcp  # Close a port
loofi firewall services        # List allowed services
loofi firewall zones           # List available zones

# Bluetooth (v17.0)
loofi bluetooth status         # Adapter info
loofi bluetooth devices        # List paired devices
loofi bluetooth scan           # Scan for nearby devices
loofi bluetooth pair <address> # Pair a device
loofi bluetooth connect <addr> # Connect to a device
loofi bluetooth power-on       # Turn adapter on
loofi bluetooth power-off      # Turn adapter off

# Storage & Disks (v17.0)
loofi storage disks            # List block devices
loofi storage mounts           # List mount points with usage
loofi storage smart /dev/sda   # SMART health for a device
loofi storage trim             # Run SSD TRIM
loofi storage usage            # Disk usage summary

# JSON output (for scripting)
loofi --json info
loofi --json health
loofi --json doctor

# Version
loofi --version
```

---

## Requirements

* **Fedora 43+** (or Atomic variant: Silverblue, Kinoite)
* **Python 3.12+**
* **PyQt6**
* **polkit**
* **libnotify** (for notifications)

### Optional

* **Ollama** — Local AI inference
* **Firejail** — Application sandboxing
* **USBGuard** — USB device control
* **Hyprland/Sway** — Tiling compositor support
* **nbfc-linux** — Fan control

---

## Testing

```bash
PYTHONPATH=loofi-fedora-tweaks python3 -m pytest tests/ -v
# 1514 tests passing
```

---

## Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License — Open Source, respects user privacy and freedom.

---

## Author

**Loofi** — [GitHub](https://github.com/loofitheboss)
