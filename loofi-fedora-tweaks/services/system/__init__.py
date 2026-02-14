"""
services/system/ — Core system services (systemd, process, commands)

Public API exports for system-level utilities.
v23.0: Added BaseSystemService and SystemService for architecture hardening.
"""

from __future__ import annotations

# System detection and management
from services.system.system import SystemManager

# Systemd service management
from services.system.services import (
    ServiceManager,
    ServiceUnit,
    UnitScope,
    UnitState,
    Result,
)

# Process management
from services.system.processes import (
    ProcessManager,
    ProcessInfo,
)

# Backward compatibility: CommandRunner lives in utils.command_runner
from utils.command_runner import CommandRunner

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
