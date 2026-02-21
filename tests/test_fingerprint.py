"""
Tests for utils/fingerprint.py — FingerprintWorker.
Covers: worker init, enrollment progress, success, failure,
stop method, and exception handling.

Note: FingerprintWorker is a QThread subclass. We install a
comprehensive mock for PyQt6 before importing the module.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Build a proper PyQt6 mock that supports QThread and pyqtSignal
_mock_qtcore = MagicMock()

# Make pyqtSignal return a MagicMock when called (used as class-level descriptors)
_mock_qtcore.pyqtSignal = lambda *args, **kwargs: MagicMock()

# Make QThread a proper class that can be subclassed


class _MockQThread:
    def __init__(self, *args, **kwargs):
        pass
    def wait(self):
        pass

_mock_qtcore.QThread = _MockQThread

_orig_pyqt6_fp = sys.modules.get('PyQt6')
_orig_qtcore_fp = sys.modules.get('PyQt6.QtCore')

sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = _mock_qtcore

from utils.fingerprint import FingerprintWorker  # noqa: E402

# Restore originals so other tests are not polluted
for _mod, _orig in [('PyQt6', _orig_pyqt6_fp), ('PyQt6.QtCore', _orig_qtcore_fp)]:
    if _orig is not None:
        sys.modules[_mod] = _orig
    else:
        sys.modules.pop(_mod, None)


# ---------------------------------------------------------------------------
# TestFingerprintWorkerInit — worker initialisation
# ---------------------------------------------------------------------------

class TestFingerprintWorkerInit(unittest.TestCase):
    """Tests for FingerprintWorker initialisation."""

    def test_default_finger(self):
        """Default finger is right-index-finger."""
        worker = FingerprintWorker()
        self.assertEqual(worker.finger, "right-index-finger")

    def test_custom_finger(self):
        """Custom finger name is stored."""
        worker = FingerprintWorker(finger="left-thumb")
        self.assertEqual(worker.finger, "left-thumb")

    def test_initial_running_state(self):
        """Worker starts with is_running set to True."""
        worker = FingerprintWorker()
        self.assertTrue(worker.is_running)


# ---------------------------------------------------------------------------
# TestFingerprintWorkerRun — enrollment process
# ---------------------------------------------------------------------------

class TestFingerprintWorkerRun(unittest.TestCase):
    """Tests for the run() method with mocked subprocess."""

    @patch('utils.fingerprint.subprocess.Popen')
    def test_run_enrollment_completed(self, mock_popen):
        """run() emits enroll_success on 'Enrollment completed'."""
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [
            "Using device /net/reactivated/Fprint/Device/0\n",
            "Enrolling right-index-finger finger.\n",
            "Enrollment scan 1 of 5\n",
            "Enrollment completed\n",
            "",  # EOF
        ]
        mock_popen.return_value = mock_process

        worker = FingerprintWorker()
        worker.progress_update = MagicMock()
        worker.enroll_success = MagicMock()
        worker.enroll_fail = MagicMock()
        worker.run()

        worker.enroll_success.emit.assert_called_once()

    @patch('utils.fingerprint.subprocess.Popen')
    def test_run_enrollment_failed(self, mock_popen):
        """run() emits enroll_fail on failure line."""
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [
            "Using device /net/reactivated/Fprint/Device/0\n",
            "Enrollment failed: timeout\n",
            "",
        ]
        mock_popen.return_value = mock_process

        worker = FingerprintWorker()
        worker.progress_update = MagicMock()
        worker.enroll_success = MagicMock()
        worker.enroll_fail = MagicMock()
        worker.run()

        worker.enroll_fail.emit.assert_called_once()

    @patch('utils.fingerprint.subprocess.Popen', side_effect=OSError("fprintd not found"))
    def test_run_handles_exception(self, mock_popen):
        """run() emits enroll_fail on exception."""
        worker = FingerprintWorker()
        worker.progress_update = MagicMock()
        worker.enroll_success = MagicMock()
        worker.enroll_fail = MagicMock()
        worker.run()

        worker.enroll_fail.emit.assert_called_once_with("fprintd not found")

    @patch('utils.fingerprint.subprocess.Popen')
    def test_run_emits_progress_updates(self, mock_popen):
        """run() emits progress_update for each non-empty line."""
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [
            "Enrollment scan 1 of 5\n",
            "Enrollment completed\n",
            "",
        ]
        mock_popen.return_value = mock_process

        worker = FingerprintWorker()
        worker.progress_update = MagicMock()
        worker.enroll_success = MagicMock()
        worker.enroll_fail = MagicMock()
        worker.run()

        self.assertEqual(worker.progress_update.emit.call_count, 2)


# ---------------------------------------------------------------------------
# TestFingerprintWorkerStop — stopping the worker
# ---------------------------------------------------------------------------

class TestFingerprintWorkerStop(unittest.TestCase):
    """Tests for the stop() method."""

    def test_stop_sets_is_running_false(self):
        """stop() sets is_running to False."""
        worker = FingerprintWorker()
        worker.stop()
        self.assertFalse(worker.is_running)

    def test_stop_from_running_state(self):
        """stop() transitions from running to stopped."""
        worker = FingerprintWorker()
        self.assertTrue(worker.is_running)
        worker.stop()
        self.assertFalse(worker.is_running)


if __name__ == '__main__':
    unittest.main()
