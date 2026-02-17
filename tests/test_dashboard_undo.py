"""Tests for utils/history.py — undo and recent changes features."""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.history import HistoryManager, HistoryEntry


class TestHistoryEntry(unittest.TestCase):
    """Tests for HistoryEntry dataclass."""

    def test_from_dict(self):
        """Test creating HistoryEntry from dict."""
        data = {
            "id": "abc123",
            "timestamp": "2026-01-01T00:00:00",
            "description": "Changed theme",
            "undo_command": ["gsettings", "set", "theme", "dark"],
        }
        entry = HistoryEntry.from_dict(data)

        self.assertEqual(entry.id, "abc123")
        self.assertEqual(entry.description, "Changed theme")
        self.assertEqual(len(entry.undo_command), 4)

    def test_from_dict_missing_id(self):
        """Test from_dict generates ID when missing."""
        data = {"timestamp": "", "description": "Test", "undo_command": []}
        entry = HistoryEntry.from_dict(data)

        self.assertTrue(len(entry.id) > 0)

    def test_to_dict(self):
        """Test serializing HistoryEntry to dict."""
        entry = HistoryEntry(
            id="abc", timestamp="2026-01-01", description="Test", undo_command=["ls"],
        )
        d = entry.to_dict()

        self.assertEqual(d["id"], "abc")
        self.assertEqual(d["description"], "Test")


class TestHistoryManagerGetRecent(unittest.TestCase):
    """Tests for HistoryManager.get_recent()."""

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    @patch('utils.history.os.makedirs')
    def test_get_recent_empty_history(self, mock_makedirs, mock_file, mock_exists):
        """Test get_recent with empty history."""
        mock_exists.return_value = True

        mgr = HistoryManager()
        recent = mgr.get_recent(3)

        self.assertEqual(len(recent), 0)

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    def test_get_recent_returns_entries(self, mock_json, mock_makedirs, mock_file, mock_exists):
        """Test get_recent returns HistoryEntry objects."""
        mock_exists.return_value = True
        mock_json.return_value = [
            {"id": "1", "timestamp": "t1", "description": "Action 1", "undo_command": ["cmd1"]},
            {"id": "2", "timestamp": "t2", "description": "Action 2", "undo_command": ["cmd2"]},
            {"id": "3", "timestamp": "t3", "description": "Action 3", "undo_command": ["cmd3"]},
        ]

        mgr = HistoryManager()
        recent = mgr.get_recent(2)

        self.assertEqual(len(recent), 2)
        self.assertIsInstance(recent[0], HistoryEntry)
        # Most recent first
        self.assertEqual(recent[0].id, "3")
        self.assertEqual(recent[1].id, "2")

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    def test_get_recent_fewer_than_count(self, mock_json, mock_makedirs, mock_file, mock_exists):
        """Test get_recent when history has fewer entries than requested."""
        mock_exists.return_value = True
        mock_json.return_value = [
            {"id": "1", "timestamp": "t1", "description": "Only one", "undo_command": []},
        ]

        mgr = HistoryManager()
        recent = mgr.get_recent(5)

        self.assertEqual(len(recent), 1)


class TestHistoryManagerCanUndo(unittest.TestCase):
    """Tests for HistoryManager.can_undo()."""

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    @patch('utils.history.os.makedirs')
    def test_cannot_undo_empty(self, mock_makedirs, mock_file, mock_exists):
        """Test can_undo returns False for empty history."""
        mock_exists.return_value = True

        mgr = HistoryManager()
        self.assertFalse(mgr.can_undo())

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    def test_can_undo_with_commands(self, mock_json, mock_makedirs, mock_file, mock_exists):
        """Test can_undo returns True when entries have undo commands."""
        mock_exists.return_value = True
        mock_json.return_value = [
            {"id": "1", "timestamp": "t1", "description": "Action", "undo_command": ["cmd"]},
        ]

        mgr = HistoryManager()
        self.assertTrue(mgr.can_undo())

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    def test_cannot_undo_no_commands(self, mock_json, mock_makedirs, mock_file, mock_exists):
        """Test can_undo returns False when entries have empty undo commands."""
        mock_exists.return_value = True
        mock_json.return_value = [
            {"id": "1", "timestamp": "t1", "description": "No undo", "undo_command": []},
        ]

        mgr = HistoryManager()
        self.assertFalse(mgr.can_undo())


class TestHistoryManagerUndoAction(unittest.TestCase):
    """Tests for HistoryManager.undo_action()."""

    @patch('utils.history.subprocess.run')
    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    @patch('utils.history.json.dump')
    def test_undo_specific_action_success(self, mock_dump, mock_json, mock_makedirs, mock_file, mock_exists, mock_run):
        """Test undoing a specific action by ID."""
        mock_exists.return_value = True
        mock_json.return_value = [
            {"id": "keep", "timestamp": "t1", "description": "Keep", "undo_command": ["cmd1"]},
            {"id": "target", "timestamp": "t2", "description": "Target", "undo_command": ["cmd2"]},
        ]
        mock_run.return_value = MagicMock(returncode=0)

        mgr = HistoryManager()
        result = mgr.undo_action("target")

        self.assertTrue(result.success)
        self.assertIn("Target", result.message)
        mock_run.assert_called_once_with(["cmd2"], check=True, timeout=60)

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    def test_undo_action_not_found(self, mock_json, mock_makedirs, mock_file, mock_exists):
        """Test undoing a non-existent action returns failure."""
        mock_exists.return_value = True
        mock_json.return_value = []

        mgr = HistoryManager()
        result = mgr.undo_action("nonexistent")

        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    def test_undo_action_no_command(self, mock_json, mock_makedirs, mock_file, mock_exists):
        """Test undoing an action with no undo command."""
        mock_exists.return_value = True
        mock_json.return_value = [
            {"id": "no-cmd", "timestamp": "t1", "description": "No command", "undo_command": []},
        ]

        mgr = HistoryManager()
        result = mgr.undo_action("no-cmd")

        self.assertFalse(result.success)
        self.assertIn("No undo command", result.message)

    @patch('utils.history.subprocess.run')
    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.load')
    def test_undo_action_subprocess_failure(self, mock_json, mock_makedirs, mock_file, mock_exists, mock_run):
        """Test undoing an action when subprocess fails."""
        mock_exists.return_value = True
        mock_json.return_value = [
            {"id": "fail", "timestamp": "t1", "description": "Fail", "undo_command": ["bad-cmd"]},
        ]
        mock_run.side_effect = OSError("No such file or directory")

        mgr = HistoryManager()
        result = mgr.undo_action("fail")

        self.assertFalse(result.success)


class TestHistoryManagerLogChange(unittest.TestCase):
    """Tests for HistoryManager.log_change() with ID field."""

    @patch('utils.history.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    @patch('utils.history.os.makedirs')
    @patch('utils.history.json.dump')
    def test_log_change_includes_id(self, mock_dump, mock_makedirs, mock_file, mock_exists):
        """Test that log_change includes an ID field in the entry."""
        mock_exists.return_value = True

        mgr = HistoryManager()
        mgr.log_change("Test action", ["gsettings", "reset"])

        # Verify json.dump was called
        self.assertTrue(mock_dump.called)
        # The first positional arg to json.dump is the data
        saved_data = mock_dump.call_args[0][0]
        self.assertGreater(len(saved_data), 0)
        self.assertIn("id", saved_data[0])
        self.assertTrue(len(saved_data[0]["id"]) > 0)


if __name__ == '__main__':
    unittest.main()
