"""
Base Action Executor — v19.0 Phase 1.

Abstract base class defining the executor interface.
All concrete executor implementations must inherit from BaseActionExecutor.

Architecture:
- execute(): run the action and return ActionResult
- preview(): return what would be executed without running
- Implementations: sync subprocess (ActionExecutor), future: Qt async (QtActionExecutor)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from core.executor.action_result import ActionResult

logger = logging.getLogger(__name__)


class BaseActionExecutor(ABC):
    """
    Abstract base class for action executors.

    Subclasses must implement:
    - execute(): Run the action and return ActionResult
    - preview(): Return what would be executed (dry-run)

    Common patterns:
    - All actions return ActionResult for consistency
    - Preview mode never modifies system state
    - Privilege escalation via privileged parameter
    - Timeout control for long-running operations
    """

    @abstractmethod
    def execute(
        self,
        command: str,
        args: Optional[List[str]] = None,
        *,
        privileged: bool = False,
        timeout: int = 120,
        action_id: str = "",
        env: Optional[Dict[str, str]] = None,
    ) -> ActionResult:
        """
        Execute a system command and return a structured result.

        Args:
            command: The executable name or path.
            args: Command arguments.
            privileged: If True, use privilege escalation (pkexec/sudo).
            timeout: Max seconds to wait.
            action_id: Optional ID for correlating with action definitions.
            env: Optional extra environment variables.

        Returns:
            ActionResult containing success status, output, and metadata.
        """
        pass

    @abstractmethod
    def preview(
        self,
        command: str,
        args: Optional[List[str]] = None,
        *,
        privileged: bool = False,
        action_id: str = "",
    ) -> ActionResult:
        """
        Preview what would be executed without running the command.

        Args:
            command: The executable name or path.
            args: Command arguments.
            privileged: If True, would use privilege escalation.
            action_id: Optional ID for correlating with action definitions.

        Returns:
            ActionResult with preview=True and command details in data field.
        """
        pass

    @classmethod
    @abstractmethod
    def set_global_dry_run(cls, enabled: bool):
        """
        Enable/disable global dry-run mode.

        When enabled, all execute() calls behave as preview().
        """
        pass
