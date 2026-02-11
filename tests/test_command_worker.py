"""
Tests for CommandWorker adapter (v23.0 Architecture Hardening).

Tests cover:
- CommandRunner integration
- Signal mapping to BaseWorker protocol
- ActionResult return
- Progress reporting
- Cancellation support
- Error handling
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

_SKIP_QT = os.environ.get("DISPLAY") is None and os.environ.get("WAYLAND_DISPLAY") is None

# Add source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

try:
    from PyQt6.QtCore import QCoreApplication
    from core.workers.command_worker import CommandWorker
    from core.executor.action_result import ActionResult
except ImportError:
    _SKIP_QT = True

pytestmark = pytest.mark.skipif(_SKIP_QT, reason="Qt/PyQt6 not available in headless environment")


class TestCommandWorkerInit(unittest.TestCase):
    """Tests for CommandWorker initialization."""

    def test_init_with_defaults(self):
        """CommandWorker initializes with minimal args."""
        worker = CommandWorker("echo", ["hello"])
        self.assertEqual(worker.command, "echo")
        self.assertEqual(worker.args, ["hello"])
        self.assertEqual(worker.description, "")

    def test_init_with_description(self):
        """CommandWorker stores description."""
        worker = CommandWorker("dnf", ["update"], description="Updating system")
        self.assertEqual(worker.description, "Updating system")

    def test_init_empty_args(self):
        """CommandWorker handles empty args list."""
        worker = CommandWorker("uptime", [])
        self.assertEqual(worker.args, [])

    def test_init_none_args(self):
        """CommandWorker converts None args to empty list."""
        worker = CommandWorker("uptime", None)
        self.assertEqual(worker.args, [])


@patch('core.workers.command_worker.CommandRunner')
class TestCommandWorkerExecution(unittest.TestCase):
    """Tests for CommandWorker command execution."""

    def test_do_work_success(self, mock_runner_class):
        """do_work returns ActionResult on success."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("echo", ["test"], description="Echo test")

        # Simulate command completion
        def run_command_side_effect(cmd, args):
            # Trigger finished signal immediately
            worker._on_finished(0)

        mock_runner.run_command.side_effect = run_command_side_effect

        result = worker.do_work()

        # Verify result
        self.assertIsInstance(result, ActionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("test", result.message.lower())

    def test_do_work_failure(self, mock_runner_class):
        """do_work returns ActionResult with success=False on error."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("false", [], description="Always fails")

        def run_command_side_effect(cmd, args):
            worker._on_finished(1)  # Non-zero exit code

        mock_runner.run_command.side_effect = run_command_side_effect

        result = worker.do_work()

        self.assertIsInstance(result, ActionResult)
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)

    def test_output_capture(self, mock_runner_class):
        """do_work captures stdout from CommandRunner."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("echo", ["hello world"])

        def run_command_side_effect(cmd, args):
            worker._on_output("hello world\n")
            worker._on_finished(0)

        mock_runner.run_command.side_effect = run_command_side_effect

        result = worker.do_work()

        self.assertTrue(result.success)
        self.assertIn("hello world", result.stdout)

    def test_progress_reporting(self, mock_runner_class):
        """Progress updates are forwarded to BaseWorker signal."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("dnf", ["update"], description="Updating")
        progress_received = []

        # Connect to progress signal
        worker.progress.connect(lambda msg, pct: progress_received.append((msg, pct)))

        def run_command_side_effect(cmd, args):
            worker._on_progress(25, "Installing package 1/4")
            worker._on_progress(50, "Installing package 2/4")
            worker._on_finished(0)

        mock_runner.run_command.side_effect = run_command_side_effect

        worker.do_work()

        # Verify progress was reported
        self.assertEqual(len(progress_received), 2)
        self.assertEqual(progress_received[0], ("Installing package 1/4", 25))
        self.assertEqual(progress_received[1], ("Installing package 2/4", 50))

    def test_error_handling(self, mock_runner_class):
        """Errors from CommandRunner are handled gracefully."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("badcommand", [])

        def run_command_side_effect(cmd, args):
            worker._on_error("Command not found")
            worker._on_finished(127)

        mock_runner.run_command.side_effect = run_command_side_effect

        result = worker.do_work()

        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 127)


@patch('core.workers.command_worker.CommandRunner')
class TestCommandWorkerCancellation(unittest.TestCase):
    """Tests for CommandWorker cancellation."""

    def test_cancel_stops_runner(self, mock_runner_class):
        """cancel() calls CommandRunner.stop()."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("sleep", ["10"])

        # Start worker (don't complete)
        mock_runner.run_command.side_effect = lambda cmd, args: None
        worker._runner = mock_runner

        # Cancel
        worker.cancel()

        # Verify stop was called
        mock_runner.stop.assert_called_once()

    def test_cancel_quits_event_loop(self, mock_runner_class):
        """cancel() quits the event loop."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("sleep", ["10"])
        worker._runner = mock_runner

        # Mock event loop
        mock_event_loop = MagicMock()
        mock_event_loop.isRunning.return_value = True
        worker._event_loop = mock_event_loop

        worker.cancel()

        # Verify quit was called
        mock_event_loop.quit.assert_called_once()

    def test_cancellation_during_output(self, mock_runner_class):
        """Output is not buffered when cancelled."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("echo", ["test"])
        worker._output_buffer = []

        # Cancel before output
        worker.cancel()

        worker._on_output("should not be captured")

        # Verify output was not buffered
        self.assertEqual(len(worker._output_buffer), 0)


@patch('core.workers.command_worker.CommandRunner')
class TestCommandWorkerEdgeCases(unittest.TestCase):
    """Tests for CommandWorker edge cases."""

    def test_no_result_from_worker(self, mock_runner_class):
        """Handles non-zero exit paths and still returns ActionResult."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("test", [])

        # Simulate completion with non-zero exit code
        mock_runner.run_command.side_effect = lambda cmd, args: worker._on_finished(1)

        result = worker.do_work()

        # Should still return ActionResult with success=False
        self.assertIsInstance(result, ActionResult)
        self.assertFalse(result.success)

    def test_negative_progress_percentage(self, mock_runner_class):
        """Negative progress percentages are clamped to 0."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("test", [])
        progress_received = []
        worker.progress.connect(lambda msg, pct: progress_received.append((msg, pct)))

        worker._on_progress(-1, "Indeterminate progress")

        # Verify clamped to 0
        self.assertEqual(progress_received[0][1], 0)

    def test_progress_over_100(self, mock_runner_class):
        """Progress percentages over 100 are clamped to 100."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("test", [])
        progress_received = []
        worker.progress.connect(lambda msg, pct: progress_received.append((msg, pct)))

        worker._on_progress(150, "Overshoot")

        # Verify clamped to 100
        self.assertEqual(progress_received[0][1], 100)

    def test_multiple_outputs(self, mock_runner_class):
        """Multiple output chunks are concatenated."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        worker = CommandWorker("test", [])

        def run_command_side_effect(cmd, args):
            worker._on_output("Line 1\n")
            worker._on_output("Line 2\n")
            worker._on_output("Line 3")
            worker._on_finished(0)

        mock_runner.run_command.side_effect = run_command_side_effect

        result = worker.do_work()

        self.assertEqual(result.stdout, "Line 1\nLine 2\nLine 3")


if __name__ == '__main__':
    # Initialize QCoreApplication for Qt signals
    if not _SKIP_QT:
        import sys
        app = QCoreApplication(sys.argv)
    unittest.main()
