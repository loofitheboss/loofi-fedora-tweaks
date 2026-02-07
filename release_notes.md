# Loofi Fedora Tweaks v4.3.0 - The Elitebook Integration Update 💻

This release brings deep integration features specifically for the HP Elitebook 840 G8, making your laptop feel truly supported on Fedora.

## 💻 Elitebook Features

* **Native Fingerprint Enrollment**:
  * No more command line or hunting in settings! Enroll your fingerprint directly from the app with a beautiful new wizard.
  * Visual feedback guides you through the process.
* **Battery Health Management**:
  * Set a charging limit (80% or 100%) to prolong your battery life.
  * **New Persistence**: Your limit now automatically reapplies after every reboot!
* **Enhanced Fan Control**:
  * Install and manage `nbfc-linux` directly.
  * Added quick profile switching (Quiet/Balanced) to manage noise.

## ✨ Improvements

* Refactored codebase for better separation of hardware concerns (`utils.battery`, `utils.fan_control`, `utils.fingerprint`).
* Improved prompt messages for better clarity.

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.3.0-1.fc43.noarch.rpm
```
