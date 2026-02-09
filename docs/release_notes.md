# Release Notes

## v20.0.2-2 "Synapse" - February 2026 (RPM Hotfix)

This packaging hotfix resolves a top title/header rendering glitch reported on Fedora KDE Plasma (Wayland/X11) after recent UI polish work.

### Highlights

- **Native Title-Bar Guard**: Main window now explicitly disables frameless/custom title flags to keep native chrome behavior
- **Top-Edge Stability**: Prevents client area visuals from appearing to overlap into top window chrome
- **Regression Test**: Added `tests/test_main_window_geometry.py` for client-area geometry sanity

### Updates Included

- `ui/main_window.py`: enforce native window flags (`FramelessWindowHint=False`, `CustomizeWindowHint=False`)
- `tests/test_main_window_geometry.py`: basic central/root widget geometry assertions
- `loofi-fedora-tweaks.spec`: release bump to `20.0.2-2` with changelog entry

### Upgrade Notes

- No breaking changes from v20.0.2
- Native dragging, resizing, and title-bar controls are preserved

## v20.0.2 "Synapse" - February 2026

The Synapse 20.0.2 update focuses on UI usability for sub-tabs and dependency updates.

### Highlights

- **Tab Scroller Fixes**: Scroll buttons, elided labels, and non-expanding top sub-tabs
- **Themed Scroller Styling**: Scroll buttons styled across dark/light/classic themes
- **Dependency Refresh**: Updated Python dependency pins to latest stable releases
- **UI Smoke Tests**: 15 tests passed, 22 skipped in headless run

### Updates Included

- `ui/tab_utils.py`: Centralized tab configuration helper
- UI tabs: Applied tab scroller configuration across consolidated tabs
- `assets/*.qss`: Styled `QTabBar::scroll-left-button` / `scroll-right-button`
- `requirements.txt`: Pinned latest dependency versions

### Upgrade Notes

- No breaking changes from v20.0.1
- Recommended to validate UI tab scrolling on a machine with OpenGL drivers

---

## v18.0.0 "Sentinel" - February 2026

Autonomous Agent Framework with AI-powered planning, 5 built-in agents, and background execution.

---

## v17.0.0 "Atlas" - February 2026

The Atlas update is a hardware & visibility release that brings four new dedicated GUI tabs, a Bluetooth manager, storage & disk health tools, and a completely overhauled Network tab.

### Highlights

- **Performance Tab**: AutoTuner GUI with workload detection and kernel tuning
- **Snapshots Tab**: Create/restore/delete across Timeshift/Snapper/BTRFS
- **Smart Logs Tab**: Color-coded journal viewer with 10 error patterns
- **Storage & Disks Tab**: Block devices, SMART health, mounts, fsck, TRIM
- **Network Overhaul**: 4 sub-tabs — Connections, DNS, Privacy, Monitoring
- **Bluetooth Manager**: Scan, pair, connect, trust, block via bluetoothctl
- **1514 Tests**: 94 new tests, 25 total tabs

### New Features

#### Performance Tab (AutoTuner GUI)

The Performance tab provides a dedicated GUI for the v15 AutoTuner utility:

| Feature | Description |
|---------|-------------|
| **Workload Detection** | Real-time CPU/memory classification (idle, desktop, compilation, gaming, server) |
| **Kernel Settings** | Display current governor, swappiness, I/O scheduler, THP |
| **Apply** | One-click apply with pkexec privilege escalation |
| **History** | Tuning history table with timestamps |
| **Auto-Refresh** | 30-second refresh timer |

#### Snapshots Tab

GUI for the v15 SnapshotManager:

| Feature | Description |
|---------|-------------|
| **Create** | Create snapshots via Timeshift, Snapper, or BTRFS |
| **Restore** | Restore from any snapshot in the timeline |
| **Delete** | Remove individual snapshots |
| **Backends** | Auto-detect available snapshot tools |
| **Retention** | Apply retention policies to clean old snapshots |

#### Smart Logs Tab

GUI for the v15 SmartLogViewer:

| Feature | Description |
|---------|-------------|
| **Pattern Analysis** | 10 built-in patterns (OOM, segfault, disk full, auth failure, etc.) |
| **Color-Coded** | Severity-based coloring (emergency=red through debug=gray) |
| **Filters** | Unit, priority, and time range filters |
| **Export** | Export to text or JSON |

#### Storage & Disks Tab

New disk management tab with `StorageManager` backend:

| Feature | Command | Description |
|---------|---------|-------------|
| **Block Devices** | `loofi storage disks` | List all block devices via lsblk |
| **SMART Health** | `loofi storage smart /dev/sda` | Health status and temperature via smartctl |
| **Mounts** | `loofi storage mounts` | Mount points with usage stats from df |
| **Filesystem Check** | — | Run fsck via pkexec |
| **SSD TRIM** | `loofi storage trim` | Run fstrim for SSD optimization |
| **Usage Summary** | `loofi storage usage` | Aggregate disk usage overview |

#### Bluetooth Manager

Added to the Hardware tab with `BluetoothManager` backend:

| Feature | Command | Description |
|---------|---------|-------------|
| **Status** | `loofi bluetooth status` | Adapter info (powered, discoverable, address) |
| **Devices** | `loofi bluetooth devices` | List paired devices with battery/type |
| **Scan** | `loofi bluetooth scan` | Discover nearby devices |
| **Pair** | `loofi bluetooth pair <addr>` | Pair a device |
| **Connect** | `loofi bluetooth connect <addr>` | Connect to a paired device |
| **Trust** | `loofi bluetooth trust <addr>` | Trust a device |
| **Power** | `loofi bluetooth power-on/off` | Toggle adapter power |

#### Network Tab Overhaul

Rewritten with 4 sub-tabs:

| Sub-Tab | Description |
|---------|-------------|
| **Connections** | WiFi network scanning, VPN status via nmcli |
| **DNS** | One-click DNS switching (Cloudflare, Google, Quad9, AdGuard, DHCP) |
| **Privacy** | Per-connection MAC address randomization |
| **Monitoring** | Interface stats + active connections with auto-refresh |

### Changed

- Gaming tab normalized to inherit `BaseTab` with `PrivilegedCommand.dnf()`.
- Hardware tab: Bluetooth card added at grid position (3,1).
- Main Window: 25-tab layout, v17.0 "Atlas" header.

### New Files

- `utils/bluetooth.py` — Bluetooth device management via bluetoothctl
- `utils/storage.py` — Disk info, SMART health, mounts via lsblk/smartctl/df
- `ui/performance_tab.py` — Performance Auto-Tuner GUI
- `ui/snapshot_tab.py` — Snapshot Timeline GUI
- `ui/logs_tab.py` — Smart Log Viewer GUI
- `ui/storage_tab.py` — Storage & Disks GUI
- `tests/test_bluetooth.py` — Bluetooth manager tests
- `tests/test_storage.py` — Storage manager tests
- `tests/test_v17_atlas.py` — GUI tab instantiation tests
- `tests/test_v17_cli.py` — CLI bluetooth/storage command tests

### Upgrade Notes

- No breaking changes from v16.0.0
- 4 new tabs appear in the sidebar (Performance, Snapshots, Smart Logs, Storage)
- Network tab completely rewritten with 4 sub-tabs
- Bluetooth card added to Hardware tab
- 2 new CLI subcommands: `bluetooth`, `storage`
- All existing commands and configurations are preserved

---

## v16.0.0 "Horizon" - February 2026

The Horizon update is a system visibility release that gives you full control over systemd services, unified package management, and firewall configuration — plus a redesigned Dashboard with live sparkline graphs.

### Highlights

- **Service Explorer**: Full systemd service browser and controller
- **Package Explorer**: Unified DNF/rpm-ostree/Flatpak package management
- **Firewall Manager**: Complete firewalld backend with zones, ports, services, and rich rules
- **Dashboard v2**: Live sparkline graphs, network speed, storage breakdown, top processes
- **1420+ Tests**: Comprehensive test coverage

### New Features

#### Service Explorer

Full systemd service browser supporting both system and user scopes:

| Operation | Command | Description |
|-----------|---------|-------------|
| **List** | `loofi service list` | Browse all services with state and enabled status |
| **Filter** | `--filter active\|inactive\|failed` | Narrow by state |
| **Search** | `--search ssh` | Substring match on name or description |
| **Start/Stop** | `loofi service start\|stop <name>` | Control service lifecycle |
| **Enable/Disable** | `loofi service enable\|disable <name>` | Boot persistence |
| **Mask/Unmask** | `loofi service mask\|unmask <name>` | Prevent or allow starting |
| **Logs** | `loofi service logs <name>` | Journal entries for a service |
| **Status** | `loofi service status <name>` | Memory, PID, timestamps, unit path |

System scope uses `pkexec` via `PrivilegedCommand`; user scope runs unprivileged with `--user`.

#### Package Explorer

Unified search, install, and remove across all package sources:

| Source | Detection | Install | Remove |
|--------|-----------|---------|--------|
| **DNF** | Default on traditional Fedora | `pkexec dnf install -y` | `pkexec dnf remove -y` |
| **rpm-ostree** | Auto on Atomic variants | `pkexec rpm-ostree install` | `pkexec rpm-ostree uninstall` |
| **Flatpak** | App IDs with 2+ dots | `flatpak install -y` | `flatpak uninstall -y` |

- `search()` combines DNF and Flatpak search results with installed indicators
- `list_installed()` merges RPM and Flatpak inventories
- `recently_installed()` shows packages from the last N days via DNF history

#### Firewall Manager

Complete firewalld management backend:

| Feature | Read | Write |
|---------|------|-------|
| **Zones** | `get_zones()`, `get_active_zones()` | `set_default_zone()` |
| **Ports** | `list_ports()` | `open_port()`, `close_port()` |
| **Services** | `list_services()`, `get_available_services()` | `add_service()`, `remove_service()` |
| **Rich Rules** | `list_rich_rules()` | `add_rich_rule()`, `remove_rich_rule()` |
| **Firewall** | `is_running()`, `get_status()` | `start_firewall()`, `stop_firewall()` |

All write operations use `pkexec firewall-cmd` with `--permanent` and automatic `--reload`.

#### Dashboard v2

Complete dashboard overhaul with live data visualization:

- **SparkLine Widget**: Custom QPainter area chart with 30 data points and gradient fill
- **CPU & RAM Sparklines**: 2-second refresh cycle with smooth area charts
- **Network Speed**: Real-time ↓/↑ bytes/sec from `/proc/net/dev`
- **Storage Breakdown**: Per-mount-point color-coded progress bars
- **Top Processes**: Top 5 by CPU usage via `ps`
- **Recent Actions**: Last 5 entries from HistoryManager
- **Quick Actions**: 4 buttons navigating to correct consolidated tabs

### New Files

- `utils/service_explorer.py` — Systemd service browser and controller
- `utils/package_explorer.py` — Unified package manager
- `utils/firewall_manager.py` — Firewalld backend
- `ui/dashboard_tab.py` — Rewritten Dashboard v2 with SparkLine widget
- `tests/test_service_explorer.py` — 55 service explorer tests
- `tests/test_package_explorer.py` — 44 package explorer tests
- `tests/test_firewall_manager.py` — 49 firewall manager tests
- `docs/ROADMAP_V16.md` — v16.0 development roadmap

### Upgrade Notes

- No breaking changes from v15.0.0
- Dashboard is completely rewritten with live graphs
- 3 new CLI subcommands: `service`, `package`, `firewall`
- All existing commands and configurations are preserved

---

## v15.0.0 "Nebula" - February 2026

The Nebula update is a system intelligence release that makes Loofi smarter about the system it manages. It introduces a performance auto-tuner, a unified snapshot timeline, an intelligent log viewer, and a quick-action command bar.

### Highlights

- **Performance Auto-Tuner**: Workload detection and system optimization recommendations
- **System Snapshot Timeline**: Unified Timeshift/Snapper/BTRFS snapshot management
- **Smart Log Viewer**: Journal analysis with 10 built-in error pattern detectors
- **Quick Actions Bar**: `Ctrl+Shift+K` floating command palette for power users
- **1290+ Tests**: Comprehensive test coverage

### New Features

#### Performance Auto-Tuner

Intelligent system optimizer that analyzes workload and recommends settings:

| Workload | Governor | Swappiness | I/O Scheduler | THP |
|----------|----------|-----------|---------------|-----|
| **Idle** | powersave | 60 | mq-deadline | always |
| **Compilation** | performance | 10 | none | madvise |
| **Gaming** | performance | 10 | none | never |
| **Server** | schedutil | 30 | mq-deadline | madvise |

- CLI: `loofi tuner analyze`, `loofi tuner apply`, `loofi tuner history`

#### System Snapshot Timeline

Unified snapshot management across multiple backends:

| Backend | Detection | Operations |
|---------|-----------|-----------|
| **Snapper** | `shutil.which("snapper")` | list, create, delete |
| **Timeshift** | `shutil.which("timeshift")` | list, create, delete |
| **BTRFS** | `shutil.which("btrfs")` | list subvolumes |

- CLI: `loofi snapshot list`, `loofi snapshot create`, `loofi snapshot backends`

#### Smart Log Viewer

10 built-in patterns with plain-English explanations:

- OOM Killer, Segfault, Disk Full, Auth Failure, Service Failed
- USB Disconnect, Kernel Panic, NetworkManager Down, Thermal Throttle, Firmware Error
- CLI: `loofi logs show`, `loofi logs errors`, `loofi logs export`

#### Quick Actions Bar

- Triggered by `Ctrl+Shift+K`
- 15+ default actions across 5 categories
- Fuzzy search with recent actions tracking
- Plugin-extensible via `QuickActionRegistry`

### New Files

- `utils/auto_tuner.py` — Performance auto-tuner
- `utils/snapshot_manager.py` — Unified snapshot management
- `utils/smart_logs.py` — Smart log viewer
- `ui/quick_actions.py` — Quick Actions Bar
- `.github/agents/Planner.agent.md` — Release planning agent
- `.github/agents/Builder.agent.md` — Backend implementation agent
- `.github/agents/Sculptor.agent.md` — Frontend/integration agent
- `.github/agents/Guardian.agent.md` — Quality assurance agent

## v14.0.0 "Quantum Leap" - February 2026

The Quantum Leap update is a reliability and polish release introducing automatic update checking, a What's New dialog for post-upgrade highlights, full configuration backup/restore/factory-reset management, and plugin lifecycle events.

### Highlights

- **Update Checker**: Automatic update notifications from GitHub releases API
- **What's New Dialog**: Post-upgrade dialog showing release highlights
- **Factory Reset**: Full backup/restore/reset management for all config files
- **Plugin Lifecycle Events**: `on_app_start`, `on_app_quit`, `on_tab_switch` hooks
- **1130+ Tests**: Comprehensive test coverage

### New Features

#### Update Checker

Check for app updates via GitHub releases API:

- Fetches latest release tag and compares with installed version
- `UpdateInfo` dataclass with version comparison and download URL
- Configurable timeout for network requests

#### What's New Dialog

Post-upgrade highlights dialog:

- Shows automatically after version upgrades
- Remembers last-seen version via `SettingsManager`
- Scrollable view with current and previous release notes
- "Don't show again" checkbox

#### Factory Reset & Backup Management

Full configuration backup and restore:

| Operation | Description |
|-----------|-------------|
| **Create Backup** | Snapshot all JSON config files with manifest |
| **List Backups** | Enumerate available backups with metadata |
| **Restore Backup** | Restore config from a named backup |
| **Delete Backup** | Remove old backups |
| **Factory Reset** | Reset to defaults with automatic pre-reset backup |

#### Plugin Lifecycle Events

New hooks for plugin developers:

- `on_app_start` — called when the application starts
- `on_app_quit` — called before application exits
- `on_tab_switch` — called when user switches tabs
- `on_settings_changed` — notified when settings change
- `get_settings_schema` — plugins can declare configurable settings

### New Files

- `utils/update_checker.py` — GitHub releases API update checker
- `utils/factory_reset.py` — Backup/restore/reset management
- `ui/whats_new_dialog.py` — Post-upgrade What's New dialog
- `tests/test_factory_reset.py` — Factory reset unit tests
- `tests/test_update_checker.py` — Update checker unit tests
loofi profile apply gaming      # Apply a profile
loofi profile create myprofile  # Create from current state
loofi profile delete myprofile  # Delete a custom profile

# Health history
loofi health-history show       # Show 24h summary
loofi health-history record     # Record current metrics
loofi health-history export data.json  # Export to JSON
loofi health-history prune      # Delete old data
```

### Shell Completions

New auto-completion scripts for:
- Bash (`completions/loofi.bash`)
- Zsh (`completions/loofi.zsh`)
- Fish (`completions/loofi.fish`)

### Test Coverage

- **839+ tests passing** (up from 564)
- 53 new profile tests
- 46 new health timeline tests
- 37 new UI smoke tests

### Files Added

- `utils/profiles.py` - Profile manager
- `utils/health_timeline.py` - Health metrics tracking
- `ui/profiles_tab.py` - Profiles UI
- `ui/health_timeline_tab.py` - Health Timeline UI
- `completions/loofi.bash` - Bash completions
- `completions/loofi.zsh` - Zsh completions
- `completions/loofi.fish` - Fish completions
- `docs/PLUGIN_SDK.md` - Expanded SDK guide
- `docs/TROUBLESHOOTING.md` - Troubleshooting guide

### Upgrade Notes

- No breaking changes from v12.0.0
- New tabs will appear automatically in the sidebar
- Existing presets and configurations are preserved
- CLI commands are additive (no removed commands)

---

## v12.0.0 "Sovereign Update" - February 2026

Virtualization, mesh networking, and state teleportation.

### Highlights

- VM Quick-Create wizard with preset flavors
- VFIO GPU Passthrough Assistant
- Loofi Link mesh networking
- State Teleport workspace capture/restore
- 18 tabs, 564 tests

---

## v11.0.0 "Aurora Update" - February 2026

Plugin manifests and diagnostics upgrades.

### Highlights

- Plugin manifest support with enable/disable
- Support bundle ZIP export
- Automation validation and dry-run

---

## v10.0.0 "Zenith Update" - February 2026

Major consolidation and modernization.

### Highlights

- Tab consolidation: 25 tabs to 15
- First-run wizard
- Command palette (Ctrl+K)
- Hardware profile auto-detection
- CI/CD pipeline

---

*For full version history, see [CHANGELOG.md](../CHANGELOG.md)*
