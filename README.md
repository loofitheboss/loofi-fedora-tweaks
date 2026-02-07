# Loofi Fedora Tweaks v9.2.0 "Pulse Update" 📊

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>Complete Fedora System Management with Real-time Monitoring, AI, Security &amp; Window Management</strong><br>
  <em>Optimized for HP Elitebook 840 G8 | Supports Atomic Variants | Developer-Focused</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v9.2.0">
    <img src="https://img.shields.io/badge/Release-v9.2.0-blue?style=for-the-badge&logo=github" alt="Release v9.2.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
</p>

---

## What's New in v9.2?

### Pulse Update - Real-time System Monitoring (v9.2)

Live system monitoring with real-time graphs and process management!

* **Performance Graphs**: Live CPU, RAM, Disk I/O, and Network I/O graphs with 60-second history
* **Process Monitor**: Top processes by CPU/Memory with kill and renice support
* **Temperature Monitoring**: CPU, GPU, and NVMe drive temperatures via hwmon sensors
* **Network Traffic Monitor**: Per-interface bandwidth tracking with active connection listing
* **Dashboard Auto-Refresh**: Health metrics update every 5 seconds with CPU load indicator
* **New CLI Commands**: `loofi processes`, `loofi temperature`, `loofi netmon`

### Vital Signs Update - System Health (v9.1)

* **Disk Space Monitoring**: Usage stats, health checks, and large directory finder
* **System Resource Monitor**: Memory, CPU, and uptime tracking
* **CLI Health Check**: Quick system health overview from terminal

### 🎬 Director Update - Window Management (v9.0)

Take control of your desktop with tiling and workspace management!

* **Compositor Detection**: Auto-detect KDE Plasma, Hyprland, or Sway
* **Tiling Presets**: Vim-style or arrow key keybindings for quick tiling
* **Workspace Templates**: Pre-configured layouts for development, gaming, creative work
* **Dotfile Sync**: Backup and sync your configs to a git repo
* **KWin Scripts**: Install custom tiling scripts for KDE Plasma

### 🛡️ Sentinel Update - Security Center (v8.5)

Proactive security hardening for your system!

* **Security Score**: Real-time security health assessment (0-100)
* **Port Auditor**: Scan open ports, identify risks, manage firewall
* **USB Guard**: Block unauthorized USB devices (BadUSB protection)
* **Application Sandbox**: Launch apps in Firejail with one click

### 🧠 Neural Update - AI Ready (v8.1)

Local AI with hardware-accelerated inference!

* **AI Hardware Detection**: CUDA, ROCm, Intel NPU, AMD Ryzen AI
* **Ollama Management**: Install Ollama, download models, manage AI locally
* **Model Library**: Llama 3, Mistral, CodeLlama, Phi-3 and more

---

## 📚 Documentation

📖 **[User Guide](docs/USER_GUIDE.md)** - Complete documentation with screenshots

---

## ✨ Feature Overview

### Pulse - Real-time Monitoring (v9.2)

| Feature | Description |
|---------|-------------|
| **Performance Graphs** | Live CPU, RAM, Disk I/O, Network I/O with 60s rolling history |
| **Process Monitor** | Sortable process table with kill/renice context menu |
| **Temperature Sensors** | hwmon-based CPU, GPU, NVMe temperature readings |
| **Network Traffic** | Per-interface bandwidth and active TCP/UDP connections |
| **Dashboard Auto-Refresh** | 5-second health metric updates with CPU load |

### 🎬 Director - Window Management (v9.0)

| Feature | Description |
|---------|-------------|
| **Compositor Detection** | KDE/Hyprland/Sway auto-detection |
| **Tiling Presets** | Vim (H/J/K/L) or Arrow key bindings |
| **Workspace Templates** | Development, Gaming, Creative layouts |
| **Dotfile Sync** | Git-based config backup |

### 🛡️ Security Center (v8.5)

| Feature | Description |
|---------|-------------|
| **Security Score** | 0-100 health rating with recommendations |
| **Port Auditor** | Find risky open ports, block with firewall |
| **USB Guard** | Whitelist/blacklist USB devices |
| **Sandbox** | Firejail/Bubblewrap app isolation |

### 🧠 AI Lab (v8.1)

| Feature | Description |
|---------|-------------|
| **Hardware Detection** | CUDA, ROCm, Intel/AMD NPU support |
| **Ollama Manager** | Install, manage, and run local AI |
| **Model Downloads** | One-click download for popular models |

### Previous Features

* **📊 Performance**: Live CPU, RAM, Disk I/O, Network I/O graphs
* **🔍 Processes**: Process monitor with kill/renice
* **🌡️ Temperature**: Hardware temperature sensors
* **📡 Network Monitor**: Per-interface bandwidth tracking
* **🔄 Replicator**: Ansible/Kickstart export
* **🔭 Watchtower**: System diagnostics
* **📦 Containers**: Distrobox GUI
* **🛠️ Developer**: PyEnv, NVM, Rustup
* **🌐 Marketplace**: Community presets
* **🔧 Boot Management**: Kernel params, ZRAM
* **⚡ Hardware Control**: CPU, GPU, Fan, Power
* **⏰ Automation**: Scheduled tasks
* **🖥️ CLI Mode**: Full command-line interface

---

## 📦 Installation

### ⚡ Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

### 📥 Direct RPM Download

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v9.2.0/loofi-fedora-tweaks-9.2.0-1.fc43.noarch.rpm
```

### 🖥️ Run from Source

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks/loofi-fedora-tweaks
pip install -r ../requirements.txt
python3 main.py
```

---

## 🖥️ CLI Usage

```bash
# Launch GUI
loofi-fedora-tweaks

# CLI commands
loofi info                    # System information
loofi health                  # System health check
loofi disk                    # Disk usage analysis
loofi processes               # Top processes by CPU/memory
loofi temperature             # Hardware temperature sensors
loofi netmon                  # Network interface monitoring
loofi cleanup                 # Run full cleanup
loofi tweak power --profile performance
loofi network dns --provider cloudflare

# Version
loofi --version
```

---

## 📋 Tabs Overview (25 Tabs)

| Tab | Description |
|:----|:------------|
| **🏠 Home** | Dashboard with system health and quick actions |
| **ℹ️ System Info** | Hardware and OS information |
| **📦 Updates** | System update management |
| **🧹 Cleanup** | Cache cleaning and orphan removal |
| **⚡ Hardware** | CPU, GPU, Fan, Power controls |
| **💻 HP Tweaks** | Battery limit, Fingerprint (HP specific) |
| **🚀 Apps** | One-click app installation |
| **⚙️ Advanced** | Kernel, Boot, System tweaks |
| **🎮 Gaming** | GameMode, MangoHud, ProtonUp |
| **🌐 Network** | DNS, Firewall, MAC management |
| **💾 Presets** | Save/Load configs, Cloud sync |
| **🌐 Marketplace** | Community presets + drift detection |
| **⏰ Scheduler** | Automated task management |
| **🔧 Boot** | Kernel params, ZRAM, Secure Boot |
| **📦 Containers** | Distrobox GUI |
| **🛠️ Developer** | Language managers, VS Code |
| **🔭 Watchtower** | Services, Boot, Journal |
| **🔄 Replicator** | Ansible/Kickstart export |
| **🧠 AI Lab** | Local AI setup **(v8.1 NEW!)** |
| **🛡️ Security** | Port audit, USB Guard **(v8.5 NEW!)** |
| **🎬 Director** | Window management **(v9.0 NEW!)** |
| **📊 Performance** | Live performance graphs with CPU, RAM, I/O **(v9.2 NEW!)** |
| **🔍 Processes** | Process monitor with kill/renice **(v9.2 NEW!)** |
| **🎨 Theming** | GTK/Qt theme settings |
| **🔒 Privacy** | Telemetry and privacy tweaks |
| **📦 Overlays** | rpm-ostree packages (Atomic only) |
| **📁 Repos** | Repository management |

---

## 🛡️ Requirements

* **Fedora 43+** (or Atomic variant: Silverblue, Kinoite)
* **Python 3.12+**
* **PyQt6**
* **polkit**
* **libnotify** (for notifications)

### Optional (for new features)

* **Ollama** - Local AI inference
* **Firejail** - Application sandboxing
* **USBGuard** - USB device control
* **Hyprland/Sway** - Tiling compositor support

---

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

MIT License - Open Source, respects user privacy and freedom.

---

## 👨‍💻 Author

**Loofi** - [GitHub](https://github.com/loofitheboss)
