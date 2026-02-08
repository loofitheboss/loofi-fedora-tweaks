# Loofi Fedora Tweaks v15.0.0 - The "Nebula" Update

A system intelligence release that makes Loofi smarter about the system it manages. Auto-tune performance based on workload, manage snapshots from a unified timeline, analyze logs with pattern detection, and execute common operations instantly from a quick-action bar.

## Highlights

* **Performance Auto-Tuner**: Workload detection + CPU/memory/IO optimization recommendations.
* **System Snapshot Timeline**: Unified Timeshift/Snapper/BTRFS snapshot management.
* **Smart Log Viewer**: Journal analysis with 10 built-in error pattern detectors.
* **Quick Actions Bar**: `Ctrl+Shift+K` floating command palette for power users.
* **4 New Dev Agents**: Planner, Builder, Sculptor, Guardian for AI-assisted development.

## New Features

### Performance Auto-Tuner
* Classifies workload into 6 profiles: idle, light, compilation, gaming, server, heavy
* Reads from /proc/stat, /proc/meminfo, /sys/ for real-time system analysis
* Recommends governor, swappiness, I/O scheduler, THP per workload
* One-click apply with pkexec privilege escalation
* Tuning history persisted to JSON (max 50 entries)

### System Snapshot Timeline
* Auto-detects Timeshift, Snapper, and BTRFS backends
* Unified list/create/delete operations across all backends
* Retention policy with automated cleanup
* Backend version detection and health reporting

### Smart Log Viewer
* 10 compiled patterns: OOM, segfault, disk full, auth failure, service failed, USB disconnect, kernel panic, NetworkManager, thermal throttle, firmware error
* Structured journalctl JSON parsing with severity labels
* Error summary with top units and pattern frequency
* Text and JSON export

### Quick Actions Bar
* Searchable action palette triggered by Ctrl+Shift+K
* 15+ default actions: Update System, Clean Cache, Security Scan, Auto-Tune, etc.
* Fuzzy search across name, description, and keywords
* Recent actions tracked (last 10) and promoted in search
* Plugin-extensible via QuickActionRegistry

## New CLI Commands

```bash
# Performance tuner
loofi tuner analyze       # Detect workload and recommend settings
loofi tuner apply         # Apply recommended settings
loofi tuner history       # Show tuning history

# Snapshot management
loofi snapshot list       # List all snapshots
loofi snapshot create     # Create a new snapshot
loofi snapshot delete ID  # Delete a snapshot
loofi snapshot backends   # Show available backends

# Smart log viewer
loofi logs show           # Show recent journal entries
loofi logs errors         # Error summary with pattern detection
loofi logs export FILE    # Export logs to file
```
loofi ai-models recommend     # Get RAM-based model recommendation
```

## Installation

**Via DNF:**

```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v12.0.0/loofi-fedora-tweaks-12.0.0-1.fc43.noarch.rpm
```

**Build from source:**

```bash
./build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-12.0.0-1.fc43.noarch.rpm
```

## Quick Start

```bash
# GUI
loofi-fedora-tweaks

# CLI
loofi info
loofi doctor
loofi vm list
loofi mesh discover
loofi teleport capture
loofi ai-models list
```
