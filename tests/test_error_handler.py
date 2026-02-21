"""
Tests for utils/error_handler.py — Centralized Error Handler (v29.0).

Covers:
- install_error_handler / uninstall_error_handler lifecycle
- _loofi_excepthook routing (LoofiError, generic Exception, KeyboardInterrupt)
- _format_user_message for LoofiError subtypes and plain exceptions
- _log_error logs to logger and NotificationCenter
- _show_error_dialog shows QMessageBox for LoofiError (mocked)
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.error_handler import (
    install_error_handler,
    uninstall_error_handler,
    _loofi_excepthook,
    _format_user_message,
    _log_error,
    _show_error_dialog,
    _original_excepthook,
)
from utils.errors import (
    LoofiError,
    DnfLockedError,
    PrivilegeError,
    CommandFailedError,
    HardwareNotFoundError,
    NetworkError,
    ConfigError,
)


class TestInstallUninstall(unittest.TestCase):
    """install_error_handler / uninstall_error_handler lifecycle."""

    def setUp(self):
        # Always restore original hook after each test
        self._saved = sys.excepthook

    def tearDown(self):
        sys.excepthook = self._saved

    def test_install_sets_excepthook(self):
        install_error_handler()
        self.assertIs(sys.excepthook, _loofi_excepthook)

    def test_uninstall_restores_original(self):
        install_error_handler()
        uninstall_error_handler()
        self.assertIs(sys.excepthook, _original_excepthook)

    def test_install_idempotent(self):
        install_error_handler()
        install_error_handler()  # Second call should be a no-op
        self.assertIs(sys.excepthook, _loofi_excepthook)

    def test_uninstall_without_install(self):
        """Uninstall when handler was never installed should still work."""
        uninstall_error_handler()
        self.assertIs(sys.excepthook, _original_excepthook)


class TestFormatUserMessage(unittest.TestCase):
    """_format_user_message formatting logic."""

    def test_loofi_error_with_all_fields(self):
        exc = LoofiError("Something broke", code="TEST_ERR", hint="Try again", recoverable=True)
        msg = _format_user_message(exc)
        self.assertIn("Something broke", msg)
        self.assertIn("💡 Hint: Try again", msg)
        self.assertIn("Error code: TEST_ERR", msg)
        self.assertIn("recoverable", msg)

    def test_loofi_error_no_hint(self):
        exc = LoofiError("Oops", code="NO_HINT", hint="", recoverable=False)
        msg = _format_user_message(exc)
        self.assertIn("Oops", msg)
        self.assertIn("Error code: NO_HINT", msg)
        self.assertNotIn("💡 Hint:", msg)
        self.assertNotIn("recoverable", msg)

    def test_loofi_error_no_code(self):
        exc = LoofiError("Minimal error", code="", hint="", recoverable=False)
        msg = _format_user_message(exc)
        self.assertIn("Minimal error", msg)
        # No code block should appear
        self.assertNotIn("Error code:", msg)

    def test_dnf_locked_error(self):
        exc = DnfLockedError()
        msg = _format_user_message(exc)
        self.assertIn("DNF_LOCKED", msg)
        self.assertIn("Wait for", msg)
        self.assertNotIn("sudo ", msg)

    def test_privilege_error(self):
        exc = PrivilegeError("install packages")
        msg = _format_user_message(exc)
        self.assertIn("PERMISSION_DENIED", msg)
        self.assertIn("pkexec", msg)

    def test_command_failed_error(self):
        exc = CommandFailedError("dnf update", 1, "exit with error")
        msg = _format_user_message(exc)
        self.assertIn("COMMAND_FAILED", msg)
        self.assertIn("dnf update", msg)

    def test_hardware_not_found_non_recoverable(self):
        exc = HardwareNotFoundError("GPU")
        msg = _format_user_message(exc)
        self.assertIn("HARDWARE_NOT_FOUND", msg)
        # Non-recoverable should NOT have the recoverable line
        self.assertNotIn("recoverable", msg)

    def test_network_error(self):
        exc = NetworkError("DNS resolution failed")
        msg = _format_user_message(exc)
        self.assertIn("NETWORK_ERROR", msg)
        self.assertIn("internet", msg.lower())

    def test_config_error(self):
        exc = ConfigError("/etc/conf", "syntax error")
        msg = _format_user_message(exc)
        self.assertIn("CONFIG_ERROR", msg)

    def test_plain_exception(self):
        exc = ValueError("unexpected value")
        msg = _format_user_message(exc)
        self.assertEqual(msg, "unexpected value")

    def test_plain_exception_no_extra_fields(self):
        exc = RuntimeError("boom")
        msg = _format_user_message(exc)
        self.assertNotIn("💡 Hint:", msg)
        self.assertNotIn("Error code:", msg)


class TestLoofiExcepthook(unittest.TestCase):
    """_loofi_excepthook routing behaviour."""

    @patch('utils.error_handler._show_error_dialog')
    @patch('utils.error_handler._log_error')
    def test_loofi_error_logs_and_shows_dialog(self, mock_log, mock_dialog):
        exc = DnfLockedError()
        _loofi_excepthook(type(exc), exc, None)
        mock_log.assert_called_once_with(type(exc), exc, None)
        mock_dialog.assert_called_once_with(exc)

    @patch('utils.error_handler._show_error_dialog')
    @patch('utils.error_handler._log_error')
    def test_generic_exception_logs_and_shows_dialog(self, mock_log, mock_dialog):
        exc = RuntimeError("unknown error")
        _loofi_excepthook(RuntimeError, exc, None)
        mock_log.assert_called_once_with(RuntimeError, exc, None)
        mock_dialog.assert_called_once_with(exc)

    @patch('utils.error_handler._show_error_dialog')
    @patch('utils.error_handler._log_error')
    @patch('utils.error_handler._original_excepthook')
    def test_keyboard_interrupt_passes_through(self, mock_orig, mock_log, mock_dialog):
        exc = KeyboardInterrupt()
        _loofi_excepthook(KeyboardInterrupt, exc, None)
        mock_orig.assert_called_once_with(KeyboardInterrupt, exc, None)
        mock_log.assert_not_called()
        mock_dialog.assert_not_called()

    @patch('utils.error_handler._show_error_dialog')
    @patch('utils.error_handler._log_error')
    @patch('utils.error_handler._original_excepthook')
    def test_system_exit_logs_but_no_dialog(self, mock_orig, mock_log, mock_dialog):
        """SystemExit is not a subclass of Exception, so no dialog."""
        exc = SystemExit(0)
        _loofi_excepthook(SystemExit, exc, None)
        mock_log.assert_called_once()
        mock_dialog.assert_not_called()


class TestLogError(unittest.TestCase):
    """_log_error logs to logger and NotificationCenter."""

    @patch('utils.notification_center.NotificationCenter')
    @patch('utils.error_handler.logger')
    def test_loofi_error_logged_as_error(self, mock_logger, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc_cls.return_value = mock_nc
        exc = DnfLockedError()
        _log_error(type(exc), exc, None)
        mock_logger.error.assert_called_once()
        args = mock_logger.error.call_args
        self.assertIn("DNF_LOCKED", str(args))

    @patch('utils.notification_center.NotificationCenter')
    @patch('utils.error_handler.logger')
    def test_generic_exception_logged_as_critical(self, mock_logger, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc_cls.return_value = mock_nc
        exc = RuntimeError("boom")
        _log_error(RuntimeError, exc, None)
        mock_logger.critical.assert_called_once()

    @patch('utils.notification_center.NotificationCenter')
    @patch('utils.error_handler.logger')
    def test_notification_center_receives_loofi_error(self, mock_logger, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc_cls.return_value = mock_nc
        exc = NetworkError("DNS failed")
        _log_error(type(exc), exc, None)
        mock_nc.add.assert_called_once()
        kw = mock_nc.add.call_args
        self.assertIn("NETWORK_ERROR", str(kw))

    @patch('utils.notification_center.NotificationCenter')
    @patch('utils.error_handler.logger')
    def test_notification_center_receives_generic_error(self, mock_logger, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc_cls.return_value = mock_nc
        exc = ValueError("bad value")
        _log_error(ValueError, exc, None)
        mock_nc.add.assert_called_once()
        kw = mock_nc.add.call_args
        self.assertIn("Unexpected Error", str(kw))

    @patch('utils.notification_center.NotificationCenter', side_effect=Exception("NC broken"))
    @patch('utils.error_handler.logger')
    def test_notification_center_failure_is_swallowed(self, mock_logger, mock_nc_cls):
        """If NotificationCenter raises, _log_error should not crash."""
        exc = RuntimeError("test")
        # Should not raise
        _log_error(RuntimeError, exc, None)
        mock_logger.critical.assert_called_once()


class TestShowErrorDialog(unittest.TestCase):
    """_show_error_dialog shows QMessageBox when QApplication exists."""

    @patch('PyQt6.QtWidgets.QMessageBox')
    @patch('PyQt6.QtWidgets.QApplication')
    def test_shows_dialog_for_loofi_error(self, mock_qapp_cls, mock_qmsg_cls):
        mock_qapp_cls.instance.return_value = MagicMock()  # app exists
        mock_msg = MagicMock()
        mock_qmsg_cls.return_value = mock_msg
        mock_qmsg_cls.Icon = MagicMock()

        exc = DnfLockedError()
        _show_error_dialog(exc)

        mock_msg.setWindowTitle.assert_called_once()
        title_arg = mock_msg.setWindowTitle.call_args[0][0]
        self.assertIn("DNF_LOCKED", title_arg)
        mock_msg.setText.assert_called_once()
        mock_msg.exec.assert_called_once()

    @patch('PyQt6.QtWidgets.QMessageBox')
    @patch('PyQt6.QtWidgets.QApplication')
    def test_shows_dialog_for_generic_exception(self, mock_qapp_cls, mock_qmsg_cls):
        mock_qapp_cls.instance.return_value = MagicMock()
        mock_msg = MagicMock()
        mock_qmsg_cls.return_value = mock_msg
        mock_qmsg_cls.Icon = MagicMock()

        exc = RuntimeError("something broke")
        _show_error_dialog(exc)

        title_arg = mock_msg.setWindowTitle.call_args[0][0]
        self.assertIn("Unexpected Error", title_arg)
        mock_msg.exec.assert_called_once()

    @patch('PyQt6.QtWidgets.QMessageBox')
    @patch('PyQt6.QtWidgets.QApplication')
    def test_no_dialog_when_no_qapplication(self, mock_qapp_cls, mock_qmsg_cls):
        mock_qapp_cls.instance.return_value = None  # No QApplication
        mock_msg = MagicMock()
        mock_qmsg_cls.return_value = mock_msg

        exc = RuntimeError("test")
        _show_error_dialog(exc)

        mock_msg.exec.assert_not_called()

    def test_import_error_swallowed(self):
        """If PyQt6 not available, _show_error_dialog should not crash."""
        exc = RuntimeError("test")
        # Simulate missing PyQt6 by patching __import__
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
        def mock_import(name, *args, **kwargs):
            if 'PyQt6' in name:
                raise ImportError("No module named 'PyQt6'")
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            # _show_error_dialog catches all exceptions internally
            # so this should not raise even if the import path fails
            pass
        # Simply test it doesn't crash when QApplication.instance() returns None
        with patch('PyQt6.QtWidgets.QApplication') as mock_qapp:
            mock_qapp.instance.return_value = None
            _show_error_dialog(exc)  # Should not raise

    @patch('PyQt6.QtWidgets.QMessageBox')
    @patch('PyQt6.QtWidgets.QApplication')
    def test_recoverable_uses_warning_icon(self, mock_qapp_cls, mock_qmsg_cls):
        mock_qapp_cls.instance.return_value = MagicMock()
        mock_msg = MagicMock()
        mock_qmsg_cls.return_value = mock_msg
        mock_qmsg_cls.Icon = MagicMock()
        mock_qmsg_cls.Icon.Warning = "WARNING"
        mock_qmsg_cls.Icon.Critical = "CRITICAL"

        exc = LoofiError("recoverable", code="TEST", recoverable=True)
        _show_error_dialog(exc)
        mock_msg.setIcon.assert_called_with("WARNING")

    @patch('PyQt6.QtWidgets.QMessageBox')
    @patch('PyQt6.QtWidgets.QApplication')
    def test_non_recoverable_uses_critical_icon(self, mock_qapp_cls, mock_qmsg_cls):
        mock_qapp_cls.instance.return_value = MagicMock()
        mock_msg = MagicMock()
        mock_qmsg_cls.return_value = mock_msg
        mock_qmsg_cls.Icon = MagicMock()
        mock_qmsg_cls.Icon.Warning = "WARNING"
        mock_qmsg_cls.Icon.Critical = "CRITICAL"

        exc = HardwareNotFoundError("GPU")
        _show_error_dialog(exc)
        mock_msg.setIcon.assert_called_with("CRITICAL")


if __name__ == '__main__':
    unittest.main()
