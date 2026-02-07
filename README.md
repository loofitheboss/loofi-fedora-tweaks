# Loofi Fedora Tweaks v6.0.0 "Autonomy Update" ⏰

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>The Ultimate System Management Utility for Fedora 43+ KDE</strong><br>
  <em>Optimized for HP Elitebook 840 G8 | Supports Atomic Variants</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v6.0.0">
    <img src="https://img.shields.io/badge/Release-v6.0.0-blue?style=for-the-badge&logo=github" alt="Release v6.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
</p>

---

## 🚀 What's New in v6.0?

### ⏰ Autonomy Update

Automate your system maintenance with scheduled tasks and a background service!

* **Scheduler Tab**: Create scheduled tasks for cleanup, updates, and more.
* **Background Service**: Lightweight systemd user service runs tasks automatically.
* **Power Triggers**: Execute actions when plugging in or unplugging AC.
* **Notifications**: Desktop toast alerts when tasks complete.

---

## ✨ Feature Overview

### 🎨 Modern UI (v5.0)

- **Glassmorphism Design**: Dark theme with blur effects and rounded corners.
* **Sidebar Navigation**: Clean, organized interface.
* **Dashboard**: System health at a glance with quick actions.

### 🧬 Atomic Support (v5.1)

- **Silverblue/Kinoite Compatible**: Detects `rpm-ostree` systems automatically.
* **System Overlays Tab**: Manage layered packages on Atomic variants.
* **Flatpak First**: Prioritizes Flatpak for app installations.

### ⚡ Hardware Control (v5.2)

- **CPU Governor**: Switch between powersave/schedutil/performance.
* **Power Profiles**: Quick toggle for power-saver/balanced/performance.
* **GPU Mode Switching**: Integrated/Hybrid/NVIDIA modes (via envycontrol).
* **Fan Control**: Manual speed slider or auto mode (via nbfc-linux).

### ☁️ Cloud Sync (v5.5)

- **Export/Import Config**: Backup all settings to JSON.
* **GitHub Gist Sync**: Push/pull config across machines.
* **Community Presets**: Browse and download shared configurations.

### ⏰ Automation (v6.0)

- **Scheduled Tasks**: Hourly, daily, weekly automation.
* **Boot Actions**: Run tasks on login.
* **Power Triggers**: On-battery / On-AC event handling.
* **System Cleanup, Update Checks, Preset Application**.

---

## 📦 Installation

### Option 1: DNF Repository (Recommended)

```bash
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/repo/loofi-fedora-tweaks.repo
sudo dnf install loofi-fedora-tweaks --refresh
```

### Option 2: Manual RPM Install

Download from [Releases](https://github.com/loofitheboss/loofi-fedora-tweaks/releases):

```bash
sudo dnf install ./loofi-fedora-tweaks-6.0.0-1.fc43.noarch.rpm
```

### Option 3: Run from Source

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
pip install -r requirements.txt
python3 loofi-fedora-tweaks/main.py
```

---

## 🔧 Background Service

Enable automated task execution:

```bash
# Enable and start the service
systemctl --user enable --now loofi-fedora-tweaks

# Check status
systemctl --user status loofi-fedora-tweaks

# Disable
systemctl --user disable --now loofi-fedora-tweaks
```

Or manage it from the **Scheduler** tab in the app.

---

## 🖥️ CLI Usage

```bash
# Launch GUI
loofi-fedora-tweaks

# Run as background daemon
loofi-fedora-tweaks --daemon

# Show version
loofi-fedora-tweaks --version
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
| **⏰ Scheduler** | Automated task management |
| **🎨 Theming** | GTK/Qt theme settings |
| **🔒 Privacy** | Telemetry and privacy tweaks |
| **📦 Overlays** | rpm-ostree layered packages (Atomic only) |
| **🩺 Doctor** | Dependency checker |
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
