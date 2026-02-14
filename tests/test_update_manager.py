"""
Tests for utils/update_manager.py — Smart Update Manager.
Part of v37.0.0 "Pinnacle".

Covers: check_updates (DNF + rpm-ostree), preview_conflicts,
schedule_update, rollback_last, get_update_history.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.update_manager import (
    UpdateManager, UpdateEntry, ConflictEntry, ScheduledUpdate,
)


class TestUpdateManagerCheckUpdates(unittest.TestCase):
    """Tests for UpdateManager.check_updates()."""

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    @patch("utils.update_manager.subprocess.run")
    def test_check_updates_dnf_with_updates(self, mock_run, mock_atomic):
        """DNF check-update returns available packages."""
        mock_run.return_value = MagicMock(
            returncode=100,
            stdout=(
                "vim-enhanced.x86_64          9.1.0-1.fc43          updates\n"
                "kernel.x86_64                6.10.0-1.fc43         updates\n"
            ),
            stderr="",
        )
        result = UpdateManager.check_updates()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "vim-enhanced")
        self.assertEqual(result[0].version, "9.1.0-1.fc43")
        self.assertEqual(result[0].repo, "updates")

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    @patch("utils.update_manager.subprocess.run")
    def test_check_updates_dnf_no_updates(self, mock_run, mock_atomic):
        """DNF check-update returns 0 when no updates available."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = UpdateManager.check_updates()
        self.assertEqual(len(result), 0)

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    @patch("utils.update_manager.subprocess.run")
    def test_check_updates_dnf_timeout(self, mock_run, mock_atomic):
        """DNF check-update timeout returns empty list."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dnf", timeout=120)
        result = UpdateManager.check_updates()
        self.assertEqual(len(result), 0)

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=True)
    @patch("utils.update_manager.subprocess.run")
    def test_check_updates_ostree(self, mock_run, mock_atomic):
        """rpm-ostree upgrade --preview lists upgradeable packages."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Checking for updates...\n"
                "============\n"
                "Upgraded vim-enhanced 9.0-1.fc43 -> 9.1-1.fc43\n"
                "Added new-pkg 1.0-1.fc43\n"
            ),
            stderr="",
        )
        result = UpdateManager.check_updates()
        self.assertGreaterEqual(len(result), 1)

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=True)
    @patch("utils.update_manager.subprocess.run")
    def test_check_updates_ostree_failure(self, mock_run, mock_atomic):
        """rpm-ostree failure returns empty list."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = UpdateManager.check_updates()
        self.assertEqual(len(result), 0)


class TestUpdateManagerConflicts(unittest.TestCase):
    """Tests for UpdateManager.preview_conflicts()."""

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    @patch("utils.update_manager.subprocess.run")
    def test_preview_no_conflicts(self, mock_run, mock_atomic):
        """No conflicts returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = UpdateManager.preview_conflicts()
        self.assertEqual(len(result), 0)

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    @patch("utils.update_manager.subprocess.run")
    def test_preview_with_conflicts(self, mock_run, mock_atomic):
        """Conflict lines in stderr are captured."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: nothing provides libfoo needed by bar-1.0\n",
        )
        result = UpdateManager.preview_conflicts(["bar"])
        self.assertEqual(len(result), 1)
        self.assertIn("nothing provides", result[0].reason)

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=True)
    @patch("utils.update_manager.subprocess.run")
    def test_preview_conflicts_ostree(self, mock_run, mock_atomic):
        """rpm-ostree conflict detection."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: Conflict with package foo\n",
        )
        result = UpdateManager.preview_conflicts()
        self.assertEqual(len(result), 1)


class TestUpdateManagerSchedule(unittest.TestCase):
    """Tests for UpdateManager.schedule_update()."""

    def test_schedule_update_basic(self):
        """Schedule returns valid ScheduledUpdate."""
        result = UpdateManager.schedule_update(packages=["vim"], when="03:00")
        self.assertIsInstance(result, ScheduledUpdate)
        self.assertEqual(result.packages, ["vim"])
        self.assertEqual(result.scheduled_time, "03:00")
        self.assertTrue(result.id.startswith("loofi-update-"))
        self.assertTrue(result.timer_unit.endswith(".timer"))

    def test_schedule_update_no_packages(self):
        """Schedule with no packages uses empty list."""
        result = UpdateManager.schedule_update()
        self.assertEqual(result.packages, [])

    @patch("utils.update_manager.SystemManager.get_package_manager", return_value="dnf")
    def test_get_schedule_commands_dnf(self, mock_pm):
        """Schedule commands for DNF."""
        schedule = ScheduledUpdate(
            id="loofi-update-test",
            packages=["vim"],
            scheduled_time="03:00",
            timer_unit="loofi-update-test.timer",
        )
        commands = UpdateManager.get_schedule_commands(schedule)
        self.assertEqual(len(commands), 4)
        # First two are write_file, last two are systemctl
        self.assertIn("tee", commands[0][1])
        self.assertIn("systemctl", commands[2][1])

    @patch("utils.update_manager.SystemManager.get_package_manager", return_value="rpm-ostree")
    def test_get_schedule_commands_ostree(self, mock_pm):
        """Schedule commands for rpm-ostree."""
        schedule = ScheduledUpdate(
            id="loofi-update-test",
            packages=[],
            scheduled_time="daily",
            timer_unit="loofi-update-test.timer",
        )
        commands = UpdateManager.get_schedule_commands(schedule)
        self.assertEqual(len(commands), 4)


class TestUpdateManagerRollback(unittest.TestCase):
    """Tests for UpdateManager.rollback_last()."""

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    def test_rollback_dnf(self, mock_atomic):
        """DNF rollback returns history undo command."""
        binary, args, desc = UpdateManager.rollback_last()
        self.assertEqual(binary, "pkexec")
        self.assertIn("history", args)
        self.assertIn("undo", args)

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=True)
    def test_rollback_ostree(self, mock_atomic):
        """rpm-ostree rollback returns rollback command."""
        binary, args, desc = UpdateManager.rollback_last()
        self.assertEqual(binary, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("rollback", args)


class TestUpdateManagerHistory(unittest.TestCase):
    """Tests for UpdateManager.get_update_history()."""

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    @patch("utils.update_manager.subprocess.run")
    def test_history_dnf(self, mock_run, mock_atomic):
        """DNF history parsing."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "   1 | update            | 2026-02-14 | Update\n"
                "   2 | install vim       | 2026-02-13 | Install\n"
            ),
            stderr="",
        )
        result = UpdateManager.get_update_history(limit=5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "1")

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=True)
    @patch("utils.update_manager.subprocess.run")
    def test_history_ostree(self, mock_run, mock_atomic):
        """rpm-ostree status --json parsing."""
        import json
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "deployments": [
                    {"id": "deploy1", "timestamp": "2026-02-14", "booted": True, "requested-packages": ["vim"]},
                    {"id": "deploy2", "timestamp": "2026-02-13", "booted": False, "requested-packages": []},
                ]
            }),
            stderr="",
        )
        result = UpdateManager.get_update_history()
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["booted"])

    @patch("utils.update_manager.SystemManager.is_atomic", return_value=False)
    @patch("utils.update_manager.subprocess.run")
    def test_history_timeout(self, mock_run, mock_atomic):
        """History timeout returns empty list."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dnf", timeout=30)
        result = UpdateManager.get_update_history()
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
