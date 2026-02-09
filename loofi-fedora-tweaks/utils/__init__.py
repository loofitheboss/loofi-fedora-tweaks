# utils/ — Pure utilities and backward-compatibility re-exports
#
# Executor layer has moved to core/executor/ (v23.0 refactor).
# These re-exports maintain backward compatibility — remove in Phase 6.
from core.executor.action_executor import ActionExecutor  # noqa: F401
from core.executor.action_result import ActionResult  # noqa: F401
