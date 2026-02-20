"""Async command execution via QProcess with timeout, progress, and Flatpak support."""
from PyQt6.QtCore import QProcess, pyqtSignal, QObject, QTimer
import re
from typing import Optional

from utils.log import get_logger

logger = get_logger(__name__)


class CommandRunner(QObject):
    output_received = pyqtSignal(str)
    stderr_received = pyqtSignal(str)
    finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(int, str)  # percentage, status_text

    # Cache Flatpak detection at class level
    _is_flatpak: Optional[bool] = None

    def __init__(self, timeout: int = 300000):
        """Initialize CommandRunner.

        Args:
            timeout: Command timeout in milliseconds (default 300000 = 5 min).
                     Set to 0 to disable timeout.
        """
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_finished)
        self.process.errorOccurred.connect(self.handle_error)

        self._timeout_ms = timeout
        self._timeout_timer: Optional[QTimer] = None
        self._kill_timer: Optional[QTimer] = None

    @classmethod
    def _detect_flatpak(cls) -> bool:
        """Detect if running inside Flatpak sandbox (cached)."""
        if cls._is_flatpak is None:
            import os
            cls._is_flatpak = os.path.exists('/.flatpak-info')
        return cls._is_flatpak

    def is_running(self) -> bool:
        """Check if a command is currently running."""
        return self.process.state() == QProcess.ProcessState.Running

    def run_command(self, command, args):
        """Start a command. Wraps with flatpak-spawn if in Flatpak sandbox."""
        if self._detect_flatpak() and command != "flatpak-spawn":
            new_args = ["--host", command] + args
            command = "flatpak-spawn"
            args = new_args

        self.process.start(command, args)

        # Start timeout timer if configured
        if self._timeout_ms > 0:
            self._timeout_timer = QTimer()
            self._timeout_timer.setSingleShot(True)
            self._timeout_timer.timeout.connect(self._on_timeout)
            self._timeout_timer.start(self._timeout_ms)

    def _on_timeout(self):
        """Handle command timeout — terminate then kill after grace period."""
        if self.is_running():
            logger.warning("Command timed out after %d ms, terminating", self._timeout_ms)
            self.error_occurred.emit("Command timed out")
            self.stop()

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        output = bytes(data).decode('utf-8', errors='replace')
        self.parse_progress(output)
        self.output_received.emit(output)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        output = bytes(data).decode('utf-8', errors='replace')
        # DNF often sends progress to stderr
        self.parse_progress(output)
        self.stderr_received.emit(output)
        # Backward compat: also emit via output_received
        self.output_received.emit(output)

    def parse_progress(self, text):
        # DNF regex for progress bar: [===       ]
        dnf_bar_match = re.search(r'\[(=+)( *)\]', text)
        if dnf_bar_match:
            equals = len(dnf_bar_match.group(1))
            spaces = len(dnf_bar_match.group(2))
            total = equals + spaces
            if total > 0:
                percent = int((equals / total) * 100)
                self.progress_update.emit(percent, "Processing...")
                return

        # DNF regex for text state (Downloading/Installing)
        if "Downloading" in text:
            self.progress_update.emit(-1, "Downloading Packages...")
            return
        if "Installing" in text:
            self.progress_update.emit(-1, "Installing...")
            return
        if "Verifying" in text:
            self.progress_update.emit(-1, "Verifying...")
            return

        # DNF/General Percentage: ( 45%)
        paren_percent = re.search(r'\(\s*(\d+)%\)', text)
        if paren_percent:
            try:
                percent = int(paren_percent.group(1))
                self.progress_update.emit(percent, "Processing...")
                return
            except (ValueError, IndexError) as e:
                logger.debug("Progress parse error (paren percent): %s", e)

        # Flatpak Percentage: 45% (often at start of line or standalone)
        flatpak_match = re.search(r'^\s*(\d+)%', text)
        if flatpak_match:
            try:
                percent = int(flatpak_match.group(1))
                self.progress_update.emit(percent, "Processing...")
                return
            except (ValueError, IndexError) as e:
                logger.debug("Progress parse error (flatpak percent): %s", e)

    def handle_finished(self, exit_code, exit_status):
        # Cancel timeout timers
        self._cancel_timers()

        if exit_status == QProcess.ExitStatus.CrashExit:
            logger.warning("Command crashed (exit code: %s)", exit_code)
            self.error_occurred.emit(f"Command crashed (exit code: {exit_code})")
        elif exit_code != 0:
            logger.debug("Command finished with non-zero exit: %s", exit_code)
        self.finished.emit(exit_code)

    def handle_error(self, error):
        self._cancel_timers()
        logger.warning("Command runner error: %s", error)
        self.error_occurred.emit(str(error))

    def stop(self):
        """Stop the running command with graceful escalation.

        Sends SIGTERM first, then SIGKILL after 5s grace period.
        """
        if self.is_running():
            self.process.terminate()
            # Set up kill timer as fallback
            self._kill_timer = QTimer()
            self._kill_timer.setSingleShot(True)
            self._kill_timer.timeout.connect(self._force_kill)
            self._kill_timer.start(5000)

    def _force_kill(self):
        """Force kill the process if it didn't terminate gracefully."""
        if self.is_running():
            logger.warning("Process did not terminate gracefully, sending SIGKILL")
            self.process.kill()

    def _cancel_timers(self):
        """Cancel any active timeout/kill timers."""
        if self._timeout_timer and self._timeout_timer.isActive():
            self._timeout_timer.stop()
        if self._kill_timer and self._kill_timer.isActive():
            self._kill_timer.stop()
