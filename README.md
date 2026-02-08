# Loofi Fedora Tweaks v12.0.0 "Sovereign Update"

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>Complete Fedora System Management — Consolidated, Modern, Hardware-Aware</strong><br>
  <em>Auto-detects HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS | Supports Atomic Variants | Developer-Focused</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v12.0.0">
    <img src="https://img.shields.io/badge/Release-v12.0.0-blue?style=for-the-badge&logo=github" alt="Release v12.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Tests-564%20passing-brightgreen?style=for-the-badge" alt="Tests"/>
</p>

---

## What's New in v12.0.0?

### Sovereign Update — Virtualization, Mesh Networking & State Teleport

The biggest release yet: full KVM/QEMU virtualization management, LAN mesh networking, and workspace state teleportation across devices.

**v11.5 Hypervisor Update**
* **VM Quick-Create Wizard**: One-click VMs for Windows 11, Fedora, Ubuntu, Kali, Arch with preset flavors
* **VFIO GPU Passthrough Assistant**: Step-by-step IOMMU group analysis and kernel cmdline generation
* **Disposable VMs**: QCOW2 overlay-based throwaway VMs for untrusted software

**v12.0 Sovereign Networking**
* **Loofi Link Mesh**: mDNS device discovery on LAN via Avahi
* **Clipboard Sync**: Encrypted clipboard sharing between paired devices
* **File Drop**: Local HTTP file transfer with checksum verification
* **State Teleport**: Capture VS Code, git, and terminal state; restore on another machine

**v11.1-v11.3 AI Polish**
* **Lite Model Library**: Curated GGUF models (Llama 3.2 1B/3B, Mistral 7B, Gemma 2B, Phi-3)
* **Voice Mode**: whisper.cpp integration for voice commands
* **Context RAG**: TF-IDF local file indexing for AI-assisted system help

**Architecture**
* **Plugin Refactor**: Virtualization and AI Lab now ship as first-party plugins with manifests
* **18-Tab Layout**: Three new sidebar tabs (Virtualization, Loofi Link, State Teleport)

---

## Documentation

* **[User Guide](docs/USER_GUIDE.md)** — Complete documentation for all features
* **[Contributing](docs/CONTRIBUTING.md)** — Development setup, code style, PR workflow
* **[Changelog](CHANGELOG.md)** — Full version history
* **[Plugin SDK](docs/PLUGIN_SDK.md)** — Build third-party plugins

---

## Feature Overview

### Tabs (v12.0)

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

### New in v12.0

| Feature | Description |
|---------|-------------|
| **VM Quick-Create** | One-click VMs with preset flavors (Windows 11, Fedora, Ubuntu, Kali, Arch) |
| **VFIO Assistant** | Step-by-step GPU passthrough with IOMMU analysis |
| **Disposable VMs** | QCOW2 overlay snapshots for throwaway environments |
| **Loofi Link Mesh** | mDNS LAN device discovery via Avahi |
| **Clipboard Sync** | Encrypted clipboard sharing between devices |
| **File Drop** | Local HTTP file transfer with checksum verification |
| **State Teleport** | Capture and restore VS Code, git, terminal state across machines |
| **AI Lite Models** | Curated GGUF models with RAM-based recommendations |
| **Voice Mode** | whisper.cpp voice commands |
| **Context RAG** | TF-IDF local file indexing for AI assistance |
| **Plugin Refactor** | VM and AI Lab as first-party manifest-based plugins |

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
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v12.0.0/loofi-fedora-tweaks-12.0.0-1.fc43.noarch.rpm
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
# Output: rpmbuild/RPMS/noarch/loofi-fedora-tweaks-12.0.0-1.fc43.noarch.rpm
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
# 564 tests passing
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
