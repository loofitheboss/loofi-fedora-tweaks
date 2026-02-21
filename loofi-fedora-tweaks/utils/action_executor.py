"""Backward-compatibility shim re-exporting ActionExecutor from core.executor."""
from core.executor.action_executor import *  # noqa: F401,F403
from core.executor.action_executor import (  # noqa: F401
    COMMAND_TIMEOUT,
    MAX_LOG_ENTRIES,
    MAX_STDERR,
    MAX_STDOUT,
    ActionExecutor,  # noqa: F401
)
