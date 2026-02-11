"""
Firewall Manager — firewalld GUI backend.
Part of v16.0 "Horizon".

Provides a clean interface to firewall-cmd for managing zones,
ports, services, and rich rules.
"""

import subprocess
import logging
from dataclasses import dataclass, field
from typing import List

from utils.commands import PrivilegedCommand

logger = logging.getLogger(__name__)


@dataclass
class FirewallInfo:
    """Snapshot of the current firewall state."""
    running: bool = False
    default_zone: str = ""
    active_zones: dict = field(default_factory=dict)   # zone -> [interfaces]
    ports: List[str] = field(default_factory=list)       # ["80/tcp", ...]
    services: List[str] = field(default_factory=list)    # ["ssh", "http", ...]
    rich_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "default_zone": self.default_zone,
            "active_zones": self.active_zones,
            "ports": self.ports,
            "services": self.services,
            "rich_rules": self.rich_rules,
        }


@dataclass
class FirewallResult:
    """Result of a firewall operation."""
    success: bool
    message: str


class FirewallManager:
    """Interface to firewalld via firewall-cmd.

    Read operations run directly (no pkexec needed for queries).
    Write operations go through pkexec.
    """

    # ------------------------------------------------------------ status
    @classmethod
    def is_available(cls) -> bool:
        """Check if firewall-cmd is installed."""
        try:
            result = subprocess.run(
                ["firewall-cmd", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    @classmethod
    def is_running(cls) -> bool:
        """Check if firewalld is running."""
        try:
            result = subprocess.run(
                ["firewall-cmd", "--state"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == "running"
        except (OSError, subprocess.TimeoutExpired):
            return False

    # ------------------------------------------------------------ info
    @classmethod
    def get_status(cls) -> FirewallInfo:
        """Get comprehensive firewall status."""
        info = FirewallInfo()
        info.running = cls.is_running()
        if not info.running:
            return info

        info.default_zone = cls.get_default_zone()
        info.active_zones = cls.get_active_zones()
        info.ports = cls.list_ports()
        info.services = cls.list_services()
        info.rich_rules = cls.list_rich_rules()
        return info

    @classmethod
    def get_default_zone(cls) -> str:
        """Get the default firewall zone."""
        try:
            result = subprocess.run(
                ["firewall-cmd", "--get-default-zone"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""

    @classmethod
    def get_zones(cls) -> List[str]:
        """List all available zones."""
        try:
            result = subprocess.run(
                ["firewall-cmd", "--get-zones"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split()
            return []
        except (OSError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def get_active_zones(cls) -> dict:
        """Get active zones with their interfaces.

        Returns:
            Dict mapping zone name to list of interfaces.
        """
        try:
            result = subprocess.run(
                ["firewall-cmd", "--get-active-zones"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return {}

            zones = {}
            current_zone = None
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("interfaces:") or line.startswith("sources:"):
                    if current_zone:
                        ifaces = line.split(":", 1)[1].strip().split()
                        zones.setdefault(current_zone, []).extend(ifaces)
                else:
                    current_zone = line
                    zones.setdefault(current_zone, [])
            return zones

        except (OSError, subprocess.TimeoutExpired):
            return {}

    # ------------------------------------------------------------ ports
    @classmethod
    def list_ports(cls, zone: str = "") -> List[str]:
        """List open ports in a zone (default zone if empty)."""
        try:
            cmd = ["firewall-cmd", "--list-ports"]
            if zone:
                cmd.extend(["--zone", zone])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split()
            return []
        except (OSError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def open_port(cls, port: str, protocol: str = "tcp",
                  zone: str = "", permanent: bool = True) -> FirewallResult:
        """Open a port.

        Args:
            port: Port number or range (e.g. "8080" or "8000-8100").
            protocol: "tcp" or "udp".
            zone: Zone name (default zone if empty).
            permanent: Make change persistent across reboots.
        """
        port_spec = f"{port}/{protocol}"
        try:
            cmd = ["pkexec", "firewall-cmd", f"--add-port={port_spec}"]
            if zone:
                cmd.extend(["--zone", zone])
            if permanent:
                cmd.append("--permanent")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                if permanent:
                    cls._reload()
                return FirewallResult(True, f"Opened port {port_spec}")
            else:
                return FirewallResult(
                    False, f"Failed to open {port_spec}: {result.stderr.strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    @classmethod
    def close_port(cls, port: str, protocol: str = "tcp",
                   zone: str = "", permanent: bool = True) -> FirewallResult:
        """Close a port."""
        port_spec = f"{port}/{protocol}"
        try:
            cmd = ["pkexec", "firewall-cmd", f"--remove-port={port_spec}"]
            if zone:
                cmd.extend(["--zone", zone])
            if permanent:
                cmd.append("--permanent")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                if permanent:
                    cls._reload()
                return FirewallResult(True, f"Closed port {port_spec}")
            else:
                return FirewallResult(
                    False, f"Failed to close {port_spec}: {result.stderr.strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    # ----------------------------------------------------------- services
    @classmethod
    def list_services(cls, zone: str = "") -> List[str]:
        """List allowed services in a zone."""
        try:
            cmd = ["firewall-cmd", "--list-services"]
            if zone:
                cmd.extend(["--zone", zone])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return sorted(result.stdout.strip().split())
            return []
        except (OSError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def get_available_services(cls) -> List[str]:
        """List all service definitions known to firewalld."""
        try:
            result = subprocess.run(
                ["firewall-cmd", "--get-services"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return sorted(result.stdout.strip().split())
            return []
        except (OSError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def add_service(cls, service: str, zone: str = "",
                    permanent: bool = True) -> FirewallResult:
        """Allow a service through the firewall."""
        try:
            cmd = ["pkexec", "firewall-cmd", f"--add-service={service}"]
            if zone:
                cmd.extend(["--zone", zone])
            if permanent:
                cmd.append("--permanent")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                if permanent:
                    cls._reload()
                return FirewallResult(True, f"Added service {service}")
            else:
                return FirewallResult(
                    False, f"Failed to add {service}: {result.stderr.strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    @classmethod
    def remove_service(cls, service: str, zone: str = "",
                       permanent: bool = True) -> FirewallResult:
        """Remove a service from the firewall."""
        try:
            cmd = ["pkexec", "firewall-cmd", f"--remove-service={service}"]
            if zone:
                cmd.extend(["--zone", zone])
            if permanent:
                cmd.append("--permanent")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                if permanent:
                    cls._reload()
                return FirewallResult(True, f"Removed service {service}")
            else:
                return FirewallResult(
                    False, f"Failed to remove {service}: {result.stderr.strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    # -------------------------------------------------------- rich rules
    @classmethod
    def list_rich_rules(cls, zone: str = "") -> List[str]:
        """List rich rules in a zone."""
        try:
            cmd = ["firewall-cmd", "--list-rich-rules"]
            if zone:
                cmd.extend(["--zone", zone])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()
            return []
        except (OSError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def add_rich_rule(cls, rule: str, zone: str = "",
                      permanent: bool = True) -> FirewallResult:
        """Add a rich rule."""
        try:
            cmd = ["pkexec", "firewall-cmd", f"--add-rich-rule={rule}"]
            if zone:
                cmd.extend(["--zone", zone])
            if permanent:
                cmd.append("--permanent")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                if permanent:
                    cls._reload()
                return FirewallResult(True, "Added rich rule")
            else:
                return FirewallResult(
                    False, f"Failed to add rule: {result.stderr.strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    @classmethod
    def remove_rich_rule(cls, rule: str, zone: str = "",
                         permanent: bool = True) -> FirewallResult:
        """Remove a rich rule."""
        try:
            cmd = ["pkexec", "firewall-cmd", f"--remove-rich-rule={rule}"]
            if zone:
                cmd.extend(["--zone", zone])
            if permanent:
                cmd.append("--permanent")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                if permanent:
                    cls._reload()
                return FirewallResult(True, "Removed rich rule")
            else:
                return FirewallResult(
                    False, f"Failed to remove rule: {result.stderr.strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    # ----------------------------------------------------- toggle firewall
    @classmethod
    def start_firewall(cls) -> FirewallResult:
        """Start firewalld."""
        try:
            binary, args, _ = PrivilegedCommand.systemctl("start", "firewalld")
            result = subprocess.run(
                [binary] + args, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return FirewallResult(True, "Firewall started")
            return FirewallResult(False, f"Failed: {result.stderr.strip()}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    @classmethod
    def stop_firewall(cls) -> FirewallResult:
        """Stop firewalld."""
        try:
            binary, args, _ = PrivilegedCommand.systemctl("stop", "firewalld")
            result = subprocess.run(
                [binary] + args, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return FirewallResult(True, "Firewall stopped")
            return FirewallResult(False, f"Failed: {result.stderr.strip()}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    # ----------------------------------------------------------- zone mgmt
    @classmethod
    def set_default_zone(cls, zone: str) -> FirewallResult:
        """Set the default firewall zone."""
        try:
            cmd = ["pkexec", "firewall-cmd", f"--set-default-zone={zone}"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return FirewallResult(True, f"Default zone set to {zone}")
            return FirewallResult(
                False, f"Failed: {result.stderr.strip()}"
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallResult(False, f"Error: {exc}")

    # ----------------------------------------------------------- internal
    @classmethod
    def _reload(cls) -> bool:
        """Reload firewalld to apply permanent changes."""
        try:
            result = subprocess.run(
                ["pkexec", "firewall-cmd", "--reload"],
                capture_output=True, text=True, timeout=15
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
