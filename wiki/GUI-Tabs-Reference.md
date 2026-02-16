# GUI Tabs Reference

Complete reference for all 29 feature tabs in Loofi Fedora Tweaks, organized by the 8 activity-based categories.

---

## 🏠 Overview

### 1. Home (`dashboard_tab.py`)
**Dashboard with system metrics and quick actions**

- System overview cards: CPU usage, RAM usage, disk space, uptime
- Quick action buttons for common tasks (update, cleanup, backup, etc.)
- Health score indicator with grade (A-F)
- Recent activity timeline
- Personalized greeting with username

### 2. System Info (`system_info_tab.py`)
**Detailed system information**

- Hardware details: CPU model, RAM capacity, GPU info
- Software info: Kernel version, Python version, Qt version
- OS detection: Fedora version, package manager (dnf/rpm-ostree), desktop environment
- Network info: Hostname, IP addresses
- Storage info: Total/used/free disk space

### 3. System Monitor (`monitor_tab.py`)
**Real-time system performance monitoring**

- Live CPU usage graph with per-core breakdown
- Memory usage graph (RAM + swap)
- Disk I/O monitoring
- Network traffic monitoring
- Process table with CPU/memory usage, sorted by resource consumption
- Kill process functionality

---

## 📦 Manage

### 4. Software (`software_tab.py`)
**Application and package management**

- **Apps Tab**: Browse and install GUI applications from curated catalog
- **Repos Tab**: Manage DNF/RPM repositories (add, remove, enable, disable)
- **Flatpak Manager**: Audit Flatpak sizes, inspect permissions, detect orphan runtimes, bulk cleanup

### 5. Maintenance (`maintenance_tab.py`)
**System updates, cleanup, and maintenance**

- **Updates**: Check for updates, preview changes, apply updates
- **Smart Updates**: Schedule automatic updates, rollback last update, view update history
- **Cleanup**: Clear package cache, journal logs, temp files, thumbnail cache
- **Overlays** (Atomic only): Manage rpm-ostree overlay packages

### 6. Snapshots (`snapshot_tab.py`)
**System backup and restore**

- Timeline view of snapshots (Timeshift or Snapper)
- Create new snapshots with description
- Restore from snapshot (requires reboot)
- Delete old snapshots
- Automatic snapshot creation before risky operations

### 7. Virtualization (`virtualization_tab.py`)
**Virtual machine management**

- **VMs**: List, create, start, stop, delete VMs via libvirt
- **VFIO**: GPU passthrough configuration for gaming VMs
- **Disposable**: Create and manage ephemeral VMs

### 8. Extensions (`extensions_tab.py`)
**Desktop environment extensions**

- Browse GNOME Shell or KDE Plasma extensions
- Search and filter by name or description
- Install, enable, disable, and remove extensions
- View extension details and ratings
- Auto-detects desktop environment

### 9. Backup (`backup_tab.py`)
**Backup wizard and restore**

- 3-step wizard: Detect backup tools → Configure backup → Manage backups
- Supports Timeshift, Snapper, and restic
- Create scheduled backups
- List and restore from backups
- Delete old backups

---

## 🔧 Hardware

### 10. Hardware (`hardware_tab.py`)
**Hardware information and device management**

- **Hardware Info**: Detailed CPU, GPU, RAM, storage info
- **HP Tweaks**: HP laptop-specific optimizations (EliteBook, ProBook)
- **Bluetooth**: Manage Bluetooth devices (pair, connect, disconnect, remove)
- **Boot Configuration**: View installed kernels, edit GRUB settings, set timeout

### 11. Performance (`performance_tab.py`)
**Auto-tuner for system optimization**

- Analyze system performance bottlenecks
- Apply automatic tuning profiles (balanced, performance, power-saver)
- Enable/disable performance features: GameMode, zram, TCP BBR congestion control
- Adjust swappiness value

### 12. Storage (`storage_tab.py`)
**Disk and filesystem management**

- **Disks**: List all block devices with size, usage, filesystem type
- **Mount Points**: View all mounted filesystems
- **SMART**: Check disk health and SMART attributes

### 13. Gaming (`gaming_tab.py`)
**Gaming optimizations and tools**

- Install gaming dependencies (Steam, GameMode, MangoHud, Lutris)
- Enable Proton compatibility layer
- Configure gamemode daemon
- View and optimize GPU settings

---

## 🌐 Network & Security

### 14. Network (`network_tab.py`)
**Network configuration and monitoring**

- **Connections**: List network interfaces (Ethernet, Wi-Fi, VPN)
- **DNS**: Configure DNS providers (Cloudflare, Google, Quad9, custom)
- **Wi-Fi**: Scan for available networks, connect, disconnect
- **VPN**: Configure OpenVPN and WireGuard connections
- **Monitoring**: Live network traffic statistics

### 15. Loofi Link (`mesh_tab.py`)
**Mesh networking and cross-device features**

- **Mesh**: Discover other Loofi instances on local network via mDNS
- **Clipboard Sync**: Share clipboard content across devices
- **File Drop**: Send files to other Loofi instances
- Requires Avahi daemon

### 16. Security & Privacy (`security_tab.py`)
**Security hardening and privacy tools**

- **Security Audit**: Scan for security issues (open ports, weak passwords, outdated packages)
- **Firewall**: Manage firewalld zones, services, and ports
- **SELinux**: View status, set enforcing/permissive mode
- **Privacy**: Clear browser history, disable telemetry
- **Audit Log**: View privileged action audit trail

---

## 🎨 Personalize

### 17. Desktop (`desktop_tab.py`)
**Desktop environment customization**

- **Director**: Quick DE tweaks (dark mode, icons, fonts)
- **Theming**: Apply GTK/Qt themes
- **Display**: Configure displays, enable fractional scaling (GNOME Wayland)
- Detects and supports GNOME, KDE Plasma, Xfce, MATE, Cinnamon

### 18. Profiles (`profiles_tab.py`)
**User profile management**

- Create and switch between user profiles (work, gaming, minimal)
- Each profile saves settings, favorites, quick actions
- Import/export profiles

### 19. Settings (`settings_tab.py`)
**Application preferences**

- Theme selection (Abyss Dark, Abyss Light)
- Language and locale
- Auto-update settings
- Notification preferences
- Developer options (debug logging, experimental features)

---

## 💻 Developer

### 20. Development (`development_tab.py`)
**Developer tools and containers**

- **Containers**: Manage Podman containers (list, start, stop, remove)
- **Dev Tools**: Install common development packages (git, gcc, python3-devel, etc.)
- Launch terminal with development environment

### 21. AI Lab (`ai_enhanced_tab.py`)
**Local AI and LLM features**

- Install and manage Ollama
- Download and run LLM models (llama3, mistral, codellama, etc.)
- Chat interface for local LLM queries
- Model management (list, pull, remove)

### 22. State Teleport (`teleport_tab.py`)
**Workspace capture and restore**

- Capture current desktop state (open windows, workspaces, terminal sessions)
- Save workspace snapshots
- Restore workspace state
- Export/import workspace profiles

---

## 🤖 Automation

### 23. Agents (`agents_tab.py`)
**AI agent management**

- Configure AI agents for automation tasks
- Agent status monitoring
- Trigger agent workflows manually
- View agent execution logs

### 24. Automation (`automation_tab.py`)
**Task scheduling and automation**

- **Scheduler**: Create scheduled tasks (cron-like)
- **Replicator**: Replicate configurations across systems
- **Pulse**: System health monitoring with alerts

---

## 📊 Health & Logs

### 25. Health Timeline (`health_timeline_tab.py`)
**System health history visualization**

- Graph of health scores over time (7 days, 30 days, 90 days)
- Health events timeline (updates, crashes, errors)
- Health score breakdown by category (disk, CPU, RAM, services)
- Export health report

### 26. Logs (`logs_tab.py`)
**Smart log viewer**

- Filter logs by level (debug, info, warning, error, critical)
- Filter by time range (last hour, last day, custom)
- Filter by service/unit
- Real-time log streaming
- Export logs to file

### 27. Diagnostics (`diagnostics_tab.py`)
**System diagnostics and troubleshooting**

- **Watchtower**: Run diagnostic scans for common issues
- **Boot Analyzer**: Analyze boot performance and slow services
- **Support Bundle**: Generate comprehensive diagnostic bundle for bug reports
- Includes system info, logs, package list, hardware details

### 28. Community (`community_tab.py`)
**Presets and plugin marketplace**

- **Presets**: Community-contributed configuration presets (gaming, development, minimal)
- **Marketplace**: Browse, search, and install third-party plugins
- **Featured Plugins**: Curated plugin list with ratings
- **Reviews**: Read and submit plugin reviews

---

## Tab Actions

Most tabs support these common actions:

- **Refresh**: Reload data from system
- **Export**: Export table data to CSV/JSON
- **Help**: Context-sensitive help for the current tab

Tabs with privileged operations (updates, installs, firewall changes) will prompt for authentication via `pkexec`.

---

## Navigation Tips

- **Search**: Type in the sidebar search box to filter tabs
- **Favorites**: Right-click any tab to add to favorites
- **Command Palette**: Press `Ctrl+K` and type tab name for instant navigation
- **Breadcrumb**: Click category name in breadcrumb bar to collapse sidebar
- **Quick Actions**: Use dashboard quick actions to jump to common tasks

---

## Next Steps

- [CLI Reference](CLI-Reference) — Command-line equivalents for all tab features
- [Configuration](Configuration) — Customize quick actions, favorites, and themes
- [Troubleshooting](Troubleshooting) — Tab-specific troubleshooting tips
