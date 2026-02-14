"""
System Monitor - Resource monitoring utilities.
Provides memory usage, CPU load, and uptime information.
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryInfo:
    """System memory information."""

    total_bytes: int
    available_bytes: int
    used_bytes: int
    percent_used: float

    @property
    def total_human(self) -> str:
        return SystemMonitor.bytes_to_human(self.total_bytes)

    @property
    def available_human(self) -> str:
        return SystemMonitor.bytes_to_human(self.available_bytes)

    @property
    def used_human(self) -> str:
        return SystemMonitor.bytes_to_human(self.used_bytes)


@dataclass
class CpuInfo:
    """CPU load information."""

    load_1min: float
    load_5min: float
    load_15min: float
    core_count: int

    @property
    def load_percent(self) -> float:
        """Load as percentage of total cores (1-min average)."""
        if self.core_count > 0:
            return round(self.load_1min / self.core_count * 100, 1)
        return 0.0


@dataclass
class SystemHealth:
    """Aggregated system health status."""

    memory: Optional[MemoryInfo]
    cpu: Optional[CpuInfo]
    uptime: str
    hostname: str

    @property
    def memory_status(self) -> str:
        """Return memory health level: ok, warning, or critical."""
        if self.memory is None:
            return "unknown"
        if self.memory.percent_used >= 90:
            return "critical"
        elif self.memory.percent_used >= 75:
            return "warning"
        return "ok"

    @property
    def cpu_status(self) -> str:
        """Return CPU health level: ok, warning, or critical."""
        if self.cpu is None:
            return "unknown"
        if self.cpu.load_percent >= 90:
            return "critical"
        elif self.cpu.load_percent >= 70:
            return "warning"
        return "ok"


class SystemMonitor:
    """Monitors system resources (memory, CPU, uptime)."""

    @staticmethod
    def bytes_to_human(num_bytes: float) -> str:
        """Convert bytes to human-readable format."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(num_bytes) < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} PB"

    @staticmethod
    def get_memory_info() -> Optional[MemoryInfo]:
        """
        Get system memory usage from /proc/meminfo.

        Returns:
            MemoryInfo object or None on error.
        """
        try:
            meminfo = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        # Values in /proc/meminfo are in kB
                        value = int(parts[1]) * 1024
                        meminfo[key] = value

            total = meminfo.get("MemTotal", 0)
            available = meminfo.get("MemAvailable", 0)
            used = total - available
            percent = (used / total * 100) if total > 0 else 0

            return MemoryInfo(
                total_bytes=total,
                available_bytes=available,
                used_bytes=used,
                percent_used=round(percent, 1),
            )
        except Exception as e:
            logger.debug("Failed to read memory info from /proc/meminfo: %s", e)
            return None

    @staticmethod
    def get_cpu_info() -> Optional[CpuInfo]:
        """
        Get CPU load averages and core count.

        Returns:
            CpuInfo object or None on error.
        """
        try:
            load_1, load_5, load_15 = os.getloadavg()
            core_count = os.cpu_count() or 1
            return CpuInfo(
                load_1min=round(load_1, 2),
                load_5min=round(load_5, 2),
                load_15min=round(load_15, 2),
                core_count=core_count,
            )
        except Exception as e:
            logger.debug("Failed to get CPU load averages: %s", e)
            return None

    @staticmethod
    def get_uptime() -> str:
        """
        Get system uptime as human-readable string.

        Returns:
            Uptime string like "2 hours, 15 minutes".
        """
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.readline().split()[0])

            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)

            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0 or not parts:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

            return ", ".join(parts)
        except Exception as e:
            logger.debug("Failed to read uptime from /proc/uptime: %s", e)
            return "unknown"

    @staticmethod
    def get_hostname() -> str:
        """Get the system hostname."""
        try:
            with open("/etc/hostname", "r") as f:
                return f.read().strip()
        except Exception as e:
            logger.debug("Failed to read hostname from /etc/hostname: %s", e)
            try:
                return subprocess.getoutput("hostname").strip()
            except Exception as e:
                logger.debug("Failed to get hostname via hostname command: %s", e)
                return "unknown"

    @classmethod
    def get_system_health(cls) -> SystemHealth:
        """
        Get aggregated system health information.

        Returns:
            SystemHealth object with all resource stats.
        """
        return SystemHealth(
            memory=cls.get_memory_info(),
            cpu=cls.get_cpu_info(),
            uptime=cls.get_uptime(),
            hostname=cls.get_hostname(),
        )
