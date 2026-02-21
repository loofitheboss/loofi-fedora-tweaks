"""
services/system/ — Core system services (systemd, process, commands)

Public API exports for system-level utilities.
v23.0: Added BaseSystemService and SystemService for architecture hardening.
"""

from __future__ import annotations

# Backward compatibility: CommandRunner lives in utils.command_runner
from utils.command_runner import CommandRunner

# Process management
from services.system.processes import (
    ProcessInfo,
    ProcessManager,
)

# Systemd service management
from services.system.services import (
    Result,
    ServiceManager,
    ServiceUnit,
    UnitScope,
    UnitState,
)

# System detection and management
from services.system.system import SystemManager

__all__ = [
    # System
    "SystemManager",
    # Services
    "ServiceManager",
    "ServiceUnit",
    "UnitScope",
    "UnitState",
    "Result",
    # Processes
    "ProcessManager",
    "ProcessInfo",
    # Backward compat
    "CommandRunner",
]
