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

- View hostname, kernel, Fedora version, CPU, RAM, disk usage, uptime, and battery status

### 🔄 Updates

- **Update All**: One-click DNF + Flatpak + Firmware updates
- **Kernel Management**: List installed kernels and remove old ones
- Individual update buttons for DNF, Flatpak, and Firmware

### 🧹 Cleanup & Maintenance

- Clean DNF cache
- Remove unused packages (autoremove)
- Vacuum system journal
- SSD Trim (fstrim)
- Rebuild RPM database

### 💻 HP Elitebook 840 G8 Tweaks

- Power profile switching (Performance/Balanced/Power Saver)
- Audio service optimization (Pipewire restart)
- Battery charge limit control (80% / 100%)

### 📦 Essential Apps

One-click installers for:

- Google Chrome, Visual Studio Code, Steam
- VLC, Discord, Spotify, OBS Studio
- GIMP, LibreOffice, Brave Browser

### ⚡ Advanced Tweaks

- DNF speed optimization (parallel downloads, fastest mirror)
- TCP BBR network optimization
- GameMode for gaming performance
- Swappiness reduction for SSDs

### 🔒 Privacy & Security

- Firewall (firewalld) controls
- Remove telemetry packages
- Security update checker

### 🎨 Theming

- Apply KDE themes (Breeze Dark/Light, Oxygen)
- Install icon themes (Papirus, Tela)
- Install developer fonts (FiraCode, JetBrains Mono)

---

## 📥 Installation

### Option 1: DNF Repository (Recommended)

```bash
sudo tee /etc/yum.repos.d/loofi-fedora-tweaks.repo << EOF
[loofi-fedora-tweaks]
name=Loofi Fedora Tweaks
baseurl=https://loofitheboss.github.io/loofi-fedora-tweaks/repo
enabled=1
gpgcheck=0
EOF

sudo dnf install loofi-fedora-tweaks
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

- Fedora 43 (KDE Plasma recommended)
- Python 3.12+
- PyQt6
- polkit (for pkexec)

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
