"""
Flatpak Manager — size visualization, permission audit, and cleanup.
Part of v37.0.0 "Pinnacle".

Provides Flatpak app size analysis, per-app permission auditing,
orphan runtime detection, and cleanup operations.
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import List

from utils.commands import CommandTuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FlatpakSizeEntry:
    """Represents a Flatpak app with its disk usage."""
    name: str
    app_id: str
    size_bytes: int = 0
    size_str: str = ""
    runtime: str = ""
    ref: str = ""


@dataclass
class FlatpakPermission:
    """Represents a single permission granted to a Flatpak app."""
    category: str  # "filesystem", "socket", "device", "dbus", etc.
    value: str     # e.g., "home:ro", "x11", "pulseaudio"


@dataclass
class FlatpakAppPermissions:
    """All permissions for a single Flatpak app."""
    app_id: str
    name: str
    permissions: List[FlatpakPermission]


# ---------------------------------------------------------------------------
# FlatpakManager
# ---------------------------------------------------------------------------

class FlatpakManager:
    """Flatpak size analysis, permission auditing, and cleanup.

    All public methods are ``@staticmethod`` so the class can be used without
    instantiation, consistent with other ``utils/*`` managers.
    """

    @staticmethod
    def is_available() -> bool:
        """Check if flatpak is installed."""
        return shutil.which("flatpak") is not None

    # -----------------------------------------------------------------
    # Size analysis
    # -----------------------------------------------------------------

    @staticmethod
    def get_flatpak_sizes() -> List[FlatpakSizeEntry]:
        """Get installed Flatpak apps with their disk sizes.

        Returns:
            List of FlatpakSizeEntry sorted by size (largest first).
        """
        entries: List[FlatpakSizeEntry] = []
        if not FlatpakManager.is_available():
            return entries

        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=name,application,size,runtime,ref"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        name = parts[0].strip()
                        app_id = parts[1].strip()
                        size_str = parts[2].strip()
                        runtime = parts[3].strip() if len(parts) > 3 else ""
                        ref = parts[4].strip() if len(parts) > 4 else ""

                        size_bytes = FlatpakManager._parse_size(size_str)
                        entries.append(FlatpakSizeEntry(
                            name=name,
                            app_id=app_id,
                            size_bytes=size_bytes,
                            size_str=size_str,
                            runtime=runtime,
                            ref=ref,
                        ))
            # Sort by size descending
            entries.sort(key=lambda e: e.size_bytes, reverse=True)
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to get Flatpak sizes: %s", e)
        return entries

    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse a human-readable size string to bytes.

        Handles formats like "1.2 GB", "500 MB", "100 kB".
        """
        size_str = size_str.strip()
        if not size_str:
            return 0

        multipliers = {
            "b": 1,
            "kb": 1024,
            "mb": 1024 ** 2,
            "gb": 1024 ** 3,
            "tb": 1024 ** 4,
        }

        try:
            parts = size_str.split()
            if len(parts) >= 2:
                number = float(parts[0].replace(",", "."))
                unit = parts[1].lower().replace("i", "")
                return int(number * multipliers.get(unit, 1))
            # Try parsing as pure number
            return int(float(size_str))
        except (ValueError, IndexError):
            return 0

    # -----------------------------------------------------------------
    # Permission audit
    # -----------------------------------------------------------------

    @staticmethod
    def get_flatpak_permissions(app_id: str) -> FlatpakAppPermissions:
        """Get permissions granted to a specific Flatpak app.

        Args:
            app_id: Flatpak application ID (e.g., "org.mozilla.firefox").

        Returns:
            FlatpakAppPermissions with all granted permissions.
        """
        permissions: List[FlatpakPermission] = []
        name = app_id

        if not FlatpakManager.is_available():
            return FlatpakAppPermissions(app_id=app_id, name=name, permissions=[])

        try:
            result = subprocess.run(
                ["flatpak", "info", "--show-permissions", app_id],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                current_category = ""
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        current_category = line[1:-1].lower()
                    elif "=" in line:
                        key, _, value = line.partition("=")
                        category = current_category or key.strip()
                        for val in value.split(";"):
                            val = val.strip()
                            if val:
                                permissions.append(FlatpakPermission(
                                    category=category,
                                    value=val,
                                ))

            # Get the display name
            info_result = subprocess.run(
                ["flatpak", "info", app_id],
                capture_output=True, text=True, timeout=15,
            )
            if info_result.returncode == 0:
                for line in info_result.stdout.splitlines():
                    if line.strip().lower().startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                        break

        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to get permissions for %s: %s", app_id, e)

        return FlatpakAppPermissions(app_id=app_id, name=name, permissions=permissions)

    @staticmethod
    def get_all_permissions() -> List[FlatpakAppPermissions]:
        """Get permissions for all installed Flatpak apps.

        Returns:
            List of FlatpakAppPermissions for each installed app.
        """
        all_perms: List[FlatpakAppPermissions] = []
        entries = FlatpakManager.get_flatpak_sizes()
        for entry in entries:
            perms = FlatpakManager.get_flatpak_permissions(entry.app_id)
            all_perms.append(perms)
        return all_perms

    # -----------------------------------------------------------------
    # Orphan detection
    # -----------------------------------------------------------------

    @staticmethod
    def find_orphan_runtimes() -> List[str]:
        """Find runtimes not referenced by any installed app.

        Returns:
            List of runtime refs that can be safely removed.
        """
        orphans: List[str] = []
        if not FlatpakManager.is_available():
            return orphans

        try:
            # Get unused runtimes via flatpak's built-in detection
            result = subprocess.run(
                ["flatpak", "uninstall", "--unused", "--assumeyes", "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if line and not line.startswith("Nothing") and not line.startswith("Info"):
                        # Lines like: "org.freedesktop.Platform/x86_64/23.08"
                        if "/" in line:
                            orphans.append(line)
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to find orphan runtimes: %s", e)
        return orphans

    # -----------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------

    @staticmethod
    def cleanup_unused() -> CommandTuple:
        """Build command to remove unused Flatpak runtimes.

        Returns:
            CommandTuple for the cleanup operation.
        """
        return ("flatpak", ["uninstall", "--unused", "--assumeyes"],
                "Removing unused Flatpak runtimes...")

    @staticmethod
    def get_total_size() -> str:
        """Get total disk space used by all Flatpak apps.

        Returns:
            Human-readable total size string.
        """
        entries = FlatpakManager.get_flatpak_sizes()
        total = sum(e.size_bytes for e in entries)

        if total >= 1024 ** 3:
            return f"{total / (1024 ** 3):.1f} GB"
        if total >= 1024 ** 2:
            return f"{total / (1024 ** 2):.1f} MB"
        if total >= 1024:
            return f"{total / 1024:.1f} KB"
        return f"{total} B"
