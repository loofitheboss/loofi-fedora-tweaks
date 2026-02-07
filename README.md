# Loofi Fedora Tweaks v7.0.0 "Community Update" 🌐

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>The Ultimate System Management Utility for Fedora 43+ KDE</strong><br>
  <em>Optimized for HP Elitebook 840 G8 | Supports Atomic Variants</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v7.0.0">
    <img src="https://img.shields.io/badge/Release-v7.0.0-blue?style=for-the-badge&logo=github" alt="Release v7.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
</p>

---

## 🚀 What's New in v7.0?

### 🌐 Community Update

Connect with the community through preset sharing and configuration tracking!

* **Preset Marketplace**: Browse and download community presets from GitHub.
* **Configuration Drift Detection**: Track when your system changes from applied presets.
* **Marketplace Tab**: New UI for discovering and applying community configurations.

---

## 📚 Documentation

📖 **[User Guide](docs/USER_GUIDE.md)** - Complete documentation with screenshots

---

## ✨ Feature Overview

### 🌐 Community Features (v7.0)

* **Preset Marketplace**: Browse community presets with ratings and downloads.
* **Search & Filter**: Find presets by category (Gaming, Privacy, Performance).
* **Drift Detection**: Know when your system configuration changes.
* **Baseline Tracking**: Compare current state to applied preset.

### 🔧 Boot Management (v6.2)

* **Kernel Parameter Editor**: Add/remove boot parameters with common presets.
* **ZRAM Tuner**: Configure memory compression ratio and algorithm.
* **Secure Boot Helper**: Generate and enroll MOK keys for third-party modules.

### 🛠️ Developer Features (v6.5)

* **CLI Mode**: Full `loofi` command-line interface for scripting.
* **Plugin System**: Extend functionality with custom plugins.
* **Operations Layer**: Clean separation of UI and business logic.

### 🌐 Localization (v6.1)

* **17 UI Files Localized**: All tabs wrapped with `self.tr()`.
* **Auto-Detection**: Loads translations based on system locale.

### ⏰ Automation (v6.0)

* **Scheduled Tasks**: Hourly, daily, weekly automation.
* **Power Triggers**: On-battery / On-AC event handling.

### ⚡ Hardware Control (v5.2)

* **CPU Governor**: Switch between powersave/schedutil/performance.
* **Power Profiles**: Quick toggle for power modes.
* **GPU Mode Switching**: Integrated/Hybrid/NVIDIA modes.
* **Fan Control**: Manual speed slider or auto mode.

### 🧬 Atomic Support (v5.1)

* **Silverblue/Kinoite Compatible**: Detects `rpm-ostree` automatically.
* **System Overlays Tab**: Manage layered packages.

---

## 📦 Installation

### ⚡ Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

### 💾 DNF Repository

```bash
# Add repository
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/loofi-fedora-tweaks.repo

# Install
sudo dnf install loofi-fedora-tweaks
```

### 📥 Direct RPM Download

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v7.0.0/loofi-fedora-tweaks-7.0.0-1.fc43.noarch.rpm
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
loofi advanced bbr            # Enable TCP BBR
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

### 🔌 Plugin Development

Create plugins in `plugins/` directory:

```python
from utils.plugin_base import LoofiPlugin, PluginInfo

class MyPlugin(LoofiPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo("My Plugin", "1.0", "Author", "Description")
    
    def create_widget(self):
        # Return PyQt6 widget
        pass
    
    def get_cli_commands(self):
        # Return dict of CLI commands
        return {}
```

---

## 📜 License

MIT License - Open Source, respects user privacy and freedom.

---

## 👨‍💻 Author

**Loofi** - [GitHub](https://github.com/loofitheboss)
