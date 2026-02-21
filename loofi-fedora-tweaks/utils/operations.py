"""Backward-compatibility shim re-exporting operation classes from core.executor."""
from core.executor.operations import *  # noqa: F401,F403
from core.executor.operations import (  # noqa: F401
    CLI_COMMANDS,
    AdvancedOps,
    CleanupOps,
    NetworkOps,
    OperationResult,
    TweakOps,
    execute_operation,
)
