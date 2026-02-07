"""
Network Monitor - Per-interface and per-application network traffic tracking.
Part of v9.2 "Pulse" update.

Reads traffic stats from /proc/net/dev, interface state from /sys/class/net,
and active connections from /proc/net/tcp{,6} and /proc/net/udp{,6}.
No external dependencies (no psutil).
"""

import os
import socket
import struct
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class InterfaceStats:
    """Traffic statistics for a single network interface."""
    name: str           # e.g., "wlp2s0", "enp3s0"
    type: str           # "wifi", "ethernet", "loopback", "vpn", "other"
    is_up: bool
    ip_address: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    send_rate: float    # bytes/sec (0 on first call)
    recv_rate: float    # bytes/sec (0 on first call)

    @property
    def bytes_sent_human(self) -> str:
        return NetworkMonitor.bytes_to_human(self.bytes_sent)

    @property
    def bytes_recv_human(self) -> str:
        return NetworkMonitor.bytes_to_human(self.bytes_recv)

    @property
    def send_rate_human(self) -> str:
        return f"{NetworkMonitor.bytes_to_human(self.send_rate)}/s"

    @property
    def recv_rate_human(self) -> str:
        return f"{NetworkMonitor.bytes_to_human(self.recv_rate)}/s"


@dataclass
class ConnectionInfo:
    """A single active network connection."""
    protocol: str       # "tcp", "udp", "tcp6", "udp6"
    local_addr: str
    local_port: int
    remote_addr: str
    remote_port: int
    state: str          # "ESTABLISHED", "LISTEN", etc.
    pid: int
    process_name: str


class NetworkMonitor:
    """
    Monitors network interfaces and active connections.

    Reads all data from /proc and /sys -- no external dependencies.
    Rate calculation uses class-level state to track deltas between calls.
    """

    # Previous readings for rate calculation: {iface_name: (timestamp, bytes_sent, bytes_recv)}
    _previous_readings: Dict[str, Tuple[float, int, int]] = {}

    # TCP connection states mapped from the hex value in /proc/net/tcp
    _TCP_STATES = {
        "01": "ESTABLISHED",
        "02": "SYN_SENT",
        "03": "SYN_RECV",
        "04": "FIN_WAIT1",
        "05": "FIN_WAIT2",
        "06": "TIME_WAIT",
        "07": "CLOSE",
        "08": "CLOSE_WAIT",
        "09": "LAST_ACK",
        "0A": "LISTEN",
        "0B": "CLOSING",
    }

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    @classmethod
    def get_all_interfaces(cls) -> List[InterfaceStats]:
        """
        Return traffic statistics for every network interface.

        Reads counters from /proc/net/dev, link state from
        /sys/class/net/<iface>/operstate, and classifies type by
        name pattern and /sys/class/net/<iface>/type.

        Returns:
            List of InterfaceStats, one per interface.  Empty list on error.
        """
        raw_stats = cls._read_proc_net_dev()
        if not raw_stats:
            return []

        now = time.monotonic()
        results: List[InterfaceStats] = []

        for name, counters in raw_stats.items():
            bytes_recv = counters["bytes_recv"]
            bytes_sent = counters["bytes_sent"]
            packets_recv = counters["packets_recv"]
            packets_sent = counters["packets_sent"]

            # Rate calculation
            send_rate = 0.0
            recv_rate = 0.0
            prev = cls._previous_readings.get(name)
            if prev is not None:
                dt = now - prev[0]
                if dt > 0:
                    send_rate = max(0.0, (bytes_sent - prev[1]) / dt)
                    recv_rate = max(0.0, (bytes_recv - prev[2]) / dt)

            cls._previous_readings[name] = (now, bytes_sent, bytes_recv)

            iface_type = cls._classify_interface(name)
            is_up = cls._is_interface_up(name)
            ip_address = cls.get_interface_ip(name) if is_up else ""

            results.append(InterfaceStats(
                name=name,
                type=iface_type,
                is_up=is_up,
                ip_address=ip_address,
                bytes_sent=bytes_sent,
                bytes_recv=bytes_recv,
                packets_sent=packets_sent,
                packets_recv=packets_recv,
                send_rate=round(send_rate, 2),
                recv_rate=round(recv_rate, 2),
            ))

        return results

    @classmethod
    def get_active_connections(cls) -> List[ConnectionInfo]:
        """
        Return all active TCP/UDP connections with process information.

        Parses /proc/net/tcp, /proc/net/tcp6, /proc/net/udp, /proc/net/udp6
        and resolves PIDs by mapping socket inodes through /proc/[pid]/fd.

        This may be slow on systems with many processes.  Unreadable
        /proc entries (permission errors) are silently skipped.

        Returns:
            List of ConnectionInfo.  Empty list on error.
        """
        inode_to_pid: Dict[str, Tuple[int, str]] = cls._build_inode_pid_map()

        connections: List[ConnectionInfo] = []

        proto_files = [
            ("tcp", "/proc/net/tcp", False),
            ("tcp6", "/proc/net/tcp6", True),
            ("udp", "/proc/net/udp", False),
            ("udp6", "/proc/net/udp6", True),
        ]

        for proto, path, is_v6 in proto_files:
            entries = cls._parse_proc_net_socket(path, is_v6)
            for entry in entries:
                inode = entry["inode"]
                pid = 0
                process_name = ""
                if inode in inode_to_pid:
                    pid, process_name = inode_to_pid[inode]

                state_str = entry.get("state", "")
                # UDP has no real state; map "07" to "CLOSE" but show as ""
                if proto.startswith("udp"):
                    state_str = cls._TCP_STATES.get(state_str, "")

                connections.append(ConnectionInfo(
                    protocol=proto,
                    local_addr=entry["local_addr"],
                    local_port=entry["local_port"],
                    remote_addr=entry["remote_addr"],
                    remote_port=entry["remote_port"],
                    state=cls._TCP_STATES.get(state_str, state_str) if proto.startswith("tcp") else state_str,
                    pid=pid,
                    process_name=process_name,
                ))

        return connections

    @classmethod
    def get_bandwidth_summary(cls) -> dict:
        """
        Aggregate bandwidth across all non-loopback interfaces.

        Returns:
            Dict with keys: total_sent (int), total_recv (int),
            total_send_rate (float), total_recv_rate (float).
        """
        interfaces = cls.get_all_interfaces()
        total_sent = 0
        total_recv = 0
        total_send_rate = 0.0
        total_recv_rate = 0.0

        for iface in interfaces:
            if iface.type == "loopback":
                continue
            total_sent += iface.bytes_sent
            total_recv += iface.bytes_recv
            total_send_rate += iface.send_rate
            total_recv_rate += iface.recv_rate

        return {
            "total_sent": total_sent,
            "total_recv": total_recv,
            "total_send_rate": round(total_send_rate, 2),
            "total_recv_rate": round(total_recv_rate, 2),
        }

    @staticmethod
    def get_interface_ip(name: str) -> str:
        """
        Get the IPv4 address assigned to *name*.

        Uses ``ip -4 addr show <iface>`` and parses the ``inet`` line.

        Args:
            name: Interface name, e.g. "wlp2s0".

        Returns:
            IPv4 address string, or "" if unavailable.
        """
        try:
            result = subprocess.run(
                ["ip", "-4", "addr", "show", name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return ""
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    # e.g. "inet 192.168.1.42/24 brd 192.168.1.255 scope global ..."
                    addr_cidr = line.split()[1]
                    return addr_cidr.split("/")[0]
        except Exception:
            pass
        return ""

    @staticmethod
    def bytes_to_human(num_bytes: float) -> str:
        """Convert a byte count (int or float) to a human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(num_bytes) < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} PB"

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read_proc_net_dev() -> Dict[str, Dict[str, int]]:
        """
        Parse /proc/net/dev and return per-interface byte/packet counters.

        /proc/net/dev format (after two header lines):
          iface: recv_bytes recv_packets ... tx_bytes tx_packets ...

        Returns:
            {iface_name: {"bytes_recv": int, "packets_recv": int,
                          "bytes_sent": int, "packets_sent": int}}
        """
        stats: Dict[str, Dict[str, int]] = {}
        try:
            with open("/proc/net/dev", "r") as f:
                lines = f.readlines()

            # Skip the two header lines
            for line in lines[2:]:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                iface, data = line.split(":", 1)
                iface = iface.strip()
                fields = data.split()
                if len(fields) < 10:
                    continue
                stats[iface] = {
                    "bytes_recv": int(fields[0]),
                    "packets_recv": int(fields[1]),
                    "bytes_sent": int(fields[8]),
                    "packets_sent": int(fields[9]),
                }
        except Exception:
            pass
        return stats

    @staticmethod
    def _classify_interface(name: str) -> str:
        """
        Classify a network interface by name pattern and /sys/class/net/<name>/type.

        Returns one of: "wifi", "ethernet", "loopback", "vpn", "other".
        """
        if name == "lo":
            return "loopback"
        if name.startswith("wl"):
            return "wifi"
        if name.startswith(("en", "eth")):
            return "ethernet"
        if name.startswith(("tun", "tap", "wg")):
            return "vpn"

        # Fall back to /sys/class/net/<name>/type
        # ARPHRD_ETHER = 1, ARPHRD_LOOPBACK = 772, ARPHRD_NONE = 0xFFFE (often tunnel)
        try:
            with open(f"/sys/class/net/{name}/type", "r") as f:
                dev_type = int(f.read().strip())
            if dev_type == 772:
                return "loopback"
            if dev_type == 1:
                # Could be ethernet or wifi; check for /sys/class/net/<name>/wireless
                if os.path.isdir(f"/sys/class/net/{name}/wireless"):
                    return "wifi"
                return "ethernet"
            if dev_type == 65534:  # ARPHRD_NONE -- tunnels, VPNs
                return "vpn"
        except Exception:
            pass

        return "other"

    @staticmethod
    def _is_interface_up(name: str) -> bool:
        """Check whether an interface is operationally up via /sys/class/net/<name>/operstate."""
        try:
            with open(f"/sys/class/net/{name}/operstate", "r") as f:
                state = f.read().strip().lower()
            return state == "up"
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  /proc/net/tcp & udp parsing
    # ------------------------------------------------------------------ #

    @classmethod
    def _parse_proc_net_socket(cls, path: str, is_v6: bool) -> List[dict]:
        """
        Parse a /proc/net/{tcp,tcp6,udp,udp6} file.

        Each data line (after the header) has the format:
          sl  local_address  rem_address  st  tx_queue:rx_queue  ...  inode

        Addresses are hex-encoded.  IPv4 is little-endian 32-bit + port.
        IPv6 is four little-endian 32-bit words + port.

        Returns:
            List of dicts with keys: local_addr, local_port, remote_addr,
            remote_port, state (hex string), inode.
        """
        entries: List[dict] = []
        try:
            with open(path, "r") as f:
                lines = f.readlines()

            for line in lines[1:]:  # skip header
                parts = line.strip().split()
                if len(parts) < 10:
                    continue
                try:
                    local_addr, local_port = cls._decode_address(parts[1], is_v6)
                    remote_addr, remote_port = cls._decode_address(parts[2], is_v6)
                    state = parts[3]
                    inode = parts[9]

                    entries.append({
                        "local_addr": local_addr,
                        "local_port": local_port,
                        "remote_addr": remote_addr,
                        "remote_port": remote_port,
                        "state": state,
                        "inode": inode,
                    })
                except (ValueError, IndexError):
                    continue
        except Exception:
            pass
        return entries

    @staticmethod
    def _decode_address(addr_hex: str, is_v6: bool) -> Tuple[str, int]:
        """
        Decode a hex address:port pair from /proc/net/tcp{,6}.

        Args:
            addr_hex: String like "0100007F:0050" (IPv4) or
                      "00000000000000000000000001000000:0050" (IPv6).
            is_v6: Whether the address is IPv6.

        Returns:
            (address_string, port_int)
        """
        host_hex, port_hex = addr_hex.split(":")
        port = int(port_hex, 16)

        if is_v6:
            # IPv6: 32 hex chars = 16 bytes, stored as four 32-bit words in
            # host byte order (little-endian on x86).
            if len(host_hex) != 32:
                return (host_hex, port)
            words = [host_hex[i:i+8] for i in range(0, 32, 8)]
            byte_groups = []
            for word in words:
                # Convert each 4-byte word from little-endian
                val = struct.unpack("=I", bytes.fromhex(word))[0]
                byte_groups.append(struct.pack("!I", val))
            raw = b"".join(byte_groups)
            # Check if it is an IPv4-mapped address (::ffff:x.x.x.x)
            if raw[:12] == b"\x00" * 10 + b"\xff\xff":
                addr = socket.inet_ntoa(raw[12:])
            else:
                try:
                    addr = socket.inet_ntop(socket.AF_INET6, raw)
                except Exception:
                    addr = host_hex
        else:
            # IPv4: 8 hex chars, little-endian 32-bit
            try:
                packed = struct.pack("<I", int(host_hex, 16))
                addr = socket.inet_ntoa(packed)
            except Exception:
                addr = host_hex

        return (addr, port)

    @staticmethod
    def _build_inode_pid_map() -> Dict[str, Tuple[int, str]]:
        """
        Build a mapping from socket inode to (pid, process_name).

        Scans /proc/[pid]/fd for symlinks of the form ``socket:[inode]``.
        Processes that cannot be read (permission errors) are silently skipped.

        Returns:
            {inode_string: (pid, process_name)}
        """
        inode_map: Dict[str, Tuple[int, str]] = {}
        try:
            pids = [
                entry for entry in os.listdir("/proc")
                if entry.isdigit()
            ]
        except Exception:
            return inode_map

        for pid_str in pids:
            fd_dir = f"/proc/{pid_str}/fd"
            try:
                fds = os.listdir(fd_dir)
            except (PermissionError, FileNotFoundError, OSError):
                continue

            pid = int(pid_str)
            process_name = ""

            for fd_name in fds:
                fd_path = os.path.join(fd_dir, fd_name)
                try:
                    target = os.readlink(fd_path)
                except (PermissionError, FileNotFoundError, OSError):
                    continue

                if target.startswith("socket:["):
                    inode = target[8:-1]  # strip "socket:[" and "]"
                    # Lazily resolve process name only when we find a socket
                    if not process_name:
                        process_name = NetworkMonitor._get_process_name(pid)
                    inode_map[inode] = (pid, process_name)

        return inode_map

    @staticmethod
    def _get_process_name(pid: int) -> str:
        """
        Read the process name for *pid* from /proc/[pid]/comm.

        Returns:
            Process name string, or "" on error.
        """
        try:
            with open(f"/proc/{pid}/comm", "r") as f:
                return f.read().strip()
        except Exception:
            return ""
