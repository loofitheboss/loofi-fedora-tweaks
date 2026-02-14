"""
Tests for utils/backup_wizard.py — Backup Wizard.
Part of v37.0.0 "Pinnacle" — T24.

Covers: detect_backup_tool, get_available_tools, create_snapshot,
list_snapshots (Timeshift + Snapper), restore_snapshot, delete_snapshot,
get_backup_status.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.backup_wizard import BackupWizard, SnapshotEntry, SnapshotResult


class TestToolDetection(unittest.TestCase):
    """Tests for detect_backup_tool() and get_available_tools()."""

    @patch("utils.backup_wizard.shutil.which")
    def test_detect_timeshift(self, mock_which):
        mock_which.side_effect = lambda t: "/usr/bin/timeshift" if t == "timeshift" else None
        self.assertEqual(BackupWizard.detect_backup_tool(), "timeshift")

    @patch("utils.backup_wizard.shutil.which")
    def test_detect_snapper(self, mock_which):
        mock_which.side_effect = lambda t: "/usr/bin/snapper" if t == "snapper" else None
        self.assertEqual(BackupWizard.detect_backup_tool(), "snapper")

    @patch("utils.backup_wizard.shutil.which", return_value=None)
    def test_detect_none(self, mock_which):
        self.assertEqual(BackupWizard.detect_backup_tool(), "none")

    @patch("utils.backup_wizard.shutil.which")
    def test_both_prefers_timeshift(self, mock_which):
        mock_which.return_value = "/usr/bin/tool"
        self.assertEqual(BackupWizard.detect_backup_tool(), "timeshift")

    @patch("utils.backup_wizard.shutil.which")
    def test_get_available_tools(self, mock_which):
        mock_which.side_effect = lambda t: "/usr/bin/snapper" if t == "snapper" else None
        result = BackupWizard.get_available_tools()
        self.assertEqual(result, ["snapper"])

    @patch("utils.backup_wizard.shutil.which", return_value=None)
    def test_is_available_false(self, mock_which):
        self.assertFalse(BackupWizard.is_available())

    @patch("utils.backup_wizard.shutil.which", return_value="/usr/bin/timeshift")
    def test_is_available_true(self, mock_which):
        self.assertTrue(BackupWizard.is_available())


class TestCreateSnapshot(unittest.TestCase):
    """Tests for create_snapshot()."""

    def test_create_timeshift(self):
        binary, args, desc = BackupWizard.create_snapshot(tool="timeshift", description="test")
        self.assertEqual(binary, "pkexec")
        self.assertIn("timeshift", args)
        self.assertIn("--create", args)
        self.assertIn("test", args)

    def test_create_snapper(self):
        binary, args, desc = BackupWizard.create_snapshot(tool="snapper", description="My backup")
        self.assertEqual(binary, "pkexec")
        self.assertIn("snapper", args)
        self.assertIn("create", args)
        self.assertIn("--description", args)

    @patch("utils.backup_wizard.shutil.which", return_value=None)
    def test_create_no_tool(self, mock_which):
        binary, args, desc = BackupWizard.create_snapshot()
        self.assertEqual(binary, "echo")

    @patch("utils.backup_wizard.shutil.which", return_value="/usr/bin/timeshift")
    def test_create_auto_detect(self, mock_which):
        binary, args, desc = BackupWizard.create_snapshot(description="auto")
        self.assertEqual(binary, "pkexec")
        self.assertIn("timeshift", args)

    def test_create_sanitizes_description(self):
        """Special characters removed from description."""
        binary, args, desc = BackupWizard.create_snapshot(
            tool="timeshift", description='test;"malicious'
        )
        # Semicolons and quotes should be stripped
        for arg in args:
            self.assertNotIn(";", arg)
            self.assertNotIn('"', arg)


class TestListSnapshots(unittest.TestCase):
    """Tests for list_snapshots()."""

    @patch("utils.backup_wizard.subprocess.run")
    def test_list_timeshift(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Device              : /dev/sda2\n"
                "---\n"
                "  1   2026-02-14_12-00-00   O   Test backup\n"
                "  2   2026-02-13_10-00-00   O   Before update\n"
            ),
        )
        result = BackupWizard.list_snapshots(tool="timeshift")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].tool, "timeshift")
        self.assertEqual(result[0].id, "1")

    @patch("utils.backup_wizard.subprocess.run")
    def test_list_snapper(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                " # | Type   | Pre # | Date                     | User | Cleanup | Description\n"
                "---+--------+-------+--------------------------+------+---------+-----------\n"
                " 0 | single |       |                          | root |         | current\n"
                " 1 | single |       | 2026-02-14 12:00:00      | root | number  | Loofi backup\n"
            ),
        )
        result = BackupWizard.list_snapshots(tool="snapper")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].tool, "snapper")

    @patch("utils.backup_wizard.subprocess.run")
    def test_list_timeshift_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="timeshift", timeout=30)
        result = BackupWizard.list_snapshots(tool="timeshift")
        self.assertEqual(len(result), 0)

    @patch("utils.backup_wizard.subprocess.run")
    def test_list_snapper_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = BackupWizard.list_snapshots(tool="snapper")
        self.assertEqual(len(result), 0)

    @patch("utils.backup_wizard.shutil.which", return_value=None)
    def test_list_no_tool(self, mock_which):
        result = BackupWizard.list_snapshots()
        self.assertEqual(len(result), 0)


class TestRestoreSnapshot(unittest.TestCase):
    """Tests for restore_snapshot()."""

    def test_restore_timeshift(self):
        binary, args, desc = BackupWizard.restore_snapshot("1", tool="timeshift")
        self.assertEqual(binary, "pkexec")
        self.assertIn("timeshift", args)
        self.assertIn("--restore", args)
        self.assertIn("1", args)

    def test_restore_snapper(self):
        binary, args, desc = BackupWizard.restore_snapshot("5", tool="snapper")
        self.assertEqual(binary, "pkexec")
        self.assertIn("snapper", args)
        self.assertIn("undochange", args)
        self.assertIn("5..0", args)

    @patch("utils.backup_wizard.shutil.which", return_value=None)
    def test_restore_no_tool(self, mock_which):
        binary, args, desc = BackupWizard.restore_snapshot("1")
        self.assertEqual(binary, "echo")


class TestDeleteSnapshot(unittest.TestCase):
    """Tests for delete_snapshot()."""

    def test_delete_timeshift(self):
        binary, args, desc = BackupWizard.delete_snapshot("1", tool="timeshift")
        self.assertEqual(binary, "pkexec")
        self.assertIn("timeshift", args)
        self.assertIn("--delete", args)

    def test_delete_snapper(self):
        binary, args, desc = BackupWizard.delete_snapshot("3", tool="snapper")
        self.assertEqual(binary, "pkexec")
        self.assertIn("snapper", args)
        self.assertIn("delete", args)
        self.assertIn("3", args)


class TestBackupStatus(unittest.TestCase):
    """Tests for get_backup_status()."""

    @patch("utils.backup_wizard.shutil.which", return_value=None)
    def test_status_no_tool(self, mock_which):
        status = BackupWizard.get_backup_status()
        self.assertEqual(status["tool"], "none")
        self.assertFalse(status["available"])
        self.assertEqual(status["snapshot_count"], 0)

    @patch("utils.backup_wizard.BackupWizard.list_snapshots")
    @patch("utils.backup_wizard.shutil.which", return_value="/usr/bin/timeshift")
    def test_status_with_snapshots(self, mock_which, mock_list):
        mock_list.return_value = [
            SnapshotEntry(id="1", date="2026-02-14", description="Test", tool="timeshift"),
            SnapshotEntry(id="2", date="2026-02-15", description="Latest", tool="timeshift"),
        ]
        status = BackupWizard.get_backup_status()
        self.assertEqual(status["tool"], "timeshift")
        self.assertTrue(status["available"])
        self.assertEqual(status["snapshot_count"], 2)
        self.assertEqual(status["last_snapshot"]["id"], "2")


if __name__ == "__main__":
    unittest.main()
