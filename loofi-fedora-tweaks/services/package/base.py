"""
Package Service Base — v23.0 Architecture Hardening.

Abstract interface for package management operations.
Supports DNF, rpm-ostree, and Flatpak backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.executor.action_result import ActionResult


class BasePackageService(ABC):
    """
    Abstract base class for package management services.

    All package service implementations must inherit from this class
    and implement the required methods. This ensures consistent API
    across DNF, rpm-ostree, and Flatpak backends.
    """

    @abstractmethod
    def install(
        self,
        packages: List[str],
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """
        Install one or more packages.

        Args:
            packages: List of package names to install
            description: Human-readable description for logging
            callback: Optional callback(message, percentage) for progress

        Returns:
            ActionResult: Success/failure with output and reboot flag
        """
        pass

    @abstractmethod
    def remove(
        self,
        packages: List[str],
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """
        Remove one or more packages.

        Args:
            packages: List of package names to remove
            description: Human-readable description for logging
            callback: Optional callback(message, percentage) for progress

        Returns:
            ActionResult: Success/failure with output
        """
        pass

    @abstractmethod
    def update(
        self,
        packages: Optional[List[str]] = None,
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """
        Update packages (or all packages if none specified).

        Args:
            packages: Optional list of specific packages to update
            description: Human-readable description for logging
            callback: Optional callback(message, percentage) for progress

        Returns:
            ActionResult: Success/failure with output and reboot flag
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        limit: int = 50
    ) -> ActionResult:
        """
        Search for packages matching query.

        Args:
            query: Search term
            limit: Maximum number of results

        Returns:
            ActionResult: Success with data containing list of matches
        """
        pass

    @abstractmethod
    def info(
        self,
        package: str
    ) -> ActionResult:
        """
        Get information about a package.

        Args:
            package: Package name

        Returns:
            ActionResult: Success with data containing package info dict
        """
        pass

    @abstractmethod
    def list_installed(self) -> ActionResult:
        """
        List all installed packages.

        Returns:
            ActionResult: Success with data containing list of installed packages
        """
        pass

    @abstractmethod
    def is_installed(self, package: str) -> bool:
        """
        Check if a package is installed.

        Args:
            package: Package name

        Returns:
            bool: True if installed, False otherwise
        """
        pass
