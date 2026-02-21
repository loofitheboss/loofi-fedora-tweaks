"""
VM Manager - libvirt/virt-install wrapper for VM lifecycle management.
Part of v11.5 "Hypervisor Update".

Provides VM creation (with Quick-Create flavour presets), start/stop/delete,
listing, and storage-pool helpers.  All subprocess calls live here so the
UI layer stays clean.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Result dataclass (mirrors utils.containers.Result)
# ---------------------------------------------------------------------------

@dataclass
class Result:
    """Operation result with message."""
    success: bool
    message: str
    data: Optional[dict] = None


# ---------------------------------------------------------------------------
# VMInfo dataclass
# ---------------------------------------------------------------------------

@dataclass
class VMInfo:
    """Represents a single libvirt virtual machine."""
    name: str
    state: str
    uuid: str = ""
    memory_mb: int = 0
    vcpus: int = 0
    disk_path: str = ""


# ---------------------------------------------------------------------------
# Quick-Create flavour presets
# ---------------------------------------------------------------------------

VM_FLAVORS: dict[str, dict[str, Any]] = {
    "windows11": {
        "label": "Windows 11",
        "ram_mb": 4096,
        "vcpus": 4,
        "disk_gb": 64,
        "iso_url": "",  # User must provide
        "needs_tpm": True,
        "needs_secureboot": True,
        "virtio_drivers": True,
        "os_variant": "win11",
    },
    "fedora": {
        "label": "Fedora Workstation",
        "ram_mb": 2048,
        "vcpus": 2,
        "disk_gb": 30,
        "iso_url": (
            "https://download.fedoraproject.org/pub/fedora/linux/"
            "releases/41/Workstation/x86_64/iso/"
        ),
        "needs_tpm": False,
        "virtio_drivers": False,
        "os_variant": "fedora-unknown",
    },
    "ubuntu": {
        "label": "Ubuntu Desktop",
        "ram_mb": 2048,
        "vcpus": 2,
        "disk_gb": 25,
        "iso_url": "",
        "needs_tpm": False,
        "virtio_drivers": False,
        "os_variant": "ubuntu-lts-latest",
    },
    "kali": {
        "label": "Kali Linux",
        "ram_mb": 2048,
        "vcpus": 2,
        "disk_gb": 30,
        "iso_url": "",
        "needs_tpm": False,
        "virtio_drivers": False,
        "os_variant": "linux2022",
    },
    "arch": {
        "label": "Arch Linux",
        "ram_mb": 1024,
        "vcpus": 2,
        "disk_gb": 20,
        "iso_url": "",
        "needs_tpm": False,
        "virtio_drivers": False,
        "os_variant": "archlinux",
    },
}

# Name validation: alphanumeric, dash, underscore only
_VM_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


class VMManager:
    """Manages libvirt VMs via virsh and virt-install."""

    # ==================== AVAILABILITY ====================

    @classmethod
    def is_available(cls) -> bool:
        """Check if the core tools (virsh, qemu-system-x86_64) are installed."""
        return (
            shutil.which("virsh") is not None
            and shutil.which("qemu-system-x86_64") is not None
        )

    # ==================== FLAVOURS ====================

    @classmethod
    def get_available_flavors(cls) -> dict:
        """Return the VM Quick-Create flavour presets."""
        return dict(VM_FLAVORS)

    # ==================== LIST / INFO ====================

    @classmethod
    def list_vms(cls) -> list:
        """List all defined VMs via ``virsh list --all``.

        Returns:
            List of VMInfo objects.
        """
        if not shutil.which("virsh"):
            return []

        try:
            result = subprocess.run(
                ["virsh", "list", "--all"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return []

            vms = []
            lines = result.stdout.strip().split("\n")
            # Skip the header lines (first two: header + dashes)
            for line in lines[2:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    # id  name  state  (id may be "-" for shut-off VMs)
                    name = parts[1]
                    state = parts[2]
                    vms.append(VMInfo(name=name, state=state))
                elif len(parts) == 2:
                    vms.append(VMInfo(name=parts[0], state=parts[1]))

            return vms

        except (subprocess.TimeoutExpired, Exception):
            return []

    @classmethod
    def get_vm_info(cls, name: str) -> Optional[VMInfo]:
        """Get detailed information about a specific VM via ``virsh dominfo``.

        Returns:
            VMInfo or None if the VM doesn't exist.
        """
        if not shutil.which("virsh"):
            return None

        try:
            result = subprocess.run(
                ["virsh", "dominfo", name],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None

            info = VMInfo(name=name, state="unknown")
            for line in result.stdout.strip().split("\n"):
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()

                if key == "state":
                    info.state = value
                elif key == "uuid":
                    info.uuid = value
                elif key == "max memory":
                    # value like "4194304 KiB"
                    try:
                        info.memory_mb = int(value.split()[0]) // 1024
                    except (ValueError, IndexError):
                        pass
                elif key == "cpu(s)":
                    try:
                        info.vcpus = int(value)
                    except ValueError:
                        pass

            return info

        except (subprocess.TimeoutExpired, Exception):
            return None

    # ==================== VM STATE ====================

    @classmethod
    def get_vm_state(cls, name: str) -> str:
        """Return the current state string for a VM (e.g. 'running', 'shut off')."""
        info = cls.get_vm_info(name)
        if info is None:
            return "unknown"
        return info.state

    # ==================== CREATE ====================

    @classmethod
    def create_vm(cls, name: str, flavor_key: str, iso_path: str, **overrides) -> Result:
        """Create a new VM using virt-install.

        Args:
            name: VM name (alphanumeric + dash + underscore only).
            flavor_key: Key from VM_FLAVORS.
            iso_path: Path to the installation ISO.
            **overrides: Override any flavour default (ram_mb, vcpus, disk_gb).

        Returns:
            Result with success/failure and message.
        """
        if not _VM_NAME_RE.match(name):
            return Result(
                False,
                "Invalid VM name. Use only letters, numbers, dashes, and underscores.",
            )

        if flavor_key not in VM_FLAVORS:
            return Result(False, f"Unknown flavour '{flavor_key}'.")

        if not iso_path or not os.path.isfile(iso_path):
            return Result(False, f"ISO file not found: {iso_path}")

        if not shutil.which("virt-install"):
            return Result(False, "virt-install is not installed.")

        flavor = dict(VM_FLAVORS[flavor_key])
        flavor.update(overrides)

        ram_mb = int(flavor.get("ram_mb", 2048))
        vcpus = int(flavor.get("vcpus", 2))
        disk_gb = int(flavor.get("disk_gb", 20))
        os_variant = str(flavor.get("os_variant", "generic"))

        disk_path = os.path.join(cls.get_default_storage_pool(), f"{name}.qcow2")

        cmd: list[str] = [
            "virt-install",
            "--name", name,
            "--ram", str(ram_mb),
            "--vcpus", str(vcpus),
            "--disk", f"path={disk_path},size={disk_gb},format=qcow2",
            "--cdrom", iso_path,
            "--os-variant", os_variant,
            "--network", "default",
            "--graphics", "spice",
            "--noautoconsole",
        ]

        # TPM support for Windows 11
        if flavor.get("needs_tpm", False):
            if shutil.which("swtpm"):
                cmd.extend(["--tpm", "backend.type=emulator,backend.version=2.0,model=tpm-crw"])
            else:
                return Result(
                    False,
                    "Windows 11 requires swtpm for TPM 2.0 emulation. "
                    "Install with: dnf install swtpm",
                )

        # Virtio drivers ISO for Windows guests
        if flavor.get("virtio_drivers", False):
            virtio_iso = "/usr/share/virtio-win/virtio-win.iso"
            if os.path.isfile(virtio_iso):
                cmd.extend(["--disk", f"path={virtio_iso},device=cdrom"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return Result(
                    True,
                    f"VM '{name}' created successfully.",
                    {"name": name, "disk": disk_path},
                )
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to create VM: {error}")

        except subprocess.TimeoutExpired:
            return Result(False, "VM creation timed out after 2 minutes.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error creating VM: {e}")

    # ==================== START / STOP / DELETE ====================

    @classmethod
    def start_vm(cls, name: str) -> Result:
        """Start a VM via ``virsh start``."""
        if not shutil.which("virsh"):
            return Result(False, "virsh is not installed.")

        try:
            result = subprocess.run(
                ["virsh", "start", name],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return Result(True, f"VM '{name}' started.")
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to start VM: {error}")
        except subprocess.TimeoutExpired:
            return Result(False, "Start operation timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error starting VM: {e}")

    @classmethod
    def stop_vm(cls, name: str) -> Result:
        """Gracefully shut down a VM via ``virsh shutdown``."""
        if not shutil.which("virsh"):
            return Result(False, "virsh is not installed.")

        try:
            result = subprocess.run(
                ["virsh", "shutdown", name],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return Result(True, f"VM '{name}' shutdown signal sent.")
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to shut down VM: {error}")
        except subprocess.TimeoutExpired:
            return Result(False, "Shutdown operation timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error shutting down VM: {e}")

    @classmethod
    def force_stop_vm(cls, name: str) -> Result:
        """Force-stop a VM via ``virsh destroy``."""
        if not shutil.which("virsh"):
            return Result(False, "virsh is not installed.")

        try:
            result = subprocess.run(
                ["virsh", "destroy", name],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return Result(True, f"VM '{name}' force-stopped.")
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to force-stop VM: {error}")
        except subprocess.TimeoutExpired:
            return Result(False, "Force-stop operation timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error force-stopping VM: {e}")

    @classmethod
    def delete_vm(cls, name: str, delete_storage: bool = False) -> Result:
        """Delete (undefine) a VM via ``virsh undefine``.

        Args:
            name: VM name to delete.
            delete_storage: If True, also remove associated disk images.
        """
        if not shutil.which("virsh"):
            return Result(False, "virsh is not installed.")

        cmd = ["virsh", "undefine", name]
        if delete_storage:
            cmd.append("--remove-all-storage")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return Result(True, f"VM '{name}' deleted.")
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to delete VM: {error}")
        except subprocess.TimeoutExpired:
            return Result(False, "Delete operation timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error deleting VM: {e}")

    # ==================== STORAGE & USER HELPERS ====================

    @classmethod
    def get_default_storage_pool(cls) -> str:
        """Return the default libvirt image storage directory.

        Falls back to ``~/.local/share/loofi-vms/`` if the system path
        doesn't exist.
        """
        system_pool = "/var/lib/libvirt/images"
        if os.path.isdir(system_pool):
            return system_pool
        user_pool = os.path.expanduser("~/.local/share/loofi-vms")
        os.makedirs(user_pool, exist_ok=True)
        return user_pool

    @classmethod
    def check_user_in_libvirt_group(cls) -> bool:
        """Check whether the current user belongs to the ``libvirt`` group."""
        try:
            result = subprocess.run(
                ["id", "-nG"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return "libvirt" in result.stdout.split()
        except (subprocess.TimeoutExpired, Exception):
            pass
        return False
