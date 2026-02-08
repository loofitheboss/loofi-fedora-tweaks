"""
mDNS-based LAN device discovery for Loofi Link.
Part of v12.0 "Sovereign Update".

Discovers other Loofi instances on the local network using Avahi/mDNS,
registers this device as a service, and provides peer connectivity checks.
"""

import os
import shutil
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from utils.containers import Result


SERVICE_TYPE = "_loofi._tcp.local."
SERVICE_PORT = 53317  # Same as LocalSend for compatibility
BROADCAST_INTERVAL = 30  # seconds

CONFIG_DIR = os.path.expanduser("~/.config/loofi-fedora-tweaks")
DEVICE_ID_FILE = os.path.join(CONFIG_DIR, "device_id")


@dataclass
class PeerDevice:
    """Represents a discovered peer on the local network."""
    name: str              # hostname or user-set name
    address: str           # IP address
    port: int              # service port
    device_id: str         # unique device identifier
    platform: str          # "linux", "android", etc.
    version: str           # Loofi version
    last_seen: float       # timestamp
    capabilities: list = field(default_factory=list)  # ["clipboard", "filedrop", "teleport"]


class MeshDiscovery:
    """mDNS-based LAN device discovery for finding other Loofi instances."""

    _publish_process: Optional[subprocess.Popen] = None

    @staticmethod
    def get_device_id() -> str:
        """Generate or load a persistent UUID from the config directory.

        Returns:
            A stable UUID string unique to this device installation.
        """
        if os.path.isfile(DEVICE_ID_FILE):
            with open(DEVICE_ID_FILE, "r") as fh:
                device_id = fh.read().strip()
                if device_id:
                    return device_id

        # Generate new ID and persist it
        os.makedirs(CONFIG_DIR, exist_ok=True)
        device_id = str(uuid.uuid4())
        with open(DEVICE_ID_FILE, "w") as fh:
            fh.write(device_id)
        return device_id

    @staticmethod
    def get_device_name() -> str:
        """Return the hostname of this machine.

        Returns:
            The hostname string.
        """
        return socket.gethostname()

    @staticmethod
    def get_local_ips() -> list:
        """Return non-loopback IPv4 addresses for this machine.

        Uses a UDP connect trick to discover the default route address,
        then falls back to hostname resolution.

        Returns:
            List of IPv4 address strings.
        """
        ips = []

        # Method 1: UDP connect to external address (no traffic sent)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.1)
            sock.connect(("8.8.8.8", 80))
            addr = sock.getsockname()[0]
            sock.close()
            if addr and addr != "0.0.0.0" and not addr.startswith("127."):
                ips.append(addr)
        except (OSError, socket.error):
            pass

        # Method 2: hostname resolution
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                addr = info[4][0]
                if not addr.startswith("127.") and addr not in ips:
                    ips.append(addr)
        except (socket.gaierror, OSError):
            pass

        return ips

    @staticmethod
    def is_avahi_available() -> bool:
        """Check whether avahi-browse is installed.

        Returns:
            True if avahi-browse is on PATH.
        """
        return shutil.which("avahi-browse") is not None

    @classmethod
    def discover_peers(cls, timeout: int = 5) -> list:
        """Discover Loofi peers on the LAN via avahi-browse.

        Parses the avahi-browse ``--resolve --parsable --terminate`` output
        into PeerDevice objects.

        Args:
            timeout: Maximum seconds to wait for avahi-browse.

        Returns:
            List of PeerDevice objects found on the network.
        """
        if not cls.is_avahi_available():
            return []

        try:
            result = subprocess.run(
                [
                    "avahi-browse",
                    "--resolve",
                    "--parsable",
                    "--terminate",
                    SERVICE_TYPE,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []

        if result.returncode != 0:
            return []

        peers = []
        now = time.time()

        for line in result.stdout.splitlines():
            # Resolved lines start with '=' and have >=9 fields
            if not line.startswith("="):
                continue
            parts = line.split(";")
            if len(parts) < 10:
                continue

            # parts: =;iface;proto;name;type;domain;hostname;address;port;txt
            address = parts[7]
            try:
                port = int(parts[8])
            except (ValueError, IndexError):
                port = SERVICE_PORT

            # Parse TXT record (remaining fields joined)
            txt_raw = ";".join(parts[9:])
            txt_fields = cls._parse_txt_record(txt_raw)

            peer = PeerDevice(
                name=txt_fields.get("name", parts[3]),
                address=address,
                port=port,
                device_id=txt_fields.get("device_id", ""),
                platform=txt_fields.get("platform", "unknown"),
                version=txt_fields.get("version", ""),
                last_seen=now,
                capabilities=txt_fields.get("capabilities", "").split(",") if txt_fields.get("capabilities") else [],
            )
            peers.append(peer)

        return peers

    @classmethod
    def register_service(cls) -> Result:
        """Register this device as an mDNS service via avahi-publish.

        Returns:
            Result indicating success or failure.
        """
        if not shutil.which("avahi-publish"):
            return Result(success=False, message="avahi-publish is not installed.")

        if cls._publish_process is not None:
            return Result(success=False, message="Service is already registered.")

        info = cls.build_service_info()
        txt_args = []
        for key, value in info.items():
            txt_args.append(f"{key}={value}")

        cmd = [
            "avahi-publish",
            "--service",
            MeshDiscovery.get_device_name(),
            SERVICE_TYPE,
            str(SERVICE_PORT),
        ] + txt_args

        try:
            cls._publish_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return Result(success=True, message="mDNS service registered.")
        except Exception as exc:
            cls._publish_process = None
            return Result(success=False, message=f"Failed to register service: {exc}")

    @classmethod
    def unregister_service(cls) -> Result:
        """Stop the avahi-publish process to unregister the mDNS service.

        Returns:
            Result indicating success or failure.
        """
        if cls._publish_process is None:
            return Result(success=False, message="No service is currently registered.")

        try:
            cls._publish_process.terminate()
            cls._publish_process.wait(timeout=5)
            cls._publish_process = None
            return Result(success=True, message="mDNS service unregistered.")
        except Exception as exc:
            cls._publish_process = None
            return Result(success=False, message=f"Failed to unregister service: {exc}")

    @classmethod
    def build_service_info(cls) -> dict:
        """Build TXT record fields for mDNS service advertisement.

        Returns:
            Dict of key-value pairs for the TXT record.
        """
        from version import __version__

        return {
            "device_id": cls.get_device_id(),
            "version": __version__,
            "platform": "linux",
            "name": cls.get_device_name(),
            "capabilities": "clipboard,filedrop,teleport",
        }

    @staticmethod
    def is_peer_alive(peer: PeerDevice) -> bool:
        """Quick TCP connect test to check if a peer is reachable.

        Args:
            peer: The PeerDevice to check.

        Returns:
            True if a TCP connection can be established.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((peer.address, peer.port))
            sock.close()
            return True
        except (OSError, socket.error):
            return False

    @staticmethod
    def _parse_txt_record(raw: str) -> dict:
        """Parse avahi TXT record string into a dict.

        Args:
            raw: The raw TXT record section from avahi-browse.

        Returns:
            Dict of key=value pairs extracted from the record.
        """
        fields = {}
        # TXT records look like: "key1=val1" "key2=val2"
        raw = raw.strip().strip('"')
        for part in raw.split('" "'):
            part = part.strip('"')
            if "=" in part:
                key, _, value = part.partition("=")
                fields[key.strip()] = value.strip()
        return fields
