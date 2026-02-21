"""
Extended tests for utils/notifications.py - NotificationManager.
Covers edge cases beyond the basic test_notifications_util.py:
  - timeout parameter forwarded correctly
  - all shortcut methods call send()
  - default icon value
  - special characters in title/body
  - subprocess timeout / SubprocessError paths
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.notifications import NotificationManager


# ---------------------------------------------------------------------------
# TestSendParameters - detailed argument forwarding
# ---------------------------------------------------------------------------

class TestSendParameters(unittest.TestCase):
    """Verify that send() forwards all parameters to notify-send correctly."""

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_default_icon_is_dialog_information(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        NotificationManager.send("Title", "Body")
        cmd = mock_run.call_args[0][0]
        icon_idx = cmd.index("--icon")
        self.assertEqual(cmd[icon_idx + 1], "dialog-information")

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_default_urgency_is_normal(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        NotificationManager.send("Title", "Body")
        cmd = mock_run.call_args[0][0]
        urg_idx = cmd.index("--urgency")
        self.assertEqual(cmd[urg_idx + 1], "normal")

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_custom_timeout_forwarded(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        NotificationManager.send("Title", "Body", timeout=10000)
        cmd = mock_run.call_args[0][0]
        expire_idx = cmd.index("--expire-time")
        self.assertEqual(cmd[expire_idx + 1], "10000")

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_zero_timeout_forwarded(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        NotificationManager.send("Title", "Body", timeout=0)
        cmd = mock_run.call_args[0][0]
        expire_idx = cmd.index("--expire-time")
        self.assertEqual(cmd[expire_idx + 1], "0")

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_title_and_body_are_last_two_args(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        NotificationManager.send("My Title", "My Body")
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[-2], "My Title")
        self.assertEqual(cmd[-1], "My Body")


# ---------------------------------------------------------------------------
# TestSpecialCharacters - unicode and edge-case strings
# ---------------------------------------------------------------------------

class TestSpecialCharacters(unittest.TestCase):
    """Notifications with special characters should not crash."""

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_unicode_in_title(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = NotificationManager.send("Update complete", "Freed 1.5 GB")
        self.assertTrue(result)

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_empty_body(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = NotificationManager.send("Title", "")
        self.assertTrue(result)

    @patch('utils.notifications.subprocess.run')
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_newlines_in_body(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = NotificationManager.send("Title", "Line1\nLine2\nLine3")
        self.assertTrue(result)
        cmd = mock_run.call_args[0][0]
        self.assertIn("Line1\nLine2\nLine3", cmd)


# ---------------------------------------------------------------------------
# TestErrorPaths - various failure modes
# ---------------------------------------------------------------------------

class TestErrorPaths(unittest.TestCase):
    """Exercise error handling paths in send()."""

    @patch('utils.notifications.subprocess.run',
           side_effect=subprocess.SubprocessError("pipe broke"))
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_subprocess_error_returns_false(self, _which, _run):
        result = NotificationManager.send("Title", "Body")
        self.assertFalse(result)

    @patch('utils.notifications.subprocess.run',
           side_effect=FileNotFoundError("not found"))
    @patch('utils.notifications.shutil.which', return_value='/usr/bin/notify-send')
    def test_file_not_found_returns_false(self, _which, _run):
        result = NotificationManager.send("Title", "Body")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# TestAllShortcuts - every convenience method must call send()
# ---------------------------------------------------------------------------

class TestAllShortcuts(unittest.TestCase):
    """Each shortcut method should delegate to send()."""

    @patch.object(NotificationManager, 'send')
    def test_notify_task_complete_success(self, mock_send):
        NotificationManager.notify_task_complete("Build", success=True)
        mock_send.assert_called_once()
        title = mock_send.call_args[0][0]
        self.assertIn("Complete", title)

    @patch.object(NotificationManager, 'send')
    def test_notify_task_complete_failure(self, mock_send):
        NotificationManager.notify_task_complete("Build", success=False)
        mock_send.assert_called_once()
        title = mock_send.call_args[0][0]
        self.assertIn("Failed", title)
        self.assertEqual(mock_send.call_args[1].get("urgency"), "critical")

    @patch.object(NotificationManager, 'send')
    def test_notify_updates_available(self, mock_send):
        NotificationManager.notify_updates_available(5)
        mock_send.assert_called_once()
        title = mock_send.call_args[0][0]
        self.assertIn("5", title)

    @patch.object(NotificationManager, 'send')
    def test_notify_cleanup_complete(self, mock_send):
        NotificationManager.notify_cleanup_complete(123.4)
        mock_send.assert_called_once()
        body = mock_send.call_args[0][1]
        self.assertIn("123.4", body)

    @patch.object(NotificationManager, 'send')
    def test_notify_sync_complete(self, mock_send):
        NotificationManager.notify_sync_complete()
        mock_send.assert_called_once()
        title = mock_send.call_args[0][0]
        self.assertIn("Sync", title)

    @patch.object(NotificationManager, 'send')
    def test_notify_preset_applied(self, mock_send):
        NotificationManager.notify_preset_applied("Gaming")
        mock_send.assert_called_once()
        body = mock_send.call_args[0][1]
        self.assertIn("Gaming", body)


# ---------------------------------------------------------------------------
# TestAppConstants - class-level constants
# ---------------------------------------------------------------------------

class TestAppConstants(unittest.TestCase):
    """Check class-level configuration constants."""

    def test_app_name_is_string(self):
        self.assertIsInstance(NotificationManager.APP_NAME, str)
        self.assertTrue(len(NotificationManager.APP_NAME) > 0)

    def test_app_icon_is_string(self):
        self.assertIsInstance(NotificationManager.APP_ICON, str)
        self.assertTrue(len(NotificationManager.APP_ICON) > 0)


if __name__ == '__main__':
    unittest.main()
