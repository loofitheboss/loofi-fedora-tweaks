"""
Backward-compatibility shim for ServiceManager.
This module has been moved to services.system.services in v23.0.
All imports are re-exported for compatibility.
"""

import subprocess  # Re-export for test mocking compatibility
import warnings

warnings.warn(
    "utils.services is deprecated, use services.system.services instead",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from services.system.services import (  # noqa: F401
    ServiceManager,
    ServiceUnit,
    UnitScope,
    UnitState,
    Result,
)

__all__ = [
    "ServiceManager",
    "ServiceUnit",
    "UnitScope",
    "UnitState",
    "Result",
    "subprocess",  # For test compatibility
]
