# Loofi Fedora Tweaks v4.4.0 - The Scalability Update 🚀

We're thinking big! This release focuses on making the app easier to maintain and more customizable for you.

## 🚀 New Features

* **Remote App Configuration**:
  * The "Essential Apps" list now fetches updates directly from GitHub.
  * This means we can add new recommended apps *instantly* without you needing to update the whole application!
* **User Presets**:
  * Introducing the **Presets Tab**!
  * Save your current setup (Theme, Icons, Battery Limit, Power Profile) into a named preset.
  * Load your favorite configs (e.g., "Gaming Mode", "Office Mode") with a single click.

## ✨ Improvements

* Moved `AppsTab` to use a threaded fetcher for better responsiveness.
* Added `urllib` based remote config to minimize dependencies.

## 📦 Installation

**Via DNF (Recommended):**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual RPM Install:**
Download the attached `.rpm` and install:

```bash
sudo dnf install ./loofi-fedora-tweaks-4.4.0-1.fc43.noarch.rpm
```
