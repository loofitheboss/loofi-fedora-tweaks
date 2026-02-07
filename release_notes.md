# Loofi Fedora Tweaks v5.2.0 - The "Silicon" Update ⚡

This update brings advanced hardware control for power users, gamers, and developers!

## ⚡ New Hardware Tab

A brand new consolidated hardware control interface:

### CPU Governor

* **Real-time frequency display**: See your current CPU frequency.
* **Governor selector**: Switch between `powersave`, `schedutil`, and `performance` instantly.

### Power Profiles

* **One-click switching**: Power Saver, Balanced, or Performance modes via `power-profiles-daemon`.

### GPU Mode Switching (Hybrid Laptops)

* **Automatic detection**: Detects NVIDIA Optimus laptops.
* **Mode toggle**: Switch between Integrated, Hybrid, and Dedicated GPU modes (via `envycontrol`).
* **Logout warning**: Clear indication that a logout/reboot is required.

### Fan Control

* **NBFC integration**: Works with `nbfc-linux` for notebook fan control.
* **Manual slider**: Set fan speed from 0-100%.
* **Auto mode**: Let the system manage fan speed automatically.

## 🏗️ Architecture

* **`utils/hardware.py`**: New `HardwareManager` class centralizing all hardware controls.
* **`ui/hardware_tab.py`**: New consolidated UI with card-based layout.
* **Auto-refresh**: Dynamic values (CPU freq, fan speed) update every 5 seconds.

## 📦 Installation

**Via DNF:**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual:**

```bash
sudo dnf install ./loofi-fedora-tweaks-5.2.0-1.fc43.noarch.rpm
```
