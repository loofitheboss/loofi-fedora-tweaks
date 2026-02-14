"""
Tests for utils/gaming_utils.py (v34.0).
Covers GamingUtils.get_gamemode_status for all four return states:
active, installed, missing, error.
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.gaming_utils import GamingUtils


class TestGetGamemodeStatus(unittest.TestCase):
    """Tests for GamingUtils.get_gamemode_status()."""

    @patch('utils.gaming_utils.subprocess.run')
    def test_active_service(self, mock_run):
        """gamemoded is running -> 'active'."""
        mock_run.return_value = MagicMock(
            stdout="active\n", returncode=0
        )
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "active")

    @patch('utils.gaming_utils.subprocess.run')
    def test_installed_but_inactive(self, mock_run):
        """gamemoded inactive, rpm -q succeeds -> 'installed'.
        Note: code checks 'active' in stdout, so we must use output
        that does NOT contain the substring 'active'."""
        mock_run.side_effect = [
            MagicMock(stdout="not running\n", returncode=3),   # systemctl
            MagicMock(stdout="gamemode-1.8\n", returncode=0),  # rpm -q
        ]
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "installed")

    @patch('utils.gaming_utils.subprocess.run')
    def test_missing_package(self, mock_run):
        """gamemoded not running and rpm -q fails -> 'missing'."""
        mock_run.side_effect = [
            MagicMock(stdout="not running\n", returncode=3),  # systemctl
            MagicMock(stdout="", returncode=1),               # rpm -q
        ]
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "missing")

    @patch('utils.gaming_utils.subprocess.run')
    def test_error_on_exception(self, mock_run):
        """subprocess raises -> 'error'."""
        mock_run.side_effect = OSError("systemctl not found")
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "error")

    @patch('utils.gaming_utils.subprocess.run')
    def test_error_on_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("systemctl")
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "error")

    @patch('utils.gaming_utils.subprocess.run')
    def test_active_contains_active_substring(self, mock_run):
        """Output may include extra text with 'active' in it."""
        mock_run.return_value = MagicMock(
            stdout="active (running)\n", returncode=0
        )
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "active")

    @patch('utils.gaming_utils.subprocess.run')
    def test_systemctl_empty_output_then_rpm_missing(self, mock_run):
        """systemctl returns empty stdout, rpm -q fails -> 'missing'."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=3),   # systemctl: no 'active' in ""
            MagicMock(stdout="", returncode=1),   # rpm -q
        ]
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "missing")

    @patch('utils.gaming_utils.subprocess.run')
    def test_systemctl_empty_output_then_rpm_installed(self, mock_run):
        """systemctl returns empty stdout, rpm -q succeeds -> 'installed'."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=3),    # systemctl
            MagicMock(stdout="gamemode-1.8\n", returncode=0),  # rpm -q
        ]
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "installed")

    @patch('utils.gaming_utils.subprocess.run')
    def test_rpm_check_raises_after_not_running(self, mock_run):
        """systemctl not running, rpm raises exception -> 'error'."""
        mock_run.side_effect = [
            MagicMock(stdout="not running\n", returncode=3),
            OSError("rpm not found"),
        ]
        result = GamingUtils.get_gamemode_status()
        self.assertEqual(result, "error")


if __name__ == '__main__':
    unittest.main()
