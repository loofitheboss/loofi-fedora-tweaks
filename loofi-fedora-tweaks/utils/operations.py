"""Backward-compatibility shim re-exporting operation classes from core.executor."""
from core.executor.operations import *  # noqa: F401,F403
from core.executor.operations import (  # noqa: F401
    OperationResult,
    CleanupOps,
    TweakOps,
    AdvancedOps,
    NetworkOps,
    execute_operation,
    CLI_COMMANDS,
)
