# Loofi Fedora Tweaks v4.6.0 - The Hardware Mastery Update 🛠️

We're going deep on HP Elitebook integration! This release ensures your settings stick and your biometrics just work.

## 🔋 Persistent Battery Limits

* **Set it and Forget it**: Your 80% battery limit now survives reboots!
* **Systemd Service**: We now generate a robust "oneshot" systemd service that reapplies your charge threshold every time your computer starts.

## 👆 Fingerprint Enrollment Wizard

* **Visual Guide**: A new GUI dialog (`fprintd` integration) walks you through the fingerprint enrollment process.
* **Progress Bar**: Visual feedback for each successful scan. No more guessing in the terminal!

## ❄️ Enhanced Fan Control

* **Profile Selection**: New Dropdown menu for **NBFC (NoteBook FanControl)**.
* **Modes**: Easily switch between **Quiet**, **Balanced**, and **Performance** cooling profiles.

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.6.0-1.fc43.noarch.rpm
```
