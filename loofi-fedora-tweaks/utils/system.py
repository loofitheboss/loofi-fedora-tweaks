"""
Backward-compatibility shim for SystemManager.
This module has been moved to services.system.system in v23.0.
All imports are re-exported for compatibility.
"""

import subprocess  # Re-export for test mocking compatibility
import warnings

warnings.warn(
    "utils.system is deprecated, use services.system.system instead",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from services.system.system import SystemManager  # noqa: F401

__all__ = ["SystemManager", "subprocess"]
