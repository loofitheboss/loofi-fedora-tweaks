"""
Tests for utils/notifications.py — NotificationManager.
Covers: is_available, send, urgency levels, missing binary,
icon paths, shortcut helpers, and error handling.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.notifications import NotificationManager


# ---------------------------------------------------------------------------
# TestIsAvailable — notify-send detection
# ---------------------------------------------------------------------------

class TestIsAvailable(unittest.TestCase):
    """Tests for is_available method."""

    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_available_when_installed(self, mock_which):
        """is_available returns True when notify-send is found."""
        self.assertTrue(NotificationManager.is_available())
        mock_which.assert_called_once_with("notify-send")

    @patch('utils.notifications.shutil.which', return_value=None)
    def test_not_available_when_missing(self, mock_which):
        """is_available returns False when notify-send is not found."""
        self.assertFalse(NotificationManager.is_available())


# ---------------------------------------------------------------------------
# TestSend — sending notifications
# ---------------------------------------------------------------------------

class TestSend(unittest.TestCase):
    """Tests for send method."""

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_send_success(self, mock_which, mock_run):
        """send returns True on successful notification."""
        mock_run.return_value = MagicMock(returncode=0)

        result = NotificationManager.send("Test Title", "Test body")

        self.assertTrue(result)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertIn("notify-send", call_args)
        self.assertIn("Test Title", call_args)
        self.assertIn("Test body", call_args)

    @patch('utils.notifications.shutil.which', return_value=None)
    def test_send_returns_false_when_unavailable(self, mock_which):
        """send returns False when notify-send is not installed."""
        result = NotificationManager.send("Title", "Body")
        self.assertFalse(result)

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_send_with_urgency_critical(self, mock_which, mock_run):
        """send passes urgency level to notify-send."""
        mock_run.return_value = MagicMock(returncode=0)

        NotificationManager.send("Alert", "Critical issue", urgency="critical")

        call_args = mock_run.call_args[0][0]
        self.assertIn("critical", call_args)

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_send_with_custom_icon(self, mock_which, mock_run):
        """send passes icon name to notify-send."""
        mock_run.return_value = MagicMock(returncode=0)

        NotificationManager.send("Title", "Body", icon="dialog-error")

        call_args = mock_run.call_args[0][0]
        self.assertIn("dialog-error", call_args)

    @patch('utils.notifications.subprocess.run', side_effect=OSError("exec failed"))
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_send_handles_exception(self, mock_which, mock_run):
        """send returns False on exception."""
        result = NotificationManager.send("Title", "Body")
        self.assertFalse(result)

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_send_includes_app_name(self, mock_which, mock_run):
        """send includes the app name in the command."""
        mock_run.return_value = MagicMock(returncode=0)

        NotificationManager.send("Title", "Body")

        call_args = mock_run.call_args[0][0]
        self.assertIn(NotificationManager.APP_NAME, call_args)


# ---------------------------------------------------------------------------
# TestShortcutMethods — convenience notification methods
# ---------------------------------------------------------------------------

class TestShortcutMethods(unittest.TestCase):
    """Tests for shortcut notification methods."""

    @patch.object(NotificationManager, 'send')
    def test_notify_task_complete_success(self, mock_send):
        """notify_task_complete sends success notification."""
        NotificationManager.notify_task_complete("System Update", success=True)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        self.assertIn("Complete", call_args[0][0])

    @patch.object(NotificationManager, 'send')
    def test_notify_task_complete_failure(self, mock_send):
        """notify_task_complete sends failure notification with critical urgency."""
        NotificationManager.notify_task_complete("Cleanup", success=False)
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        self.assertEqual(call_kwargs.get("urgency"), "critical")


if __name__ == '__main__':
    unittest.main()
