"""
Backward-compatibility shim for ProcessManager.
This module has been moved to services.system.processes in v23.0.
All imports are re-exported for compatibility.
"""

import os  # Re-export for test mocking compatibility
import subprocess  # Re-export for test mocking compatibility
import time  # Re-export for test mocking compatibility
import warnings

warnings.warn(
    "utils.processes is deprecated, use services.system.processes instead",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from services.system.processes import (  # noqa: F401
    ProcessManager,
    ProcessInfo,
)

__all__ = [
    "ProcessManager",
    "ProcessInfo",
    "os",  # For test compatibility
    "subprocess",  # For test compatibility
    "time",  # For test compatibility
]
