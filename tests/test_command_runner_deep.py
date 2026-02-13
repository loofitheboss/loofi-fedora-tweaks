"""Deep tests for utils/command_runner.py — CommandRunner with QProcess mocking."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from PyQt6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from utils.command_runner import CommandRunner


class TestCommandRunnerInit(unittest.TestCase):
    def test_creates_runner(self):
        runner = CommandRunner()
        self.assertIsNotNone(runner)
        self.assertIsNotNone(runner.process)

    def test_signals_exist(self):
        runner = CommandRunner()
        self.assertTrue(hasattr(runner, 'output_received'))
        self.assertTrue(hasattr(runner, 'finished'))
        self.assertTrue(hasattr(runner, 'error_occurred'))
        self.assertTrue(hasattr(runner, 'progress_update'))


class TestRunCommand(unittest.TestCase):
    @patch.object(CommandRunner, 'process', create=True)
    def test_normal_command(self, mock_proc):
        runner = CommandRunner()
        with patch("os.path.exists", return_value=False):
            runner.run_command("echo", ["hello"])

    @patch("os.path.exists", return_value=True)
    def test_flatpak_sandbox(self, mock_exists):
        runner = CommandRunner()
        with patch.object(runner.process, 'start') as mock_start:
            runner.run_command("echo", ["hello"])
            mock_start.assert_called_once()
            call_args = mock_start.call_args
            self.assertEqual(call_args[0][0], "flatpak-spawn")
            self.assertIn("--host", call_args[0][1])


class TestParseProgress(unittest.TestCase):
    def setUp(self):
        self.runner = CommandRunner()
        self.progress_calls = []
        self.runner.progress_update.connect(
            lambda pct, msg: self.progress_calls.append((pct, msg))
        )

    def test_dnf_bar(self):
        self.runner.parse_progress("[=====     ]")
        self.assertEqual(len(self.progress_calls), 1)
        self.assertEqual(self.progress_calls[0][0], 50)

    def test_full_bar(self):
        self.runner.parse_progress("[==========]")
        self.assertEqual(self.progress_calls[0][0], 100)

    def test_downloading_text(self):
        self.runner.parse_progress("Downloading packages...")
        self.assertEqual(self.progress_calls[0][0], -1)
        self.assertIn("Downloading", self.progress_calls[0][1])

    def test_installing_text(self):
        self.runner.parse_progress("Installing packages...")
        self.assertEqual(self.progress_calls[0][0], -1)
        self.assertIn("Installing", self.progress_calls[0][1])

    def test_verifying_text(self):
        self.runner.parse_progress("Verifying packages...")
        self.assertEqual(self.progress_calls[0][0], -1)
        self.assertIn("Verifying", self.progress_calls[0][1])

    def test_paren_percent(self):
        self.runner.parse_progress("Progress ( 45%)")
        self.assertEqual(self.progress_calls[0][0], 45)

    def test_flatpak_percent(self):
        self.runner.parse_progress("  75%")
        self.assertEqual(self.progress_calls[0][0], 75)

    def test_no_match(self):
        self.runner.parse_progress("random text")
        self.assertEqual(len(self.progress_calls), 0)


class TestHandleFinished(unittest.TestCase):
    def test_success(self):
        runner = CommandRunner()
        signals = []
        runner.finished.connect(lambda code: signals.append(code))
        runner.handle_finished(0, 0)
        self.assertEqual(signals, [0])

    def test_failure(self):
        runner = CommandRunner()
        signals = []
        runner.finished.connect(lambda code: signals.append(code))
        runner.handle_finished(1, 1)
        self.assertEqual(signals, [1])


class TestHandleError(unittest.TestCase):
    def test_error(self):
        runner = CommandRunner()
        errors = []
        runner.error_occurred.connect(lambda msg: errors.append(msg))
        runner.handle_error("ProcessCrashed")
        self.assertEqual(len(errors), 1)


class TestStop(unittest.TestCase):
    def test_stop_running(self):
        runner = CommandRunner()
        from PyQt6.QtCore import QProcess
        with patch.object(runner.process, 'state', return_value=QProcess.ProcessState.Running):
            with patch.object(runner.process, 'terminate') as mock_term:
                runner.stop()
                mock_term.assert_called_once()

    def test_stop_not_running(self):
        runner = CommandRunner()
        from PyQt6.QtCore import QProcess
        with patch.object(runner.process, 'state', return_value=QProcess.ProcessState.NotRunning):
            with patch.object(runner.process, 'terminate') as mock_term:
                runner.stop()
                mock_term.assert_not_called()


class TestHandleStdout(unittest.TestCase):
    def test_emits_output(self):
        runner = CommandRunner()
        outputs = []
        runner.output_received.connect(lambda text: outputs.append(text))
        with patch.object(runner.process, 'readAllStandardOutput', return_value=b"test output"):
            runner.handle_stdout()
            self.assertEqual(len(outputs), 1)
            self.assertIn("test", outputs[0])


class TestHandleStderr(unittest.TestCase):
    def test_emits_output(self):
        runner = CommandRunner()
        outputs = []
        runner.output_received.connect(lambda text: outputs.append(text))
        with patch.object(runner.process, 'readAllStandardError', return_value=b"error text"):
            runner.handle_stderr()
            self.assertEqual(len(outputs), 1)
            self.assertIn("error", outputs[0])


if __name__ == "__main__":
    unittest.main()
