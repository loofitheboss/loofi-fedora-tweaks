# Release Notes

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
