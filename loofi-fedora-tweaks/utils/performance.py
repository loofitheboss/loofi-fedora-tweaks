"""
Performance Collector - Real-time system metrics collection.
Reads from /proc to gather CPU, memory, network, and disk I/O samples
for live performance graphing. Part of the v9.2 Pulse Update.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CpuSample:
    """A single CPU usage sample."""

    timestamp: float
    percent: float  # Overall CPU usage %
    per_core: List[float]  # Per-core usage %


@dataclass
class MemorySample:
    """A single memory usage sample."""

    timestamp: float
    percent: float
    used_bytes: int
    total_bytes: int


@dataclass
class NetworkSample:
    """A single network I/O sample."""

    timestamp: float
    bytes_sent: int
    bytes_recv: int
    send_rate: float  # bytes/sec
    recv_rate: float  # bytes/sec


@dataclass
class DiskIOSample:
    """A single disk I/O sample."""

    timestamp: float
    read_bytes: int
    write_bytes: int
    read_rate: float  # bytes/sec
    write_rate: float  # bytes/sec


class PerformanceCollector:
    """
    Collects real-time system performance metrics by reading /proc.

    Stores the last 60 samples of each metric type in ring buffers
    for use by live performance graphs.
    """

    # Maximum number of samples to retain per metric
    MAX_SAMPLES = 60

    # Disk sector size in bytes (standard Linux block layer)
    SECTOR_SIZE = 512

    def __init__(self) -> None:
        # Ring buffers for each metric type
        self._cpu_history: deque = deque(maxlen=self.MAX_SAMPLES)
        self._memory_history: deque = deque(maxlen=self.MAX_SAMPLES)
        self._network_history: deque = deque(maxlen=self.MAX_SAMPLES)
        self._disk_io_history: deque = deque(maxlen=self.MAX_SAMPLES)

        # Previous readings for delta calculations
        self._prev_cpu_times: Optional[List[List[int]]] = None
        self._prev_cpu_timestamp: float = 0.0

        self._prev_net_bytes: Optional[Tuple[int, int]] = None
        self._prev_net_timestamp: float = 0.0

        self._prev_disk_bytes: Optional[Tuple[int, int]] = None
        self._prev_disk_timestamp: float = 0.0

    # ==================== STATIC HELPERS ====================

    @staticmethod
    def bytes_to_human(num_bytes: float) -> str:
        """Convert bytes to human-readable format."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(num_bytes) < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} PB"

    # ==================== /proc READERS ====================

    @staticmethod
    def _read_proc_stat() -> List[List[int]]:
        """
        Read CPU time counters from /proc/stat.

        Returns:
            List of int-lists. Index 0 is the aggregate 'cpu' line,
            indices 1..N are per-core 'cpuN' lines.
            Each inner list contains:
            [user, nice, system, idle, iowait, irq, softirq, steal]
        """
        results = []
        try:
            with open("/proc/stat", "r") as f:
                for line in f:
                    if not line.startswith("cpu"):
                        break
                    parts = line.split()
                    # parts[0] is 'cpu' or 'cpu0', etc.
                    # parts[1:] are the time counters
                    if len(parts) >= 5:
                        results.append([int(v) for v in parts[1:9]])
        except (OSError, IOError, ValueError) as e:
            logger.debug("Failed to read /proc/stat: %s", e)
        return results

    @staticmethod
    def _calc_cpu_percent(prev: List[int], curr: List[int]) -> float:
        """Calculate CPU usage % between two /proc/stat readings."""
        if len(prev) < 4 or len(curr) < 4:
            return 0.0

        prev_idle = prev[3] + (prev[4] if len(prev) > 4 else 0)
        curr_idle = curr[3] + (curr[4] if len(curr) > 4 else 0)

        prev_total = sum(prev)
        curr_total = sum(curr)

        total_delta = curr_total - prev_total
        idle_delta = curr_idle - prev_idle

        if total_delta <= 0:
            return 0.0

        usage = (1.0 - idle_delta / total_delta) * 100.0
        return round(max(0.0, min(100.0, usage)), 1)

    @staticmethod
    def _read_proc_meminfo() -> Dict[str, int]:
        """
        Read memory information from /proc/meminfo.

        Returns:
            Dict mapping field names to values in bytes.
        """
        meminfo: Dict[str, int] = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        # Values in /proc/meminfo are in kB
                        value = int(parts[1]) * 1024
                        meminfo[key] = value
        except (OSError, IOError, ValueError) as e:
            logger.debug("Failed to read /proc/meminfo: %s", e)
        return meminfo

    @staticmethod
    def _read_proc_net_dev() -> Tuple[int, int]:
        """
        Read network byte counters from /proc/net/dev.
        Sums all non-loopback interfaces.

        Returns:
            Tuple of (total_bytes_recv, total_bytes_sent).
        """
        total_recv = 0
        total_sent = 0
        try:
            with open("/proc/net/dev", "r") as f:
                # Skip the two header lines
                f.readline()
                f.readline()
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Format: "iface: recv_bytes packets ... sent_bytes packets ..."
                    colon_idx = line.find(":")
                    if colon_idx < 0:
                        continue
                    iface = line[:colon_idx].strip()
                    # Skip loopback
                    if iface == "lo":
                        continue
                    fields = line[colon_idx + 1:].split()
                    if len(fields) >= 10:
                        total_recv += int(fields[0])  # bytes received
                        total_sent += int(fields[8])  # bytes transmitted
        except (OSError, IOError, ValueError) as e:
            logger.debug("Failed to read /proc/net/dev: %s", e)
        return total_recv, total_sent

    @staticmethod
    def _read_proc_diskstats() -> Tuple[int, int]:
        """
        Read disk I/O counters from /proc/diskstats.
        Sums all real block devices (skips loop, ram, dm- devices).

        Returns:
            Tuple of (total_read_bytes, total_write_bytes).
        """
        total_read = 0
        total_write = 0
        try:
            with open("/proc/diskstats", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 14:
                        continue
                    device = parts[2]
                    # Skip virtual/loop/ram devices
                    if device.startswith(("loop", "ram", "dm-")):
                        continue
                    # Only count whole-disk devices (e.g., sda, nvme0n1, vda)
                    # Skip partitions (sda1, nvme0n1p1, etc.)
                    if _is_partition(device):
                        continue
                    # Field 5 (index 5): sectors read
                    # Field 9 (index 9): sectors written
                    sectors_read = int(parts[5])
                    sectors_written = int(parts[9])
                    total_read += sectors_read * PerformanceCollector.SECTOR_SIZE
                    total_write += sectors_written * PerformanceCollector.SECTOR_SIZE
        except (OSError, IOError, ValueError) as e:
            logger.debug("Failed to read /proc/diskstats: %s", e)
        return total_read, total_write

    # ==================== COLLECTION METHODS ====================

    def collect_cpu(self) -> Optional[CpuSample]:
        """
        Collect a CPU usage sample by comparing /proc/stat readings.

        The first call establishes a baseline and returns 0% usage.
        Subsequent calls calculate actual usage from the delta.

        Returns:
            CpuSample stored in the ring buffer, or None on error.
        """
        try:
            now = time.monotonic()
            current_times = self._read_proc_stat()
            if not current_times:
                return None

            if self._prev_cpu_times is None:
                # First reading: establish baseline, report 0%
                self._prev_cpu_times = current_times
                self._prev_cpu_timestamp = now
                core_count = max(len(current_times) - 1, 1)
                sample = CpuSample(
                    timestamp=now,
                    percent=0.0,
                    per_core=[0.0] * core_count,
                )
                self._cpu_history.append(sample)
                return sample

            # Calculate overall CPU usage (index 0 is aggregate)
            overall = self._calc_cpu_percent(self._prev_cpu_times[0], current_times[0])

            # Calculate per-core usage (indices 1..N)
            per_core = []
            prev_cores = self._prev_cpu_times[1:]
            curr_cores = current_times[1:]
            for i in range(len(curr_cores)):
                if i < len(prev_cores):
                    core_pct = self._calc_cpu_percent(prev_cores[i], curr_cores[i])
                else:
                    core_pct = 0.0
                per_core.append(core_pct)

            sample = CpuSample(
                timestamp=now,
                percent=overall,
                per_core=per_core,
            )
            self._cpu_history.append(sample)

            # Store current as previous for next call
            self._prev_cpu_times = current_times
            self._prev_cpu_timestamp = now

            return sample
        except (OSError, ValueError, TypeError) as e:
            logger.debug("Failed to collect CPU sample: %s", e)
            return None

    def collect_memory(self) -> Optional[MemorySample]:
        """
        Collect a memory usage sample from /proc/meminfo.

        Returns:
            MemorySample stored in the ring buffer, or None on error.
        """
        try:
            now = time.monotonic()
            meminfo = self._read_proc_meminfo()

            total = meminfo.get("MemTotal", 0)
            available = meminfo.get("MemAvailable", 0)
            if total <= 0:
                return None

            used = total - available
            percent = round(used / total * 100.0, 1)

            sample = MemorySample(
                timestamp=now,
                percent=percent,
                used_bytes=used,
                total_bytes=total,
            )
            self._memory_history.append(sample)
            return sample
        except (ValueError, KeyError, TypeError) as e:
            logger.debug("Failed to collect memory sample: %s", e)
            return None

    def collect_network(self) -> Optional[NetworkSample]:
        """
        Collect a network I/O sample from /proc/net/dev.

        Calculates send/recv rates from the delta since the last call.
        The first call establishes a baseline with 0 rates.

        Returns:
            NetworkSample stored in the ring buffer, or None on error.
        """
        try:
            now = time.monotonic()
            recv, sent = self._read_proc_net_dev()

            if self._prev_net_bytes is None:
                # First reading: baseline
                self._prev_net_bytes = (recv, sent)
                self._prev_net_timestamp = now
                sample = NetworkSample(
                    timestamp=now,
                    bytes_sent=sent,
                    bytes_recv=recv,
                    send_rate=0.0,
                    recv_rate=0.0,
                )
                self._network_history.append(sample)
                return sample

            elapsed = now - self._prev_net_timestamp
            if elapsed <= 0:
                elapsed = 1.0

            prev_recv, prev_sent = self._prev_net_bytes
            send_rate = max(0.0, (sent - prev_sent) / elapsed)
            recv_rate = max(0.0, (recv - prev_recv) / elapsed)

            sample = NetworkSample(
                timestamp=now,
                bytes_sent=sent,
                bytes_recv=recv,
                send_rate=round(send_rate, 1),
                recv_rate=round(recv_rate, 1),
            )
            self._network_history.append(sample)

            self._prev_net_bytes = (recv, sent)
            self._prev_net_timestamp = now

            return sample
        except (ValueError, TypeError) as e:
            logger.debug("Failed to collect network sample: %s", e)
            return None

    def collect_disk_io(self) -> Optional[DiskIOSample]:
        """
        Collect a disk I/O sample from /proc/diskstats.

        Calculates read/write rates from the delta since the last call.
        The first call establishes a baseline with 0 rates.

        Returns:
            DiskIOSample stored in the ring buffer, or None on error.
        """
        try:
            now = time.monotonic()
            read_bytes, write_bytes = self._read_proc_diskstats()

            if self._prev_disk_bytes is None:
                # First reading: baseline
                self._prev_disk_bytes = (read_bytes, write_bytes)
                self._prev_disk_timestamp = now
                sample = DiskIOSample(
                    timestamp=now,
                    read_bytes=read_bytes,
                    write_bytes=write_bytes,
                    read_rate=0.0,
                    write_rate=0.0,
                )
                self._disk_io_history.append(sample)
                return sample

            elapsed = now - self._prev_disk_timestamp
            if elapsed <= 0:
                elapsed = 1.0

            prev_read, prev_write = self._prev_disk_bytes
            read_rate = max(0.0, (read_bytes - prev_read) / elapsed)
            write_rate = max(0.0, (write_bytes - prev_write) / elapsed)

            sample = DiskIOSample(
                timestamp=now,
                read_bytes=read_bytes,
                write_bytes=write_bytes,
                read_rate=round(read_rate, 1),
                write_rate=round(write_rate, 1),
            )
            self._disk_io_history.append(sample)

            self._prev_disk_bytes = (read_bytes, write_bytes)
            self._prev_disk_timestamp = now

            return sample
        except (ValueError, TypeError) as e:
            logger.debug("Failed to collect disk I/O sample: %s", e)
            return None

    def collect_all(self) -> Dict[str, Optional[object]]:
        """
        Convenience method to collect all metrics at once.

        Returns:
            Dict with keys 'cpu', 'memory', 'network', 'disk_io'
            mapping to their respective sample objects (or None).
        """
        return {
            "cpu": self.collect_cpu(),
            "memory": self.collect_memory(),
            "network": self.collect_network(),
            "disk_io": self.collect_disk_io(),
        }

    # ==================== HISTORY ACCESSORS ====================

    def get_cpu_history(self) -> List[CpuSample]:
        """Return list of stored CPU samples (oldest first)."""
        return list(self._cpu_history)

    def get_memory_history(self) -> List[MemorySample]:
        """Return list of stored memory samples (oldest first)."""
        return list(self._memory_history)

    def get_network_history(self) -> List[NetworkSample]:
        """Return list of stored network samples (oldest first)."""
        return list(self._network_history)

    def get_disk_io_history(self) -> List[DiskIOSample]:
        """Return list of stored disk I/O samples (oldest first)."""
        return list(self._disk_io_history)


def _is_partition(device: str) -> bool:
    """
    Check if a block device name represents a partition rather than
    a whole disk.

    Examples:
        sda -> False, sda1 -> True
        nvme0n1 -> False, nvme0n1p1 -> True
        vda -> False, vda1 -> True
    """
    # NVMe partitions: nvme0n1p1, nvme0n1p2, ...
    if "nvme" in device and "p" in device:
        # Split on 'p' after 'n' portion: nvme0n1 vs nvme0n1p1
        # A partition has a 'p' followed by digits after the namespace number
        import re

        if re.match(r"^nvme\d+n\d+p\d+$", device):
            return True
        return False

    # SCSI/SATA/virtio: sda1, vda1, hda1, xvda1, etc.
    # Whole disks end in a letter, partitions end in digits
    if device and device[-1].isdigit():
        return True

    return False
