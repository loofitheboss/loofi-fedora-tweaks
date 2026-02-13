"""
Tests for utils/focus_mode.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.focus_mode import FocusMode


class TestFocusMode(unittest.TestCase):
    """Tests for FocusMode manager."""

    def test_remove_focus_entries(self):
        """Focus block markers are removed from hosts text."""
        content = "127.0.0.1 localhost\n# LOOFI-FOCUS-MODE-START\n127.0.0.1 reddit.com\n# LOOFI-FOCUS-MODE-END\n::1 localhost"
        cleaned = FocusMode._remove_focus_entries(content)
        self.assertIn("127.0.0.1 localhost", cleaned)
        self.assertIn("::1 localhost", cleaned)
        self.assertNotIn("reddit.com", cleaned)

    @patch('utils.focus_mode.FocusMode.get_profile', return_value=None)
    def test_enable_missing_profile(self, mock_profile):
        """Enable fails if profile does not exist."""
        result = FocusMode.enable("missing")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])

    @patch('utils.focus_mode.FocusMode.save_config')
    @patch('utils.focus_mode.FocusMode.load_config', return_value={"active": False, "active_profile": None, "profiles": {}})
    @patch('utils.focus_mode.FocusMode._kill_processes', return_value=["discord"])
    @patch('utils.focus_mode.FocusMode._enable_dnd', return_value={"success": True, "message": "ok"})
    @patch('utils.focus_mode.FocusMode._block_domains', return_value={"success": True, "message": "blocked"})
    @patch('utils.focus_mode.FocusMode.get_profile')
    def test_enable_success_updates_state(self, mock_profile, mock_block, mock_dnd, mock_kill, mock_load, mock_save):
        """Enable executes blockers, DND, process kill and sets active profile."""
        mock_profile.return_value = {
            "blocked_domains": ["reddit.com"],
            "enable_dnd": True,
            "kill_processes": ["discord"],
        }

        result = FocusMode.enable("default")

        self.assertTrue(result["success"])
        self.assertTrue(result["hosts_modified"])
        self.assertTrue(result["dnd_enabled"])
        self.assertEqual(result["processes_killed"], ["discord"])
        mock_save.assert_called_once()

    @patch('utils.focus_mode.FocusMode.save_config')
    @patch('utils.focus_mode.FocusMode.load_config', return_value={"active": True, "active_profile": "default", "profiles": {}})
    @patch('utils.focus_mode.FocusMode._disable_dnd', return_value={"success": True, "message": "ok"})
    @patch('utils.focus_mode.FocusMode._restore_hosts', return_value={"success": True, "message": "ok"})
    def test_disable_success(self, mock_restore, mock_dnd, mock_load, mock_save):
        """Disable restores state and reports success."""
        result = FocusMode.disable()
        self.assertTrue(result["success"])
        self.assertTrue(result["hosts_restored"])
        self.assertTrue(result["dnd_disabled"])

    @patch('utils.focus_mode.FocusMode.disable', return_value={"success": True, "message": "off"})
    @patch('utils.focus_mode.FocusMode.is_active', return_value=True)
    def test_toggle_when_active_calls_disable(self, mock_active, mock_disable):
        """toggle() delegates to disable when already active."""
        result = FocusMode.toggle()
        self.assertTrue(result["success"])
        mock_disable.assert_called_once()

    @patch('utils.focus_mode.FocusMode._gnome_dnd', return_value={"success": True, "message": "gnome"})
    @patch('utils.focus_mode.FocusMode._kde_dnd', return_value={"success": False, "message": "kde fail"})
    def test_enable_dnd_fallbacks_to_gnome(self, mock_kde, mock_gnome):
        """DND enable falls back from KDE to GNOME when needed."""
        result = FocusMode._enable_dnd()
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "gnome")

    @patch('utils.focus_mode.subprocess.run')
    def test_kde_dnd_enable_success(self, mock_run):
        """KDE DND helper returns success when dbus command succeeds."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = FocusMode._kde_dnd(True)
        self.assertTrue(result["success"])

    @patch('utils.focus_mode.subprocess.run')
    def test_kill_processes_filters_successes(self, mock_run):
        """Only successfully killed process names are returned."""
        mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=1)]
        killed = FocusMode._kill_processes(["steam", "discord"])
        self.assertEqual(killed, ["steam"])

    @patch('utils.focus_mode.subprocess.run')
    def test_get_running_distractions(self, mock_run):
        """Process scan returns only present distraction names."""
        mock_run.return_value = MagicMock(stdout="steam\nbash\n", returncode=0)
        running = FocusMode.get_running_distractions(["steam", "discord"])
        self.assertEqual(running, ["steam"])

    @patch('utils.focus_mode.FocusMode._remove_focus_entries', return_value="127.0.0.1 localhost\n")
    @patch('utils.focus_mode.subprocess.run')
    @patch('builtins.open', new_callable=mock_open, read_data="127.0.0.1 localhost\n")
    def test_block_domains_pkexec_denied(self, mock_file, mock_run, mock_remove):
        """_block_domains returns failure when pkexec write fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"denied")

        result = FocusMode._block_domains(["reddit.com"]) 

        self.assertFalse(result["success"])
        self.assertIn("Failed to modify hosts", result["message"])


if __name__ == '__main__':
    unittest.main()
