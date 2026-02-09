"""
Centralized Action Executor — v19.0 Foundation (Phase 1 Refactor).

All system-level actions route through this executor.
Provides: preview mode, dry-run, structured results, action logging.

Usage:
    from core.executor.action_executor import ActionExecutor

    # Preview what would happen:
    result = ActionExecutor().preview("dnf", ["check-update"])

    # Execute for real:
    result = ActionExecutor().execute("dnf", ["check-update"])

    # With privilege escalation:
    result = ActionExecutor().execute("dnf", ["clean", "all"], privileged=True)

    # Legacy classmethod API (backward compatible):
    result = ActionExecutor.run("dnf", ["check-update"], preview=True)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.executor.action_result import ActionResult
from core.executor.base_executor import BaseActionExecutor

logger = logging.getLogger(__name__)

# Limits
COMMAND_TIMEOUT = 120  # seconds
MAX_STDOUT = 4000
MAX_STDERR = 2000
MAX_LOG_ENTRIES = 500

# Action log location
_LOG_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "loofi-fedora-tweaks",
)
_ACTION_LOG_FILE = os.path.join(_LOG_DIR, "action_log.jsonl")


class ActionExecutor(BaseActionExecutor):
    """
    Synchronous subprocess-based executor (concrete implementation).

    Features:
    - Preview mode: returns what would execute, without running.
    - Dry-run mode (global): logs but never executes.
    - Structured ActionResult for every call.
    - JSON-lines action log for diagnostics export.
    - Flatpak-aware: auto-wraps with flatpak-spawn when inside sandbox.
    - pkexec integration for privilege escalation.
    """

    _dry_run_global: bool = False

    def execute(
        self,
        command: str,
        args: Optional[List[str]] = None,
        *,
        privileged: bool = False,
        timeout: int = COMMAND_TIMEOUT,
        action_id: str = "",
        env: Optional[Dict[str, str]] = None,
    ) -> ActionResult:
        """
        Execute a system command and return a structured result.

        Args:
            command: The executable name or path.
            args: Command arguments.
            privileged: If True, use pkexec for privilege escalation.
            timeout: Max seconds to wait.
            action_id: Optional ID for correlating with action definitions.
            env: Optional extra environment variables.

        Returns:
            ActionResult containing success status, output, and metadata.
        """
        args = args or []

        # Global dry-run intercept
        if self._dry_run_global:
            return self.preview(
                command, args, privileged=privileged, action_id=action_id
            )

        # Build final command list
        cmd = self._build_command(command, args, privileged=privileged)

        # Execute
        result = self._execute_subprocess(
            cmd, timeout=timeout, action_id=action_id, env=env
        )
        self._log_action(cmd, result)
        return result

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
            privileged: If True, would use pkexec for privilege escalation.
            action_id: Optional ID for correlating with action definitions.

        Returns:
            ActionResult with preview=True and command details in data field.
        """
        args = args or []
        cmd = self._build_command(command, args, privileged=privileged)

        result = ActionResult.previewed(cmd[0], cmd[1:], action_id=action_id)
        self._log_action(cmd, result)
        return result

    @classmethod
    def set_global_dry_run(cls, enabled: bool):
        """Enable/disable global dry-run mode."""
        cls._dry_run_global = enabled

    # ========== Legacy classmethod API (backward compatible) ==========
    @classmethod
    def run(
        cls,
        command: str,
        args: Optional[List[str]] = None,
        *,
        preview: bool = False,
        pkexec: bool = False,
        timeout: int = COMMAND_TIMEOUT,
        action_id: str = "",
        env: Optional[Dict[str, str]] = None,
    ) -> ActionResult:
        """
        Legacy classmethod API for backward compatibility.

        DEPRECATED: Use ActionExecutor().execute() or .preview() instead.

        Args:
            command: The executable name or path.
            args: Command arguments.
            preview: If True, return what would run without executing.
            pkexec: If True, prepend pkexec for privilege escalation.
            timeout: Max seconds to wait.
            action_id: Optional ID for correlating with action definitions.
            env: Optional extra environment variables.
        """
        executor = cls()
        if preview:
            return executor.preview(
                command, args, privileged=pkexec, action_id=action_id
            )
        else:
            return executor.execute(
                command,
                args,
                privileged=pkexec,
                timeout=timeout,
                action_id=action_id,
                env=env,
            )

    def _build_command(
        self, command: str, args: List[str], *, privileged: bool = False
    ) -> List[str]:
        """Build the final command list, handling Flatpak and privilege escalation."""
        cmd = [command] + args

        # Privilege escalation via pkexec
        if privileged:
            cmd = ["pkexec"] + cmd

        # Flatpak sandbox detection
        if os.path.exists("/.flatpak-info") and cmd[0] != "flatpak-spawn":
            cmd = ["flatpak-spawn", "--host"] + cmd

        return cmd

    def _execute_subprocess(
        self,
        cmd: List[str],
        *,
        timeout: int,
        action_id: str,
        env: Optional[Dict[str, str]],
    ) -> ActionResult:
        """Run the subprocess and return an ActionResult."""
        run_env = None
        if env:
            run_env = {**os.environ, **env}

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=run_env,
            )

            stdout = (proc.stdout or "")[:MAX_STDOUT]
            stderr = (proc.stderr or "")[:MAX_STDERR]

            if proc.returncode == 0:
                return ActionResult(
                    success=True,
                    message=stdout.strip()[:300] or "OK",
                    exit_code=0,
                    stdout=stdout,
                    stderr=stderr,
                    action_id=action_id,
                )
            else:
                return ActionResult(
                    success=False,
                    message=f"Exit {proc.returncode}: {stderr.strip()[:300]}",
                    exit_code=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    action_id=action_id,
                )

        except subprocess.TimeoutExpired:
            return ActionResult.fail(
                f"Command timed out after {timeout}s",
                exit_code=-1,
                action_id=action_id,
            )
        except FileNotFoundError:
            return ActionResult.fail(
                f"Command not found: {cmd[0]}",
                exit_code=127,
                action_id=action_id,
            )
        except OSError as exc:
            return ActionResult.fail(
                f"OS error: {exc}",
                exit_code=-1,
                action_id=action_id,
            )

    def _log_action(self, cmd: List[str], result: ActionResult):
        """Append action to JSON-lines log file."""
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
            entry = {
                "ts": result.timestamp,
                "cmd": cmd,
                "success": result.success,
                "exit_code": result.exit_code,
                "preview": result.preview,
                "message": result.message[:200],
            }
            with open(_ACTION_LOG_FILE, "a") as fh:
                fh.write(json.dumps(entry) + "\n")

            # Trim log if too large
            self._trim_log()
        except OSError:
            pass  # Non-critical — don't fail actions over logging

    def _trim_log(self):
        """Keep log file bounded to MAX_LOG_ENTRIES lines."""
        try:
            path = Path(_ACTION_LOG_FILE)
            if not path.exists():
                return
            lines = path.read_text().splitlines()
            if len(lines) > MAX_LOG_ENTRIES:
                trimmed = lines[-MAX_LOG_ENTRIES:]
                path.write_text("\n".join(trimmed) + "\n")
        except OSError:
            pass

    @classmethod
    def get_action_log(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Read recent action log entries for diagnostics export."""
        try:
            path = Path(_ACTION_LOG_FILE)
            if not path.exists():
                return []
            lines = path.read_text().splitlines()
            entries = []
            for line in lines[-limit:]:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return entries
        except OSError:
            return []

    @classmethod
    def export_diagnostics(cls) -> Dict[str, Any]:
        """Export full diagnostics bundle (action log + system info)."""
        return {
            "version": "19.0.0",
            "exported_at": time.time(),
            "action_log": cls.get_action_log(limit=100),
            "dry_run_global": cls._dry_run_global,
        }
