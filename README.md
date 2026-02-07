# Loofi Fedora Tweaks

<p align="center">
  <img src="loofi-fedora-tweaks/assets/icon.png" alt="Loofi Fedora Tweaks" width="128"/>
</p>

<p align="center">
  <strong>A powerful GUI utility for Fedora 43 KDE, optimized for HP Elitebook 840 G8</strong>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases">
    <img src="https://img.shields.io/github/v/release/loofitheboss/loofi-fedora-tweaks" alt="Release"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/KDE_Plasma-6-purple" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green" alt="Python"/>
</p>

---

## ✨ Features

### 📊 System Info

# Loofi Fedora Tweaks v3.0.0

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Fedora](https://img.shields.io/badge/Fedora-43-blue)

**Loofi Fedora Tweaks** is a post-install configuration tool specifically designed for **Fedora 43 KDE**, optimized for the **HP Elitebook 840 G8**.

## 🚀 Key Features (v3.0.0)

* **System Info**: View detailed specs, battery health, and uptime.
* **Updates Manager**:
  * Real-time progress bars for DNF and Flatpak updates.
  * Update Firmware (`fwupdmgr`) and managing Kernels.
* **Repository Management**:
  * One-click **RPM Fusion** (Free & Non-Free) enablement.
  * Install Multimedia Codecs (`ffmpeg`, `gstreamer`).
  * Enable Flathub.
* **Cleanup & Safety**:
  * Safe cleanup (DNF cache, Journal vacuum).
  * **Timeshift Integration**: Warns before risky operations if no snapshot exists.
* **HP Elitebook Tweaks**:
  * **Battery Limits**: Set 80% or 100% charge threshold (Persistent via systemd).
  * **Fan Control**: Easy install for `nbfc-linux`.
  * **Audio**: One-click Pipewire restart.
* **Essential Apps**: Install VS Code, Chrome, Discord, Spotify, and more.
* **Privacy & Theming**: Remove telemetry, toggle Firewall, and install fonts/themes.
* **Modern UI**: Polished interface with KDE Breeze styling and System Tray support.

## 📦 Installation

### Option 1: DNF Repository (Recommended)

```bash
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/repo/loofi-fedora-tweaks.repo
sudo dnf install loofi-fedora-tweaks --refresh
```

### Option 2: RPM Package

```bash
sudo dnf install ./loofi-fedora-tweaks-2.0.0-1.fc43.noarch.rpm
```

### Option 3: Flatpak

```bash
flatpak install --user loofi-fedora-tweaks.flatpak
flatpak run org.loofi.FedoraTweaks
```

### Option 4: From Source

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
./run.sh
```

---

## 📋 Requirements

* Fedora 43 (KDE Plasma recommended)
* Python 3.12+
* PyQt6
* polkit (for pkexec)

---

## 📸 Screenshots

*Coming soon*

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📜 License

This project is open source and available under the MIT License.

---

## 👨‍💻 Author

**Loofi** - [GitHub](https://github.com/loofitheboss)
