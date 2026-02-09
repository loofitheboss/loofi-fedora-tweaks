"""
Storage Manager — disk information, SMART health, and mount management.
Part of v17.0 "Atlas".

Wraps ``lsblk``, ``smartctl``, ``findmnt``, ``df``, and ``udisksctl`` for
unified disk and storage management. All privileged operations go through
pkexec.
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BlockDevice:
    """Represents a block device from lsblk."""
    name: str                  # e.g. "sda", "nvme0n1p1"
    path: str                  # e.g. "/dev/sda"
    size: str                  # human-readable, e.g. "500G"
    device_type: str           # "disk", "part", "lvm", "crypt", "loop"
    fstype: str = ""           # filesystem type, e.g. "ext4", "btrfs"
    mountpoint: str = ""
    label: str = ""
    uuid: str = ""
    model: str = ""
    serial: str = ""
    ro: bool = False           # read-only
    rm: bool = False           # removable
    hotplug: bool = False
    children: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "type": self.device_type,
            "fstype": self.fstype,
            "mountpoint": self.mountpoint,
            "label": self.label,
            "model": self.model,
            "ro": self.ro,
            "rm": self.rm,
        }


@dataclass
class SmartHealth:
    """SMART health data for a disk."""
    device: str
    model: str = ""
    serial: str = ""
    health_passed: bool = True
    temperature_c: int = 0
    power_on_hours: int = 0
    reallocated_sectors: int = 0
    raw_output: str = ""

    def to_dict(self) -> dict:
        return {
            "device": self.device,
            "model": self.model,
            "serial": self.serial,
            "health_passed": self.health_passed,
            "temperature_c": self.temperature_c,
            "power_on_hours": self.power_on_hours,
            "reallocated_sectors": self.reallocated_sectors,
        }


@dataclass
class MountInfo:
    """A filesystem mount point."""
    source: str        # device path
    target: str        # mount point
    fstype: str
    options: str
    size: str = ""
    used: str = ""
    avail: str = ""
    use_percent: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "fstype": self.fstype,
            "size": self.size,
            "used": self.used,
            "avail": self.avail,
            "use_percent": self.use_percent,
        }


@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    message: str


# ---------------------------------------------------------------------------
# StorageManager
# ---------------------------------------------------------------------------

class StorageManager:
    """Disk and storage management operations.

    All methods are classmethods for stateless use.
    """

    # ----------------------------------------------------------- block devices

    @classmethod
    def list_block_devices(cls) -> List[BlockDevice]:
        """List all block devices using lsblk.

        Returns:
            Flat list of BlockDevice objects (disks + partitions).
        """
        devices: List[BlockDevice] = []
        try:
            result = subprocess.run(
                ["lsblk", "-J", "-o",
                 "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL,UUID,MODEL,SERIAL,RO,RM,HOTPLUG"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return devices

            data = json.loads(result.stdout)
            for dev in data.get("blockdevices", []):
                devices.append(cls._parse_block_device(dev))
                for child in dev.get("children", []):
                    devices.append(cls._parse_block_device(child))
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            logger.warning("lsblk failed: %s", exc)
        return devices

    @classmethod
    def list_disks(cls) -> List[BlockDevice]:
        """List only physical disks (type=disk), excluding loop devices."""
        return [d for d in cls.list_block_devices()
                if d.device_type == "disk" and not d.name.startswith("loop")]

    @classmethod
    def list_partitions(cls) -> List[BlockDevice]:
        """List only partitions."""
        return [d for d in cls.list_block_devices()
                if d.device_type == "part"]

    @classmethod
    def _parse_block_device(cls, data: dict) -> BlockDevice:
        """Parse a single lsblk JSON entry."""
        return BlockDevice(
            name=data.get("name", ""),
            path=data.get("path", ""),
            size=data.get("size", ""),
            device_type=data.get("type", ""),
            fstype=data.get("fstype") or "",
            mountpoint=data.get("mountpoint") or "",
            label=data.get("label") or "",
            uuid=data.get("uuid") or "",
            model=(data.get("model") or "").strip(),
            serial=(data.get("serial") or "").strip(),
            ro=data.get("ro", False),
            rm=data.get("rm", False),
            hotplug=data.get("hotplug", False),
        )

    # ----------------------------------------------------------- SMART health

    @classmethod
    def get_smart_health(cls, device: str) -> SmartHealth:
        """Get SMART health data for a disk device.

        Args:
            device: Device path like /dev/sda or /dev/nvme0n1.

        Returns:
            SmartHealth with parsed data.
        """
        health = SmartHealth(device=device)
        try:
            result = subprocess.run(
                ["pkexec", "smartctl", "-a", device],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout
            health.raw_output = output

            for line in output.splitlines():
                line_stripped = line.strip()
                if "Device Model:" in line or "Model Number:" in line:
                    health.model = line_stripped.split(":", 1)[1].strip()
                elif "Serial Number:" in line:
                    health.serial = line_stripped.split(":", 1)[1].strip()
                elif "SMART overall-health" in line:
                    health.health_passed = "PASSED" in line
                elif "Temperature_Celsius" in line or "Temperature:" in line:
                    # SMART attribute line: "194 Temperature_Celsius ... 30"
                    # Or NVMe: "Temperature: 30 Celsius"
                    temp_match = re.search(r"(\d+)\s*$", line_stripped)
                    if temp_match:
                        health.temperature_c = int(temp_match.group(1))
                elif "Power_On_Hours" in line:
                    hours_match = re.search(r"(\d+)\s*$", line_stripped)
                    if hours_match:
                        health.power_on_hours = int(hours_match.group(1))
                elif "Reallocated_Sector" in line:
                    sect_match = re.search(r"(\d+)\s*$", line_stripped)
                    if sect_match:
                        health.reallocated_sectors = int(sect_match.group(1))
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("smartctl failed for %s: %s", device, exc)
        return health

    # ----------------------------------------------------------- mounts

    @classmethod
    def list_mounts(cls) -> List[MountInfo]:
        """List mounted filesystems using df.

        Returns:
            List of MountInfo for real filesystems (excludes tmpfs, devtmpfs).
        """
        mounts: List[MountInfo] = []
        try:
            result = subprocess.run(
                ["df", "-hT", "--output=source,target,fstype,size,used,avail,pcent"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return mounts

            lines = result.stdout.strip().splitlines()
            for line in lines[1:]:  # skip header
                parts = line.split()
                if len(parts) < 7:
                    continue
                source = parts[0]
                # Skip virtual filesystems
                if not source.startswith("/"):
                    continue
                mounts.append(MountInfo(
                    source=source,
                    target=parts[1],
                    fstype=parts[2],
                    options="",
                    size=parts[3],
                    used=parts[4],
                    avail=parts[5],
                    use_percent=parts[6],
                ))
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("df failed: %s", exc)
        return mounts

    # ----------------------------------------------------------- filesystem ops

    @classmethod
    def check_filesystem(cls, device: str) -> StorageResult:
        """Run filesystem check on a device (must be unmounted).

        Args:
            device: Device path like /dev/sda1.

        Returns:
            StorageResult with check output.
        """
        try:
            result = subprocess.run(
                ["pkexec", "fsck", "-n", device],
                capture_output=True, text=True, timeout=120
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                return StorageResult(True, f"Filesystem OK: {output}")
            return StorageResult(False, f"Issues found: {output}")
        except subprocess.TimeoutExpired:
            return StorageResult(False, "Filesystem check timed out")
        except OSError as exc:
            return StorageResult(False, f"Error: {exc}")

    @classmethod
    def trim_ssd(cls) -> StorageResult:
        """Run fstrim on all mounted filesystems."""
        try:
            result = subprocess.run(
                ["pkexec", "fstrim", "-av"],
                capture_output=True, text=True, timeout=120
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                return StorageResult(True, f"Trim complete:\n{output}")
            return StorageResult(False, f"Trim failed: {output}")
        except subprocess.TimeoutExpired:
            return StorageResult(False, "SSD trim timed out")
        except OSError as exc:
            return StorageResult(False, f"Error: {exc}")

    # ----------------------------------------------------------- disk usage

    @classmethod
    def get_usage_summary(cls) -> Dict[str, str]:
        """Get a simple disk usage summary."""
        summary: Dict[str, str] = {}
        for mount in cls.list_mounts():
            summary[mount.target] = (
                f"{mount.used}/{mount.size} ({mount.use_percent})"
            )
        return summary
