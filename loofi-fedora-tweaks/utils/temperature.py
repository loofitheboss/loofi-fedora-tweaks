"""
Backward compatibility shim for temperature.py

DEPRECATED: Import from services.hardware instead.
This module will be removed in v24.0.
"""

import warnings
import glob  # For test mocking compatibility
from services.hardware.temperature import (
    TemperatureManager,
    TemperatureSensor,
    _read_millidegree,
    _read_sysfs_value,
)

warnings.warn(
    "utils.temperature is deprecated. Import from services.hardware instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "TemperatureManager",
    "TemperatureSensor",
    "glob",
    "_read_millidegree",
    "_read_sysfs_value",
]
