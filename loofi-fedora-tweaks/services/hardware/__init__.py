"""
Hardware Services Layer — v23.0 Architecture Hardening

Centralized hardware abstraction for:
- CPU/GPU/thermal management (hardware.py)
- Battery control (battery.py)
- Disk monitoring (disk.py)
- Temperature sensors (temperature.py)
- Bluetooth management (bluetooth.py)
- Hardware profile detection (hardware_profiles.py)
"""

from services.hardware.hardware import HardwareManager
from services.hardware.battery import BatteryManager
from services.hardware.disk import DiskManager, DiskUsage, LargeDirectory
from services.hardware.temperature import (
    TemperatureManager,
    TemperatureSensor,
)
from services.hardware.bluetooth import (
    BluetoothManager,
    BluetoothDevice,
    BluetoothDeviceType,
    BluetoothResult,
    BluetoothStatus,
)
from services.hardware.hardware_profiles import (
    PROFILES,
    detect_hardware_profile,
    get_profile_label,
    get_all_profiles,
)

__all__ = [
    # Hardware management
    "HardwareManager",
    # Battery
    "BatteryManager",
    # Disk
    "DiskManager",
    "DiskUsage",
    "LargeDirectory",
    # Temperature
    "TemperatureManager",
    "TemperatureSensor",
    # Bluetooth
    "BluetoothManager",
    "BluetoothDevice",
    "BluetoothDeviceType",
    "BluetoothResult",
    "BluetoothStatus",
    # Hardware profiles
    "PROFILES",
    "detect_hardware_profile",
    "get_profile_label",
    "get_all_profiles",
]
