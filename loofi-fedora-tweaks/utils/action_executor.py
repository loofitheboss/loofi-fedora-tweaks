# Backward-compatibility shim — canonical location is core/executor/action_executor.py
# Remove this file after all imports are migrated (Phase 5-6)
from core.executor.action_executor import *  # noqa: F401,F403
from core.executor.action_executor import ActionExecutor  # noqa: F401
from core.executor.action_executor import (  # noqa: F401
    COMMAND_TIMEOUT,
    MAX_STDOUT,
    MAX_STDERR,
    MAX_LOG_ENTRIES,
)
