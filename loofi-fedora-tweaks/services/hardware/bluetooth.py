"""
Bluetooth Manager — device scanning, pairing, and control.
Part of v17.0 "Atlas".

Wraps ``bluetoothctl`` for device discovery, pairing/unpairing,
connect/disconnect, trust/block, and battery level queries.
All privileged operations use pkexec where needed.
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

class BluetoothDeviceType(Enum):
    """Device type classification."""
    AUDIO = "audio"
    INPUT = "input"
    PHONE = "phone"
    COMPUTER = "computer"
    UNKNOWN = "unknown"


@dataclass
class BluetoothDevice:
    """Represents a discovered or paired Bluetooth device."""
    address: str
    name: str
    paired: bool = False
    connected: bool = False
    trusted: bool = False
    blocked: bool = False
    battery: int = -1          # -1 = unknown
    icon: str = ""
    device_type: BluetoothDeviceType = BluetoothDeviceType.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "name": self.name,
            "paired": self.paired,
            "connected": self.connected,
            "trusted": self.trusted,
            "blocked": self.blocked,
            "battery": self.battery,
            "device_type": self.device_type.value,
        }


@dataclass
class BluetoothResult:
    """Result of a Bluetooth operation."""
    success: bool
    message: str


@dataclass
class BluetoothStatus:
    """Overall adapter status."""
    powered: bool = False
    discoverable: bool = False
    pairable: bool = False
    adapter_name: str = ""
    adapter_address: str = ""


# ---------------------------------------------------------------------------
# BluetoothManager
# ---------------------------------------------------------------------------

class BluetoothManager:
    """Bluetooth device management via bluetoothctl.

    All methods are classmethods for stateless use.
    """

    # ----------------------------------------------------------- status

    @classmethod
    def get_adapter_status(cls) -> BluetoothStatus:
        """Get Bluetooth adapter information."""
        status = BluetoothStatus()
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return status

            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Name:"):
                    status.adapter_name = line.split(":", 1)[1].strip()
                elif line.startswith("Controller"):
                    status.adapter_address = line.split()[1] if len(line.split()) > 1 else ""
                elif line.startswith("Powered:"):
                    status.powered = "yes" in line.lower()
                elif line.startswith("Discoverable:"):
                    status.discoverable = "yes" in line.lower()
                elif line.startswith("Pairable:"):
                    status.pairable = "yes" in line.lower()
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("bluetoothctl show failed: %s", exc)
        return status

    # ----------------------------------------------------------- list

    @classmethod
    def list_devices(cls, paired_only: bool = False) -> List[BluetoothDevice]:
        """List Bluetooth devices.

        Args:
            paired_only: If True, only return paired devices.

        Returns:
            List of BluetoothDevice objects.
        """
        devices: List[BluetoothDevice] = []
        try:
            cmd = ["bluetoothctl", "devices"]
            if paired_only:
                cmd.append("Paired")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return devices

            # Parse "Device AA:BB:CC:DD:EE:FF DeviceName"
            for line in result.stdout.strip().splitlines():
                match = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)", line.strip())
                if match:
                    addr = match.group(1)
                    name = match.group(2)
                    device = cls._get_device_info(addr, name)
                    devices.append(device)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Failed to list devices: %s", exc)
        return devices

    @classmethod
    def _get_device_info(cls, address: str, name: str) -> BluetoothDevice:
        """Get detailed info for a single device."""
        device = BluetoothDevice(address=address, name=name)
        try:
            result = subprocess.run(
                ["bluetoothctl", "info", address],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return device

            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Paired:"):
                    device.paired = "yes" in line.lower()
                elif line.startswith("Connected:"):
                    device.connected = "yes" in line.lower()
                elif line.startswith("Trusted:"):
                    device.trusted = "yes" in line.lower()
                elif line.startswith("Blocked:"):
                    device.blocked = "yes" in line.lower()
                elif line.startswith("Icon:"):
                    icon = line.split(":", 1)[1].strip()
                    device.icon = icon
                    device.device_type = cls._classify_device(icon)
                elif "Battery Percentage" in line:
                    pct_match = re.search(r"\((\d+)\)", line)
                    if pct_match:
                        device.battery = int(pct_match.group(1))
        except (OSError, subprocess.TimeoutExpired):
            pass
        return device

    @staticmethod
    def _classify_device(icon: str) -> BluetoothDeviceType:
        """Classify device type from icon string."""
        icon_lower = icon.lower()
        if "audio" in icon_lower or "headset" in icon_lower or "headphone" in icon_lower:
            return BluetoothDeviceType.AUDIO
        elif "input" in icon_lower or "keyboard" in icon_lower or "mouse" in icon_lower:
            return BluetoothDeviceType.INPUT
        elif "phone" in icon_lower:
            return BluetoothDeviceType.PHONE
        elif "computer" in icon_lower:
            return BluetoothDeviceType.COMPUTER
        return BluetoothDeviceType.UNKNOWN

    # ----------------------------------------------------------- scan

    @classmethod
    def scan(cls, timeout: int = 10) -> List[BluetoothDevice]:
        """Scan for nearby Bluetooth devices.

        Args:
            timeout: Scan duration in seconds.

        Returns:
            List of discovered devices.
        """
        try:
            # Start scan, wait, then read devices
            subprocess.run(
                ["bluetoothctl", "--timeout", str(timeout), "scan", "on"],
                capture_output=True, text=True, timeout=timeout + 5
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        return cls.list_devices(paired_only=False)

    # ----------------------------------------------------------- actions

    @classmethod
    def pair(cls, address: str) -> BluetoothResult:
        """Pair with a device."""
        return cls._run_action("pair", address, f"Pairing with {address}")

    @classmethod
    def unpair(cls, address: str) -> BluetoothResult:
        """Remove a paired device."""
        return cls._run_action("remove", address, f"Removing {address}")

    @classmethod
    def connect(cls, address: str) -> BluetoothResult:
        """Connect to a paired device."""
        return cls._run_action("connect", address, f"Connecting to {address}")

    @classmethod
    def disconnect(cls, address: str) -> BluetoothResult:
        """Disconnect a device."""
        return cls._run_action("disconnect", address, f"Disconnecting {address}")

    @classmethod
    def trust(cls, address: str) -> BluetoothResult:
        """Trust a device (auto-connect)."""
        return cls._run_action("trust", address, f"Trusting {address}")

    @classmethod
    def block(cls, address: str) -> BluetoothResult:
        """Block a device."""
        return cls._run_action("block", address, f"Blocking {address}")

    @classmethod
    def unblock(cls, address: str) -> BluetoothResult:
        """Unblock a device."""
        return cls._run_action("unblock", address, f"Unblocking {address}")

    # ----------------------------------------------------------- adapter power

    @classmethod
    def power_on(cls) -> BluetoothResult:
        """Power on the Bluetooth adapter."""
        return cls._run_action("power", "on", "Powering on Bluetooth")

    @classmethod
    def power_off(cls) -> BluetoothResult:
        """Power off the Bluetooth adapter."""
        return cls._run_action("power", "off", "Powering off Bluetooth")

    # ----------------------------------------------------------- internal

    @classmethod
    def _run_action(cls, action: str, target: str,
                    description: str) -> BluetoothResult:
        """Execute a bluetoothctl action."""
        try:
            result = subprocess.run(
                ["bluetoothctl", action, target],
                capture_output=True, text=True, timeout=15
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0 or "successful" in output.lower():
                return BluetoothResult(True, f"{description} — OK")
            return BluetoothResult(False, f"Failed: {output}")
        except subprocess.TimeoutExpired:
            return BluetoothResult(False, f"Timed out: {description}")
        except OSError as exc:
            return BluetoothResult(False, f"Error: {exc}")
