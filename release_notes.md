# Loofi Fedora Tweaks v4.5.0 - The Polish Update ✨

We've been busy under the hood making things smoother and more reliable!

## 🛡️ Robustness Improvements

* **Smarter System Tray**: The app now intelligently checks if your desktop environment supports a System Tray before trying to create an icon. No more potential crashes on minimal window managers!
* **Graceful Degradation**: Features like "User Presets" now check if tools like `powerprofilesctl` or `gsettings` are actually installed. If they're missing (e.g., on a desktop without a battery), the app won't panic—it just works around it.

## 🧪 Technical Improvements

* **Unit Tests**: We've added a comprehensive test suite for our core utilities (`tests/test_utils.py`) to prevent regressions.
* **Linting & Cleanup**: Fixed numerous internal code warnings for a cleaner, more maintainable codebase.

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.5.0-1.fc43.noarch.rpm
```
