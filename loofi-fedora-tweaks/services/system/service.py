"""
System Service Implementation — v23.0 Architecture Hardening.

Concrete implementation of BaseSystemService for Fedora systems.
Wraps systemctl and other system commands via CommandWorker.
"""

from __future__ import annotations

import logging
import os

from core.executor.action_result import ActionResult
from core.workers.command_worker import CommandWorker
from services.system.base import BaseSystemService
from services.system.system import SystemManager

logger = logging.getLogger(__name__)


class SystemService(BaseSystemService):
    """
    System service implementation for Fedora.

    Provides power management, hostname, and bootloader operations.
    Uses CommandWorker for async execution and delegates to SystemManager
    for system detection and information.
    """

    def reboot(self, *, description: str = "", delay_seconds: int = 0) -> ActionResult:
        """Reboot the system using systemctl."""
        desc = description or "Rebooting system"

        if delay_seconds > 0:
            args = ["systemctl", "reboot", f"--when=+{delay_seconds}"]
        else:
            args = ["systemctl", "reboot"]

        worker = CommandWorker("pkexec", args, description=desc)
        worker.start()
        worker.wait()

        result = worker.get_result()
        return (
            result
            if result
            else ActionResult(
                success=False,
                message="Reboot command failed",
                action_id="system_reboot_failed",
            )
        )

    def shutdown(
        self, *, description: str = "", delay_seconds: int = 0
    ) -> ActionResult:
        """Shutdown the system using systemctl."""
        desc = description or "Shutting down system"

        if delay_seconds > 0:
            args = ["systemctl", "poweroff", f"--when=+{delay_seconds}"]
        else:
            args = ["systemctl", "poweroff"]

        worker = CommandWorker("pkexec", args, description=desc)
        worker.start()
        worker.wait()

        result = worker.get_result()
        return (
            result
            if result
            else ActionResult(
                success=False,
                message="Shutdown command failed",
                action_id="system_shutdown_failed",
            )
        )

    def suspend(self, *, description: str = "") -> ActionResult:
        """Suspend the system using systemctl."""
        desc = description or "Suspending system"

        worker = CommandWorker("systemctl", ["suspend"], description=desc)
        worker.start()
        worker.wait()

        result = worker.get_result()
        return (
            result
            if result
            else ActionResult(
                success=False,
                message="Suspend command failed",
                action_id="system_suspend_failed",
            )
        )

    def update_grub(self, *, description: str = "") -> ActionResult:
        """Update GRUB configuration."""
        desc = description or "Updating GRUB configuration"

        # Detect UEFI vs BIOS
        try:
            if os.path.exists("/sys/firmware/efi"):
                grub_cfg = "/etc/grub2-efi.cfg"
            else:
                grub_cfg = "/etc/grub2.cfg"
        except Exception as e:
            logger.debug("Failed to detect UEFI/BIOS boot mode: %s", e)
            grub_cfg = "/etc/grub2.cfg"  # Fallback

        worker = CommandWorker(
            "pkexec", ["grub2-mkconfig", "-o", grub_cfg], description=desc
        )
        worker.start()
        worker.wait()

        result = worker.get_result()
        return (
            result
            if result
            else ActionResult(
                success=False,
                message="GRUB update failed",
                action_id="system_grub_update_failed",
            )
        )

    def set_hostname(self, hostname: str, *, description: str = "") -> ActionResult:
        """Set system hostname using hostnamectl."""
        if not hostname or not hostname.strip():
            return ActionResult(
                success=False,
                message="Hostname cannot be empty",
                action_id="system_hostname_empty",
            )

        desc = description or f"Setting hostname to '{hostname}'"

        worker = CommandWorker(
            "pkexec",
            ["hostnamectl", "set-hostname", hostname.strip()],
            description=desc,
        )
        worker.start()
        worker.wait()

        result = worker.get_result()
        return (
            result
            if result
            else ActionResult(
                success=False,
                message="Hostname update failed",
                action_id="system_hostname_failed",
            )
        )

    @staticmethod
    def is_atomic() -> bool:
        """
        Check if running on Atomic  Fedora.

        Delegates to SystemManager for consistency with existing code.

        Returns:
            bool: True if Atomic system, False otherwise
        """
        return SystemManager.is_atomic()

    @staticmethod
    def get_variant_name() -> str:
        """
        Get Fedora variant name.

        Delegates to SystemManager for consistency.

        Returns:
            str: Variant name (e.g., "Silverblue", "Workstation")
        """
        return SystemManager.get_variant_name()

    @staticmethod
    def get_package_manager() -> str:
        """
        Get package manager for this system.

        Delegates to SystemManager for consistency.

        Returns:
            str: "dnf" or "rpm-ostree"
        """
        return SystemManager.get_package_manager()

    @staticmethod
    def has_pending_reboot() -> bool:
        """
        Check if system has pending changes requiring reboot.

        Delegates to SystemManager for Atomic detection.

        Returns:
            bool: True if reboot needed, False otherwise
        """
        return SystemManager.has_pending_deployment()
