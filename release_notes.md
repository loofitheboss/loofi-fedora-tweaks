# Loofi Fedora Tweaks v4.0.1 - Hotfix

This is a hotfix release for v4.0.0 addressing a startup crash.

## 🐛 Bug Fixes

* Fixed a critical startup crash caused by an incorrect import in the main window logic (`UnboundLocalError`).

## 🚀 Key Features (v4.0.0)

* **Gaming Optimizations**: GameMode, MangoHud, ProtonUp-Qt.
* **Network & Privacy**: DNS Switcher, MAC Randomization.
* **Repo Fix**: DNF repository is fully functional.

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/repo/loofi-fedora-tweaks.repo
sudo dnf install loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.0.1-1.fc43.noarch.rpm
```
