# Loofi Fedora Tweaks v4.0.0 - Gaming & Network Update

This release introduces powerful new features for gamers and privacy-conscious users, along with further UI refinements.

## 🚀 New Features

### 🎮 Gaming Optimizations

* **Feral GameMode & MangoHud**: One-click installation and status monitoring for these essential gaming tools.
* **ProtonUp-Qt**: Easily install and manage Proton GE versions for Steam directly from the app (Flatpak).
* **Steam Devices**: Fix controller recognition issues with strict udev rules.

### 🌐 Network & Privacy

* **DNS Switcher**: Quickly toggle your DNS settings between high-speed/privacy providers:
  * Google (8.8.8.8)
  * Cloudflare (1.1.1.1)
  * Quad9 (9.9.9.9)
  * AdGuard
  * System Default (DHCP)
* **MAC Address Randomization**: Enable Wi-Fi MAC randomization to protect your privacy on public networks.

## 📦 Improvements

* **UI Polish**: Refined layout and consistent styling across new tabs.
* **Stability**: Fixed minor syntax issues and improved dependency handling.

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/repo/loofi-fedora-tweaks.repo
sudo dnf install loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.0.0-1.fc43.noarch.rpm
```
