"""
CommandWorker — Adapter bridging CommandRunner and BaseWorker.

Part of v23.0 Architecture Hardening.
Wraps existing CommandRunner to provide BaseWorker interface without breaking
25+ tabs that depend on CommandRunner directly.

Usage:
    ```python
    from core.workers import CommandWorker

    worker = CommandWorker("dnf", ["update", "-y"], description="Updating system...")
    worker.progress.connect(lambda msg, pct: print(f"{msg} - {pct}%"))
    worker.finished.connect(lambda result: print(f"Done: {result.message}"))
    worker.error.connect(lambda msg: print(f"Error: {msg}"))
    worker.start()
    ```
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from PyQt6.QtCore import QEventLoop
from utils.command_runner import CommandRunner

from core.executor.action_result import ActionResult
from core.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class CommandWorker(BaseWorker):
    """
    Background worker for running system commands via CommandRunner.

    Adapts CommandRunner's QProcess-based interface to BaseWorker's
    standardized signal protocol. Provides thread-safe command execution
    with progress reporting and ActionResult return.

    Features:
    - Flatpak-aware (auto-wraps with flatpak-spawn --host)
    - Progress parsing for DNF/Flatpak output
    - Cancellation support (terminates process)
    - Returns ActionResult with exit code, stdout, stderr

    Attributes:
        command: Command to execute (e.g., "dnf")
        args: Command arguments list
        description: Human-readable description for logging
    """

    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        description: str = "",
        parent: Optional[Any] = None,
    ):
        """
        Initialize command worker.

        Args:
            command: Command binary to execute
            args: List of command arguments (default: empty list)
            description: Human-readable action description
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.command = command
        self.args = args or []
        self.description = description

        # Internal state
        self._runner: Optional[CommandRunner] = None
        self._output_buffer: List[str] = []
        self._exit_code: Optional[int] = None
        self._event_loop: Optional[QEventLoop] = None

    def do_work(self) -> ActionResult:
        """
        Execute command and return ActionResult.

        Wraps CommandRunner in a QEventLoop to synchronously wait for
        completion within the worker thread context.

        Returns:
            ActionResult: Structured result with exit code and output
        """
        logger.debug(
            "CommandWorker executing: %s %s", self.command, " ".join(self.args)
        )

        # Initialize runner and connect signals
        self._runner = CommandRunner()
        self._output_buffer = []
        self._exit_code = None

        # Map CommandRunner signals to our internal handlers
        self._runner.output_received.connect(self._on_output)
        self._runner.progress_update.connect(self._on_progress)
        self._runner.finished.connect(self._on_finished)
        self._runner.error_occurred.connect(self._on_error)

        # Create event loop to wait for completion
        self._event_loop = QEventLoop()

        # Start command (may finish synchronously in tests/mocks)
        self._runner.run_command(self.command, self.args)

        # Run loop until command finishes, unless completion already happened
        if self._exit_code is None:
            self._event_loop.exec()

        # Build ActionResult from captured output
        stdout_text = "".join(self._output_buffer)
        success = self._exit_code == 0 if self._exit_code is not None else False

        result = ActionResult(
            success=success,
            message=self.description
            or f"Command {'succeeded' if success else 'failed'}",
            exit_code=self._exit_code,
            stdout=stdout_text,
            stderr="",  # CommandRunner merges stderr into output
            action_id=f"{self.command}_{self.args[0] if self.args else 'no_args'}",
        )

        logger.debug("CommandWorker completed with exit code %s", self._exit_code)
        return result

    def _on_output(self, text: str) -> None:
        """
        Handle output from CommandRunner.

        Args:
            text: Output chunk from stdout/stderr
        """
        if not self.is_cancelled():
            self._output_buffer.append(text)
            # Note: Progress is handled separately via _on_progress

    def _on_progress(self, percentage: int, message: str) -> None:
        """
        Handle progress updates from CommandRunner.

        Args:
            percentage: Progress percentage (0-100, or -1 for indeterminate)
            message: Progress message
        """
        if not self.is_cancelled():
            # Map CommandRunner's progress to BaseWorker's report_progress
            prog = max(0, min(100, percentage)) if percentage >= 0 else 0
            self.report_progress(message, prog)

    def _on_finished(self, exit_code: int) -> None:
        """
        Handle command completion from CommandRunner.

        Args:
            exit_code: Process exit code
        """
        self._exit_code = exit_code

        # Quit event loop to unblock do_work()
        if self._event_loop and self._event_loop.isRunning():
            self._event_loop.quit()

    def _on_error(self, error_msg: str) -> None:
        """
        Handle errors from CommandRunner.

        Args:
            error_msg: Error message
        """
        logger.warning("CommandWorker error: %s", error_msg)
        # Don't emit error signal here - let do_work() return ActionResult
        # with success=False and the error will propagate via BaseWorker.error

        # Still need to quit the event loop
        if self._event_loop and self._event_loop.isRunning():
            self._event_loop.quit()

    def cancel(self) -> None:
        """
        Cancel running command.

        Stops the CommandRunner process and sets cancellation flag.
        """
        super().cancel()

        if self._runner:
            logger.debug("Cancelling CommandRunner process")
            self._runner.stop()

        # Quit event loop if waiting
        if self._event_loop and self._event_loop.isRunning():
            self._event_loop.quit()
