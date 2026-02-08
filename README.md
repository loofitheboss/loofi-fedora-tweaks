# Loofi Fedora Tweaks v13.0.0 "Nexus Update"

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>Complete Fedora System Management — Consolidated, Modern, Hardware-Aware</strong><br>
  <em>Auto-detects HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS | Supports Atomic Variants | Developer-Focused</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v13.0.0">
    <img src="https://img.shields.io/badge/Release-v13.0.0-blue?style=for-the-badge&logo=github" alt="Release v13.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Tests-839%2B%20passing-brightgreen?style=for-the-badge" alt="Tests"/>
</p>

---

## What's New in v13.0.0?

### Nexus Update — System Profiles, Health Timeline & Plugin SDK v2

A major integration update bringing system profiles for quick-switching configurations, health timeline for tracking metrics over time, and an enhanced plugin SDK.

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

### Tabs (v13.0)

| Tab | Contains | Description |
|-----|----------|-------------|
| **Home** | Dashboard | System health overview with quick actions |
| **System Info** | Hardware/OS | CPU, RAM, disk, battery, OS information |
| **System Monitor** | Performance + Processes | Live graphs, process manager with kill/renice |
| **Maintenance** | Updates + Cleanup + Overlays | DNF/Flatpak updates, cache cleaning, rpm-ostree layers |
| **Hardware** | Hardware + Tweaks | CPU governor, GPU, fan, power, battery limit, audio, fingerprint |
| **Software** | Apps + Repos | One-click app install, repository management |
| **Security & Privacy** | Security + Privacy | Security score, port audit, USB guard, firewall, telemetry |
| **Network** | Network | DNS, firewall, MAC randomization |
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

### New in v13.0

| Feature | Description |
|---------|-------------|
| **System Profiles** | 5 built-in profiles (Gaming, Development, Battery Saver, Presentation, Server) |
| **Custom Profiles** | Create your own profiles with CPU governor, compositor, notifications |
| **Profile Capture** | Capture current system state as a new profile |
| **Health Timeline** | SQLite-based metrics tracking (CPU temp, RAM, disk, load) |
| **Anomaly Detection** | Flag metrics that deviate 2+ standard deviations from the mean |
| **Metrics Export** | Export health data to JSON or CSV |
| **Plugin SDK v2** | Permissions model, update checking, dependency validation |
| **Shell Completions** | Bash, Zsh, and Fish auto-completion scripts |
| **CLI: profile** | Manage system profiles from the command line |
| **CLI: health-history** | View, record, and export health metrics |

### Previous Feature Highlights

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
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v13.0.0/loofi-fedora-tweaks-13.0.0-1.fc43.noarch.rpm
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
# Output: rpmbuild/RPMS/noarch/loofi-fedora-tweaks-13.0.0-1.fc43.noarch.rpm
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
# 839+ tests passing
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
