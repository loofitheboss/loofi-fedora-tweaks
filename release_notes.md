# Loofi Fedora Tweaks v16.0.0 - The "Horizon" Update

A system visibility release that gives you full control over systemd services, unified package management across all sources, and firewall configuration — plus a redesigned Dashboard with live sparkline graphs.

## Highlights

* **Service Explorer**: Full systemd service browser with lifecycle control.
* **Package Explorer**: Unified DNF/rpm-ostree/Flatpak search, install, and remove.
* **Firewall Manager**: Complete firewalld backend with zones, ports, services, and rich rules.
* **Dashboard v2**: Live CPU/RAM sparkline graphs, network speed, storage breakdown, top processes.

## New Features

### Service Explorer
* Browse all system and user systemd services with state, enabled status, and description
* Start, stop, restart, enable, disable, mask, and unmask services
* View detailed service info: memory usage, PID, timestamps, unit file path
* Read journal logs per service with configurable line count
* System scope uses pkexec; user scope runs unprivileged

### Package Explorer
* Unified search across DNF and Flatpak remotes with installed indicators
* Install and remove packages with automatic source detection (DNF/rpm-ostree/Flatpak)
* List all installed packages (RPM + Flatpak) with search filter
* Browse recently installed packages via DNF history
* Full atomic Fedora support (auto-selects rpm-ostree)

### Firewall Manager
* Comprehensive firewall status: running state, zones, ports, services, rich rules
* Open/close ports with permanent or runtime modes
* Manage service allowlists (add/remove services)
* Rich rule management for advanced configurations
* Zone management: list, set default, view active zones
* Start/stop firewalld via pkexec

### Dashboard v2
* SparkLine widget: custom QPainter area chart with 30 data points and gradient fill
* Live CPU and RAM sparklines refreshed every 2 seconds
* Network speed indicator (↓/↑ bytes/sec from /proc/net/dev)
* Per-mount-point storage breakdown with color-coded progress bars
* Top 5 processes by CPU usage
* Recent actions feed from HistoryManager
* Quick Actions grid with correct tab navigation

## New CLI Commands

```bash
# Service management
loofi service list                   # List all services
loofi service list --filter active   # Filter by state
loofi service list --search ssh      # Search by name
loofi service start sshd             # Start a service
loofi service stop bluetooth         # Stop a service
loofi service restart nginx          # Restart a service
loofi service enable sshd            # Enable on boot
loofi service disable bluetooth      # Disable on boot
loofi service logs nginx             # View journal logs
loofi service status sshd            # Detailed info

# Package management
loofi package search --query vim     # Search all sources
loofi package install vim            # Install (auto-detect)
loofi package remove vim             # Remove a package
loofi package list                   # List installed packages
loofi package list --source flatpak  # Filter by source
loofi package recent                 # Recently installed

# Firewall management
loofi firewall status                # Full firewall status
loofi firewall ports                 # List open ports
loofi firewall open-port 8080/tcp    # Open a port
loofi firewall close-port 8080/tcp   # Close a port
loofi firewall services              # List allowed services
loofi firewall zones                 # List available zones
```

## Installation

**Via DNF:**

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v16.0.0/loofi-fedora-tweaks-16.0.0-1.noarch.rpm
```

**Build from source:**

```bash
./build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-16.0.0-1.noarch.rpm
```

## Quick Start

```bash
# GUI
loofi-fedora-tweaks

# CLI
loofi info
loofi service list
loofi package search --query vim
loofi firewall status
```
