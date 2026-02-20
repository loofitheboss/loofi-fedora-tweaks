"""Backward-compatibility shim re-exporting ActionExecutor from core.executor."""
from core.executor.action_executor import *  # noqa: F401,F403
from core.executor.action_executor import ActionExecutor  # noqa: F401
from core.executor.action_executor import (  # noqa: F401
    COMMAND_TIMEOUT,
    MAX_STDOUT,
    MAX_STDERR,
    MAX_LOG_ENTRIES,
)
