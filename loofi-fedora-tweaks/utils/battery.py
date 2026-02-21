"""
Backward compatibility shim for battery.py

DEPRECATED: Import from services.hardware instead.
This module will be removed in v24.0.
"""

import warnings

from services.hardware.battery import BatteryManager

warnings.warn(
    "utils.battery is deprecated. Import from services.hardware instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["BatteryManager"]
