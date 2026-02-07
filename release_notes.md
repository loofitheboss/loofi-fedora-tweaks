# Loofi Fedora Tweaks v6.0.0 - The "Autonomy" Update ⏰

This major update introduces task automation and a background service!

## ⏰ New Scheduler Tab

Schedule automated tasks to run in the background:

### Supported Actions

* **🧹 System Cleanup** - Auto-clean caches and orphaned packages
* **📦 Update Check** - Check for updates and notify you
* **☁️ Sync Config** - Auto-sync your settings to GitHub Gist
* **💾 Apply Preset** - Auto-apply a preset on schedule

### Schedule Triggers

* **⏰ Hourly / 📅 Daily / 📆 Weekly** - Time-based automation
* **🚀 On Boot** - Run when you log in
* **🔋 On Battery** - Trigger when unplugging AC
* **🔌 On AC Power** - Trigger when plugging in

## 🔧 Background Service

* **Systemd User Service** - Runs in the background without root
* **Enable/Disable** - One-click service management from the app
* **Power-aware** - Automatically detects power state changes
* **Notifications** - Toast notifications when tasks complete

## 🏗️ New Modules

| File | Description |
|:---|:---|
| `utils/notifications.py` | Desktop notification wrapper |
| `utils/scheduler.py` | Task scheduling engine |
| `utils/daemon.py` | Background service daemon |
| `ui/scheduler_tab.py` | Scheduler management UI |
| `config/loofi-fedora-tweaks.service` | Systemd unit file |

## 📦 Installation

**Via DNF:**

```bash
sudo dnf update loofi-fedora-tweaks --refresh
```

**Enable the background service:**

```bash
systemctl --user enable --now loofi-fedora-tweaks
```

## 🚀 CLI Support

Run in daemon mode directly:

```bash
loofi-fedora-tweaks --daemon
```

Check version:

```bash
loofi-fedora-tweaks --version
```
