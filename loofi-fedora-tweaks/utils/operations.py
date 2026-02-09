# Backward-compatibility shim — canonical location is core/executor/operations.py
# Remove this file after all imports are migrated (Phase 5-6)
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
