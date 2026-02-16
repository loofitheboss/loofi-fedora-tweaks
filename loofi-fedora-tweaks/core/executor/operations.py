"""
Operations Layer - Business logic extracted from UI tabs.
Provides reusable operations for both GUI and CLI.
"""

import logging
import subprocess
import os
import getpass
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)

from core.executor.action_result import ActionResult
from services.system import SystemManager
from utils.commands import PrivilegedCommand


@dataclass
class OperationResult:
    """Result of an operation."""

    success: bool
    message: str
    output: str = ""
    needs_reboot: bool = False


class CleanupOps:
    """Cleanup and maintenance operations."""

    @staticmethod
    def clean_dnf_cache() -> Tuple[str, List[str], str]:
        """Clean DNF package cache."""
        pm = SystemManager.get_package_manager()
        if pm == "rpm-ostree":
            return (
                "pkexec",
                ["rpm-ostree", "cleanup", "--base"],
                "Cleaning rpm-ostree base...",
            )
        return ("pkexec", ["dnf", "clean", "all"], "Cleaning DNF cache...")

    @staticmethod
    def autoremove() -> Tuple[str, List[str], str]:
        """Remove unused packages."""
        pm = SystemManager.get_package_manager()
        if pm == "rpm-ostree":
            return (
                "pkexec",
                ["rpm-ostree", "cleanup", "-m"],
                "Cleaning rpm-ostree metadata...",
            )
        return ("pkexec", ["dnf", "autoremove", "-y"], "Removing unused packages...")

    @staticmethod
    def vacuum_journal(days: int = 14) -> Tuple[str, List[str], str]:
        """Vacuum system journal."""
        return (
            "pkexec",
            ["journalctl", f"--vacuum-time={days}d"],
            f"Vacuuming journal ({days} days)...",
        )

    @staticmethod
    def trim_ssd() -> Tuple[str, List[str], str]:
        """TRIM SSD for performance."""
        return ("pkexec", ["fstrim", "-av"], "Trimming SSD...")

    @staticmethod
    def rebuild_rpmdb() -> Tuple[str, List[str], str]:
        """Rebuild RPM database."""
        return ("pkexec", ["rpm", "--rebuilddb"], "Rebuilding RPM database...")

    @staticmethod
    def list_timeshift() -> Tuple[str, List[str], str]:
        """List Timeshift snapshots."""
        return ("pkexec", ["timeshift", "--list"], "Listing Timeshift snapshots...")


class TweakOps:
    """HP Elitebook specific tweaks."""

    BATTERY_SYSFS = "/sys/class/power_supply/BAT0/charge_control_end_threshold"

    @staticmethod
    def set_power_profile(profile: str) -> Tuple[str, List[str], str]:
        """Set power profile (performance/balanced/power-saver)."""
        valid = ["performance", "balanced", "power-saver"]
        if profile not in valid:
            profile = "balanced"
        return (
            "powerprofilesctl",
            ["set", profile],
            f"Setting power profile to {profile}...",
        )

    @staticmethod
    def get_power_profile() -> str:
        """Get current power profile."""
        try:
            result = subprocess.run(
                ["powerprofilesctl", "get"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get power profile: %s", e)
            return "unknown"

    @staticmethod
    def restart_audio() -> Tuple[str, List[str], str]:
        """Restart Pipewire audio services."""
        return (
            "systemctl",
            ["--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"],
            "Restarting audio services...",
        )

    @staticmethod
    def set_battery_limit(limit: int) -> OperationResult:
        """Set battery charge limit (HP Elitebook)."""
        if not 50 <= limit <= 100:
            return OperationResult(False, "Invalid limit (50-100)")

        if not os.path.exists(TweakOps.BATTERY_SYSFS):
            return OperationResult(
                False, "Battery limit not supported on this hardware"
            )

        try:
            binary, args, desc = PrivilegedCommand.write_file(
                TweakOps.BATTERY_SYSFS, str(limit)
            )
            result = subprocess.run(
                [binary] + args,
                input=str(limit),
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode == 0:
                return OperationResult(True, f"Battery limit set to {limit}%")
            return OperationResult(False, f"Failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return OperationResult(False, str(e))

    @staticmethod
    def install_nbfc() -> Tuple[str, List[str], str]:
        """Install NBFC fan control.

        Note: systemctl enable must be run separately after install.
        """
        result: Tuple[str, List[str], str] = PrivilegedCommand.dnf(
            "install", "nbfc-linux"
        )
        return result

    @staticmethod
    def set_fan_profile(profile: str) -> Tuple[str, List[str], str]:
        """Set NBFC fan profile."""
        return (
            "nbfc",
            ["config", "-a", profile.lower()],
            f"Setting fan profile to {profile}...",
        )


class AdvancedOps:
    """Advanced system optimization operations."""

    @staticmethod
    def apply_dnf_tweaks() -> OperationResult:
        """Optimize DNF configuration.

        Appends max_parallel_downloads and fastestmirror to dnf.conf
        if not already present.
        """
        conf_path = "/etc/dnf/dnf.conf"
        tweaks = {
            "max_parallel_downloads": "max_parallel_downloads=10",
            "fastestmirror": "fastestmirror=True",
        }

        try:
            # Read current config
            try:
                with open(conf_path, "r") as f:
                    content = f.read()
            except (OSError, PermissionError):
                content = ""

            lines_to_add = []
            for key, line in tweaks.items():
                if key not in content:
                    lines_to_add.append(line)

            if not lines_to_add:
                return OperationResult(True, "DNF already optimized")

            append_content = "\n".join(lines_to_add) + "\n"
            result = subprocess.run(
                ["pkexec", "tee", "-a", conf_path],
                input=append_content,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode == 0:
                return OperationResult(True, "DNF optimizations applied")
            return OperationResult(False, f"Failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError, IOError) as e:
            return OperationResult(False, str(e))

    @staticmethod
    def enable_tcp_bbr() -> OperationResult:
        """Enable TCP BBR congestion control."""
        conf_path = "/etc/sysctl.d/99-bbr.conf"
        content = "net.core.default_qdisc=fq\nnet.ipv4.tcp_congestion_control=bbr\n"

        try:
            # Write sysctl config
            result = subprocess.run(
                ["pkexec", "tee", conf_path],
                input=content,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                return OperationResult(
                    False, f"Failed to write config: {result.stderr}"
                )

            # Reload sysctl
            result = subprocess.run(
                ["pkexec", "sysctl", "--system"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode == 0:
                return OperationResult(True, "TCP BBR enabled")
            return OperationResult(False, f"sysctl reload failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return OperationResult(False, str(e))

    @staticmethod
    def install_gamemode() -> OperationResult:
        """Install and configure GameMode."""
        user = getpass.getuser()

        try:
            # Install gamemode
            binary, args, desc = PrivilegedCommand.dnf("install", "gamemode")
            result = subprocess.run(
                [binary] + args,
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
            if result.returncode != 0:
                return OperationResult(False, f"Install failed: {result.stderr}")

            # Add user to gamemode group
            result = subprocess.run(
                ["pkexec", "usermod", "-aG", "gamemode", user],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode == 0:
                return OperationResult(True, f"GameMode installed for {user}")
            return OperationResult(False, f"usermod failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return OperationResult(False, str(e))

    @staticmethod
    def set_swappiness(value: int = 10) -> OperationResult:
        """Set system swappiness value."""
        if not 0 <= value <= 100:
            value = 10
        conf_path = "/etc/sysctl.d/99-swappiness.conf"
        content = f"vm.swappiness={value}\n"

        try:
            # Write sysctl config
            result = subprocess.run(
                ["pkexec", "tee", conf_path],
                input=content,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                return OperationResult(
                    False, f"Failed to write config: {result.stderr}"
                )

            # Reload sysctl
            result = subprocess.run(
                ["pkexec", "sysctl", "--system"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode == 0:
                return OperationResult(True, f"Swappiness set to {value}")
            return OperationResult(False, f"sysctl reload failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return OperationResult(False, str(e))


class NetworkOps:
    """Network configuration operations."""

    DNS_PROVIDERS = {
        "cloudflare": ("1.1.1.1", "1.0.0.1"),
        "google": ("8.8.8.8", "8.8.4.4"),
        "quad9": ("9.9.9.9", "149.112.112.112"),
        "opendns": ("208.67.222.222", "208.67.220.220"),
    }

    @staticmethod
    def set_dns(provider: str) -> OperationResult:
        """Set DNS provider."""
        if provider.lower() not in NetworkOps.DNS_PROVIDERS:
            return OperationResult(False, f"Unknown provider: {provider}")

        primary, secondary = NetworkOps.DNS_PROVIDERS[provider.lower()]

        try:
            # Get active connection
            result = subprocess.run(
                ["nmcli", "-t", "-", "NAME", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            if result.returncode != 0:
                return OperationResult(False, "No active connection found")

            connections = result.stdout.strip().split("\n")
            if not connections:
                return OperationResult(False, "No active connection found")

            conn = connections[0]

            # Set DNS
            dns_cmd = [
                "nmcli",
                "connection",
                "modify",
                conn,
                "ipv4.dns",
                f"{primary} {secondary}",
                "ipv4.ignore-auto-dns",
                "yes",
            ]

            result = subprocess.run(
                dns_cmd, capture_output=True, text=True, check=False, timeout=15
            )
            if result.returncode != 0:
                return OperationResult(False, f"Failed: {result.stderr}")

            # Restart connection
            subprocess.run(
                ["nmcli", "connection", "up", conn],
                capture_output=True,
                check=False,
                timeout=30,
            )

            return OperationResult(
                True, f"DNS set to {provider} ({primary}, {secondary})"
            )

        except (subprocess.SubprocessError, OSError) as e:
            return OperationResult(False, str(e))


def execute_operation(
    op_tuple: Tuple[str, List[str], str],
    *,
    preview: bool = False,
) -> ActionResult:
    """
    Execute a tuple-style operation through the centralized ActionExecutor.

    Bridges existing (command, args, status) tuples to v19.0 ActionResult.
    Use this for CLI and headless execution paths.
    GUI paths continue using CommandRunner + QProcess.
    """
    from core.executor.action_executor import ActionExecutor

    command, args, _status = op_tuple
    pkexec = command == "pkexec"
    if pkexec:
        command = args[0]
        args = args[1:]
    return ActionExecutor.run(command, args, preview=preview, pkexec=pkexec)


# CLI command registry for future use
CLI_COMMANDS = {
    "cleanup": {
        "dnf": CleanupOps.clean_dnf_cache,
        "autoremove": CleanupOps.autoremove,
        "journal": CleanupOps.vacuum_journal,
        "trim": CleanupOps.trim_ssd,
        "rpmdb": CleanupOps.rebuild_rpmdb,
    },
    "tweak": {
        "power": TweakOps.set_power_profile,
        "audio": TweakOps.restart_audio,
        "battery": TweakOps.set_battery_limit,
    },
    "advanced": {
        "dnf-tweaks": AdvancedOps.apply_dnf_tweaks,
        "bbr": AdvancedOps.enable_tcp_bbr,
        "gamemode": AdvancedOps.install_gamemode,
        "swappiness": AdvancedOps.set_swappiness,
    },
    "network": {
        "dns": NetworkOps.set_dns,
    },
}
