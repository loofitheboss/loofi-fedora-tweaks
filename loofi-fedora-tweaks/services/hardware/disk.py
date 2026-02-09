"""
Disk Manager - Disk space monitoring and analysis utilities.
Provides disk usage stats, low space warnings, and large directory detection.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class DiskUsage:
    """Represents disk usage for a mount point."""
    mount_point: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent_used: float
    filesystem: str = ""

    @property
    def total_human(self) -> str:
        return DiskManager.bytes_to_human(self.total_bytes)

    @property
    def used_human(self) -> str:
        return DiskManager.bytes_to_human(self.used_bytes)

    @property
    def free_human(self) -> str:
        return DiskManager.bytes_to_human(self.free_bytes)


@dataclass
class LargeDirectory:
    """Represents a directory with its size."""
    path: str
    size_bytes: int

    @property
    def size_human(self) -> str:
        return DiskManager.bytes_to_human(self.size_bytes)


class DiskManager:
    """Manages disk space monitoring and analysis."""

    # Thresholds for disk space warnings
    WARNING_PERCENT = 80
    CRITICAL_PERCENT = 90

    @staticmethod
    def bytes_to_human(num_bytes: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(num_bytes) < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} PB"

    @staticmethod
    def get_disk_usage(path: str = "/") -> Optional[DiskUsage]:
        """
        Get disk usage for the given path's mount point.

        Args:
            path: Filesystem path to check (defaults to root).

        Returns:
            DiskUsage object or None on error.
        """
        try:
            usage = shutil.disk_usage(path)
            percent = (usage.used / usage.total * 100) if usage.total > 0 else 0
            return DiskUsage(
                mount_point=path,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                percent_used=round(percent, 1),
            )
        except Exception:
            return None

    @staticmethod
    def get_all_mount_points() -> List[DiskUsage]:
        """
        Get disk usage for all mounted filesystems.

        Returns:
            List of DiskUsage objects for each mount point.
        """
        results = []
        try:
            output = subprocess.run(
                ["df", "-B1", "--output=target,size,used,avail,pcent,source"],
                capture_output=True,
                text=True,
                check=False,
            )
            if output.returncode != 0:
                return results

            lines = output.stdout.strip().split("\n")[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if len(parts) >= 6:
                    mount = parts[0]
                    # Skip virtual filesystem mount points (not device sources)
                    # e.g., /dev (devtmpfs), /sys, /proc
                    # Keep /run/media (removable device auto-mounts)
                    if mount.startswith("/run/media"):
                        pass  # Allow removable media mounts
                    elif mount.startswith(("/dev", "/run", "/sys", "/proc")):
                        continue
                    if mount in ("/boot", "/boot/efi"):
                        continue
                    try:
                        total = int(parts[1])
                        used = int(parts[2])
                        avail = int(parts[3])
                        pct = float(parts[4].rstrip("%"))
                        fs = parts[5]
                        results.append(
                            DiskUsage(
                                mount_point=mount,
                                total_bytes=total,
                                used_bytes=used,
                                free_bytes=avail,
                                percent_used=pct,
                                filesystem=fs,
                            )
                        )
                    except (ValueError, IndexError):
                        continue
        except Exception:
            pass

        return results

    @staticmethod
    def check_disk_health(path: str = "/") -> Tuple[str, str]:
        """
        Check disk health and return status level and message.

        Args:
            path: Filesystem path to check.

        Returns:
            Tuple of (level, message) where level is 'ok', 'warning', or 'critical'.
        """
        usage = DiskManager.get_disk_usage(path)
        if usage is None:
            return ("unknown", "Unable to check disk usage")

        if usage.percent_used >= DiskManager.CRITICAL_PERCENT:
            return (
                "critical",
                f"Disk critically full: {usage.percent_used}% used ({usage.free_human} free)",
            )
        elif usage.percent_used >= DiskManager.WARNING_PERCENT:
            return (
                "warning",
                f"Disk space low: {usage.percent_used}% used ({usage.free_human} free)",
            )
        else:
            return (
                "ok",
                f"Disk healthy: {usage.percent_used}% used ({usage.free_human} free)",
            )

    @staticmethod
    def find_large_directories(
        path: str = "/home", max_depth: int = 2, top_n: int = 5
    ) -> List[LargeDirectory]:
        """
        Find the largest directories under the given path.

        Args:
            path: Root path to search from.
            max_depth: Maximum directory depth to scan.
            top_n: Number of results to return.

        Returns:
            List of LargeDirectory objects, sorted by size descending.
        """
        results = []
        try:
            output = subprocess.run(
                ["du", "-B1", f"--max-depth={max_depth}", path],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if output.returncode not in (0, 1):  # du returns 1 on permission errors
                return results

            for line in output.stdout.strip().split("\n"):
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    try:
                        size = int(parts[0])
                        dir_path = parts[1]
                        if dir_path != path:  # Skip the root itself
                            results.append(LargeDirectory(path=dir_path, size_bytes=size))
                    except ValueError:
                        continue

            results.sort(key=lambda d: d.size_bytes, reverse=True)
            return results[:top_n]
        except (subprocess.TimeoutExpired, Exception):
            return results
