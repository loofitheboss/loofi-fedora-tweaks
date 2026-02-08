# Loofi Fedora Tweaks v12.0.0 - The "Sovereign" Update

The biggest release yet: full KVM/QEMU virtualization, LAN mesh networking, and workspace state teleportation across devices.

## Highlights

* **VM Quick-Create Wizard**: One-click VMs for Windows 11, Fedora, Ubuntu, Kali, Arch with auto-TPM and virtio drivers.
* **VFIO GPU Passthrough**: Step-by-step IOMMU analysis, kernel cmdline generation, and dracut config.
* **Loofi Link Mesh**: Discover devices on LAN via mDNS, share clipboard, and drop files.
* **State Teleport**: Capture VS Code, git, and terminal workspace state; restore on another machine.

## New Features

### v11.5 Hypervisor Update
* VM Quick-Create with 5 preset flavors (Windows 11, Fedora, Ubuntu, Kali, Arch)
* VFIO GPU Passthrough Assistant with prerequisites check and step-by-step plan
* Disposable VMs using QCOW2 overlay snapshots for untrusted software
* New **Virtualization** tab with VMs, GPU Passthrough, and Disposable sub-tabs

### v12.0 Sovereign Networking
* Loofi Link mesh device discovery via Avahi mDNS
* Encrypted clipboard sync between paired devices
* File Drop with local HTTP transfer and checksum verification
* State Teleport workspace capture and cross-device restore
* New **Loofi Link** tab with Devices, Clipboard, and File Drop sub-tabs
* New **State Teleport** tab with Capture, Saved States, and Restore sections

### v11.1-v11.3 AI Polish
* Lite Model Library with 6 curated GGUF models and RAM-based recommendations
* Voice Mode with whisper.cpp transcription
* Context RAG with TF-IDF local file indexing (security-filtered)
* Enhanced **AI Lab** tab with Models, Voice, and Knowledge sub-tabs

### Architecture
* Virtualization and AI Lab refactored as first-party plugins with JSON manifests
* 18-tab sidebar layout (up from 15)
* 564 tests passing (up from 225)

## New CLI Commands

```bash
# Virtualization
loofi vm list                 # List virtual machines
loofi vm start <name>         # Start a VM
loofi vm stop <name>          # Stop a VM
loofi vfio check              # Check VFIO prerequisites
loofi vfio gpus               # List GPU passthrough candidates
loofi vfio plan               # Generate step-by-step VFIO setup plan

# Mesh Networking
loofi mesh discover           # Discover LAN devices
loofi mesh status             # Show device ID and local IPs

# State Teleport
loofi teleport capture        # Capture workspace state
loofi teleport list           # List saved packages
loofi teleport restore <id>   # Restore a package

# AI Models
loofi ai-models list          # List installed and recommended models
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
