"""
System Manager - Central system detection and abstraction layer.
Handles detection of Fedora Atomic variants (Silverblue, Kinoite, etc.)
"""

import os
import subprocess
import shutil


class SystemManager:
    """Manages system detection and provides system-level information."""

    # Cache the result to avoid repeated filesystem checks
    _is_atomic_cached = None
    _pending_reboot_cached = None

    @classmethod
    def is_atomic(cls) -> bool:
        """
        Check if running on an Atomic/Immutable Fedora variant.
        (Silverblue, Kinoite, Sericea, Onyx, or any OSTree-based system)

        Returns:
            True if running on an Atomic system, False otherwise.
        """
        if cls._is_atomic_cached is None:
            cls._is_atomic_cached = os.path.exists("/run/ostree-booted")
        return cls._is_atomic_cached

    @classmethod
    def get_variant_name(cls) -> str:
        """
        Get the name of the Fedora variant.

        Returns:
            String like "Silverblue", "Kinoite", "Workstation", etc.
        """
        if not cls.is_atomic():
            return "Workstation"

        # Try to read the variant from os-release
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("VARIANT="):
                        variant = line.split("=")[1].strip().strip('"')
                        return variant
        except Exception:
            pass

        return "Atomic"  # Generic fallback

    @classmethod
    def get_package_manager(cls) -> str:
        """
        Get the appropriate package manager for this system.

        Returns:
            'rpm-ostree' for Atomic systems, 'dnf' for traditional Workstation.
        """
        return "rpm-ostree" if cls.is_atomic() else "dnf"

    @classmethod
    def has_pending_deployment(cls) -> bool:
        """
        Check if there's a pending rpm-ostree deployment waiting for reboot.

        Returns:
            True if reboot is needed to apply changes, False otherwise.
        """
        if not cls.is_atomic():
            return False

        try:
            result = subprocess.run(
                ["rpm-ostree", "status", "--json"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                deployments = data.get("deployments", [])
                # If there's more than one deployment and first isn't booted, reboot pending
                if len(deployments) > 1:
                    return not deployments[0].get("booted", False)
        except Exception:
            pass

        return False

    @classmethod
    def get_layered_packages(cls) -> list:
        """
        Get list of layered (overlayed) packages on Atomic systems.

        Returns:
            List of package names layered on top of the base image.
        """
        if not cls.is_atomic():
            return []

        try:
            result = subprocess.run(
                ["rpm-ostree", "status", "--json"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                deployments = data.get("deployments", [])
                if deployments:
                    # Get the booted deployment
                    for dep in deployments:
                        if dep.get("booted", False):
                            return dep.get("requested-local-packages", []) + \
                                dep.get("requested-packages", [])
        except Exception:
            pass

        return []

    @classmethod
    def is_flatpak_available(cls) -> bool:
        """Check if Flatpak is installed and available."""
        return shutil.which("flatpak") is not None

    @classmethod
    def is_flathub_enabled(cls) -> bool:
        """Check if Flathub remote is configured."""
        try:
            result = subprocess.run(
                ["flatpak", "remotes"],
                capture_output=True, text=True, check=False
            )
            return "flathub" in result.stdout.lower()
        except Exception:
            return False
