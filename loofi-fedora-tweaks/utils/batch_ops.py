"""
Batch Operations Manager — v31.0 Smart UX
Handles batch install/remove operations for Software and Maintenance tabs.
"""

from typing import List, Tuple

from services.system import SystemManager
from utils.commands import PrivilegedCommand


class BatchOpsManager:
    """Manages batch package operations with Atomic/Traditional branching."""

    @staticmethod
    def batch_install(packages: List[str]) -> Tuple[str, List[str], str]:
        """
        Build operation tuple for batch installing packages.

        Args:
            packages: List of package names to install.

        Returns:
            Tuple of (binary, args, description).

        Raises:
            ValueError: If packages list is empty.
        """
        if not packages:
            raise ValueError("No packages specified for batch install")

        pm = SystemManager.get_package_manager()
        desc = f"Installing {len(packages)} package(s): {', '.join(packages[:5])}"
        if len(packages) > 5:
            desc += f" and {len(packages) - 5} more"

        if pm == "rpm-ostree":
            return ("pkexec", ["rpm-ostree", "install"] + packages, desc)

        binary, args, _ = PrivilegedCommand.dnf("install", *packages)
        return (binary, args, desc)

    @staticmethod
    def batch_remove(packages: List[str]) -> Tuple[str, List[str], str]:
        """
        Build operation tuple for batch removing packages.

        Args:
            packages: List of package names to remove.

        Returns:
            Tuple of (binary, args, description).

        Raises:
            ValueError: If packages list is empty.
        """
        if not packages:
            raise ValueError("No packages specified for batch remove")

        pm = SystemManager.get_package_manager()
        desc = f"Removing {len(packages)} package(s): {', '.join(packages[:5])}"
        if len(packages) > 5:
            desc += f" and {len(packages) - 5} more"

        if pm == "rpm-ostree":
            return ("pkexec", ["rpm-ostree", "uninstall"] + packages, desc)

        binary, args, _ = PrivilegedCommand.dnf("remove", *packages)
        return (binary, args, desc)

    @staticmethod
    def batch_update() -> Tuple[str, List[str], str]:
        """
        Build operation tuple for updating all packages.

        Returns:
            Tuple of (binary, args, description).
        """
        pm = SystemManager.get_package_manager()
        desc = "Updating all packages"

        if pm == "rpm-ostree":
            return ("pkexec", ["rpm-ostree", "upgrade"], desc)

        binary, args, _ = PrivilegedCommand.dnf("upgrade")
        return (binary, args, desc)

    @staticmethod
    def validate_packages(packages: List[str]) -> List[str]:
        """
        Sanitize package names — remove empty strings and whitespace.

        Args:
            packages: Raw list of package name strings.

        Returns:
            Cleaned list of non-empty package names.
        """
        return [p.strip() for p in packages if p and p.strip()]
