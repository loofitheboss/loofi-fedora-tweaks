"""
Boot analysis utilities.
Part of v7.5 "Watchtower" update.

Parses systemd-analyze output to help users identify slow boot services.
"""

import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServiceTime:
    """Represents a service's startup time."""
    service: str
    time_seconds: float
    is_slow: bool = False  # >5s considered slow


@dataclass
class BootStats:
    """Overall boot timing statistics."""
    firmware_time: Optional[float] = None
    loader_time: Optional[float] = None
    kernel_time: Optional[float] = None
    userspace_time: Optional[float] = None
    total_time: Optional[float] = None


class BootAnalyzer:
    """
    Analyzes systemd boot performance.

    Parses `systemd-analyze blame` and `systemd-analyze` output
    to provide boot time visualization and optimization suggestions.
    """

    SLOW_THRESHOLD = 5.0  # Seconds - services taking longer are flagged

    @classmethod
    def get_boot_stats(cls) -> BootStats:
        """
        Get overall boot timing statistics.

        Returns:
            BootStats with timing breakdown.
        """
        try:
            result = subprocess.run(
                ["systemd-analyze", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return BootStats()

            stats = BootStats()
            output = result.stdout

            # Parse output like:
            # Startup finished in 2.5s (firmware) + 1.2s (loader) + 3.1s (kernel) + 15.2s (userspace) = 22.0s
            import re

            firmware_match = re.search(r'([\d.]+)s \(firmware\)', output)
            if firmware_match:
                stats.firmware_time = float(firmware_match.group(1))

            loader_match = re.search(r'([\d.]+)s \(loader\)', output)
            if loader_match:
                stats.loader_time = float(loader_match.group(1))

            kernel_match = re.search(r'([\d.]+)s \(kernel\)', output)
            if kernel_match:
                stats.kernel_time = float(kernel_match.group(1))

            userspace_match = re.search(r'([\d.]+)s \(userspace\)', output)
            if userspace_match:
                stats.userspace_time = float(userspace_match.group(1))

            total_match = re.search(r'= ([\d.]+)s', output)
            if total_match:
                stats.total_time = float(total_match.group(1))

            return stats

        except Exception:
            return BootStats()

    @classmethod
    def get_blame_data(cls, limit: int = 30) -> list[ServiceTime]:
        """
        Get list of services ordered by startup time.

        Args:
            limit: Maximum number of services to return.

        Returns:
            List of ServiceTime objects, slowest first.
        """
        try:
            result = subprocess.run(
                ["systemd-analyze", "blame", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            services = []
            import re

            for line in result.stdout.strip().split("\n")[:limit]:
                line = line.strip()
                if not line:
                    continue

                # Parse lines like "15.234s NetworkManager.service"
                match = re.match(r'([\d.]+)(ms|s|min)\s+(.+)', line)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2)
                    service = match.group(3).strip()

                    # Convert to seconds
                    if unit == "ms":
                        time_seconds = value / 1000
                    elif unit == "min":
                        time_seconds = value * 60
                    else:
                        time_seconds = value

                    services.append(ServiceTime(
                        service=service,
                        time_seconds=time_seconds,
                        is_slow=time_seconds >= cls.SLOW_THRESHOLD
                    ))

            return services

        except Exception:
            return []

    @classmethod
    def get_slow_services(cls, threshold: float = None) -> list[ServiceTime]:
        """
        Get services that take longer than threshold to start.

        Args:
            threshold: Seconds threshold (default: SLOW_THRESHOLD)

        Returns:
            List of slow services.
        """
        if threshold is None:
            threshold = cls.SLOW_THRESHOLD

        all_services = cls.get_blame_data(limit=100)
        return [s for s in all_services if s.time_seconds >= threshold]

    @classmethod
    def get_critical_chain(cls) -> str:
        """
        Get the critical chain of services.

        Shows the path of services that determined total boot time.

        Returns:
            Critical chain output as string.
        """
        try:
            result = subprocess.run(
                ["systemd-analyze", "critical-chain", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""

    @classmethod
    def get_optimization_suggestions(cls) -> list[str]:
        """
        Generate optimization suggestions based on boot analysis.

        Returns:
            List of suggestion strings.
        """
        suggestions = []
        slow = cls.get_slow_services()
        stats = cls.get_boot_stats()

        if not slow and not stats.total_time:
            return ["Unable to analyze boot - systemd-analyze may not be available."]

        # Check total boot time
        if stats.total_time and stats.total_time > 30:
            suggestions.append(
                f"⚠️ Total boot time is {stats.total_time:.1f}s. "
                "Consider disabling unused services."
            )

        # Flag slow services
        for service in slow[:5]:  # Top 5 slowest
            suggestions.append(
                f"🐢 {service.service} takes {service.time_seconds:.1f}s. "
                "Consider masking if not needed."
            )

        # Check for known problematic services
        problematic = {
            "NetworkManager-wait-online.service": "Usually not needed for desktops",
            "plymouth-quit-wait.service": "Can be disabled if boot screen not needed",
            "dnf-makecache.service": "Can be disabled if you update manually",
        }

        all_services = cls.get_blame_data(limit=100)
        for service in all_services:
            if service.service in problematic:
                suggestions.append(
                    f"💡 {service.service}: {problematic[service.service]}"
                )

        if not suggestions:
            suggestions.append("✅ Boot performance looks good!")

        return suggestions
