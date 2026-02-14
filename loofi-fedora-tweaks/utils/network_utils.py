"""
Network utility functions for nmcli-based operations.

Extracted from ui/network_tab.py in v34.0 to enforce the
'no subprocess in UI' architectural rule.
"""

import subprocess
from typing import List, Optional, Tuple

from utils.log import get_logger

logger = get_logger(__name__)


class NetworkUtils:
    """Static utility methods for NetworkManager (nmcli) operations."""

    @staticmethod
    def scan_wifi() -> List[Tuple[str, str, str, str]]:
        """Scan for available WiFi networks via nmcli.

        Returns:
            List of (ssid, signal, security, active_status) tuples.
        """
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,ACTIVE",
                 "device", "wifi", "list", "--rescan", "yes"],
                capture_output=True, text=True, timeout=15
            )
            rows: List[Tuple[str, str, str, str]] = []
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split(":")
                if len(parts) >= 4:
                    ssid = parts[0] or "(Hidden)"
                    signal = f"{parts[1]}%"
                    security = parts[2] or "Open"
                    active = "Connected" if parts[3] == "yes" else ""
                    rows.append((ssid, signal, security, active))
            return rows
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("WiFi scan failed: %s", e)
            return []

    @staticmethod
    def load_vpn_connections() -> List[Tuple[str, str, str]]:
        """Load VPN connections from NetworkManager.

        Returns:
            List of (name, type, status) tuples.
        """
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,ACTIVE", "connection", "show"],
                capture_output=True, text=True, timeout=5
            )
            rows: List[Tuple[str, str, str]] = []
            for line in result.stdout.strip().splitlines():
                lower = line.lower()
                if "vpn" in lower or "wireguard" in lower or "openvpn" in lower:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        name = parts[0]
                        conn_type = parts[1]
                        status = "🟢 Active" if parts[2] == "yes" else "Inactive"
                        rows.append((name, conn_type, status))
            return rows
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to load VPN: %s", e)
            return []

    @staticmethod
    def detect_current_dns() -> str:
        """Detect current DNS servers from NetworkManager.

        Returns:
            Comma-separated DNS servers, or descriptive fallback string.
        """
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "IP4.DNS", "device", "show"],
                capture_output=True, text=True, timeout=5
            )
            dns_servers = set()
            for line in result.stdout.splitlines():
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        dns_servers.add(val)
            if dns_servers:
                return ", ".join(sorted(dns_servers))
            return ""
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to detect DNS: %s", e)
            return ""

    @staticmethod
    def get_active_connection() -> Optional[str]:
        """Return the connection name of the active WiFi or Ethernet connection."""
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
                capture_output=True, text=True, timeout=5
            )
            for line in res.stdout.splitlines():
                if "wifi" in line or "ethernet" in line:
                    return line.split(":")[0]
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get active connection: %s", e)
        return None

    @staticmethod
    def check_hostname_privacy(connection_name: str) -> Optional[bool]:
        """Check if hostname is hidden from DHCP broadcasts.

        Returns:
            True if hidden, False if visible, None on error.
        """
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "ipv4.dhcp-send-hostname",
                 "connection", "show", connection_name],
                capture_output=True, text=True, timeout=5
            )
            val = result.stdout.strip().split(":")[-1].strip() if result.stdout.strip() else ""
            return val == "no"
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check hostname privacy: %s", e)
            return None

    @staticmethod
    def reactivate_connection(connection_name: str) -> bool:
        """Reactivate a NetworkManager connection (e.g. after DNS change).

        Returns:
            True on success, False on failure.
        """
        try:
            subprocess.run(
                ["nmcli", "con", "up", connection_name],
                capture_output=True, timeout=10
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to reactivate connection: %s", e)
            return False
