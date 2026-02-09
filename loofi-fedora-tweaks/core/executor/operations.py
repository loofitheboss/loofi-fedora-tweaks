"""
Operations Layer - Business logic extracted from UI tabs.
Provides reusable operations for both GUI and CLI.
"""

import subprocess
import os
import getpass
from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable
from pathlib import Path

from utils.system import SystemManager


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
            return ("pkexec", ["rpm-ostree", "cleanup", "--base"], "Cleaning rpm-ostree base...")
        return ("pkexec", ["dnf", "clean", "all"], "Cleaning DNF cache...")
    
    @staticmethod
    def autoremove() -> Tuple[str, List[str], str]:
        """Remove unused packages."""
        pm = SystemManager.get_package_manager()
        if pm == "rpm-ostree":
            return ("pkexec", ["rpm-ostree", "cleanup", "-m"], "Cleaning rpm-ostree metadata...")
        return ("pkexec", ["dnf", "autoremove", "-y"], "Removing unused packages...")
    
    @staticmethod
    def vacuum_journal(days: int = 14) -> Tuple[str, List[str], str]:
        """Vacuum system journal."""
        return ("pkexec", ["journalctl", f"--vacuum-time={days}d"], f"Vacuuming journal ({days} days)...")
    
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
        return ("powerprofilesctl", ["set", profile], f"Setting power profile to {profile}...")
    
    @staticmethod
    def get_power_profile() -> str:
        """Get current power profile."""
        try:
            result = subprocess.run(
                ["powerprofilesctl", "get"],
                capture_output=True, text=True, check=False
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
    
    @staticmethod
    def restart_audio() -> Tuple[str, List[str], str]:
        """Restart Pipewire audio services."""
        return ("systemctl", ["--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"], 
                "Restarting audio services...")
    
    @staticmethod
    def set_battery_limit(limit: int) -> OperationResult:
        """Set battery charge limit (HP Elitebook)."""
        if not 50 <= limit <= 100:
            return OperationResult(False, "Invalid limit (50-100)")
        
        if not os.path.exists(TweakOps.BATTERY_SYSFS):
            return OperationResult(False, "Battery limit not supported on this hardware")
        
        try:
            cmd = f"echo {limit} > {TweakOps.BATTERY_SYSFS}"
            result = subprocess.run(
                ["pkexec", "sh", "-c", cmd],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return OperationResult(True, f"Battery limit set to {limit}%")
            return OperationResult(False, f"Failed: {result.stderr}")
        except Exception as e:
            return OperationResult(False, str(e))
    
    @staticmethod
    def install_nbfc() -> Tuple[str, List[str], str]:
        """Install NBFC fan control."""
        return ("pkexec", ["sh", "-c", "dnf install -y nbfc-linux && systemctl enable --now nbfc_service"],
                "Installing nbfc-linux...")
    
    @staticmethod
    def set_fan_profile(profile: str) -> Tuple[str, List[str], str]:
        """Set NBFC fan profile."""
        return ("nbfc", ["config", "-a", profile.lower()], f"Setting fan profile to {profile}...")


class AdvancedOps:
    """Advanced system optimization operations."""
    
    @staticmethod
    def apply_dnf_tweaks() -> Tuple[str, List[str], str]:
        """Optimize DNF configuration."""
        cmd = ("grep -q 'max_parallel_downloads' /etc/dnf/dnf.conf || "
               "echo 'max_parallel_downloads=10' >> /etc/dnf/dnf.conf; "
               "grep -q 'fastestmirror' /etc/dnf/dnf.conf || "
               "echo 'fastestmirror=True' >> /etc/dnf/dnf.conf")
        return ("pkexec", ["sh", "-c", cmd], "Applying DNF optimizations...")
    
    @staticmethod
    def enable_tcp_bbr() -> Tuple[str, List[str], str]:
        """Enable TCP BBR congestion control."""
        cmd = ("echo 'net.core.default_qdisc=fq' > /etc/sysctl.d/99-bbr.conf && "
               "echo 'net.ipv4.tcp_congestion_control=bbr' >> /etc/sysctl.d/99-bbr.conf && "
               "sysctl --system")
        return ("pkexec", ["sh", "-c", cmd], "Enabling TCP BBR...")
    
    @staticmethod
    def install_gamemode() -> Tuple[str, List[str], str]:
        """Install and configure GameMode."""
        user = getpass.getuser()
        cmd = f"dnf install -y gamemode && usermod -aG gamemode {user}"
        return ("pkexec", ["sh", "-c", cmd], f"Installing GameMode for {user}...")
    
    @staticmethod
    def set_swappiness(value: int = 10) -> Tuple[str, List[str], str]:
        """Set system swappiness value."""
        if not 0 <= value <= 100:
            value = 10
        cmd = f"echo 'vm.swappiness={value}' > /etc/sysctl.d/99-swappiness.conf && sysctl --system"
        return ("pkexec", ["sh", "-c", cmd], f"Setting swappiness to {value}...")


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
                ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
                capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                return OperationResult(False, "No active connection found")
            
            connections = result.stdout.strip().split("\n")
            if not connections:
                return OperationResult(False, "No active connection found")
            
            conn = connections[0]
            
            # Set DNS
            dns_cmd = ["nmcli", "connection", "modify", conn, 
                      f"ipv4.dns", f"{primary} {secondary}",
                      "ipv4.ignore-auto-dns", "yes"]
            
            result = subprocess.run(dns_cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                return OperationResult(False, f"Failed: {result.stderr}")
            
            # Restart connection
            subprocess.run(["nmcli", "connection", "up", conn], 
                          capture_output=True, check=False)
            
            return OperationResult(True, f"DNS set to {provider} ({primary}, {secondary})")
            
        except Exception as e:
            return OperationResult(False, str(e))


def execute_operation(
    op_tuple: Tuple[str, List[str], str],
    *,
    preview: bool = False,
) -> "ActionResult":
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
