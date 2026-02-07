# Loofi Fedora Tweaks v5.1.0 - The "Atomic" Update ⚛️

This update brings full support for Fedora Silverblue, Kinoite, and other Atomic Desktop variants!

## ⚛️ Fedora Atomic Support

* **rpm-ostree Detection**: The app automatically detects if you're on an immutable system and routes all commands accordingly.
* **Overlays Tab**: A new tab (visible only on Atomic systems) to manage layered packages, with "Remove" and "Reset to Base Image" options.
* **Reboot Indicators**: The Dashboard now shows when a reboot is required to apply pending changes.
* **System Type Display**: See "Workstation (dnf)" or "Silverblue (rpm-ostree)" right on the Dashboard.

## 🔐 Polkit Integration

* **Professional Auth Dialogs**: We now ship a polkit policy file (`org.loofi.fedora-tweaks.policy`) for cleaner authentication prompts.
* **Action Categories**: Separate policies for package management, updates, hardware settings, and system cleanup.

## 🏗️ Architecture Improvements

* **New `utils/system.py`**: Central `SystemManager` class for all system detection logic.
* **New `utils/package_manager.py`**: Unified `PackageManager` abstraction for DNF and rpm-ostree.
* **Modular Design**: Paves the way for a future CLI version (`loofi-cli`).

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**

```bash
sudo dnf install ./loofi-fedora-tweaks-5.1.0-1.fc43.noarch.rpm
```

**On Silverblue/Kinoite:**

```bash
rpm-ostree install ./loofi-fedora-tweaks-5.1.0-1.fc43.noarch.rpm --apply-live
```
