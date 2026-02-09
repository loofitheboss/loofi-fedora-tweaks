# Loofi Fedora Tweaks v17.0.0 - The "Atlas" Update

A hardware & visibility release that brings four new dedicated tabs for v15 features, a Bluetooth manager, storage & disk health tools, and a completely overhauled Network tab — 25 tabs, 1514 tests.

## Highlights

* **Performance Tab**: AutoTuner GUI with workload detection & kernel tuning
* **Snapshots Tab**: Create/restore/delete across Timeshift/Snapper/BTRFS
* **Smart Logs Tab**: Color-coded journal viewer with 10 error patterns
* **Storage & Disks Tab**: Block devices, SMART health, mounts, fsck, TRIM
* **Network Overhaul**: 4 sub-tabs — Connections, DNS, Privacy, Monitoring
* **Bluetooth Manager**: Scan, pair, connect, trust, block via bluetoothctl

## New Features

### Performance Tab (AutoTuner GUI)
* Real-time workload detection (idle, desktop, compilation, gaming, server)
* Kernel settings display: governor, swappiness, I/O scheduler, THP
* One-click "Apply Recommendations" with pkexec privilege escalation
* Tuning history table with timestamps
* 30-second auto-refresh timer

### Snapshots Tab
* Create, restore, and delete snapshots across multiple backends
* Auto-detects Timeshift, Snapper, and BTRFS subvolumes
* Retention policy management
* Snapshot timeline table with type, description, and timestamp

### Smart Logs Tab
* Color-coded log entries by severity (emergency=red through debug=gray)
* 10 built-in error patterns: OOM, segfault, disk full, auth failure, etc.
* Pattern analysis table showing matched count and suggested fixes
* Filters: unit, priority, time range
* Export to text or JSON

### Storage & Disks Tab
* Block device inventory via lsblk (name, size, type, mountpoint, removable)
* SMART health monitoring via smartctl (health status, temperature)
* Mount point listing with usage stats (total, used, available, use%)
* Filesystem check (fsck) via pkexec
* SSD TRIM optimization via fstrim
* Disk usage summary

### Network Tab Overhaul
* **Connections**: WiFi network scanning, VPN status via nmcli
* **DNS**: One-click switching (Cloudflare, Google, Quad9, AdGuard, DHCP default)
* **Privacy**: Per-connection MAC address randomization
* **Monitoring**: Interface stats + active connections with auto-refresh

### Bluetooth Manager (Hardware Tab)
* Adapter status (powered, discoverable, pairable, adapter address)
* Device scanning with configurable timeout
* Pair, unpair, connect, disconnect, trust, block, unblock
* Battery level and device type classification
* Device types: audio, computer, input, phone, network, imaging

## New CLI Commands

```bash
# Bluetooth management (v17.0)
loofi bluetooth status         # Adapter info
loofi bluetooth devices        # List paired devices
loofi bluetooth scan           # Scan for nearby devices
loofi bluetooth pair <address> # Pair a device
loofi bluetooth connect <addr> # Connect to a device
loofi bluetooth disconnect <a> # Disconnect a device
loofi bluetooth trust <addr>   # Trust a device
loofi bluetooth power-on       # Turn adapter on
loofi bluetooth power-off      # Turn adapter off

# Storage & disks (v17.0)
loofi storage disks            # List block devices
loofi storage mounts           # List mount points with usage
loofi storage smart /dev/sda   # SMART health for a device
loofi storage trim             # Run SSD TRIM
loofi storage usage            # Disk usage summary
```

## Installation

**Via DNF:**

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v17.0.0/loofi-fedora-tweaks-17.0.0-1.noarch.rpm
```

**Build from source:**

```bash
./build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-17.0.0-1.noarch.rpm
```

## Quick Start

```bash
# GUI
loofi-fedora-tweaks

# CLI
loofi info
loofi bluetooth status
loofi storage disks
```
