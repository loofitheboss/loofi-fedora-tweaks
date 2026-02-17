# Gaming & Virtualization Skills

## Game Mode
- **GameMode activation** — Install and enable Feral GameMode for performance
- **CPU governor** — Switch to performance governor during gaming
- **Process priority** — Elevate game process priority automatically

**Modules:** `utils/gaming_utils.py`, `core/executor/operations.py` (AdvancedOps)
**UI:** Gaming Tab
**CLI:** `advanced`

## GPU Passthrough (VFIO)
- **IOMMU setup** — Configure IOMMU groups for GPU isolation
- **VFIO binding** — Bind GPU to vfio-pci driver
- **Configuration wizard** — Step-by-step passthrough setup
- **Verification** — Validate passthrough readiness

**Modules:** `utils/vfio.py`
**UI:** Gaming Tab, Virtualization Tab
**CLI:** `vfio`

## Virtual Machine Management
- **VM lifecycle** — Create, start, stop, delete KVM/QEMU VMs
- **VM configuration** — CPU, RAM, disk, network settings per VM
- **VM templates** — Quick-create VMs from predefined templates
- **Disposable VMs** — Create temporary VMs that auto-delete on shutdown

**Modules:** `utils/vm_manager.py`, `utils/virtualization.py`, `utils/disposable_vm.py`
**UI:** Virtualization Tab
**CLI:** `vm`

## Performance Optimization for Gaming
- **TCP BBR** — Enable BBR congestion control for lower latency
- **Swappiness tuning** — Reduce swappiness for gaming workloads
- **DNF tweaks** — Optimize package manager for faster operations

**Modules:** `core/executor/operations.py` (AdvancedOps)
**CLI:** `advanced`

## Gaming Profiles
- **Quick-switch** — One-click gaming profile activation
- **Custom profiles** — Save and load gaming-specific system configurations
- **Auto-detection** — Detect game launches and apply profile

**Modules:** `utils/profiles.py`
**UI:** Profiles Tab
**CLI:** `profile`

## GPU Management
- **GPU detection** — Identify discrete and integrated GPUs
- **Driver info** — Display active GPU driver and version
- **GPU monitoring** — Temperature, utilization, memory usage

**Modules:** `services/hardware/hardware.py`
**UI:** Hardware Tab
