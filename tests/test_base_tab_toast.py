"""Tests for ui/base_tab.py toast methods (v47.0)."""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestBaseTabToast(unittest.TestCase):
    """Tests for BaseTab toast convenience methods."""

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def _create_base_tab(self):
        """Create a BaseTab instance for testing."""
        from ui.base_tab import BaseTab
        tab = BaseTab()
        return tab

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_toast_no_parent(self):
        """Toast should not crash when there is no parent MainWindow."""
        tab = self._create_base_tab()
        # Should not raise
        tab.show_toast("Test", "Message", "general")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_success_no_parent(self):
        """show_success should not crash when there is no parent."""
        tab = self._create_base_tab()
        tab.show_success("All good")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_error_no_parent(self):
        """show_error should not crash when there is no parent."""
        tab = self._create_base_tab()
        tab.show_error("Something failed")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_info_no_parent(self):
        """show_info should not crash when there is no parent."""
        tab = self._create_base_tab()
        tab.show_info("Informational message")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_toast_with_main_window(self):
        """Toast should delegate to MainWindow's show_toast."""
        tab = self._create_base_tab()
        mock_mw = MagicMock()
        mock_mw.show_toast = MagicMock()
        tab._find_main_window = MagicMock(return_value=mock_mw)
        tab.show_toast("Title", "Msg", "security")
        mock_mw.show_toast.assert_called_once_with("Title", "Msg", "security")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_success_delegates_to_toast(self):
        """show_success should call show_toast with 'general' category."""
        tab = self._create_base_tab()
        tab.show_toast = MagicMock()
        tab.show_success("Done")
        tab.show_toast.assert_called_once()
        args = tab.show_toast.call_args[0]
        self.assertEqual(args[2], "general")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_error_delegates_to_toast(self):
        """show_error should call show_toast with 'security' category."""
        tab = self._create_base_tab()
        tab.show_toast = MagicMock()
        tab.show_error("Fail")
        tab.show_toast.assert_called_once()
        args = tab.show_toast.call_args[0]
        self.assertEqual(args[2], "security")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_show_info_delegates_to_toast(self):
        """show_info should call show_toast with 'system' category."""
        tab = self._create_base_tab()
        tab.show_toast = MagicMock()
        tab.show_info("Note")
        tab.show_toast.assert_called_once()
        args = tab.show_toast.call_args[0]
        self.assertEqual(args[2], "system")

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_find_main_window_returns_none_for_orphan(self):
        """_find_main_window returns None for an unparented tab."""
        tab = self._create_base_tab()
        result = tab._find_main_window()
        self.assertIsNone(result)

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_on_command_finished_success_shows_toast(self):
        """on_command_finished with exit code 0 should show success toast."""
        tab = self._create_base_tab()
        tab.show_success = MagicMock()
        tab.on_command_finished(0)
        tab.show_success.assert_called_once()

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_on_command_finished_failure_shows_error(self):
        """on_command_finished with non-zero exit code should show error toast."""
        tab = self._create_base_tab()
        tab.show_error = MagicMock()
        tab.on_command_finished(1)
        tab.show_error.assert_called_once()


if __name__ == '__main__':
    unittest.main()
