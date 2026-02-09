"""
Backward compatibility shim for bluetooth.py

DEPRECATED: Import from services.hardware instead.
This module will be removed in v24.0.
"""

import warnings
import subprocess  # For test mocking compatibility
from services.hardware.bluetooth import (
    BluetoothManager,
    BluetoothDevice,
    BluetoothDeviceType,
    BluetoothResult,
    BluetoothStatus,
)

warnings.warn(
    "utils.bluetooth is deprecated. Import from services.hardware instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "BluetoothManager",
    "BluetoothDevice",
    "BluetoothDeviceType",
    "BluetoothResult",
    "BluetoothStatus",
]
