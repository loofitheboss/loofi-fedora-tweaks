"""
Package Service Implementations — v23.0 Architecture Hardening.

Concrete implementations of BasePackageService for DNF and rpm-ostree.
Uses CommandWorker for async operations, delegates to existing utils.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from core.executor.action_result import ActionResult
from core.workers.command_worker import CommandWorker
from services.package.base import BasePackageService
from services.system.system import SystemManager

logger = logging.getLogger(__name__)


class DnfPackageService(BasePackageService):
    """
    Package service implementation for DNF (traditional Fedora).

    Delegates to DNF package manager for traditional Fedora installations.
    """

    def install(
        self,
        packages: List[str],
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """Install packages using DNF with pkexec."""
        if not packages:
            return ActionResult(
                success=False,
                message="No packages specified",
                action_id="dnf_install_empty"
            )

        desc = description or f"Installing {len(packages)} package(s) with DNF"

        # Use CommandWorker for async execution
        worker = CommandWorker("pkexec", ["dnf", "install", "-y"] + packages, description=desc)

        if callback:
            worker.progress.connect(lambda msg, pct: callback(msg, pct))

        # For now, run synchronously (can be made async by returning worker)
        worker.start()
        worker.wait()

        result = worker.get_result()
        return result if result else ActionResult(
            success=False,
            message="Worker returned no result",
            action_id="dnf_install_no_result"
        )

    def remove(
        self,
        packages: List[str],
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """Remove packages using DNF with pkexec."""
        if not packages:
            return ActionResult(success=False, message="No packages specified")

        desc = description or f"Removing {len(packages)} package(s) with DNF"
        worker = CommandWorker("pkexec", ["dnf", "remove", "-y"] + packages, description=desc)

        if callback:
            worker.progress.connect(lambda msg, pct: callback(msg, pct))

        worker.start()
        worker.wait()
        result = worker.get_result()
        return result if result else ActionResult(success=False, message="Worker returned no result")

    def update(
        self,
        packages: Optional[List[str]] = None,
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """Update packages using DNF with pkexec."""
        if packages:
            desc = description or f"Updating {len(packages)} package(s) with DNF"
            args = ["pkexec", "dnf", "update", "-y"] + packages
        else:
            desc = description or "Updating all packages with DNF"
            args = ["pkexec", "dnf", "update", "-y"]

        worker = CommandWorker("pkexec", args[1:], description=desc)
        if callback:
            worker.progress.connect(lambda msg, pct: callback(msg, pct))

        worker.start()
        worker.wait()
        result = worker.get_result()
        return result if result else ActionResult(success=False, message="Worker returned no result")

    def search(self, query: str, *, limit: int = 50) -> ActionResult:
        """Search for packages using DNF."""
        worker = CommandWorker("dnf", ["search", query], description=f"Searching for '{query}'")
        worker.start()
        worker.wait()
        result = worker.get_result()

        if result and result.success:
            # Parse stdout to extract package names (simplified)
            lines = result.stdout.split('\n')
            matches = [line.split('.')[0].strip() for line in lines if '.x86_64' in line or '.noarch' in line]
            result.data = {"matches": matches[:limit], "total": len(matches)}

        return result if result else ActionResult(success=False, message="Search failed")

    def info(self, package: str) -> ActionResult:
        """Get package information using DNF."""
        worker = CommandWorker("dnf", ["info", package], description=f"Getting info for '{package}'")
        worker.start()
        worker.wait()
        result = worker.get_result()

        if result and result.success:
            # Parse info from stdout (simplified)
            result.data = {"package": package, "raw_info": result.stdout}

        return result if result else ActionResult(success=False, message="Info query failed")

    def list_installed(self) -> ActionResult:
        """List installed packages using DNF."""
        worker = CommandWorker("dnf", ["list", "installed"], description="Listing installed packages")
        worker.start()
        worker.wait()
        result = worker.get_result()

        if result and result.success:
            lines = result.stdout.split('\n')
            packages = [line.split('.')[0].strip() for line in lines if '.x86_64' in line or '.noarch' in line]
            result.data = {"packages": packages, "count": len(packages)}

        return result if result else ActionResult(success=False, message="List failed")

    def is_installed(self, package: str) -> bool:
        """Check if package is installed using DNF."""
        worker = CommandWorker("rpm", ["-q", package], description=f"Checking if '{package}' is installed")
        worker.start()
        worker.wait()
        result = worker.get_result()
        return result and result.exit_code == 0 if result else False


class RpmOstreePackageService(BasePackageService):
    """
    Package service implementation for rpm-ostree (Atomic Fedora).

    Delegates to rpm-ostree for Silverblue, Kinoite, and other OSTree variants.
    """

    def install(
        self,
        packages: List[str],
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """Install packages using rpm-ostree with --apply-live if possible."""
        if not packages:
            return ActionResult(success=False, message="No packages specified")

        desc = description or f"Installing {len(packages)} package(s) with rpm-ostree"

        # Try --apply-live first for immediate effect
        worker = CommandWorker(
            "pkexec",
            ["rpm-ostree", "install", "--apply-live"] + packages,
            description=desc
        )

        if callback:
            worker.progress.connect(lambda msg, pct: callback(msg, pct))

        worker.start()
        worker.wait()
        result = worker.get_result()

        if result and result.exit_code != 0 and "cannot apply" in result.stdout.lower():
            # Fallback to regular install (requires reboot)
            logger.info("--apply-live not available, falling back to regular install")
            worker = CommandWorker(
                "pkexec",
                ["rpm-ostree", "install"] + packages,
                description=f"{desc} (reboot required)"
            )
            worker.start()
            worker.wait()
            result = worker.get_result()
            if result:
                result.needs_reboot = True

        return result if result else ActionResult(success=False, message="Install failed")

    def remove(
        self,
        packages: List[str],
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """Remove packages using rpm-ostree."""
        if not packages:
            return ActionResult(success=False, message="No packages specified")

        desc = description or f"Removing {len(packages)} package(s) with rpm-ostree"
        worker = CommandWorker(
            "pkexec",
            ["rpm-ostree", "uninstall"] + packages,
            description=desc
        )

        if callback:
            worker.progress.connect(lambda msg, pct: callback(msg, pct))

        worker.start()
        worker.wait()
        result = worker.get_result()

        if result:
            result.needs_reboot = True  # rpm-ostree typically requires reboot

        return result if result else ActionResult(success=False, message="Remove failed")

    def update(
        self,
        packages: Optional[List[str]] = None,
        *,
        description: str = "",
        callback: Optional[callable] = None
    ) -> ActionResult:
        """Update system using rpm-ostree upgrade."""
        if packages:
            # rpm-ostree doesn't support selective updates
            return ActionResult(
                success=False,
                message="rpm-ostree does not support selective package updates"
            )

        desc = description or "Upgrading system with rpm-ostree"
        worker = CommandWorker("pkexec", ["rpm-ostree", "upgrade"], description=desc)

        if callback:
            worker.progress.connect(lambda msg, pct: callback(msg, pct))

        worker.start()
        worker.wait()
        result = worker.get_result()

        if result:
            result.needs_reboot = True

        return result if result else ActionResult(success=False, message="Update failed")

    def search(self, query: str, *, limit: int = 50) -> ActionResult:
        """Search delegates to DNF for package database queries."""
        return ActionResult(
            success=False,
            message="Search not implemented for rpm-ostree, use DNF search instead"
        )

    def info(self, package: str) -> ActionResult:
        """Get package info delegates to rpm."""
        worker = CommandWorker("rpm", ["-qi", package], description=f"Getting info for '{package}'")
        worker.start()
        worker.wait()
        result = worker.get_result()

        if result and result.success:
            result.data = {"package": package, "raw_info": result.stdout}

        return result if result else ActionResult(success=False, message="Info query failed")

    def list_installed(self) -> ActionResult:
        """List installed packages using rpm."""
        worker = CommandWorker("rpm", ["-qa"], description="Listing installed packages")
        worker.start()
        worker.wait()
        result = worker.get_result()

        if result and result.success:
            packages = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            result.data = {"packages": packages, "count": len(packages)}

        return result if result else ActionResult(success=False, message="List failed")

    def is_installed(self, package: str) -> bool:
        """Check if package is installed using rpm."""
        worker = CommandWorker("rpm", ["-q", package], description=f"Checking if '{package}' is installed")
        worker.start()
        worker.wait()
        result = worker.get_result()
        return result and result.exit_code == 0 if result else False


def get_package_service() -> BasePackageService:
    """
    Factory function to get the appropriate package service for this system.

    Auto-detects whether running on Atomic (rpm-ostree) or traditional (DNF)
    Fedora and returns the corresponding service implementation.

    Returns:
        BasePackageService: DnfPackageService or RpmOstreePackageService
    """
    pm = SystemManager.get_package_manager()

    if pm == "rpm-ostree":
        logger.debug("Using RpmOstreePackageService for Atomic Fedora")
        return RpmOstreePackageService()
    else:
        logger.debug("Using DnfPackageService for traditional Fedora")
        return DnfPackageService()
