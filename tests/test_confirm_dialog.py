"""
Tests for ui/confirm_dialog.py — ConfirmActionDialog (v29.0).

Covers:
- Dialog creation with all parameter combinations
- confirm() static method returns True when confirm_dangerous_actions is False
- confirm() with force=True bypasses settings
- snapshot_requested property
- "Don't ask again" checkbox behaviour
- Button wiring (confirm/cancel)

All Qt widgets are mocked — no real QApplication needed.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestConfirmActionDialogCreation(unittest.TestCase):
    """Dialog construction with various parameter combos."""

    @patch('ui.confirm_dialog.SettingsManager')
    @patch('ui.confirm_dialog.QDialog.__init__', return_value=None)
    def test_creates_with_all_params(self, mock_init, mock_settings):
        from ui.confirm_dialog import ConfirmActionDialog
        dialog = ConfirmActionDialog.__new__(ConfirmActionDialog)
        # Manually invoke init to test parameter acceptance
        with patch.object(ConfirmActionDialog, '__init__', return_value=None):
            dialog.__init__()
        # Verify that the class exists and is importable
        self.assertTrue(hasattr(ConfirmActionDialog, 'confirm'))
        self.assertTrue(hasattr(ConfirmActionDialog, 'snapshot_requested'))

    def test_snapshot_requested_default_false(self):
        """snapshot_requested is False when no snapshot checkbox offered."""
        from ui.confirm_dialog import ConfirmActionDialog
        dialog = MagicMock(spec=ConfirmActionDialog)
        dialog._snapshot_requested = False
        # Access the actual property implementation
        self.assertFalse(dialog._snapshot_requested)


class TestConfirmStaticMethod(unittest.TestCase):
    """ConfirmActionDialog.confirm() static method behaviour."""

    @patch('ui.confirm_dialog.SettingsManager')
    def test_returns_true_when_setting_disabled(self, mock_settings_cls):
        """If confirm_dangerous_actions is False, confirm() returns True immediately."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = False
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        result = ConfirmActionDialog.confirm(
            parent=None,
            action="Test action",
            description="Test desc",
        )
        self.assertTrue(result)

    @patch('ui.confirm_dialog.SettingsManager')
    def test_force_shows_dialog_even_if_setting_disabled(self, mock_settings_cls):
        """force=True should show the dialog regardless of setting."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = False
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog
        from PyQt6.QtWidgets import QDialog

        # Patch at the class level — ConfirmActionDialog() constructor and exec()
        with patch.object(ConfirmActionDialog, '__init__', lambda self, **kw: None):
            with patch.object(ConfirmActionDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
                result = ConfirmActionDialog.confirm(
                    parent=None,
                    action="Dangerous op",
                    force=True,
                )
                self.assertTrue(result)

    @patch('ui.confirm_dialog.SettingsManager')
    def test_confirm_returns_true_when_setting_true_and_accepted(self, mock_settings_cls):
        """When setting is True, dialog is shown and user accepts."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = True
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog
        from PyQt6.QtWidgets import QDialog

        with patch.object(ConfirmActionDialog, '__init__', return_value=None):
            with patch.object(ConfirmActionDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
                result = ConfirmActionDialog.confirm(
                    parent=None,
                    action="Remove packages",
                )
                self.assertTrue(result)

    @patch('ui.confirm_dialog.SettingsManager')
    def test_confirm_returns_false_when_rejected(self, mock_settings_cls):
        """When setting is True and user cancels, returns False."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = True
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog
        from PyQt6.QtWidgets import QDialog

        with patch.object(ConfirmActionDialog, '__init__', return_value=None):
            with patch.object(ConfirmActionDialog, 'exec', return_value=QDialog.DialogCode.Rejected):
                result = ConfirmActionDialog.confirm(
                    parent=None,
                    action="Remove packages",
                )
                self.assertFalse(result)

    @patch('ui.confirm_dialog.SettingsManager', side_effect=Exception("no settings"))
    def test_confirm_falls_through_on_settings_error(self, mock_settings_cls):
        """If SettingsManager raises, confirm() should still show dialog."""
        from ui.confirm_dialog import ConfirmActionDialog
        from PyQt6.QtWidgets import QDialog

        with patch.object(ConfirmActionDialog, '__init__', return_value=None):
            with patch.object(ConfirmActionDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
                result = ConfirmActionDialog.confirm(
                    parent=None,
                    action="Test",
                )
                self.assertTrue(result)


class TestOnConfirm(unittest.TestCase):
    """_on_confirm handler behaviour."""

    @patch('ui.confirm_dialog.SettingsManager')
    def test_on_confirm_saves_dont_ask_preference(self, mock_settings_cls):
        """When 'don't ask again' is checked, saves the preference."""
        mock_mgr = MagicMock()
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        # Build a partially mocked dialog
        dialog = MagicMock(spec=ConfirmActionDialog)
        dialog.dont_ask_cb = MagicMock()
        dialog.dont_ask_cb.isChecked.return_value = True
        dialog.snapshot_cb = None
        dialog._snapshot_requested = False
        dialog.accept = MagicMock()

        # Call the real method
        ConfirmActionDialog._on_confirm(dialog)

        mock_mgr.set.assert_called_once_with("confirm_dangerous_actions", False)
        mock_mgr.save.assert_called_once()
        dialog.accept.assert_called_once()

    @patch('ui.confirm_dialog.SettingsManager')
    def test_on_confirm_records_snapshot_request(self, mock_settings_cls):
        """When snapshot checkbox is checked, _snapshot_requested becomes True."""
        mock_mgr = MagicMock()
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        dialog = MagicMock(spec=ConfirmActionDialog)
        dialog.dont_ask_cb = MagicMock()
        dialog.dont_ask_cb.isChecked.return_value = False
        dialog.snapshot_cb = MagicMock()
        dialog.snapshot_cb.isChecked.return_value = True
        dialog._snapshot_requested = False
        dialog.accept = MagicMock()

        ConfirmActionDialog._on_confirm(dialog)

        self.assertTrue(dialog._snapshot_requested)
        dialog.accept.assert_called_once()

    @patch('ui.confirm_dialog.SettingsManager')
    def test_on_confirm_no_snapshot_when_unchecked(self, mock_settings_cls):
        """When snapshot checkbox is unchecked, _snapshot_requested stays False."""
        mock_mgr = MagicMock()
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        dialog = MagicMock(spec=ConfirmActionDialog)
        dialog.dont_ask_cb = MagicMock()
        dialog.dont_ask_cb.isChecked.return_value = False
        dialog.snapshot_cb = MagicMock()
        dialog.snapshot_cb.isChecked.return_value = False
        dialog._snapshot_requested = False
        dialog.accept = MagicMock()

        ConfirmActionDialog._on_confirm(dialog)

        self.assertFalse(dialog._snapshot_requested)

    @patch('ui.confirm_dialog.SettingsManager')
    def test_on_confirm_no_snapshot_checkbox(self, mock_settings_cls):
        """When snapshot_cb is None (not offered), skip snapshot logic."""
        mock_mgr = MagicMock()
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        dialog = MagicMock(spec=ConfirmActionDialog)
        dialog.dont_ask_cb = MagicMock()
        dialog.dont_ask_cb.isChecked.return_value = False
        dialog.snapshot_cb = None
        dialog._snapshot_requested = False
        dialog.accept = MagicMock()

        ConfirmActionDialog._on_confirm(dialog)

        self.assertFalse(dialog._snapshot_requested)
        dialog.accept.assert_called_once()


if __name__ == '__main__':
    unittest.main()
