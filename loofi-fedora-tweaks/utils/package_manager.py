"""
Package Manager - Unified abstraction for DNF and rpm-ostree.
Routes package operations to the appropriate backend based on system type.
"""

import subprocess
from dataclasses import dataclass
from typing import List
from utils.system import SystemManager


@dataclass
class PackageResult:
    """Result of a package operation."""
    success: bool
    message: str
    needs_reboot: bool = False
    output: str = ""


class PackageManager:
    """
    Unified package manager that abstracts DNF and rpm-ostree.
    Automatically routes commands to the appropriate backend.
    """

    def __init__(self):
        self.is_atomic = SystemManager.is_atomic()
        self.backend = SystemManager.get_package_manager()

    def install(self, packages: List[str], use_flatpak: bool = False) -> PackageResult:
        """
        Install one or more packages.

        Args:
            packages: List of package names to install.
            use_flatpak: If True, install via Flatpak instead of system package manager.

        Returns:
            PackageResult with success status and messages.
        """
        if not packages:
            return PackageResult(False, "No packages specified")

        if use_flatpak:
            return self._install_flatpak(packages)

        if self.is_atomic:
            return self._install_rpm_ostree(packages)
        else:
            return self._install_dnf(packages)

    def _install_dnf(self, packages: List[str]) -> PackageResult:
        """Install packages using DNF."""
        cmd = ["pkexec", "dnf", "install", "-y"] + packages
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            if result.returncode == 0:
                return PackageResult(True, f"Installed: {', '.join(packages)}", output=result.stdout)
            else:
                return PackageResult(False, f"Failed to install: {result.stderr}", output=result.stderr)
        except Exception as e:
            return PackageResult(False, f"Error: {str(e)}")

    def _install_rpm_ostree(self, packages: List[str]) -> PackageResult:
        """Install packages using rpm-ostree with live apply."""
        # Try --apply-live first for immediate effect
        cmd = ["pkexec", "rpm-ostree", "install", "--apply-live"] + packages
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
            if result.returncode == 0:
                return PackageResult(
                    True,
                    f"Installed: {', '.join(packages)}",
                    needs_reboot=False,
                    output=result.stdout
                )
            elif "cannot apply" in result.stderr.lower():
                # Fall back to regular install (requires reboot)
                cmd = ["pkexec", "rpm-ostree", "install"] + packages
                result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
                if result.returncode == 0:
                    return PackageResult(
                        True,
                        f"Installed (reboot required): {', '.join(packages)}",
                        needs_reboot=True,
                        output=result.stdout
                    )
            return PackageResult(False, f"Failed: {result.stderr}", output=result.stderr)
        except Exception as e:
            return PackageResult(False, f"Error: {str(e)}")

    def _install_flatpak(self, packages: List[str]) -> PackageResult:
        """Install packages using Flatpak."""
        results = []
        for pkg in packages:
            # Assume flathub remote
            cmd = ["flatpak", "install", "-y", "flathub", pkg]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
                if result.returncode == 0:
                    results.append(f"✓ {pkg}")
                else:
                    results.append(f"✗ {pkg}: {result.stderr[:50]}")
            except Exception as e:
                results.append(f"✗ {pkg}: {str(e)}")

        success = all("✓" in r for r in results)
        return PackageResult(success, "\n".join(results))

    def remove(self, packages: List[str]) -> PackageResult:
        """Remove one or more packages."""
        if not packages:
            return PackageResult(False, "No packages specified")

        if self.is_atomic:
            cmd = ["pkexec", "rpm-ostree", "uninstall"] + packages
        else:
            cmd = ["pkexec", "dnf", "remove", "-y"] + packages

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            if result.returncode == 0:
                needs_reboot = self.is_atomic  # rpm-ostree always needs reboot for removal
                return PackageResult(True, f"Removed: {', '.join(packages)}", needs_reboot=needs_reboot)
            else:
                return PackageResult(False, f"Failed: {result.stderr}")
        except Exception as e:
            return PackageResult(False, f"Error: {str(e)}")

    def update(self) -> PackageResult:
        """Run system update."""
        if self.is_atomic:
            cmd = ["pkexec", "rpm-ostree", "upgrade"]
        else:
            cmd = ["pkexec", "dnf", "update", "-y"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            if result.returncode == 0:
                needs_reboot = self.is_atomic
                return PackageResult(True, "System updated successfully", needs_reboot=needs_reboot, output=result.stdout)
            else:
                return PackageResult(False, f"Update failed: {result.stderr}", output=result.stderr)
        except Exception as e:
            return PackageResult(False, f"Error: {str(e)}")

    def reset_to_base(self) -> PackageResult:
        """Reset rpm-ostree to base image (Atomic only)."""
        if not self.is_atomic:
            return PackageResult(False, "Not an Atomic system")

        cmd = ["pkexec", "rpm-ostree", "reset"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
            if result.returncode == 0:
                return PackageResult(True, "Reset to base image (reboot required)", needs_reboot=True)
            else:
                return PackageResult(False, f"Reset failed: {result.stderr}")
        except Exception as e:
            return PackageResult(False, f"Error: {str(e)}")

    def get_layered_packages(self) -> List[str]:
        """Get list of layered packages (Atomic only)."""
        return SystemManager.get_layered_packages()
