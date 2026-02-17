# System Management Skills

## Package Management
- **Install/Remove packages** — DNF or rpm-ostree auto-detected via `SystemManager.get_package_manager()`
- **Smart updates** — Batch package updates with conflict resolution and rollback
- **Autoremove** — Clean unused dependency packages
- **Flatpak management** — Install, update, remove Flatpak applications
- **Repository management** — Enable/disable/add package repositories

**Modules:** `utils/package_manager.py`, `utils/package_explorer.py`, `utils/flatpak_manager.py`
**UI:** Software Tab, Maintenance Tab
**CLI:** `package`, `updates`, `flatpak-manage`

## System Cleanup
- **DNF cache clean** — Purge package manager cache
- **Journal vacuum** — Trim systemd journal to size/time limits
- **SSD TRIM** — Discard unused filesystem blocks
- **RPM DB rebuild** — Repair corrupted RPM database
- **Autoremove** — Remove orphaned packages

**Modules:** `core/executor/operations.py` (CleanupOps)
**UI:** Maintenance Tab
**CLI:** `cleanup`

## Service Management
- **Service control** — Start, stop, restart, enable, disable systemd units
- **Service discovery** — List all services with status, type, description
- **Service monitoring** — Track service state changes

**Modules:** `utils/service_explorer.py`, `services/system/service.py`
**UI:** Settings Tab (services section)
**CLI:** `service`

## Boot Configuration
- **Boot analysis** — Analyze boot time and identify slow services
- **GRUB config** — Modify bootloader parameters safely
- **Kernel parameters** — View and set kernel command line options
- **Secure Boot** — Check and manage Secure Boot status

**Modules:** `utils/boot_analyzer.py`, `utils/boot_config.py`, `utils/secureboot.py`, `utils/kernel.py`
**UI:** System Info Tab, Diagnostics Tab
**CLI:** `boot`

## System Information
- **Hardware detection** — CPU, GPU, RAM, motherboard, battery info
- **Hardware profiles** — Auto-detect hardware model (HP EliteBook, ThinkPad, etc.)
- **OS detection** — Traditional vs Atomic (Silverblue/Kinoite) Fedora
- **Kernel info** — Running kernel version, parameters, modules

**Modules:** `utils/system_info_utils.py`, `utils/hardware_profiles.py`, `services/hardware/`
**UI:** System Info Tab, Hardware Tab
**CLI:** `info`, `hardware`

## Process Management
- **Process listing** — Top processes by CPU, memory, I/O
- **Process control** — Kill, signal, priority adjustment
- **Resource tracking** — Per-process resource consumption history

**Modules:** `utils/process.py`, `services/system/processes.py`
**UI:** Monitor Tab
**CLI:** `processes`

## Factory Reset
- **Full reset** — Restore system to default configuration state
- **Selective reset** — Reset specific components (network, desktop, packages)

**Modules:** `utils/factory_reset.py`
**UI:** Settings Tab (advanced section)
