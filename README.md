# Loofi Fedora Tweaks v5.0.0 "Visual Revolution" 🎨

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>The Ultimate Post-Install Utility for Fedora 43 KDE</strong><br>
  <em>Optimized for HP Elitebook 840 G8</em>
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v5.0.0">
    <img src="https://img.shields.io/badge/Release-v5.0.0-blue?style=for-the-badge&logo=github" alt="Release v5.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Plasma-6-purple?style=for-the-badge&logo=kde" alt="KDE Plasma"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
</p>

---

## 🚀 What's New in v5.0?

### 🎨 Visual Revolution

We've completely redesigned the UI to feel like a modern, premium desktop app.

* **Modern Sidebar**: Replaced cluttered tabs with a sleek, vertical navigation menu.
* **Dashboard**: A new "Home" screen with **System Health Checks** (Snapshots, Updates) and **Quick Action** buttons.
* **Dark Glass Theme**: A custom-built `modern.qss` theme brings rounded corners, subtle animations, and a cohesive dark mode without external dependencies.

---

## ✨ Key Features

### 🛡️ Safety Net (New in v4.7)

* **Snapshot Integration**: Automatically prompts you to create a **Timeshift** snapshot before running risky operations like System Updates or Cleanup.
* **Undo System**: Made a mistake? The new **Undo** button in the Network tab lets you revert changes (like MAC Randomization) instantly.
* **Smart Locks**: Gracefully handles DNF locks—no more frozen windows if an update is running in the background.

### ⚡ Hardware Mastery (Optimized for HP Elitebook)

* **Persistent Battery Limits**: Set your charge threshold to **80%** or **100%** and have it persist across reboots via a dedicated Systemd service.
* **Fingerprint Wizard**: Enroll your biometrics using a simplified GUI (wraps `fprintd`).
* **Fan Control Profiles**: Switch between **Quiet**, **Balanced**, and **Performance** modes using `nbfc-linux`.

### 🎮 Gaming & Performance

* **GameMode & MangoHud**: Toggle performance overlays and optimizations with one click.
* **ProtonUp-Qt**: Easily install compatibility tools for Steam.
* **DNS Switcher**: Fast switching between Google (8.8.8.8), Cloudflare (1.1.1.1), and Quad9.

### 📦 System Management

* **Repositories**: Enable **RPM Fusion** (Free/Non-Free), Multimedia Codecs, and Flathub with a single click.
* **Essential Apps**: Bulk install VS Code, Chrome, Discord, Spotify, and more.
* **Cleanup**: One-click system cleaning (dnf autoremove, cache cleaning) with built-in safety checks.

---

## 📦 Installation

### Option 1: DNF Repository (Recommended)

Add the repo to receive automatic updates:

```bash
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/repo/loofi-fedora-tweaks.repo
sudo dnf install loofi-fedora-tweaks --refresh
```

### Option 2: Manual RPM Install

Download the latest `.rpm` from [Releases](https://github.com/loofitheboss/loofi-fedora-tweaks/releases) and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-5.0.0-1.fc43.noarch.rpm
```

### Option 3: Run from Source

Requirements: `python3-pyqt6`, `polkit`, `dnf`.

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
./run.sh
```

---

## 📸 Screenshots

| Dashboard | Dark Theme |
|:---:|:---:|
| *New Home Screen with Health Checks* | *Glassmorphism UI* |
| *(Screenshot Placeholder)* | *(Screenshot Placeholder)* |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

Values user privacy and freedom. Open Source. MIT License.

---

## 👨‍💻 Author

**Loofi** - [GitHub](https://github.com/loofitheboss)
