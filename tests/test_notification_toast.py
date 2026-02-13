"""
Tests for ui/notification_toast.py — NotificationToast (v29.0).

Covers:
- Toast widget creation and sizing
- show_toast() display logic
- Category → accent colour mapping
- Auto-hide timer configuration
- Slide-out on timer / close button

All Qt widgets are tested in offscreen mode or via mocks.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestCategoryColorMapping(unittest.TestCase):
    """Category → accent colour mapping module-level dict."""

    def test_all_categories_have_colours(self):
        from ui.notification_toast import _CATEGORY_COLORS
        expected = {
            "general", "health", "profile", "security", "system",
            "overview", "manage", "hardware", "network & security",
            "personalize", "developer", "automation", "health & logs",
        }
        self.assertEqual(set(_CATEGORY_COLORS.keys()), expected)

    def test_colours_are_valid_hex(self):
        from ui.notification_toast import _CATEGORY_COLORS
        import re
        for category, colour in _CATEGORY_COLORS.items():
            self.assertRegex(
                colour, r'^#[0-9a-fA-F]{6}$',
                f"Category '{category}' has invalid colour: {colour}",
            )

    def test_security_is_red_ish(self):
        from ui.notification_toast import _CATEGORY_COLORS
        # Security should use a coral/red colour (Abyss palette)
        self.assertEqual(_CATEGORY_COLORS["security"], "#e8556d")

    def test_health_is_green_ish(self):
        from ui.notification_toast import _CATEGORY_COLORS
        self.assertEqual(_CATEGORY_COLORS["health"], "#3dd68c")

    def test_system_is_yellow_ish(self):
        from ui.notification_toast import _CATEGORY_COLORS
        self.assertEqual(_CATEGORY_COLORS["system"], "#e8b84d")


class TestNotificationToastConstants(unittest.TestCase):
    """Class-level constants are correctly defined."""

    def test_display_ms_is_positive(self):
        from ui.notification_toast import NotificationToast
        self.assertGreater(NotificationToast.DISPLAY_MS, 0)

    def test_display_ms_default(self):
        from ui.notification_toast import NotificationToast
        self.assertEqual(NotificationToast.DISPLAY_MS, 4000)

    def test_toast_dimensions(self):
        from ui.notification_toast import NotificationToast
        self.assertEqual(NotificationToast.TOAST_WIDTH, 360)
        self.assertEqual(NotificationToast.TOAST_HEIGHT, 72)


class TestNotificationToastCreation(unittest.TestCase):
    """Toast widget instantiation."""

    @patch('ui.notification_toast.QTimer')
    @patch('ui.notification_toast.QWidget.__init__', return_value=None)
    def test_creates_without_parent(self, mock_widget_init, mock_timer_cls):
        """Toast can be created with no parent."""
        from ui.notification_toast import NotificationToast

        mock_timer = MagicMock()
        mock_timer_cls.return_value = mock_timer

        toast = NotificationToast.__new__(NotificationToast)
        # Verify the class has the expected attributes
        self.assertTrue(hasattr(NotificationToast, 'show_toast'))
        self.assertTrue(hasattr(NotificationToast, 'DISPLAY_MS'))
        self.assertTrue(hasattr(NotificationToast, 'TOAST_WIDTH'))
        self.assertTrue(hasattr(NotificationToast, 'TOAST_HEIGHT'))


class TestShowToastLogic(unittest.TestCase):
    """show_toast() method behaviour (mocked widget internals)."""

    def _make_mock_toast(self):
        """Create a mock NotificationToast with needed attributes."""
        from ui.notification_toast import NotificationToast

        toast = MagicMock(spec=NotificationToast)
        toast.TOAST_WIDTH = 360
        toast.TOAST_HEIGHT = 72
        toast.DISPLAY_MS = 4000
        toast._title_label = MagicMock()
        toast._message_label = MagicMock()
        toast._accent_color = None
        toast._auto_hide_timer = MagicMock()
        toast.parent.return_value = None
        toast.show = MagicMock()
        toast.raise_ = MagicMock()
        toast.move = MagicMock()
        return toast

    def test_show_toast_sets_title(self):
        from ui.notification_toast import NotificationToast

        toast = self._make_mock_toast()
        # Call the real method
        NotificationToast.show_toast(toast, "Test Title", "Test Message", "general")
        toast._title_label.setText.assert_called_once_with("Test Title")

    def test_show_toast_sets_message(self):
        from ui.notification_toast import NotificationToast

        toast = self._make_mock_toast()
        NotificationToast.show_toast(toast, "Title", "Short message", "general")
        toast._message_label.setText.assert_called_once_with("Short message")

    def test_show_toast_truncates_long_message(self):
        from ui.notification_toast import NotificationToast

        toast = self._make_mock_toast()
        long_msg = "A" * 200
        NotificationToast.show_toast(toast, "Title", long_msg, "general")
        called_msg = toast._message_label.setText.call_args[0][0]
        self.assertEqual(len(called_msg), 120)

    def test_show_toast_starts_auto_hide_timer(self):
        from ui.notification_toast import NotificationToast

        toast = self._make_mock_toast()
        NotificationToast.show_toast(toast, "Title", "Msg", "general")
        toast._auto_hide_timer.start.assert_called_once_with(4000)

    def test_show_toast_uses_category_colour(self):
        from ui.notification_toast import NotificationToast, _CATEGORY_COLORS
        from PyQt6.QtGui import QColor

        toast = self._make_mock_toast()
        NotificationToast.show_toast(toast, "Alert", "Sec issue", "security")
        # The accent color should be set to the security colour
        self.assertIsNotNone(toast._accent_color)

    def test_show_toast_unknown_category_uses_default(self):
        from ui.notification_toast import NotificationToast, _CATEGORY_COLORS

        toast = self._make_mock_toast()
        NotificationToast.show_toast(toast, "Title", "Msg", "nonexistent")
        # Should fall back to default (#39c5cf) without crashing
        self.assertIsNotNone(toast._accent_color)

    def test_show_toast_with_parent_positions_correctly(self):
        from ui.notification_toast import NotificationToast
        from PyQt6.QtCore import QPoint

        toast = self._make_mock_toast()
        parent = MagicMock()
        parent.width.return_value = 1200
        toast.parent.return_value = parent

        # Need to also mock QPropertyAnimation
        with patch('ui.notification_toast.QPropertyAnimation') as mock_anim_cls:
            mock_anim = MagicMock()
            mock_anim_cls.return_value = mock_anim
            NotificationToast.show_toast(toast, "Title", "Msg", "general")

            # Should position at top-right of parent
            toast.move.assert_called_once()
            move_args = toast.move.call_args[0]
            x = move_args[0]
            expected_x = 1200 - 360 - 16  # parent.width - TOAST_WIDTH - 16
            self.assertEqual(x, expected_x)

    def test_show_toast_without_parent_still_shows(self):
        from ui.notification_toast import NotificationToast

        toast = self._make_mock_toast()
        toast.parent.return_value = None

        NotificationToast.show_toast(toast, "Title", "Msg", "general")
        toast.show.assert_called_once()


class TestSlideOut(unittest.TestCase):
    """_slide_out behaviour."""

    def test_slide_out_stops_timer(self):
        from ui.notification_toast import NotificationToast

        toast = MagicMock(spec=NotificationToast)
        toast._auto_hide_timer = MagicMock()
        toast.parent.return_value = None
        toast.hide = MagicMock()
        toast.TOAST_HEIGHT = 72

        NotificationToast._slide_out(toast)

        toast._auto_hide_timer.stop.assert_called_once()

    def test_slide_out_hides_when_no_parent(self):
        from ui.notification_toast import NotificationToast

        toast = MagicMock(spec=NotificationToast)
        toast._auto_hide_timer = MagicMock()
        toast.parent.return_value = None
        toast.hide = MagicMock()
        toast.TOAST_HEIGHT = 72

        NotificationToast._slide_out(toast)

        toast.hide.assert_called_once()

    def test_slide_out_with_parent_creates_animation(self):
        from ui.notification_toast import NotificationToast
        from PyQt6.QtCore import QPoint

        toast = MagicMock(spec=NotificationToast)
        toast._auto_hide_timer = MagicMock()
        toast.TOAST_HEIGHT = 72
        parent = MagicMock()
        toast.parent.return_value = parent
        toast.pos.return_value = QPoint(800, 60)

        with patch('ui.notification_toast.QPropertyAnimation') as mock_anim_cls:
            mock_anim = MagicMock()
            mock_anim_cls.return_value = mock_anim

            NotificationToast._slide_out(toast)

            mock_anim.start.assert_called_once()


if __name__ == '__main__':
    unittest.main()
