# Loofi Fedora Tweaks - User Guide 📖

> **Version 9.2.0 "Pulse Update"**  
> Complete documentation for all features and functionality.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Dashboard](#dashboard)
3. [Performance Monitor (v9.2)](#performance-monitor)
4. [Process Manager (v9.2)](#process-manager)
5. [Temperature Monitor (v9.2)](#temperature-monitor)
6. [Network Traffic Monitor (v9.2)](#network-traffic-monitor)
7. [Developer Tools (v7.1+)](#developer-tools)
8. [Watchtower Diagnostics (v7.5+)](#watchtower-diagnostics)
9. [Replicator - IaC Export (v8.0+)](#replicator---iac-export)
10. [Security Center (v8.5+)](#security-center)
11. [Director - Window Management (v9.0)](#director---window-management)
12. [Boot Management](#boot-management)
13. [Marketplace & Drift Detection](#marketplace--drift-detection)
14. [CLI Reference](#cli-reference)
15. [All Tabs Overview](#all-tabs-overview)
16. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# One-command install
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

### Launch

```bash
# GUI Mode
loofi-fedora-tweaks

# CLI Mode
loofi info
loofi cleanup
```

---

## Dashboard

The **Dashboard** is your system health overview:

| Card | Description |
|------|-------------|
| **CPU Usage** | Current CPU utilization percentage |
| **Memory** | RAM usage (used/total) |
| **Disk Space** | Storage utilization |

### Quick Actions

| Button | Action |
|--------|--------|
| **Run Cleanup** | Clean DNF cache, vacuum journal, TRIM SSD |
| **Check Updates** | Check for system updates |
| **Apply Preset** | Apply your saved configuration preset |

### Auto-Refresh (v9.2)

The dashboard now auto-refreshes every 5 seconds with live system health:

| Indicator | Description |
|-----------|-------------|
| **CPU Load** | Real-time CPU usage with color-coded status (green/yellow/red) |
| **Memory** | Current RAM usage updated automatically |
| **Disk** | Disk space utilization |

---

## Performance Monitor

### 📊 Performance Tab (v9.2)

Real-time system performance graphs with 60-second rolling history:

| Graph | Data Source | Description |
|-------|------------|-------------|
| **CPU Usage** | `/proc/stat` | Per-core and total CPU utilization percentage |
| **Memory** | `/proc/meminfo` | Used, cached, and available RAM |
| **Disk I/O** | `/proc/diskstats` | Read/write throughput in MB/s |
| **Network I/O** | `/proc/net/dev` | Upload/download bandwidth per interface |

All data is collected directly from `/proc` without external dependencies (no psutil required).

**Key Features:**
- Graphs auto-update every 2 seconds
- 60-second rolling window with history
- Human-readable bandwidth display (KB/s, MB/s, GB/s)
- Catppuccin Mocha color-coded charts

---

## Process Manager

### 🔍 Process Manager Tab (v9.2)

Monitor and manage running processes with a sortable tree view:

| Column | Description |
|--------|-------------|
| **PID** | Process ID |
| **Name** | Process name from /proc/[pid]/stat |
| **User** | Process owner |
| **CPU %** | CPU usage (calculated from /proc/[pid]/stat deltas) |
| **Memory %** | RAM usage percentage |
| **Memory** | Absolute memory in human-readable format |
| **State** | Process state (R=Running, S=Sleeping, Z=Zombie, etc.) |

**Context Menu (Right-Click):**

| Action | Description |
|--------|-------------|
| **Kill (SIGTERM)** | Gracefully terminate the process |
| **Force Kill (SIGKILL)** | Forcefully terminate the process |
| **Renice** | Change process priority (-20 to 19) |

Privileged operations automatically escalate via `pkexec` when needed.

**Sorting & Filtering:**
- Click column headers to sort by any field
- Filter by current user only
- Top processes by CPU or memory usage

---

## Temperature Monitor

### 🌡️ Temperature Monitoring (v9.2)

Hardware temperature monitoring via the Linux hwmon sysfs interface:

| Sensor Type | hwmon Drivers | Example |
|-------------|---------------|---------|
| **CPU** | coretemp, k10temp, zenpower | Intel Core, AMD Ryzen |
| **GPU** | amdgpu, nouveau, nvidia | Discrete graphics cards |
| **Disk** | nvme, drivetemp | NVMe SSDs, SATA drives |
| **Other** | Various | Motherboard, chipset sensors |

**Health Status Levels:**

| Status | Condition | Indicator |
|--------|-----------|-----------|
| **OK** | All sensors below thresholds | Green |
| **Warning** | Any sensor at/above high threshold | Yellow |
| **Critical** | Any sensor at/above critical threshold | Red |

Temperature data is read from `/sys/class/hwmon/hwmon*/temp*_input` files.

---

## Network Traffic Monitor

### 📡 Network Traffic Monitor (v9.2)

Per-interface network monitoring with bandwidth tracking and connection listing:

| Feature | Description |
|---------|-------------|
| **Interface Stats** | Bytes sent/received, packet counts per interface |
| **Bandwidth Calculation** | Real-time upload/download rates |
| **Interface Classification** | Auto-detect WiFi, Ethernet, Loopback, VPN |
| **Active Connections** | TCP/UDP connections with remote addresses |
| **Process Mapping** | Map connections to owning processes via /proc/[pid]/fd |

**Interface Types:**

| Pattern | Type |
|---------|------|
| `wl*` | WiFi |
| `en*`, `eth*` | Ethernet |
| `lo` | Loopback |
| `tun*`, `wg*` | VPN |

Data sources: `/proc/net/dev`, `/proc/net/tcp`, `/proc/net/udp`, `/sys/class/net/*/operstate`

---

## Developer Tools

### 📦 Containers Tab (v7.1+)

Manage Distrobox containers graphically:

| Feature | Description |
|---------|-------------|
| **Container List** | View all containers with status (running/stopped) |
| **Create Container** | Select from popular images (Fedora, Ubuntu, Arch, etc.) |
| **Context Menu** | Right-click to Enter, Stop, Delete, or Open Terminal |
| **Export Apps** | Export applications from containers to host |

### 🛠️ Developer Tab (v7.1+)

One-click installation for development environments:

**Language Version Managers:**

| Tool | Description |
|------|-------------|
| **PyEnv** | Install multiple Python versions without affecting system |
| **NVM** | Node.js version manager for JavaScript development |
| **Rustup** | Rust toolchain installer with easy version switching |

**VS Code Extension Profiles:**

| Profile | Extensions Included |
|---------|---------------------|
| **Python** | pylance, debugpy, black, jupyter, ruff |
| **C/C++** | cpptools, cmake-tools, clang-format |
| **Rust** | rust-analyzer, toml, lldb |
| **Web** | prettier, eslint, tailwindcss |
| **Containers** | docker, remote-containers |

---

## Watchtower Diagnostics

### 🔭 Watchtower Tab (v7.5+)

System diagnostics hub with three sub-tabs:

#### Services

| Feature | Description |
|---------|-------------|
| **Gaming Filter** | Show only gaming-related services (GameMode, Steam, etc.) |
| **Failed Filter** | Find services that failed to start |
| **Context Menu** | Start, Stop, Restart, Mask, Unmask services |

#### Boot Analyzer

| Feature | Description |
|---------|-------------|
| **Boot Stats** | Firmware, loader, kernel, userspace timing |
| **Slow Services** | List services taking >5s to start |
| **Suggestions** | Optimization recommendations |

#### Journal Viewer

| Feature | Description |
|---------|-------------|
| **Quick Diagnostic** | Error count and failed services at a glance |
| **Boot Errors** | View current boot errors |
| **🆘 Panic Button** | Export forum-ready log with system info |

---

## Replicator - IaC Export

### 🔄 Replicator Tab (v8.0+)

Export your system configuration as Infrastructure as Code:

#### Ansible Playbook Export

Generate standard Ansible playbooks that work on any Fedora/RHEL machine:

| Option | Description |
|--------|-------------|
| **DNF Packages** | Export user-installed packages |
| **Flatpak Apps** | Export Flatpak applications |
| **GNOME Settings** | Export theme, fonts, settings |

**Usage:**

```bash
cd ~/loofi-playbook
ansible-playbook site.yml --ask-become-pass
```

#### Kickstart Generator

Create Anaconda-compatible .ks files for automated installs:

| Option | Description |
|--------|-------------|
| **Packages** | Include DNF package list |
| **Flatpaks** | Add Flatpak install in %post |

**Usage during installation:**

```
inst.ks=file:///path/to/loofi.ks
```

---

## Boot Management

The **Boot** tab provides three powerful sections:

### 1. Kernel Parameters

| Preset | Parameters | Use Case |
|--------|------------|----------|
| **AMD GPU** | `amdgpu.ppfeaturemask=0xffffffff` | Enable AMD GPU overclocking |
| **Intel IOMMU** | `intel_iommu=on iommu=pt` | GPU passthrough for VMs |
| **NVIDIA** | `nvidia-drm.modeset=1` | Enable NVIDIA modesetting |

### 2. ZRAM Configuration

| Setting | Range | Recommendation |
|---------|-------|----------------|
| **Size** | 25-150% RAM | 50-100% for most users |
| **Algorithm** | zstd, lz4, lzo | `zstd` (best compression) |

### 3. Secure Boot & MOK

1. **Generate Key**: Creates RSA 2048-bit key pair
2. **Enroll Key**: Imports key to MOK list
3. **Reboot**: Press any key in MOK Manager, enter password

---

## Marketplace & Drift Detection

### Community Marketplace (v7.0+)

1. **Search**: Find presets by name or description
2. **Filter**: Categories (Gaming, Privacy, Performance, etc.)
3. **Download**: Save preset locally
4. **Apply**: Apply preset and set drift baseline

### Configuration Drift Detection

| State | Meaning |
|-------|---------|
| **No Baseline** | No preset has been applied with tracking |
| **Stable** | System matches the baseline |
| **Drifted** | Changes detected |

---

## CLI Reference

### Basic Commands

```bash
loofi info              # System information
loofi cleanup           # Full cleanup
loofi cleanup dnf       # DNF cache only
loofi cleanup journal   # Journal vacuum
```

### Power Management

```bash
loofi tweak power --profile performance
loofi tweak power --profile balanced
loofi tweak battery --limit 80  # HP Elitebook
```

### Network

```bash
loofi network dns --provider cloudflare
loofi network dns --provider google
```

### System Monitoring (v9.2)

```bash
loofi health                  # System health overview
loofi disk                    # Disk usage analysis
loofi disk --details          # Include large directory listing
loofi processes               # Top 15 processes by CPU
loofi processes --sort memory # Sort by memory usage
loofi processes -n 25         # Show top 25 processes
loofi temperature             # Hardware temperature readings
loofi netmon                  # Network interface stats
loofi netmon --connections    # Include active connections
```

---

## All Tabs Overview

| Tab | Icon | Description |
|-----|------|-------------|
| **Home** | 🏠 | Dashboard with system health |
| **System Info** | ℹ️ | Hardware specs, OS version |
| **Updates** | 📦 | System update management |
| **Cleanup** | 🧹 | Cache cleaning, orphan removal |
| **Hardware** | ⚡ | CPU governor, power profiles |
| **HP Tweaks** | 💻 | Battery limit (HP specific) |
| **Apps** | 🚀 | One-click app installation |
| **Advanced** | ⚙️ | DNF optimization, TCP BBR |
| **Gaming** | 🎮 | MangoHud, ProtonUp |
| **Network** | 🌐 | DNS, firewall, MAC |
| **Presets** | 💾 | Save/load configurations |
| **Marketplace** | 🌐 | Community presets |
| **Scheduler** | ⏰ | Automated tasks |
| **Boot** | 🔧 | Kernel params, ZRAM |
| **Containers** | 📦 | Distrobox GUI **(v7.1)** |
| **Developer** | 🛠️ | Version managers, VS Code **(v7.1)** |
| **Watchtower** | 🔭 | Services, boot, journal **(v7.5)** |
| **Replicator** | 🔄 | Ansible/Kickstart export **(v8.0)** |
| **AI Lab** | 🧠 | Local AI setup (Ollama) **(v8.1)** |
| **Security** | 🛡️ | Port audit, USB Guard **(v8.5)** |
| **Director** | 🎬 | Window management **(v9.0)** |
| **Performance** | 📊 | Live CPU, RAM, I/O graphs **(v9.2)** |
| **Processes** | 🔍 | Process monitor with kill/renice **(v9.2)** |
| **Repos** | 📁 | Repository management |
| **Privacy** | 🔒 | Telemetry settings |
| **Theming** | 🎨 | GTK/Qt themes |
| **Overlays** | 📦 | rpm-ostree (Atomic only) |

---

## Troubleshooting

### App Won't Launch

```bash
pip install PyQt6
python3 main.py
```

### Permission Denied

```bash
sudo dnf install polkit
```

### Panic Log for Support

Use the **Watchtower** → **Journal** → **🆘 Export Panic Log** button to generate a forum-ready diagnostic file.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/loofitheboss/loofi-fedora-tweaks/issues)
- **Releases**: [GitHub Releases](https://github.com/loofitheboss/loofi-fedora-tweaks/releases)

---

*Documentation last updated: v9.2.0 - February 2026*
