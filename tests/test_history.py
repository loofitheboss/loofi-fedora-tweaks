"""
Tests for utils/history.py — HistoryManager.
Covers: log_change, get_last_action, undo_last_action,
history loading/saving, max entries limit, and error handling.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.history import HistoryManager


# ---------------------------------------------------------------------------
# TestHistoryInit — initialisation
# ---------------------------------------------------------------------------

class TestHistoryInit(unittest.TestCase):
    """Tests for HistoryManager initialisation."""

    @patch('utils.history.os.makedirs')
    def test_init_creates_directory(self, mock_makedirs):
        """__init__ creates the history directory."""
        _ = HistoryManager()  # noqa: F841
        mock_makedirs.assert_called_once()


# ---------------------------------------------------------------------------
# TestLogChange — adding history entries
# ---------------------------------------------------------------------------

class TestLogChange(unittest.TestCase):
    """Tests for log_change method."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpfile = os.path.join(self.tmpdir, "history.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('utils.history.os.makedirs')
    def test_log_change_creates_entry(self, mock_makedirs):
        """log_change adds an entry with timestamp, description, and undo_command."""
        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        hm.log_change("Enabled dark mode", ["gsettings", "set", "theme", "light"])

        with open(self.tmpfile) as f:
            history = json.load(f)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["description"], "Enabled dark mode")
        self.assertEqual(history[0]["undo_command"], ["gsettings", "set", "theme", "light"])
        self.assertIn("timestamp", history[0])

    @patch('utils.history.os.makedirs')
    def test_log_change_appends_to_existing(self, mock_makedirs):
        """log_change appends to existing history."""
        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        hm.log_change("First action", ["echo", "undo1"])
        hm.log_change("Second action", ["echo", "undo2"])

        with open(self.tmpfile) as f:
            history = json.load(f)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["description"], "Second action")

    @patch('utils.history.os.makedirs')
    def test_log_change_enforces_max_50_entries(self, mock_makedirs):
        """log_change keeps only the last 50 entries."""
        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        for i in range(55):
            hm.log_change(f"Action {i}", ["echo", str(i)])

        with open(self.tmpfile) as f:
            history = json.load(f)

        self.assertEqual(len(history), 50)
        # Should keep the most recent entries
        self.assertEqual(history[-1]["description"], "Action 54")


# ---------------------------------------------------------------------------
# TestGetLastAction — retrieving last action
# ---------------------------------------------------------------------------

class TestGetLastAction(unittest.TestCase):
    """Tests for get_last_action method."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpfile = os.path.join(self.tmpdir, "history.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('utils.history.os.makedirs')
    def test_get_last_action_returns_last_entry(self, mock_makedirs):
        """get_last_action returns the most recent entry."""
        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        hm.log_change("First", ["echo", "1"])
        hm.log_change("Second", ["echo", "2"])

        last = hm.get_last_action()
        self.assertEqual(last["description"], "Second")

    @patch('utils.history.os.makedirs')
    def test_get_last_action_returns_none_when_empty(self, mock_makedirs):
        """get_last_action returns None when no history exists."""
        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        last = hm.get_last_action()
        self.assertIsNone(last)


# ---------------------------------------------------------------------------
# TestUndoLastAction — undo operations
# ---------------------------------------------------------------------------

class TestUndoLastAction(unittest.TestCase):
    """Tests for undo_last_action method."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpfile = os.path.join(self.tmpdir, "history.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('utils.history.subprocess.run')
    @patch('utils.history.os.makedirs')
    def test_undo_last_action_success(self, mock_makedirs, mock_run):
        """undo_last_action executes command and removes entry on success."""
        mock_run.return_value = MagicMock(returncode=0)

        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        hm.log_change("Test action", ["echo", "undo"])

        result = hm.undo_last_action()

        self.assertTrue(result.success)
        self.assertIn("Undid", result.message)
        mock_run.assert_called_once_with(["echo", "undo"], check=True)

    @patch('utils.history.os.makedirs')
    def test_undo_last_action_no_history(self, mock_makedirs):
        """undo_last_action returns failure when history is empty."""
        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        result = hm.undo_last_action()

        self.assertFalse(result.success)
        self.assertIn("No actions", result.message)

    @patch('utils.history.subprocess.run', side_effect=subprocess.CalledProcessError(1, "cmd"))
    @patch('utils.history.os.makedirs')
    def test_undo_last_action_command_failure(self, mock_makedirs, mock_run):
        """undo_last_action returns failure when undo command fails."""
        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        hm.log_change("Test action", ["false"])

        result = hm.undo_last_action()

        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestHistoryFilePersistence — file handling
# ---------------------------------------------------------------------------

class TestHistoryFilePersistence(unittest.TestCase):
    """Tests for history file loading edge cases."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpfile = os.path.join(self.tmpdir, "history.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('utils.history.os.makedirs')
    def test_load_history_corrupted_json(self, mock_makedirs):
        """Corrupted JSON returns empty list."""
        with open(self.tmpfile, "w") as f:
            f.write("not valid json{{{")

        hm = HistoryManager()
        hm.HISTORY_FILE = self.tmpfile

        last = hm.get_last_action()
        self.assertIsNone(last)

    @patch('utils.history.os.makedirs')
    def test_load_history_missing_file(self, mock_makedirs):
        """Missing history file returns empty list."""
        hm = HistoryManager()
        hm.HISTORY_FILE = os.path.join(self.tmpdir, "nonexistent.json")

        last = hm.get_last_action()
        self.assertIsNone(last)


if __name__ == '__main__':
    unittest.main()
