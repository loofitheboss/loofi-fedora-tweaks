"""
Tests for utils/software_utils.py (v34.0).
Covers SoftwareUtils.is_check_command_satisfied with
success, failure, missing binary, and invalid command cases.
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from subprocess import CalledProcessError

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.software_utils import SoftwareUtils


class TestIsCheckCommandSatisfied(unittest.TestCase):
    """Tests for SoftwareUtils.is_check_command_satisfied()."""

    @patch('utils.software_utils.subprocess.run')
    def test_command_succeeds(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = SoftwareUtils.is_check_command_satisfied("rpm -q gimp")
        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('utils.software_utils.subprocess.run')
    def test_command_fails_nonzero(self, mock_run):
        mock_run.side_effect = CalledProcessError(1, "rpm -q gimp")
        result = SoftwareUtils.is_check_command_satisfied("rpm -q gimp")
        self.assertFalse(result)

    @patch('utils.software_utils.subprocess.run')
    def test_command_binary_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("No such file")
        result = SoftwareUtils.is_check_command_satisfied("nonexistent --check")
        self.assertFalse(result)

    def test_invalid_command_string(self):
        """shlex.split raises ValueError on unclosed quotes -> returns False."""
        result = SoftwareUtils.is_check_command_satisfied("rpm -q 'unclosed")
        self.assertFalse(result)

    @patch('utils.software_utils.subprocess.run')
    def test_empty_string(self, mock_run):
        """Empty string splits to [] -> subprocess raises."""
        mock_run.side_effect = FileNotFoundError()
        # shlex.split("") returns [], subprocess.run([]) raises
        result = SoftwareUtils.is_check_command_satisfied("")
        # Either ValueError from shlex or FileNotFoundError from subprocess
        self.assertFalse(result)

    @patch('utils.software_utils.subprocess.run')
    def test_which_flatpak(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = SoftwareUtils.is_check_command_satisfied("which flatpak")
        self.assertTrue(result)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["which", "flatpak"])

    @patch('utils.software_utils.subprocess.run')
    def test_check_true_called(self, mock_run):
        """Verify check=True is passed to subprocess.run."""
        mock_run.return_value = MagicMock(returncode=0)
        SoftwareUtils.is_check_command_satisfied("rpm -q vim")
        _, kwargs = mock_run.call_args
        self.assertTrue(kwargs.get("check", False))

    @patch('utils.software_utils.subprocess.run')
    def test_command_with_complex_args(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = SoftwareUtils.is_check_command_satisfied(
            "flatpak info org.gimp.GIMP"
        )
        self.assertTrue(result)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["flatpak", "info", "org.gimp.GIMP"])


if __name__ == '__main__':
    unittest.main()
