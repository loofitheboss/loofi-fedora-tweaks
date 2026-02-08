# Loofi Fedora Tweaks v11.0.0 "Aurora Update"

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>Complete Fedora System Management — Consolidated, Modern, Hardware-Aware</strong><br>
  <em>Auto-detects HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS | Supports Atomic Variants | Developer-Focused</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v11.0.0">
    <img src="https://img.shields.io/badge/Release-v11.0.0-blue?style=for-the-badge&logo=github" alt="Release v11.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Tests-225%20passing-brightgreen?style=for-the-badge" alt="Tests"/>
</p>

---

## What's New in v11.0.0?

### Aurora Update — Extensibility & Diagnostics

This release hardens the platform and unlocks extensibility without sacrificing stability.

**New Features**
* **Plugin Manifest Support**: `plugin.json` with version gating and permissions metadata
* **Plugin Manager UI**: Enable/disable plugins from the Community tab
* **Support Bundle Export**: One-click ZIP with logs and system info (Diagnostics + CLI)
* **Automation Validation**: Rule validation and dry-run simulation before execution
* **CLI Enhancements**: `loofi plugins` and `loofi support-bundle`

**Quality Improvements**
* **Unified Theme Loading**: Single source of truth for QSS styling
* **Improved Logging**: Structured error logging in Pulse, remote config, command runner
* **CI Smoke Checks**: CLI sanity checks added to CI pipeline

---

## Documentation

* **[User Guide](docs/USER_GUIDE.md)** — Complete documentation for all features
* **[Contributing](docs/CONTRIBUTING.md)** — Development setup, code style, PR workflow
* **[Changelog](CHANGELOG.md)** — Full version history
* **[Plugin SDK](docs/PLUGIN_SDK.md)** — Build third-party plugins

---

## Feature Overview

### Consolidated Tabs (v11.0)

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
| **AI Lab** | AI | Ollama management, hardware detection |
| **Automation** | Scheduler + Replicator + Pulse | Task scheduling, IaC export, event-driven automation |
| **Community** | Presets + Marketplace | Save/load presets, browse community presets |
| **Diagnostics** | Watchtower + Boot | Services, boot analyzer, journal viewer |

### New in v11.0

| Feature | Description |
|---------|-------------|
| **Plugin Manager** | Enable/disable plugins in Community tab |
| **Plugin Manifests** | `plugin.json` metadata with version gating |
| **Support Bundle** | Export logs and system info as ZIP |
| **Automation Validation** | Validate and simulate rules before execution |
| **CLI Additions** | `plugins` and `support-bundle` commands |

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
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v11.0.0/loofi-fedora-tweaks-11.0.0-1.fc43.noarch.rpm
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
# Output: rpmbuild/RPMS/noarch/loofi-fedora-tweaks-11.0.0-1.fc43.noarch.rpm
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
# 225 tests passing
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
