"""
Backward compatibility shim for disk.py

DEPRECATED: Import from services.hardware instead.
This module will be removed in v24.0.
"""

import warnings
from services.hardware.disk import DiskManager, DiskUsage, LargeDirectory

warnings.warn(
    "utils.disk is deprecated. Import from services.hardware instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["DiskManager", "DiskUsage", "LargeDirectory"]
