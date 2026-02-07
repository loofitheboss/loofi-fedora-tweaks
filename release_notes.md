# Loofi Fedora Tweaks v4.1.0 - The Polish Update ✨

Welcome to v4.1.0! This release focuses on refining the user experience and making the app feel more native and professional.

## ✨ New Features

* **Visual Progress Bars**:
  * Say goodbye to scrolling text logs! We now have a proper progress bar that shows download and installation status for DNF and Flatpak operations.
  * Cleaner, more focused UI during updates.
* **System Tray Integration**:
  * The app now minimizes to the system tray instead of quitting.
  * Look for the Loofi icon in your panel!
* **Modern Styling**:
  * Refined look for progress bars and group boxes to match the modern Fedora aesthetic.

## 🐛 Bug Fixes

* Fixed a potential crash on startup related to dependency checking.
* Improved robustness of internal command handling.

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.1.0-1.fc43.noarch.rpm
```
