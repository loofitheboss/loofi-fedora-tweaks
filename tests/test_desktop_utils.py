"""
Tests for utils/desktop_utils.py (v34.0).
Covers DesktopUtils.detect_color_scheme for dark, light,
OSError fallback, and timeout fallback scenarios.
"""
import unittest
import subprocess
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.desktop_utils import DesktopUtils


class TestDetectColorScheme(unittest.TestCase):
    """Tests for DesktopUtils.detect_color_scheme()."""

    @patch('utils.desktop_utils.subprocess.run')
    def test_dark_scheme(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="'prefer-dark'\n"
        )
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "dark")

    @patch('utils.desktop_utils.subprocess.run')
    def test_light_scheme(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="'prefer-light'\n"
        )
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "light")

    @patch('utils.desktop_utils.subprocess.run')
    def test_light_scheme_no_quotes(self, mock_run):
        mock_run.return_value = MagicMock(stdout="prefer-light\n")
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "light")

    @patch('utils.desktop_utils.subprocess.run')
    def test_default_scheme(self, mock_run):
        """'default' without 'light' -> falls through to dark."""
        mock_run.return_value = MagicMock(stdout="'default'\n")
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "dark")

    @patch('utils.desktop_utils.subprocess.run')
    def test_empty_output_defaults_dark(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "dark")

    @patch('utils.desktop_utils.subprocess.run')
    def test_oserror_defaults_dark(self, mock_run):
        mock_run.side_effect = OSError("gsettings not found")
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "dark")

    @patch('utils.desktop_utils.subprocess.run')
    def test_timeout_defaults_dark(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("gsettings", 3)
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "dark")

    @patch('utils.desktop_utils.subprocess.run')
    def test_double_quoted_value(self, mock_run):
        mock_run.return_value = MagicMock(stdout='"prefer-dark"\n')
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "dark")

    @patch('utils.desktop_utils.subprocess.run')
    def test_light_with_double_quotes(self, mock_run):
        mock_run.return_value = MagicMock(stdout='"prefer-light"\n')
        result = DesktopUtils.detect_color_scheme()
        self.assertEqual(result, "light")

    @patch('utils.desktop_utils.subprocess.run')
    def test_gsettings_command_args(self, mock_run):
        """Verify correct gsettings command is called."""
        mock_run.return_value = MagicMock(stdout="'prefer-dark'\n")
        DesktopUtils.detect_color_scheme()
        mock_run.assert_called_once_with(
            ["gsettings", "get",
             "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True, timeout=3,
        )


if __name__ == '__main__':
    unittest.main()
