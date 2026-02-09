"""
Backward compatibility shim for hardware.py

DEPRECATED: Import from services.hardware instead.
This module will be removed in v24.0.
"""

import warnings
from services.hardware.hardware import HardwareManager

warnings.warn(
    "utils.hardware is deprecated. Import from services.hardware instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["HardwareManager"]
