# Changelog

All notable changes to this project will be documented in this file.

## [6.1.0] - 2026-02-07 "Polyglot Update"

### Added

- **Internationalization (i18n)**: Full localization infrastructure.
- **Translation Files**: `.ts` files for English (`en.ts`) and Swedish (`sv.ts`).
- **414 Translatable Strings**: All UI text wrapped with `self.tr()`.
- **Auto Locale Detection**: `QTranslator` loads translations based on system language.

### Changed

- `main.py`: Added `QTranslator` and `QLocale` integration.
- All 17 UI tab files updated with `self.tr()` wrappers.

### New Files

- `resources/translations/en.ts` - English source strings.
- `resources/translations/sv.ts` - Swedish translation template.
- `resources/translations/README.md` - Translator documentation.

---

## [6.0.0] - 2026-02-07 "Autonomy Update"

### Added

- **Scheduler Tab**: New tab for managing scheduled automation tasks.
- **Background Service**: Systemd user service (`loofi-fedora-tweaks.service`) for running tasks automatically.
- **Notifications**: Desktop toast notifications via `notify-send` when tasks complete.
- **Power Triggers**: Execute tasks when switching to battery or AC power.
- **CLI Daemon Mode**: `--daemon` flag to run as background process.

### New Files

- `utils/scheduler.py` - Task scheduling engine with time and power triggers.
- `utils/notifications.py` - Desktop notification wrapper.
- `utils/daemon.py` - Background service daemon.
- `ui/scheduler_tab.py` - Scheduler management UI.
- `config/loofi-fedora-tweaks.service` - Systemd unit file.

---

## [5.5.0] - 2026-02-07 "Ecosystem Update"

### Added

- **Cloud Sync**: Sync configuration to GitHub Gist.
- **Config Export/Import**: Backup and restore all settings to JSON.
- **Community Presets**: Browse and download presets from GitHub.
- **Redesigned Presets Tab**: Three sub-tabs (My Presets, Community, Backup & Sync).

### New Files

- `utils/config_manager.py` - Full config export/import.
- `utils/cloud_sync.py` - GitHub Gist sync and community presets.

---

## [5.2.0] - 2026-02-07 "Silicon Update"

### Added

- **Hardware Tab**: New consolidated hardware control tab.
- **CPU Governor Switching**: Toggle powersave/schedutil/performance.
- **Power Profile Management**: Quick switch power-saver/balanced/performance.
- **GPU Mode Switching**: Integrated/Hybrid/Dedicated modes via envycontrol.
- **Fan Control**: Manual slider and auto mode via nbfc-linux.

### New Files

- `utils/hardware.py` - HardwareManager for CPU, GPU, Fan, Power controls.
- `ui/hardware_tab.py` - Consolidated hardware control UI.

---

## [5.1.0] - 2026-02-07 "Atomic Update"

### Added

- **Atomic/Silverblue Support**: Automatic detection of rpm-ostree systems.
- **System Overlays Tab**: Manage layered packages on Atomic variants.
- **Polkit Policy**: Professional authorization dialogs.
- **Unified Package Manager**: Abstracts dnf and rpm-ostree operations.

### New Files

- `utils/system.py` - SystemManager for system detection.
- `utils/package_manager.py` - Unified package management.
- `ui/overlays_tab.py` - Layered package management UI.
- `config/org.loofi.fedora-tweaks.policy` - Polkit policy file.

---

## [5.0.0] - 2026-02-07 "Visual Revolution"

### Added

- **Modern Sidebar Navigation**: Replaced top tabs with a sleek left-side menu.
- **Dashboard Tab**: New "Home" screen with system health checks and quick action buttons.
- **Dark Theme (modern.qss)**: Custom glassmorphism-inspired QSS theme with rounded corners.

### Changed

- `ui/main_window.py` now uses `QStackedWidget` + `QListWidget` instead of `QTabWidget`.
- Window resized to 1100x700 for better content display.

## [4.7.0] - 2026-02-07 "Safety Net"

### Added

- **Timeshift Snapshot Prompts**: Before risky operations, the app prompts for a Timeshift backup.
- **Undo System**: `utils/history.py` tracks changes; "Undo" button in Network tab reverts actions.
- **DNF Lock Detection**: `utils/safety.py` checks for running DNF/RPM processes to prevent hangs.

### Changed

- `ui/updates_tab.py` and `ui/cleanup_tab.py` now include safety checks before operations.

## [4.6.0] - 2026-02-07 "Hardware Mastery"

### Added

- **Persistent Battery Limits**: Battery charge limits (80%/100%) now persist via a Systemd oneshot service.
- **Fingerprint Enrollment Wizard**: GUI dialog wrapping `fprintd-enroll` with progress bar.
- **Fan Control Profiles**: Dropdown to switch NBFC profiles (Quiet/Balanced/Performance).

### Changed

- `utils/battery.py` now generates a Systemd service file.
- `ui/tweaks_tab.py` includes fan profile dropdown and fingerprint button.

## [4.5.0] - 2026-02-06 "Refinement"

### Added

- Unit tests for core utilities (`tests/`).
- Robustness improvements: checks for missing tools (`gsettings`, `powerprofilesctl`).

### Fixed

- System Tray initialization crashes on systems without tray support.

## [4.0.0] - 2026-02-05 "Gaming & Network"

### Added

- **Gaming Tab**: GameMode, MangoHud, ProtonUp-Qt, Steam Devices.
- **Network Tab**: DNS Switcher (Google, Cloudflare, Quad9), MAC Randomization.
- **Presets Tab**: Save and load system configurations.

### Changed

- Major UI reorganization into more logical categories.

## [3.0.0] - 2026-02-04 "Essential Apps"

### Added

- **Apps Tab**: One-click install for VS Code, Chrome, Discord, Spotify, etc.
- **Repos Tab**: Enable RPM Fusion, Flathub, Multimedia Codecs.
- **Privacy Tab**: Disable telemetry and trackers.

## [2.0.0] - 2026-02-03 "Updates & Cleanup"

### Added

- **Updates Tab**: Real-time progress bars for DNF and Flatpak updates.
- **Cleanup Tab**: Safe system cleaning with confirmation dialogs.
- **System Tray**: Minimize to tray, quick access menu.

## [1.0.0] - 2026-02-01 "Initial Release"

### Added

- **System Info Tab**: View CPU, RAM, Battery, Disk, Uptime.
- **HP Tweaks Tab**: Battery charge limits, audio fixes.
- Basic PyQt6 structure.
