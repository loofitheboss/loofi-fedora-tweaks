"""
System Service Base — v23.0 Architecture Hardening.

Abstract interface for system-level operations.
Supports reboot, shutdown, suspend, and GRUB updates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.executor.action_result import ActionResult


class BaseSystemService(ABC):
    """
    Abstract base class for system-level operations.

    Provides consistent interface for power management, bootloader
    configuration, and other system-wide actions.
    """

    @abstractmethod
    def reboot(
        self,
        *,
        description: str = "",
        delay_seconds: int = 0
    ) -> ActionResult:
        """
        Reboot the system.

        Args:
            description: Human-readable description for logging
            delay_seconds: Delay before reboot (default: immediate)

        Returns:
            ActionResult: Success/failure with message
        """
        pass

    @abstractmethod
    def shutdown(
        self,
        *,
        description: str = "",
        delay_seconds: int = 0
    ) -> ActionResult:
        """
        Shutdown the system.

        Args:
            description: Human-readable description for logging
            delay_seconds: Delay before shutdown (default: immediate)

        Returns:
            ActionResult: Success/failure with message
        """
        pass

    @abstractmethod
    def suspend(
        self,
        *,
        description: str = ""
    ) -> ActionResult:
        """
        Suspend the system (sleep).

        Args:
            description: Human-readable description for logging

        Returns:
            ActionResult: Success/failure with message
        """
        pass

    @abstractmethod
    def update_grub(
        self,
        *,
        description: str = ""
    ) -> ActionResult:
        """
        Update GRUB bootloader configuration.

        Args:
            description: Human-readable description for logging

        Returns:
            ActionResult: Success/failure with message
        """
        pass

    @abstractmethod
    def set_hostname(
        self,
        hostname: str,
        *,
        description: str = ""
    ) -> ActionResult:
        """
        Set system hostname.

        Args:
            hostname: New hostname to set
            description: Human-readable description for logging

        Returns:
            ActionResult: Success/failure with message
        """
        pass
