Name:           loofi-fedora-tweaks
Version:        25.0.3
Release:        1%{?dist}
Summary:        Complete Fedora system management with AI, security, and window management

License:        MIT
URL:            https://github.com/loofitheboss/loofi-fedora-tweaks
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3
Requires:       python3-pyqt6
Requires:       qt6-qtbase-gui
Requires:       mesa-libGL
Requires:       mesa-libEGL
Requires:       polkit
Requires:       libnotify
Requires:       python3-fastapi
Requires:       python3-uvicorn
Requires:       python3-jwt
Requires:       python3-bcrypt
Requires:       python3-httpx

%description
A comprehensive GUI application for Fedora 43+ (KDE Plasma) with system maintenance,
developer tooling, AI integration, security hardening, window management, virtualization,
mesh networking, and workspace state teleportation.
Features: VM Quick-Create, VFIO GPU Passthrough, Loofi Link Mesh, State Teleport,
AI Lab, Security Center, Director, Containers, Watchtower diagnostics, Replicator IaC.

%prep
%setup -q

%install
mkdir -p "%{buildroot}/usr/lib/%{name}"
mkdir -p "%{buildroot}/usr/bin"
mkdir -p "%{buildroot}/usr/share/applications"
mkdir -p "%{buildroot}/usr/share/polkit-1/actions"
mkdir -p "%{buildroot}/usr/lib/systemd/user"
mkdir -p "%{buildroot}/usr/share/icons/hicolor/128x128/apps"

cp -r loofi-fedora-tweaks/* "%{buildroot}/usr/lib/%{name}/"

# Ensure all installed files are world-readable
find "%{buildroot}/usr/lib/%{name}" -type f -exec chmod 644 {} +
find "%{buildroot}/usr/lib/%{name}" -type d -exec chmod 755 {} +

cat > "%{buildroot}/usr/bin/%{name}" << 'EOF'
#!/bin/bash
APP_DIR=/usr/lib/loofi-fedora-tweaks
LOG_DIR="${HOME}/.local/share/loofi-fedora-tweaks"
mkdir -p "${LOG_DIR}"
export PYTHONPATH="${APP_DIR}${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "${APP_DIR}/main.py" "$@" 2>>"${LOG_DIR}/startup.log"
EOF
chmod +x "%{buildroot}/usr/bin/%{name}"

install -m 644 %{name}.desktop "%{buildroot}/usr/share/applications/"
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.policy "%{buildroot}/usr/share/polkit-1/actions/"
install -m 644 loofi-fedora-tweaks/config/loofi-fedora-tweaks.service "%{buildroot}/usr/lib/systemd/user/"
install -m 644 loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png "%{buildroot}/usr/share/icons/hicolor/128x128/apps/"

%files
%defattr(-,root,root,-)
/usr/lib/%{name}
%attr(755,root,root) /usr/bin/%{name}
/usr/share/applications/%{name}.desktop
/usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy
/usr/lib/systemd/user/loofi-fedora-tweaks.service
/usr/share/icons/hicolor/128x128/apps/loofi-fedora-tweaks.png

%changelog
* Wed Feb 11 2026 Loofi <loofi@example.com> - 25.0.3-1
- v25.0.3 Maintenance Update Crash Hotfix
- Fixed crash when clicking Maintenance update actions by unifying update execution path
- Aligned update-all sequencing to include system update as queued first step
- Added headless regression coverage for maintenance update command selection and queue startup

* Mon Feb 09 2026 Loofi <loofi@example.com> - 24.0.0-1
- v24.0 Power Features
- Created BaseActionExecutor ABC with privileged execution support (pkexec integration)
- Centralized BaseWorker QThread pattern in core/workers/
- Migrated system services to services/system/ (system.py, services.py, processes.py, process.py)
- Migrated hardware services to services/hardware/ (hardware.py, battery.py, disk.py, temperature.py, bluetooth.py, hardware_profiles.py)
- Created scripts/ directory with packaging scripts (build_rpm.sh, build_flatpak.sh, build_appimage.sh, build_sdist.sh)
- Added comprehensive import validation tests (34 tests)
- Backward-compatibility shims in utils/ with deprecation warnings

* Mon Feb 09 2026 Loofi <loofi@example.com> - 21.0.1-1
- Packaging: Remove python-jose test dependency (fixes RPM install on Fedora)
- Use PyJWT's ExpiredSignatureError instead of python-jose in tests
- All runtime code already uses PyJWT correctly

* Mon Feb 09 2026 Loofi <loofi@example.com> - 21.0.0-1
- v21.0 UX Stabilization & Layout Integrity
- Baseline layout fixes: native title bar, border cleanup, documentMode
- Scoped QTabBar scroller styling
- Minimum window size (800x500) with consistent margins
- HiDPI safety: font-metrics-based sizing, pt units
- Frameless mode feature flag (stub)
- Layout regression tests
- Theme-aware inline styles (top-3 fixes)

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.2-2
- UI hotfix: force native title-bar flags in MainWindow to prevent top chrome overlap on KDE Plasma (Wayland/X11)
- Tests: add main-window geometry sanity test for central client-area placement

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.2-1
- UI: Fix top tab overflow by enabling scroll buttons and styling scrollers
- Dependencies: refresh Python dependencies to latest versions

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.1-1
- Packaging: switch JWT dependency to python3-jwt (PyJWT) for Fedora 43

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.0-1
- v20.0 Synapse Phase 1: Remote Management & EventBus Hive Mind
- Loofi Web API: Headless FastAPI server with JWT auth (--web flag)
- EventBus: Thread-safe pub/sub system for inter-agent communication
- AgentScheduler: Event-driven agent execution with rate limiting
- Web Dashboard: Mobile-responsive dark-theme UI for remote management
- Real agents: cleanup.json, security.json, thermal.json with event subscriptions
- 66 new tests: API security, EventBus thread safety, agent integration

* Mon Feb 09 2026 Loofi <loofi@example.com> - 19.0.0-1
- v19.0 Vanguard Phase 1: Centralized ActionExecutor with preview and dry-run
- Unified ActionResult schema for all system actions
- Structured JSONL action logging with diagnostics export
- Agent Arbitrator for thermal/battery-aware scheduling
- Operations bridge for CLI/headless execution
- v19.0 Vanguard Phase 2: UX enhancements
- Breadcrumb bar showing Category > Page with description
- Status bar with keyboard shortcut hints and version badge
- Sidebar badges: recommended (star) and advanced (gear) labels
- Tooltips on all 26 sidebar tabs
- Category auto-select first child on click
- Dark and light theme styles for all new elements
- 1593 tests passing

* Mon Feb 09 2026 Loofi <loofi@example.com> - 18.1.1-1
- v18.1.1 Hotfix: Fix startup crash due to sidebar refactor
- Fixed AttributeError on startup (setCurrentRow)
- Stabilized QTreeWidget initialization

* Mon Feb 09 2026 Loofi <loofi@example.com> - 18.1.0-1
- v18.1 Navigator: Categorized Sidebar & Enhanced UX
- UX Overhaul: Refactored sidebar with collapsible categories (System, Hardware, Network, etc.)
- Improved Navigation: Updated search and keyboard shortcuts for hierarchical menu
- Dashboard shortcuts updated for new structure

* Mon Feb 09 2026 Loofi <loofi@example.com> - 18.0.0-1
- v18.0 Sentinel: Autonomous Agent Framework, AI Agent Planner
- Agent Framework: Configurable agents for system monitoring, security, cleanup
- Agent Runner: Background execution engine with rate limiting and scheduling
- AI-Powered Planner: Natural language goal to agent configuration
- Agents Tab: Dashboard, management, and creation UI
- CLI agent commands: list, status, enable, disable, run, create

* Sun Feb 08 2026 Loofi <loofi@example.com> - 17.0.0-1
- v17.0 Atlas: Performance, Snapshots, Smart Logs, Storage, Network Overhaul
- Performance Tab: AutoTuner GUI with workload detection and kernel tuning
- Snapshots Tab: Unified snapshot management for Timeshift/Snapper/BTRFS
- Smart Logs Tab: Journal viewer with pattern detection and filtering
- Storage Tab: Disk health, mount points, and usage analysis
- Network Tab: Complete overhaul with DNS, Privacy, and Monitoring sub-tabs
- Bluetooth Manager: Full bluetoothctl wrapper with device management
- 94 new tests across 4 new modules

* Sun Feb 08 2026 Loofi <loofi@example.com> - 15.0.0-1
- v15.0 Nebula: Auto-Tuner, Snapshot Timeline, Smart Logs, Quick Actions Bar
- Startup crash resilience: file logging, error dialogs, desktop notifications
- Fixed launcher script: PYTHONPATH, stderr logging, Qt dependency requirements
- Added RPM deps: qt6-qtbase-gui, mesa-libGL, mesa-libEGL
- Bug fixes: voice.py return, safety.py lazy import, drift.py exception handling
- Fixed sys.modules test pollution, updated stale version assertions

* Sun Feb 08 2026 Loofi <loofi@example.com> - 13.5.0-1
- UX Polish: Settings system, light theme, keyboard shortcuts, notification center
- Settings tab with Appearance, Behavior, and Advanced sub-tabs
- SettingsManager singleton with JSON persistence and atomic writes
- Catppuccin Latte light theme (light.qss) with full selector coverage
- Sidebar search/filter for tab navigation
- Keyboard shortcuts: Ctrl+1-9 tab switch, Ctrl+Tab/Shift+Tab cycling, F1 help
- Notification center with FIFO eviction, persistence, slide-out panel
- Centralised tooltip constants module for all UI elements
- i18n fixes: wrapped remaining hardcoded strings in hardware_tab
- 82 new tests (settings, notification center, tooltips, extended coverage)

* Sun Feb 08 2026 Loofi <loofi@example.com> - 13.1.0-1
- Stability update: exception cleanup, security hardening, test coverage
- Replaced ~50 bare/broad exceptions with specific types + logging across 20 files
- Error return standardization with Result dataclass in config_manager and history
- Removed all shell=True subprocess calls (4 instances)
- Rate limiter for clipboard sync and file drop servers
- Clipboard server now binds to 127.0.0.1 by default (configurable)
- 188 new tests across 11 test files (988+ tests total)

* Sun Feb 08 2026 Loofi <loofi@example.com> - 13.0.0-1
- Nexus Update: System profiles, health timeline, plugin SDK v2
- System Profiles: 5 built-in profiles (Gaming, Development, Battery Saver, Presentation, Server)
- Custom profile creation with CPU governor, compositor, and notification settings
- Health Timeline: SQLite-based metrics tracking for CPU temp, RAM, disk, load
- Health Timeline export to JSON/CSV with anomaly detection
- Mesh networking enhancements with peer discovery and clipboard sync
- Plugin SDK v2 with permissions model, update checking, and dependency validation
- Shell completions for bash, zsh, and fish
- New CLI commands: profile, health-history, preset, focus-mode, security-audit
- 20-tab sidebar layout with Profiles and Health tabs
- 839+ tests passing

* Sun Feb 08 2026 Loofi <loofi@example.com> - 12.0.0-1
- Sovereign Update: Virtualization, mesh networking, and state teleportation
- VM Quick-Create wizard with 5 preset flavors (Windows 11, Fedora, Ubuntu, Kali, Arch)
- VFIO GPU Passthrough Assistant with IOMMU analysis and kernel cmdline generation
- Disposable VMs using QCOW2 overlay snapshots
- Loofi Link mesh device discovery via Avahi mDNS
- Encrypted clipboard sync and File Drop with checksum verification
- State Teleport workspace capture and cross-device restore
- AI Lite Model Library with RAM-based recommendations
- Voice Mode with whisper.cpp transcription
- Context RAG with TF-IDF local file indexing
- Virtualization and AI Lab refactored as first-party plugins
- 18-tab sidebar layout, 564 tests passing
- New CLI commands: vm, vfio, mesh, teleport, ai-models

* Sun Feb 08 2026 Loofi <loofi@example.com> - 11.0.0-1
- Aurora Update: Extensibility and diagnostics upgrades
- Plugin manifest support with enable/disable state and CLI management
- Plugin Manager UI under Community tab
- Support bundle ZIP export (Diagnostics + CLI)
- Automation rule validation and dry-run simulation
- Unified stylesheet loading and improved logging visibility

* Sat Feb 07 2026 Loofi <loofi@example.com> - 10.0.0-1
- Zenith Update: Major consolidation and modernization release
- Tab consolidation: 25 tabs reduced to 15 with sub-navigation
- New BaseTab class eliminates code duplication across UI layer
- First-run wizard with hardware auto-detection
- Command palette (Ctrl+K) for global feature search
- Hardware profiles: HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS
- Centralized command builder (PrivilegedCommand) for safe pkexec operations
- Error handling framework with recovery hints
- CI/CD pipeline with GitHub Actions
- New consolidated tabs: Maintenance, Software, Monitor, Desktop, Development, Community, Automation, Diagnostics
- Privacy features merged into Security Center
- HP Tweaks merged into Hardware tab (now hardware-agnostic)
- CLI version synced, new doctor and suggest commands
- 40+ new unit tests, shared test fixtures

* Sat Feb 07 2026 Loofi <loofi@example.com> - 9.2.0-1
- Pulse Update: Real-time performance monitoring and process management
- Performance tab: Live CPU, RAM, Network, Disk I/O graphs
- Process monitor tab: Top processes with kill/renice support
- Temperature monitoring via hwmon sensors
- Network traffic monitor with per-interface bandwidth
- Dashboard auto-refresh with CPU load indicator
- CLI commands: processes, temperature, netmon

* Sat Feb 07 2026 Loofi <loofi@example.com> - 9.0.0-1
- Director Update: Window management for KDE, Hyprland, Sway
- Director tab: Tiling presets, workspace templates, dotfile sync
- KWin script installer for advanced KDE tiling

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.5.0-1
- Sentinel Update: Proactive security hardening
- Security Center tab: Port auditor with security scoring
- USB Guard integration for BadUSB protection
- Firejail sandbox manager for application isolation

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.1.0-1
- Neural Update: AI-ready foundation
- AI Lab tab: Hardware detection, Ollama management
- Model downloads for Llama, Mistral, CodeLlama

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.0.0-1
- Replicator Update: Developer tools, diagnostics, and IaC exports

* Sat Feb 07 2026 Loofi <loofi@example.com> - 7.0.0-1
- Community Update: Marketplace and Drift Detection
- Preset Marketplace for community presets
- Configuration drift detection
- New marketplace tab UI

* Sat Feb 07 2026 Loofi <loofi@example.com> - 6.5.0-1
- Architect Update: CLI and Plugin System
- Full CLI mode with subcommands
- Plugin system for extensions
- Operations layer refactoring

* Sat Feb 07 2026 Loofi <loofi@example.com> - 6.2.0-1
- Engine Room Update: Boot management features
- Kernel parameter editor with grubby wrapper
- ZRAM tuner for memory compression
- Secure Boot MOK helper
