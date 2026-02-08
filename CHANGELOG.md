# Changelog

All notable changes to this project will be documented in this file.

## [11.0.0] - 2026-02-08 "Aurora Update"

### Added

- **Plugin Manifests**: `plugin.json` metadata with version gating and enable/disable state.
- **Plugin Manager UI**: Manage plugins from the Community tab.
- **Support Bundle Export**: ZIP with logs and system info (Diagnostics + CLI).
- **Automation Validation**: Rule validation and dry-run simulation.
- **Release Checklist**: New `docs/RELEASE_CHECKLIST.md`.

### Changed

- **Theme Loading**: Unified stylesheet loading via `modern.qss`.
- **Logging**: Structured error logging for Pulse, remote config, and command runner.
- **CI**: Added CLI smoke checks to CI workflow.

## [10.0.0] - 2026-02-07 "Zenith Update"

### Major Changes

- **Tab Consolidation**: 25 tabs reduced to 15 with sub-navigation via QTabWidget.
- **BaseTab Class**: New `ui/base_tab.py` eliminates code duplication across all command-executing tabs.
- **PrivilegedCommand Builder**: Centralized `utils/commands.py` for safe pkexec operations (argument arrays, not shell strings).
- **Error Framework**: `utils/errors.py` with typed exceptions (DnfLockedError, PrivilegeError, etc.) and recovery hints.
- **Hardware Profiles**: Auto-detect HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS via DMI sysfs data.

### New Features

- **First-Run Wizard**: Hardware auto-detection, use-case selection, and profile persistence on first launch.
- **Command Palette**: Ctrl+K opens a fuzzy-search palette with 60+ feature entries and keyboard navigation.
- **Shared Formatting**: `utils/formatting.py` with bytes_to_human(), seconds_to_human(), percent_bar().
- **CI/CD Pipeline**: GitHub Actions workflows for lint (flake8), test (pytest), build (Fedora 43 rpmbuild), and tag-triggered releases.

### Consolidated Tabs

- **Maintenance**: Merges Updates + Cleanup + Overlays (Atomic overlay conditionally shown).
- **Software**: Merges Apps + Repos into Applications and Repositories sub-tabs.
- **System Monitor**: Merges Performance + Processes with live graphs and process management.
- **Hardware**: Absorbs HP Tweaks (now hardware-agnostic) with audio, battery limit, and fingerprint cards.
- **Security & Privacy**: Merges Security Center + Privacy tab with firewall, telemetry, and security updates sections.
- **Desktop**: Merges Director + Theming into Window Manager and Theming sub-tabs.
- **Development**: Merges Containers + Developer Tools with Distrobox GUI and toolchain installers.
- **Community**: Merges Presets + Marketplace with community preset browsing.
- **Automation**: Merges Scheduler + Replicator + Pulse for task scheduling, IaC exports, and event-driven automation.
- **Diagnostics**: Merges Watchtower + Boot with services, journal viewer, boot analyzer.

### CLI Enhancements

- **`--json` Flag**: Machine-readable JSON output for all CLI commands.
- **`doctor` Command**: Checks critical and optional tool dependencies.
- **`hardware` Command**: Shows detected hardware profile.
- **Version Sync**: CLI version now imports from centralized `version.py`.

### New Files

- `ui/base_tab.py` - Common base class for command-executing tabs
- `ui/maintenance_tab.py` - Consolidated maintenance tab (Updates + Cleanup + Overlays)
- `ui/software_tab.py` - Consolidated software tab (Apps + Repos)
- `ui/monitor_tab.py` - Consolidated system monitor (Performance + Processes)
- `ui/diagnostics_tab.py` - Consolidated diagnostics (Watchtower + Boot)
- `ui/desktop_tab.py` - Consolidated desktop tab (Director + Theming)
- `ui/development_tab.py` - Consolidated development tab (Containers + Developer)
- `ui/community_tab.py` - Consolidated community tab (Presets + Marketplace)
- `ui/automation_tab.py` - Consolidated automation tab (Scheduler + Replicator)
- `ui/wizard.py` - First-run wizard with hardware detection
- `ui/command_palette.py` - Ctrl+K fuzzy-search command palette
- `utils/errors.py` - Centralized error hierarchy
- `utils/commands.py` - PrivilegedCommand builder
- `utils/formatting.py` - Shared formatting utilities
- `utils/hardware_profiles.py` - Hardware profile auto-detection
- `tests/conftest.py` - Shared test fixtures
- `tests/test_v10_features.py` - 57 tests for v10 foundation modules
- `tests/test_cli_enhanced.py` - 30 tests for enhanced CLI
- `.github/workflows/ci.yml` - CI pipeline (lint, test, build)
- `.github/workflows/release.yml` - Tag-triggered release pipeline

### Tests

- 87+ new unit tests covering errors, commands, formatting, hardware profiles, and CLI.
- Shared test fixtures in `conftest.py` for mock_subprocess, temp_config_dir, mock_which.

---

## [9.1.0] - 2026-02-07 "Pulse Update"

### Added

- **Event-Driven Automation**: React to hardware changes, network status, and system events in real-time.
- **SystemPulse Engine**: DBus-based event listener for power, network, and monitor changes with polling fallback.
- **Focus Mode**: Distraction blocking with domain blocking, Do Not Disturb, and process killing.
- **Automation Profiles**: Create rules that trigger actions based on system events.
- **Automation Tab**: New UI for managing automation rules, focus mode profiles, and system status.
- **System Tray Focus Toggle**: Quick Focus Mode toggle from the system tray.
- **Power Event Triggers**: React immediately to AC/Battery transitions.
- **Network Event Triggers**: Detect public Wi-Fi, home network, and VPN connections.
- **Monitor Event Triggers**: React to ultrawide monitor connections, laptop-only mode.

### Automation Actions

- Set Power Profile (power-saver, balanced, performance)
- Set CPU Governor (powersave, schedutil, performance)
- Enable/Disable VPN
- Enable/Disable KWin Tiling
- Set Theme (light/dark)
- Enable/Disable Focus Mode
- Run Custom Command

### New Preset Rules

- **Battery Saver**: Auto-switch to power-saver profile on battery
- **Ultrawide Tiling**: Enable tiling when ultrawide monitor connected

### New Files

- `utils/pulse.py` - DBus event listener with power, network, and monitor detection
- `utils/focus_mode.py` - Focus Mode with domain blocking and process management
- `utils/automation_profiles.py` - Event-triggered automation rules engine
- `ui/pulse_tab.py` - Automation and Focus Mode UI
- `tests/test_pulse_system.py` - Unit tests for v9.1 features

---

## [9.0.0] - 2026-02-07 "Director Update"

### Added

- **Disk Space Monitoring**: New `utils/disk.py` module with disk usage stats, health checks, and large directory finder.
- **System Resource Monitor**: New `utils/monitor.py` module with memory usage, CPU load, and uptime tracking.
- **Dashboard Health Indicators**: Disk usage and memory usage now displayed in the Dashboard health card with color-coded status.
- **CLI `health` Command**: Quick system health overview showing memory, CPU, disk, and power profile status.
- **CLI `disk` Command**: Disk usage analysis with optional `--details` flag for large directory listing.
- **CLI Mode from Main Entry**: New `--cli` / `-c` flag on main entry point to launch CLI mode directly.

### Fixed

- CLI version updated from 7.0.0 to 9.0.0 to match the application version.

### New Files

- `utils/disk.py` - Disk space monitoring and analysis
- `utils/monitor.py` - System resource monitoring (memory, CPU, uptime)
- `tests/test_new_features.py` - Tests for disk, monitor, and CLI features

---

## [9.0.0] - 2026-02-07 "Director Update"

### Added

- **Director Tab**: Window management for KDE, Hyprland, and Sway.
- **TilingManager**: Configuration helpers for Hyprland and Sway with workspace templates.
- **KWinManager**: KDE Plasma tiling scripts and keybinding presets.
- **DotfileManager**: Backup and sync configs to a git repository.
- **Workspace Templates**: Pre-configured layouts for development, gaming, creative work.

### New Files

- `utils/tiling.py` - Hyprland/Sway configuration management
- `utils/kwin_tiling.py` - KDE KWin scripts and window rules
- `ui/director_tab.py` - Window management UI

---

## [8.5.0] - 2026-02-07 "Sentinel Update"

### Added

- **Security Tab**: Complete security hardening center with scoring.
- **Port Auditor**: Scan open ports, identify risks, manage firewall rules.
- **USB Guard Integration**: Block unauthorized USB devices (BadUSB protection).
- **Sandbox Manager**: Launch applications in Firejail/Bubblewrap sandboxes.
- **Security Score**: Real-time 0-100 security health assessment.

### New Files

- `utils/sandbox.py` - Firejail and Bubblewrap wrappers
- `utils/usbguard.py` - USBGuard integration
- `utils/ports.py` - Port scanning and firewall management
- `ui/security_tab.py` - Security Center UI

---

## [8.1.0] - 2026-02-07 "Neural Update"

### Added

- **AI Lab Tab**: Local AI setup and model management interface.
- **AI Hardware Detection**: CUDA, ROCm, Intel NPU, AMD Ryzen AI detection.
- **Ollama Management**: Install Ollama, download and manage models.
- **Model Library**: Support for Llama3, Mistral, CodeLlama, Phi-3, Gemma.
- **Ansible Safety Disclaimer**: Added prominent warning header to exported playbooks.

### New Files

- `utils/ai.py` - Ollama manager and AI configuration
- `utils/hardware.py` - Extended with AI capabilities detection
- `ui/ai_tab.py` - AI Lab UI

---

## [8.0.0] - 2026-02-07 "Replicator Update"

### Added

- **Replicator Tab**: Export system configuration as Infrastructure as Code.
- **Ansible Playbook Export**: Generate playbooks with packages, Flatpaks, GNOME settings.
- **Kickstart Generator**: Create Anaconda-compatible .ks files for automated installs.
- **Watchtower Tab**: Combined diagnostics hub with services, boot analyzer, journal viewer.
- **Gaming-Focused Service Manager**: Filter and manage gaming-related systemd services.
- **Boot Time Analyzer**: Visualize boot time breakdown with optimization suggestions.
- **Panic Button Log Export**: One-click forum-ready diagnostic log export.
- **Containers Tab**: Distrobox GUI for managing development containers.
- **Developer Tab**: One-click install for PyEnv, NVM, Rustup + VS Code extension profiles.
- **Lazy Tab Loading**: Tabs load on-demand for faster application startup.

### New Files

- `utils/ansible_export.py` - Ansible playbook generator
- `utils/kickstart.py` - Kickstart file generator
- `utils/services.py` - Gaming-focused systemd service manager
- `utils/boot_analyzer.py` - Boot time analyzer
- `utils/journal.py` - Journal viewer with panic button
- `utils/containers.py` - Distrobox wrapper
- `utils/devtools.py` - PyEnv, NVM, Rustup installers
- `utils/vscode.py` - VS Code extension management
- `ui/replicator_tab.py` - IaC export UI
- `ui/watchtower_tab.py` - Diagnostics hub UI
- `ui/containers_tab.py` - Container management UI
- `ui/developer_tab.py` - Developer tools UI
- `ui/lazy_widget.py` - Lazy loading widget

---

## [7.0.0] - 2026-02-07 "Community Update"

### Added

- **Preset Marketplace**: Browse and download community presets from GitHub.
- **Configuration Drift Detection**: Track system changes from applied presets.
- **Marketplace Tab**: New UI for community preset discovery.

### New Files

- `utils/marketplace.py` - GitHub-based preset marketplace
- `utils/drift.py` - Configuration drift detection
- `ui/marketplace_tab.py` - Marketplace UI

---

## [6.5.0] - 2026-02-07 "Architect Update"

### Added

- **CLI Mode**: Headless `loofi` command for scripting and automation.
- **Operations Layer**: Extracted business logic from UI tabs (`utils/operations.py`).
- **Plugin System**: Modular architecture for third-party extensions (`utils/plugin_base.py`).
- **Plugins Directory**: `plugins/` folder for community extensions.

### CLI Commands

```bash
loofi info              # System information
loofi cleanup           # DNF clean + journal vacuum + SSD trim
loofi tweak power       # Set power profile
loofi advanced bbr      # Enable TCP BBR
loofi network dns       # Set DNS provider
```

### New Files

- `utils/operations.py` - CleanupOps, TweakOps, AdvancedOps, NetworkOps
- `utils/plugin_base.py` - LoofiPlugin ABC + PluginLoader
- `cli/main.py` - CLI entrypoint
- `plugins/__init__.py` - Plugins directory

---

## [6.2.0] - 2026-02-07 "Engine Room Update"\n\n### Added\n\n- **Boot Tab**: New comprehensive boot management interface.\n- **Kernel Parameter Editor**: GUI wrapper for `grubby` with common presets.\n- **ZRAM Tuner**: Adjust compressed swap size and compression algorithm.\n- **Secure Boot Helper**: MOK key generation and enrollment wizard.\n- **Backup/Restore**: Auto-backup GRUB config before changes.\n\n### New Files\n\n- `utils/kernel.py` - Kernel parameter management.\n- `utils/zram.py` - ZRAM configuration.\n- `utils/secureboot.py` - MOK key management.\n- `ui/boot_tab.py` - Boot management GUI.\n\n---\n\n## [6.1.0] - 2026-02-07 \"Polyglot Update\"

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
