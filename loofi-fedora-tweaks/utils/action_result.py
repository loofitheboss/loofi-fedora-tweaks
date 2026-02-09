# Backward-compatibility shim — canonical location is core/executor/action_result.py
# Remove this file after all imports are migrated (Phase 5-6)
from core.executor.action_result import *  # noqa: F401,F403
from core.executor.action_result import ActionResult  # noqa: F401
