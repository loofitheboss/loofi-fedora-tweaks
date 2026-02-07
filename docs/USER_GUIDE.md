# Loofi Fedora Tweaks - User Guide 📖

Welcome to **Loofi Fedora Tweaks v5.0.0**! This guide will help you get started with the app and explore all its features.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Navigation](#navigation)
3. [Dashboard](#dashboard)
4. [System Updates](#system-updates)
5. [HP Elitebook Tweaks](#hp-elitebook-tweaks)
6. [Gaming & Performance](#gaming--performance)
7. [Network & Privacy](#network--privacy)
8. [Safety Features](#safety-features)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

**Recommended: Using DNF**

```bash
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/repo/loofi-fedora-tweaks.repo
sudo dnf install loofi-fedora-tweaks --refresh
```

**Manual Install**
Download the `.rpm` from [GitHub Releases](https://github.com/loofitheboss/loofi-fedora-tweaks/releases) and run:

```bash
sudo dnf install ./loofi-fedora-tweaks-5.0.0-1.fc43.noarch.rpm
```

### Launching the App

After installation, you can launch the app from:

* **Application Menu**: Search for "Loofi Fedora Tweaks"
* **Terminal**: Run `loofi-fedora-tweaks`

---

## Navigation

Loofi Fedora Tweaks v5.0 features a **modern sidebar navigation** on the left side of the window. Click any item to switch between sections:

| Icon | Section | Description |
|:---:|:---|:---|
| 🏠 | **Home** | Dashboard with quick actions and system health |
| ℹ️ | **System Info** | View CPU, RAM, Battery, and Disk info |
| 📦 | **Updates** | Manage DNF and Flatpak updates |
| 🧹 | **Cleanup** | Clean cache, orphan packages, and logs |
| 💻 | **HP Tweaks** | Battery limits, Fan control, Fingerprint setup |
| 🚀 | **Apps** | Install essential apps (VS Code, Chrome, etc.) |
| 🎮 | **Gaming** | GameMode, MangoHud, Proton tools |
| 🌐 | **Network** | DNS Switcher, MAC Randomization, Undo |
| 💾 | **Presets** | Save and load system configurations |
| 📂 | **Repos** | Enable RPM Fusion, Flathub, Codecs |
| 🔒 | **Privacy** | Telemetry and privacy settings |
| 🎨 | **Theming** | Change accent colors and themes |

---

## Dashboard

The **Dashboard** (Home) is your starting point. It shows:

### System Health

* **Snapshot Status**: Shows if Timeshift is installed and ready.
* **Update Status**: Indicates if updates are available.

### Quick Actions

Four large buttons for common tasks:

* 🧹 **Clean Cache**: Jump to the Cleanup tab.
* 🔄 **Update All**: Jump to the Updates tab.
* 🔋 **Power Profile**: Jump to the Presets tab.
* 🎮 **Gaming Mode**: Jump to the Gaming tab.

---

## System Updates

### Update All

Click **Update All** to run:

```bash
sudo dnf update -y && flatpak update -y
```

Before any update, the app will:

1. **Check for DNF Lock**: If another update is running, you'll see a warning instead of the app freezing.
2. **Prompt for Snapshot**: If Timeshift is installed, you'll be asked to create a backup first.

### Per-Package Updates

You can also see individual package updates and choose which to install.

---

## HP Elitebook Tweaks

Specific optimizations for **HP Elitebook 840 G8**.

### Battery Charge Limit

* **80% Limit**: Click to limit battery charge to 80%, extending battery lifespan.
* **100% Limit**: Click to allow full charge.
* **Persistence**: The setting is saved via a Systemd service and reapplied on every reboot.

### Fingerprint Reader

* Click **Enroll Fingerprint** to launch the fingerprint setup wizard.
* The wizard wraps `fprintd-enroll` with a visual progress bar.

### Fan Control (NBFC)

* If `nbfc-linux` is installed, you can switch between **Quiet**, **Balanced**, and **Performance** fan profiles.
* If not installed, you'll see a prompt to install it.

---

## Gaming & Performance

### GameMode

* **Enable**: Click to activate Feral GameMode (CPU/GPU performance boost).
* **Disable**: Click to deactivate.

### MangoHud

* **Toggle**: Enable/disable the FPS overlay for Vulkan/OpenGL games.

### ProtonUp-Qt

* **Install**: One-click install for ProtonUp-Qt, a tool to manage Proton-GE versions for Steam.

### Steam Devices

* **Install**: Fix controller support by installing `steam-devices` udev rules.

---

## Network & Privacy

### DNS Switcher

Quickly switch your system DNS to one of the following:

* **Google**: 8.8.8.8, 8.8.4.4
* **Cloudflare**: 1.1.1.1, 1.0.0.1
* **Quad9**: 9.9.9.9, 149.112.112.112
* **Reset**: Restore to automatic DHCP DNS.

### MAC Randomization

* Toggle to randomize your Wi-Fi MAC address on each connection for enhanced privacy.

### Undo Last Action

* Made a mistake? Click **Undo Last Action** to revert your most recent network change (like MAC randomization or DNS override).

---

## Safety Features

Loofi Fedora Tweaks is designed to keep your system safe.

### Timeshift Snapshot Prompts

Before you run **Update All** or **Clean All**, the app checks if Timeshift is installed. If it is, you'll be prompted:

> "Would you like to create a Timeshift snapshot before proceeding?"

* Click **Yes** to create a backup.
* Click **No** to skip (at your own risk).

### DNF Lock Detection

If another package manager (like GNOME Software or another terminal) is running an update, the app will detect the lock file (`/var/run/dnf.pid`) and display a warning instead of hanging.

### Undo System

The **Network** tab tracks your changes in a history file. If you toggle MAC Randomization or change DNS, you can click **Undo** to revert.

---

## Troubleshooting

### App Won't Start

* Ensure `python3-pyqt6` is installed: `sudo dnf install python3-pyqt6`
* Try running from terminal to see errors: `loofi-fedora-tweaks`

### "pkexec not found"

* Install polkit: `sudo dnf install polkit`

### Battery Limit Not Persisting

* Ensure the Systemd service is enabled: `systemctl status loofi-battery-limit.service`
* If it fails, check logs: `journalctl -xeu loofi-battery-limit.service`

### Fingerprint Enrollment Fails

* Ensure `fprintd` is installed: `sudo dnf install fprintd fprintd-pam`
* Run `fprintd-enroll` manually to check for errors.

### Fan Control Not Showing Profiles

* Install NBFC: Follow the [nbfc-linux](https://github.com/nbfc-linux/nbfc-linux) installation guide.
* Load a profile for your laptop model.

---

## Feedback & Support

Found a bug or have a feature request?

* Open an issue on [GitHub](https://github.com/loofitheboss/loofi-fedora-tweaks/issues)

---

**Thank you for using Loofi Fedora Tweaks!** 🎉
