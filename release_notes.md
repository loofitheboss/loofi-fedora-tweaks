# Loofi Fedora Tweaks v5.5.0 - The "Ecosystem" Update 🌐

This update introduces cloud sync and community preset sharing!

## 🌐 New Presets & Sync Tab

The Presets tab has been completely redesigned with three sub-tabs:

### 📁 My Presets

* Save and restore your system configuration locally.

### 🌐 Community Presets

* **Browse**: Discover presets shared by other Fedora users.
* **Download**: One-click download and apply community presets.
* **Categories**: Gaming, Productivity, Privacy, and more.

### ☁️ Backup & Sync

* **Export/Import**: Backup all settings to a JSON file.
* **GitHub Gist Sync**: Sync your config to a private Gist.
  * Push your config to the cloud.
  * Pull config from Gist on any machine.
  * Secure: Uses your personal GitHub token.

## 🏗️ New Utilities

* **`utils/config_manager.py`**: `ConfigManager` for full config export/import.
* **`utils/cloud_sync.py`**: `CloudSyncManager` for Gist sync and community presets.

## 📦 Installation

**Via DNF:**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Manual:**

```bash
sudo dnf install ./loofi-fedora-tweaks-5.5.0-1.fc43.noarch.rpm
```

## 🔐 Privacy Note

* All cloud features are **optional**.
* GitHub tokens are stored locally with restrictive permissions.
* Community presets are read-only from a public GitHub repo.
