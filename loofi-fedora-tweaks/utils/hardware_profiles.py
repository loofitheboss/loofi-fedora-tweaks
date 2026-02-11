"""
Backward compatibility shim for hardware_profiles.py

DEPRECATED: Import from services.hardware instead.
This module will be removed in v24.0.
"""

import warnings
import os  # noqa: F401 - For test mocking compatibility
from services.hardware.hardware_profiles import (
    PROFILES,
    detect_hardware_profile,
    get_profile_label,
    get_all_profiles,
)

warnings.warn(
    "utils.hardware_profiles is deprecated. Import from services.hardware instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "PROFILES",
    "detect_hardware_profile",
    "get_profile_label",
    "get_all_profiles",
]
