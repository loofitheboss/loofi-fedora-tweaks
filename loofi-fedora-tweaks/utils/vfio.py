"""
VFIO Passthrough Assistant - guided GPU passthrough configuration.
Part of v11.5 "Hypervisor Update".

Walks the user through IOMMU / VFIO setup: prerequisite checks, GPU
candidate detection, kernel-arg generation, dracut/modprobe config, and
a step-by-step plan the user can review before applying changes.

Builds on VirtualizationManager (utils/virtualization.py) for low-level
IOMMU/GPU queries.
"""

import os
import re
import shutil
import subprocess
from typing import Optional

from utils.virtualization import VirtualizationManager, IOMMUDevice


class VFIOAssistant:
    """Guided GPU passthrough / VFIO configuration helper."""

    # ==================== PREREQUISITES ====================

    @classmethod
    def check_prerequisites(cls) -> dict:
        """Check whether the system meets VFIO passthrough requirements.

        Returns:
            Dict with boolean keys: kvm_ok, iommu_ok, second_gpu, vfio_module.
        """
        kvm_ok = VirtualizationManager.is_kvm_module_loaded()
        iommu_ok = VirtualizationManager.is_iommu_enabled()

        # Do we have more than one GPU?
        gpus = VirtualizationManager.find_gpu_devices()
        second_gpu = len(gpus) >= 2

        vfio_module = cls._is_vfio_module_available()

        return {
            "kvm_ok": kvm_ok,
            "iommu_ok": iommu_ok,
            "second_gpu": second_gpu,
            "vfio_module": vfio_module,
        }

    @classmethod
    def _is_vfio_module_available(cls) -> bool:
        """Check whether the vfio-pci kernel module is loaded or loadable."""
        try:
            result = subprocess.run(
                ["modinfo", "vfio-pci"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False

    # ==================== GPU CANDIDATE DETECTION ====================

    @classmethod
    def get_passthrough_candidates(cls) -> list:
        """Find GPUs eligible for passthrough (i.e. NOT the primary display).

        Checks ``/sys/class/drm/card*/device/boot_vga`` to identify the
        primary display adapter, then returns all other GPUs.

        Returns:
            List of dicts with keys: slot, description, vendor_id, device_id,
            driver, iommu_group.
        """
        all_gpus = VirtualizationManager.find_gpu_devices()
        primary_slot = cls._get_primary_gpu_slot()

        candidates = []
        for group, device in all_gpus:
            if device.slot == primary_slot:
                continue  # skip the boot-VGA GPU
            candidates.append({
                "slot": device.slot,
                "description": device.description,
                "vendor_id": device.vendor_id,
                "device_id": device.device_id,
                "driver": device.driver,
                "iommu_group": group.group_id,
            })

        return candidates

    @classmethod
    def _get_primary_gpu_slot(cls) -> str:
        """Identify the PCI slot of the primary (boot_vga) GPU."""
        drm_base = "/sys/class/drm"
        try:
            for entry in sorted(os.listdir(drm_base)):
                boot_vga_path = os.path.join(drm_base, entry, "device", "boot_vga")
                if os.path.isfile(boot_vga_path):
                    try:
                        with open(boot_vga_path, "r") as f:
                            if f.read().strip() == "1":
                                # Resolve the PCI slot from the device symlink
                                device_link = os.path.join(drm_base, entry, "device")
                                if os.path.islink(device_link):
                                    return os.path.basename(os.readlink(device_link))
                    except (PermissionError, OSError):
                        continue
        except (FileNotFoundError, PermissionError):
            pass
        return ""

    # ==================== CONFIG GENERATION ====================

    @classmethod
    def generate_kernel_args(cls, device_ids: list) -> str:
        """Generate kernel command-line additions for VFIO passthrough.

        Args:
            device_ids: List of ``"vendor:device"`` ID pairs (e.g. ``["10de:2503"]``).

        Returns:
            Full kernel cmdline string, e.g.
            ``"iommu=on vfio-pci.ids=10de:2503,10de:228e"``
        """
        # Determine vendor-specific IOMMU arg
        _, vendor, _ = VirtualizationManager.check_cpu_virt_extensions()
        if vendor == "Intel":
            iommu_arg = "intel_iommu=on"
        elif vendor == "AMD":
            iommu_arg = "amd_iommu=on"
        else:
            iommu_arg = "iommu=on"

        ids_str = ",".join(device_ids)
        return f"{iommu_arg} iommu=pt vfio-pci.ids={ids_str}"

    @classmethod
    def generate_dracut_config(cls, device_ids: list) -> str:
        """Generate content for ``/etc/dracut.conf.d/vfio.conf``.

        Ensures vfio-pci is loaded very early in the initramfs.
        """
        lines = [
            '# VFIO passthrough - generated by Loofi Fedora Tweaks',
            'add_drivers+=" vfio vfio_iommu_type1 vfio_pci "',
        ]
        return "\n".join(lines) + "\n"

    @classmethod
    def generate_modprobe_config(cls, device_ids: list) -> str:
        """Generate content for ``/etc/modprobe.d/vfio.conf``.

        Binds specific PCI IDs to vfio-pci so the host driver
        never claims them.
        """
        ids_str = ",".join(device_ids)
        lines = [
            "# VFIO passthrough - generated by Loofi Fedora Tweaks",
            f"options vfio-pci ids={ids_str}",
            "softdep nvidia pre: vfio-pci",
            "softdep nouveau pre: vfio-pci",
            "softdep amdgpu pre: vfio-pci",
        ]
        return "\n".join(lines) + "\n"

    # ==================== GRUB HELPERS ====================

    @classmethod
    def get_current_grub_cmdline(cls) -> str:
        """Read the current ``GRUB_CMDLINE_LINUX`` from ``/etc/default/grub``."""
        grub_path = "/etc/default/grub"
        try:
            with open(grub_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GRUB_CMDLINE_LINUX="):
                        # Strip the variable name and surrounding quotes
                        value = line.split("=", 1)[1]
                        return value.strip('"').strip("'")
        except (FileNotFoundError, PermissionError):
            pass
        return ""

    @classmethod
    def build_grub_update_command(cls) -> tuple:
        """Build the command to regenerate the GRUB config.

        Returns:
            (cmd, args, description) tuple following the PrivilegedCommand pattern.
        """
        return (
            "pkexec",
            ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"],
            "Regenerating GRUB configuration...",
        )

    @classmethod
    def build_dracut_rebuild_command(cls) -> tuple:
        """Build the command to rebuild the initramfs via dracut.

        Returns:
            (cmd, args, description) tuple following the PrivilegedCommand pattern.
        """
        return (
            "pkexec",
            ["dracut", "--force"],
            "Rebuilding initramfs with VFIO modules...",
        )

    # ==================== STEP-BY-STEP PLAN ====================

    @classmethod
    def get_step_by_step_plan(cls, target_gpu: dict) -> list:
        """Generate a full VFIO setup plan for user review.

        Args:
            target_gpu: Dict with at least ``vendor_id`` and ``device_id`` keys
                        (as returned by ``get_passthrough_candidates()``).

        Returns:
            List of step dicts with: step_number, description, command,
            reversible (bool).
        """
        device_id_pair = f"{target_gpu['vendor_id']}:{target_gpu['device_id']}"
        device_ids = [device_id_pair]
        kernel_args = cls.generate_kernel_args(device_ids)
        dracut_content = cls.generate_dracut_config(device_ids)
        modprobe_content = cls.generate_modprobe_config(device_ids)

        steps = [
            {
                "step_number": 1,
                "description": (
                    "Add IOMMU and VFIO kernel parameters to GRUB. "
                    f"Append to GRUB_CMDLINE_LINUX: {kernel_args}"
                ),
                "command": f"Edit /etc/default/grub: GRUB_CMDLINE_LINUX append '{kernel_args}'",
                "reversible": True,
            },
            {
                "step_number": 2,
                "description": "Write dracut config to load VFIO modules in initramfs.",
                "command": f"pkexec tee /etc/dracut.conf.d/vfio.conf  (content: {dracut_content.strip()})",
                "reversible": True,
            },
            {
                "step_number": 3,
                "description": "Write modprobe config to bind device to vfio-pci.",
                "command": f"pkexec tee /etc/modprobe.d/vfio.conf  (content: {modprobe_content.strip()})",
                "reversible": True,
            },
            {
                "step_number": 4,
                "description": "Regenerate GRUB configuration.",
                "command": "pkexec grub2-mkconfig -o /boot/grub2/grub.cfg",
                "reversible": True,
            },
            {
                "step_number": 5,
                "description": "Rebuild initramfs to include VFIO modules.",
                "command": "pkexec dracut --force",
                "reversible": True,
            },
            {
                "step_number": 6,
                "description": "Reboot to apply changes. The target GPU will be claimed by vfio-pci.",
                "command": "systemctl reboot",
                "reversible": True,
            },
        ]
        return steps
