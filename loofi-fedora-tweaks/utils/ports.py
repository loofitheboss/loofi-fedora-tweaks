"""
Port Auditor - Network port security scanner.
Part of v8.5 "Sentinel" update.

Scans open ports, identifies listening services,
and provides firewall management via firewall-cmd.
"""

import logging
import subprocess
import shutil
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Operation result."""
    success: bool
    message: str
    data: Optional[dict] = None


@dataclass
class OpenPort:
    """Represents an open network port."""
    protocol: str  # tcp, udp
    port: int
    address: str
    process: str
    pid: int
    is_risky: bool = False
    risk_reason: str = ""


class PortAuditor:
    """
    Scans and audits open network ports.

    Features:
    - List all listening ports
    - Identify risky services
    - Close ports via firewall
    """

    # Known risky ports/services
    RISKY_PORTS = {
        22: ("SSH", "Remote access - ensure key auth only"),
        23: ("Telnet", "CRITICAL: Unencrypted, disable immediately"),
        21: ("FTP", "Unencrypted file transfer"),
        3306: ("MySQL", "Database exposed to network"),
        5432: ("PostgreSQL", "Database exposed to network"),
        27017: ("MongoDB", "Database - often unauth by default"),
        6379: ("Redis", "Cache - often unauth by default"),
        8080: ("HTTP Alt", "Common development server"),
        5900: ("VNC", "Remote desktop - ensure auth"),
        3389: ("RDP", "Windows remote desktop"),
        1433: ("MSSQL", "SQL Server exposed"),
        11211: ("Memcached", "Cache - often unauth"),
    }

    @classmethod
    def scan_ports(cls) -> list[OpenPort]:
        """
        Scan all open listening ports.
        Uses ss (socket statistics) for accuracy.
        """
        ports = []

        try:
            # ss -tulwn: TCP/UDP listening with numeric ports
            result = subprocess.run(
                ["ss", "-tulwn"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 5:
                    continue

                protocol = parts[0].lower()
                local_addr = parts[4]

                # Parse address:port
                if ":" in local_addr:
                    addr_parts = local_addr.rsplit(":", 1)
                    address = addr_parts[0]
                    try:
                        port = int(addr_parts[1])
                    except ValueError:
                        continue
                else:
                    continue

                # Get process info
                process = "unknown"
                pid = 0

                # Check if risky
                is_risky = False
                risk_reason = ""

                if port in cls.RISKY_PORTS:
                    is_risky = True
                    risk_reason = cls.RISKY_PORTS[port][1]

                # World-exposed is risky
                if address in ["0.0.0.0", "*", "[::]", "::"]:
                    if port in cls.RISKY_PORTS:
                        is_risky = True
                        risk_reason = f"{cls.RISKY_PORTS[port][0]}: {cls.RISKY_PORTS[port][1]}"

                ports.append(OpenPort(
                    protocol=protocol.replace("tcp", "TCP").replace("udp", "UDP"),
                    port=port,
                    address=address,
                    process=process,
                    pid=pid,
                    is_risky=is_risky,
                    risk_reason=risk_reason
                ))

            # Enhance with process info from ss -tulpn (requires sudo)
            cls._enhance_with_process_info(ports)

            return ports

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Port scan failed: %s", e)
            return []

    @classmethod
    def _enhance_with_process_info(cls, ports: list[OpenPort]):
        """Add process information to ports (best effort)."""
        try:
            result = subprocess.run(
                ["ss", "-tulpn"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return

            for line in result.stdout.strip().split("\n")[1:]:
                if not line.strip():
                    continue

                # Look for pattern: users:(("process",pid=123,...))
                match = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
                if match:
                    process_name = match.group(1)
                    pid = int(match.group(2))

                    # Match to port
                    parts = line.split()
                    if len(parts) >= 5:
                        local_addr = parts[4]
                        if ":" in local_addr:
                            try:
                                port_num = int(local_addr.rsplit(":", 1)[1])
                                for p in ports:
                                    if p.port == port_num:
                                        p.process = process_name
                                        p.pid = pid
                                        break
                            except ValueError:
                                pass

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to enhance port info: %s", e)

    @classmethod
    def get_risky_ports(cls) -> list[OpenPort]:
        """Get only risky open ports."""
        return [p for p in cls.scan_ports() if p.is_risky]

    @classmethod
    def is_firewalld_running(cls) -> bool:
        """Check if firewalld is running."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "firewalld"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check firewalld status: %s", e)
            return False

    @classmethod
    def block_port(cls, port: int, protocol: str = "tcp") -> Result:
        """
        Block a port using firewall-cmd.

        Args:
            port: Port number to block
            protocol: tcp or udp
        """
        if not shutil.which("firewall-cmd"):
            return Result(False, "firewall-cmd not found")

        if not cls.is_firewalld_running():
            return Result(False, "firewalld is not running")

        try:
            # Remove from allowed (if present) and add to blocked
            subprocess.run(
                ["pkexec", "firewall-cmd", "--remove-port",
                 f"{port}/{protocol}", "--permanent"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Reload firewall
            subprocess.run(
                ["pkexec", "firewall-cmd", "--reload"],
                capture_output=True,
                text=True,
                timeout=30
            )

            return Result(True, f"Port {port}/{protocol} blocked")

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def allow_port(cls, port: int, protocol: str = "tcp") -> Result:
        """
        Allow a port using firewall-cmd.

        Args:
            port: Port number to allow
            protocol: tcp or udp
        """
        if not shutil.which("firewall-cmd"):
            return Result(False, "firewall-cmd not found")

        if not cls.is_firewalld_running():
            return Result(False, "firewalld is not running")

        try:
            result = subprocess.run(
                ["pkexec", "firewall-cmd", "--add-port",
                 f"{port}/{protocol}", "--permanent"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return Result(False, f"Failed: {result.stderr}")

            # Reload firewall
            subprocess.run(
                ["pkexec", "firewall-cmd", "--reload"],
                capture_output=True,
                text=True,
                timeout=30
            )

            return Result(True, f"Port {port}/{protocol} allowed")

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def get_firewall_status(cls) -> dict:
        """Get firewall status and open ports."""
        status = {
            "running": False,
            "default_zone": "unknown",
            "allowed_ports": [],
            "allowed_services": []
        }

        if not cls.is_firewalld_running():
            return status

        status["running"] = True

        try:
            # Get default zone
            result = subprocess.run(
                ["firewall-cmd", "--get-default-zone"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                status["default_zone"] = result.stdout.strip()

            # Get allowed ports
            result = subprocess.run(
                ["firewall-cmd", "--list-ports"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                status["allowed_ports"] = result.stdout.strip().split()

            # Get allowed services
            result = subprocess.run(
                ["firewall-cmd", "--list-services"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                status["allowed_services"] = result.stdout.strip().split()

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get firewall status: %s", e)

        return status

    @classmethod
    def get_security_score(cls) -> dict:
        """
        Calculate a simple security score based on open ports.

        Returns score from 0-100 and recommendations.
        """
        ports = cls.scan_ports()
        risky = [p for p in ports if p.is_risky]

        # Start with 100, deduct for issues
        score = 100
        recommendations = []

        # Deduct for each risky port
        for p in risky:
            if p.port == 23:  # Telnet is critical
                score -= 30
                recommendations.append(f"CRITICAL: Disable Telnet on port {p.port}")
            elif p.port in [3306, 5432, 27017, 6379]:  # Databases
                score -= 15
                recommendations.append(f"Database {p.process} on port {p.port} exposed")
            else:
                score -= 10
                recommendations.append(f"Review {p.process} on port {p.port}: {p.risk_reason}")

        # Check if firewall is running
        if not cls.is_firewalld_running():
            score -= 20
            recommendations.append("Firewall is not running!")

        score = max(0, score)

        return {
            "score": score,
            "open_ports": len(ports),
            "risky_ports": len(risky),
            "recommendations": recommendations,
            "rating": "Excellent" if score >= 90 else
            "Good" if score >= 70 else
            "Fair" if score >= 50 else "Poor"
        }
