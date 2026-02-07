# Loofi Fedora Tweaks v8.0.0 "Replicator Update" 🔄

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>The Ultimate System Management & Developer Tooling for Fedora 43+ KDE</strong><br>
  <em>Optimized for HP Elitebook 840 G8 | Supports Atomic Variants | Developer-Focused</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v8.0.0">
    <img src="https://img.shields.io/badge/Release-v8.0.0-blue?style=for-the-badge&logo=github" alt="Release v8.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
</p>

---

## 🚀 What's New in v8.0?

### 🔄 Replicator Update - Infrastructure as Code

Export your entire system configuration and replicate it anywhere!

* **Ansible Playbook Export**: Generate standard Ansible playbooks from your installed packages, Flatpaks, and GNOME settings.
* **Kickstart Generator**: Create Anaconda-compatible .ks files for automated Fedora reinstalls.
* **No Loofi Required**: Exported configs work with standard tools—use them anywhere.

### 🔭 Watchtower Update (v7.5) - System Diagnostics

* **Gaming-Focused Service Manager**: Filter services by gaming, failed, or active states.
* **Boot Analyzer**: Visualize boot time breakdown with optimization suggestions.
* **Panic Button**: One-click log export ready for support forums.

### 🛠️ Developer Update (v7.1) - Containers & Dev Tools

* **Distrobox GUI**: Create, enter, and manage containers graphically.
* **Language Version Managers**: One-click install for PyEnv, NVM, Rustup.
* **VS Code Extension Profiles**: Install curated extension packs for Python, C++, Rust, Web, Containers.

### ⚡ Performance Enhancement

* **Lazy Tab Loading**: Tabs load on-demand for instant startup.

---

## 📚 Documentation

📖 **[User Guide](docs/USER_GUIDE.md)** - Complete documentation with screenshots

---

## ✨ Feature Overview

### 🔄 Replicator - IaC Export (v8.0)

| Feature | Description |
|---------|-------------|
| **Ansible Export** | Generate playbooks with packages, Flatpaks, settings |
| **Kickstart Export** | Create .ks files for automated installs |
| **Preview Mode** | View generated config before export |

### 🔭 Watchtower - Diagnostics (v7.5)

| Feature | Description |
|---------|-------------|
| **Service Manager** | Start/stop/mask services with gaming filter |
| **Boot Analyzer** | Identify slow services, get optimization tips |
| **Journal Viewer** | Quick error view + Panic Button export |

### 🛠️ Developer Tools (v7.1)

| Feature | Description |
|---------|-------------|
| **Containers** | Distrobox GUI for development environments |
| **Version Managers** | PyEnv, NVM, Rustup installers |
| **VS Code Setup** | Extension profiles for Python, C++, Rust, Web |

### Previous Features

* **🌐 Marketplace**: Browse/download community presets
* **🔧 Boot Management**: Kernel params, ZRAM, Secure Boot
* **⚡ Hardware Control**: CPU, GPU, Fan, Power profiles
* **🧬 Atomic Support**: Silverblue/Kinoite compatible
* **⏰ Automation**: Scheduled tasks, power triggers
* **🖥️ CLI Mode**: Full command-line interface

---

## 📦 Installation

### ⚡ Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

### 📥 Direct RPM Download

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v8.0.0/loofi-fedora-tweaks-8.0.0-1.fc43.noarch.rpm
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
loofi cleanup                 # Run full cleanup
loofi tweak power --profile performance
loofi network dns --provider cloudflare

# Version
loofi --version
```

---

## 📋 Tabs Overview

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
| **📦 Containers** | Distrobox GUI **(v7.1 NEW!)** |
| **🛠️ Developer** | Language managers, VS Code **(v7.1 NEW!)** |
| **🔭 Watchtower** | Services, Boot, Journal **(v7.5 NEW!)** |
| **🔄 Replicator** | Ansible/Kickstart export **(v8.0 NEW!)** |
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
