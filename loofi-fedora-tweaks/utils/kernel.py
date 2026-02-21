"""
Kernel Manager - Kernel parameter and boot configuration management.
Provides safe interface for modifying kernel boot parameters via grubby.
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class KernelResult:
    """Result of a kernel operation."""

    success: bool
    message: str
    output: str = ""
    backup_path: Optional[str] = None


class KernelManager:
    """
    Manages kernel boot parameters and GRUB configuration.
    Uses grubby for safe parameter modification.
    """

    GRUB_DEFAULT = "/etc/default/grub"
    BACKUP_DIR = Path.home() / ".local/share/loofi-fedora-tweaks/backups"

    # Common kernel parameters with descriptions
    COMMON_PARAMS = {
        # AMD GPU
        "amdgpu.ppfeaturemask=0xffffffff": "AMD GPU: Enable all power management features",
        "amdgpu.dc=1": "AMD GPU: Enable Display Core",
        # Intel
        "intel_iommu=on": "Intel IOMMU: Required for GPU passthrough",
        "intel_pstate=disable": "Intel P-State: Use acpi-cpufreq instead",
        # NVIDIA
        "nvidia-drm.modeset=1": "NVIDIA: Enable kernel modesetting",
        "nvidia.NVreg_PreserveVideoMemoryAllocations=1": "NVIDIA: Preserve VRAM for suspend",
        # Performance
        "mitigations=off": "⚠️ Disable CPU security mitigations (faster, less secure)",
        "nowatchdog": "Disable watchdog (reduces interrupts)",
        "nmi_watchdog=0": "Disable NMI watchdog",
        # Display
        "quiet": "Suppress boot messages",
        "splash": "Show boot splash screen",
        # Debugging
        "rd.driver.blacklist=nouveau": "Blacklist nouveau driver (for NVIDIA)",
        "modprobe.blacklist=nouveau": "Blacklist nouveau at modprobe level",
        # Virtualization
        "iommu=pt": "IOMMU passthrough mode",
        "kvm.ignore_msrs=1": "KVM: Ignore unknown MSRs",
    }

    @classmethod
    def get_current_params(cls) -> List[str]:
        """
        Get current kernel command line parameters.

        Returns:
            List of current kernel parameters.
        """
        try:
            with open("/proc/cmdline", "r") as f:
                cmdline = f.read().strip()
            # Split but preserve quoted strings
            return cmdline.split()
        except (OSError, IOError) as e:
            logger.debug("Failed to read /proc/cmdline: %s", e)
            return []

    @classmethod
    def get_default_params(cls) -> List[str]:
        """
        Get default kernel parameters from /etc/default/grub.

        Returns:
            List of default GRUB_CMDLINE_LINUX parameters.
        """
        try:
            with open(cls.GRUB_DEFAULT, "r") as f:
                for line in f:
                    if line.startswith("GRUB_CMDLINE_LINUX="):
                        # Extract value between quotes
                        value = line.split("=", 1)[1].strip().strip('"')
                        return value.split() if value else []
        except (OSError, IOError) as e:
            logger.debug("Failed to read default GRUB parameters: %s", e)
        return []

    @classmethod
    def backup_grub(cls) -> KernelResult:
        """
        Create a timestamped backup of /etc/default/grub.

        Returns:
            KernelResult with backup path if successful.
        """
        try:
            cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = cls.BACKUP_DIR / f"grub_backup_{timestamp}"

            shutil.copy2(cls.GRUB_DEFAULT, backup_path)

            return KernelResult(
                success=True, message="Backup created", backup_path=str(backup_path)
            )
        except OSError as e:
            return KernelResult(False, f"Backup failed: {str(e)}")

    @classmethod
    def add_param(cls, param: str) -> KernelResult:
        """
        Add a kernel parameter using grubby.

        Args:
            param: Kernel parameter to add (e.g., "intel_iommu=on")

        Returns:
            KernelResult with operation status.
        """
        if not param:
            return KernelResult(False, "No parameter specified")

        # Create backup first
        backup_result = cls.backup_grub()
        if not backup_result.success:
            return backup_result

        # Use grubby to add the parameter
        cmd = ["pkexec", "grubby", "--update-kernel=ALL", f"--args={param}"]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=60
            )
            if result.returncode == 0:
                return KernelResult(
                    success=True,
                    message=f"Added parameter: {param}\nReboot required to apply.",
                    output=result.stdout,
                    backup_path=backup_result.backup_path,
                )
            else:
                return KernelResult(
                    success=False,
                    message=f"Failed to add parameter: {result.stderr}",
                    output=result.stderr,
                )
        except (subprocess.SubprocessError, OSError) as e:
            return KernelResult(False, f"Error: {str(e)}")

    @classmethod
    def remove_param(cls, param: str) -> KernelResult:
        """
        Remove a kernel parameter using grubby.

        Args:
            param: Kernel parameter to remove.

        Returns:
            KernelResult with operation status.
        """
        if not param:
            return KernelResult(False, "No parameter specified")

        # Create backup first
        backup_result = cls.backup_grub()
        if not backup_result.success:
            return backup_result

        # Use grubby to remove the parameter
        cmd = ["pkexec", "grubby", "--update-kernel=ALL", f"--remove-args={param}"]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=60
            )
            if result.returncode == 0:
                return KernelResult(
                    success=True,
                    message=f"Removed parameter: {param}\nReboot required to apply.",
                    output=result.stdout,
                    backup_path=backup_result.backup_path,
                )
            else:
                return KernelResult(
                    success=False,
                    message=f"Failed to remove parameter: {result.stderr}",
                    output=result.stderr,
                )
        except (subprocess.SubprocessError, OSError) as e:
            return KernelResult(False, f"Error: {str(e)}")

    @classmethod
    def has_param(cls, param: str) -> bool:
        """Check if a parameter (or its key) is currently set."""
        current = cls.get_current_params()
        param_key = param.split("=")[0]
        return any(p.startswith(param_key) for p in current)

    @classmethod
    def get_backups(cls) -> List[Path]:
        """Get list of available GRUB backups."""
        if not cls.BACKUP_DIR.exists():
            return []
        return sorted(cls.BACKUP_DIR.glob("grub_backup_*"), reverse=True)

    @classmethod
    def restore_backup(cls, backup_path: str) -> KernelResult:
        """
        Restore a GRUB backup.

        Args:
            backup_path: Path to the backup file.

        Returns:
            KernelResult with operation status.
        """
        if not os.path.exists(backup_path):
            return KernelResult(False, "Backup file not found")

        try:
            # Use pkexec to copy back
            cmd = ["pkexec", "cp", backup_path, cls.GRUB_DEFAULT]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=600
            )

            if result.returncode == 0:
                # Rebuild grub config
                rebuild_cmd = ["pkexec", "grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"]
                subprocess.run(
                    rebuild_cmd, capture_output=True, check=False, timeout=120
                )

                return KernelResult(
                    success=True,
                    message="Backup restored. Reboot required to apply.",
                    output=result.stdout,
                )
            else:
                return KernelResult(False, f"Restore failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return KernelResult(False, f"Error: {str(e)}")
