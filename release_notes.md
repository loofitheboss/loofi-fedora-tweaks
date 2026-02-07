# Loofi Fedora Tweaks v4.2.0 - The Safety & Resilience Update 🛡️

This release prioritizes system stability and ensures you have all the necessary tools for a smooth experience.

## 🛡️ New Safety Features

* **Dependency Doctor**:
  * On startup, the app now checks for critical and optional tools (Gamemode, Mangohud, Timeshift, etc.).
  * A new "System Doctor" dialog (accessible via Tray Icon) helps you install missing dependencies with one click.
* **Snapshot Integration**:
  * Before performing risky operations (like System Updates or removing packages), the app now prompts you to create a **Timeshift** or **Snapper** snapshot.
  * You can create snapshots directly from the prompt!

## ✨ Improvements

* Refactored `CleanupTab` to use the new Safety Manager.
* Enhanced internal architecture for better modularity (`utils.safety`, `ui.doctor`).

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.2.0-1.fc43.noarch.rpm
```
