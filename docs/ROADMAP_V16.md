# Loofi Fedora Tweaks v16.0.0 "Horizon" — Roadmap

## Vision

v16.0 "Horizon" is a **system control and visibility** release that gives users deep, hands-on management of their Fedora system's core infrastructure. It introduces a full systemd Service Manager, a Package Explorer for search/install/remove across all package managers, a Firewall Manager for firewalld, and a completely overhauled Dashboard with live graphs, storage breakdown, and recent action history.

## Release Features

### 1. Service Manager (`utils/service_explorer.py` + sub-tab in Diagnostics)

A full systemd service browser that goes far beyond the existing gaming-focused ServiceManager.

**Capabilities:**
- Browse all system & user services with search/filter
- Start, stop, restart, enable, disable, mask/unmask services
- View live unit status and recent journal logs per service
- Color-coded state indicators (active=green, failed=red, inactive=gray)
- Enable/disable toggle with boot persistence
- CLI: `loofi service list`, `loofi service start/stop/restart/enable/disable <name>`, `loofi service logs <name>`

**Architecture:**
- `utils/service_explorer.py` — `ServiceExplorer` with `@staticmethod` methods
- `ServiceInfo` dataclass with name, description, state, enabled, sub_state, memory usage
- Returns operation tuples for privileged commands
- Extends (not replaces) existing `utils/services.py`

### 2. Package Explorer (`utils/package_explorer.py` + sub-tab in Software)

A unified package search/install/remove interface across DNF, rpm-ostree, and Flatpak.

**Capabilities:**
- Search packages across DNF and Flatpak simultaneously
- Show package details: version, size, repo, description, installed status
- Install/remove packages with privilege escalation
- List installed packages with filter
- Show recently installed packages (last 30 days)
- CLI: `loofi package search <query>`, `loofi package install <name>`, `loofi package remove <name>`, `loofi package list`, `loofi package recent`

**Architecture:**
- `utils/package_explorer.py` — `PackageExplorer` class
- `PackageInfo` dataclass with name, version, repo, size, description, installed, source (dnf/flatpak)
- Auto-detects Atomic vs Traditional for install/remove operations
- Returns operation tuples for privileged commands

### 3. Firewall Manager (`utils/firewall_manager.py` + sub-tab in Security)

A firewalld GUI for managing zones, ports, and services without touching the terminal.

**Capabilities:**
- Show current zone, list all zones
- List open ports and active services per zone
- Add/remove port rules (tcp/udp)
- Add/remove service rules (http, ssh, etc.)
- Toggle firewall on/off
- Show rich rules
- CLI: `loofi firewall status`, `loofi firewall ports`, `loofi firewall open-port <port>/<proto>`, `loofi firewall close-port <port>/<proto>`, `loofi firewall services`

**Architecture:**
- `utils/firewall_manager.py` — `FirewallManager` class
- `FirewallInfo` dataclass with zone, ports, services, state
- Uses `firewall-cmd` with pkexec for privileged operations

### 4. Dashboard v2 (`ui/dashboard_tab.py` overhaul)

A complete dashboard rebuild with real-time graphs, storage breakdown, network speed, and recent action history.

**Capabilities:**
- Mini CPU & RAM live graphs (sparkline-style, last 30 seconds)
- Storage breakdown bar showing used/free per mount point
- Network speed indicator (upload/download bytes/sec)
- Top 5 processes by CPU usage
- Recent actions feed from HistoryManager (last 10)
- Quick Actions remain (Clean Cache, Update All, Power Profile, Gaming Mode) — now working

**Architecture:**
- Rewrite `ui/dashboard_tab.py` with QTimer-based live metrics
- Reuse `SystemMonitor` and `PerformanceCollector` from existing utils
- Mini sparkline widget from monitor_tab.py's `MiniGraph`

## Timeline

1. Create roadmap ✅
2. Implement `utils/service_explorer.py`
3. Implement `utils/package_explorer.py`
4. Implement `utils/firewall_manager.py`
5. Overhaul `ui/dashboard_tab.py`
6. Add CLI commands for service, package, firewall
7. Write comprehensive tests
8. Version bump, changelog, build, release
