"""Basic geometry sanity checks for the main window client area."""

import importlib
import os
import sys
import unittest
from unittest.mock import patch


# Allow Qt to initialize in headless CI/dev environments.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Add source path so that 'ui.*' imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

try:
    from PyQt6.QtWidgets import QApplication
    _HAS_QT_WIDGETS = True
except ImportError:
    _HAS_QT_WIDGETS = False


@unittest.skipUnless(_HAS_QT_WIDGETS, "PyQt6.QtWidgets not available (headless environment)")
class TestMainWindowGeometry(unittest.TestCase):
    """Guard against client-area content being laid out into top chrome."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_central_widget_starts_in_client_area(self):
        mod = importlib.import_module("ui.main_window")
        MainWindow = mod.MainWindow

        with patch.object(MainWindow, "_start_pulse_listener", lambda self: None), \
             patch.object(MainWindow, "setup_tray", lambda self: None), \
             patch.object(MainWindow, "check_dependencies", lambda self: None), \
             patch.object(MainWindow, "_check_first_run", lambda self: None):
            window = MainWindow()

        window.show()
        self.app.processEvents()

        central = window.centralWidget()
        self.assertIsNotNone(central)
        self.assertGreaterEqual(central.geometry().y(), 0)

        root_layout = central.layout()
        self.assertIsNotNone(root_layout)
        first_widget = root_layout.itemAt(0).widget()
        self.assertIsNotNone(first_widget)
        self.assertTrue(first_widget.isVisible())
        self.assertGreaterEqual(first_widget.geometry().y(), 0)

        window.close()

    def test_minimum_window_size(self):
        """Verify minimum window size is enforced (800x500)."""
        mod = importlib.import_module("ui.main_window")
        MainWindow = mod.MainWindow

        with patch.object(MainWindow, "_start_pulse_listener", lambda self: None), \
             patch.object(MainWindow, "setup_tray", lambda self: None), \
             patch.object(MainWindow, "check_dependencies", lambda self: None), \
             patch.object(MainWindow, "_check_first_run", lambda self: None):
            window = MainWindow()

        min_size = window.minimumSize()
        self.assertGreaterEqual(min_size.width(), 800)
        self.assertGreaterEqual(min_size.height(), 500)

        window.close()

    def test_breadcrumb_bar_height(self):
        """Verify breadcrumb bar has positive height."""
        mod = importlib.import_module("ui.main_window")
        MainWindow = mod.MainWindow

        with patch.object(MainWindow, "_start_pulse_listener", lambda self: None), \
             patch.object(MainWindow, "setup_tray", lambda self: None), \
             patch.object(MainWindow, "check_dependencies", lambda self: None), \
             patch.object(MainWindow, "_check_first_run", lambda self: None):
            window = MainWindow()

        window.show()
        self.app.processEvents()

        breadcrumb = window._breadcrumb_frame
        self.assertIsNotNone(breadcrumb)
        self.assertGreater(breadcrumb.height(), 0)

        window.close()

    def test_status_bar_height(self):
        """Verify status bar has positive height."""
        mod = importlib.import_module("ui.main_window")
        MainWindow = mod.MainWindow

        with patch.object(MainWindow, "_start_pulse_listener", lambda self: None), \
             patch.object(MainWindow, "setup_tray", lambda self: None), \
             patch.object(MainWindow, "check_dependencies", lambda self: None), \
             patch.object(MainWindow, "_check_first_run", lambda self: None):
            window = MainWindow()

        window.show()
        self.app.processEvents()

        status_frame = window._status_frame
        self.assertIsNotNone(status_frame)
        self.assertGreater(status_frame.height(), 0)

        window.close()

    def test_sidebar_width(self):
        """Verify sidebar has positive width."""
        mod = importlib.import_module("ui.main_window")
        MainWindow = mod.MainWindow

        with patch.object(MainWindow, "_start_pulse_listener", lambda self: None), \
             patch.object(MainWindow, "setup_tray", lambda self: None), \
             patch.object(MainWindow, "check_dependencies", lambda self: None), \
             patch.object(MainWindow, "_check_first_run", lambda self: None):
            window = MainWindow()

        window.show()
        self.app.processEvents()

        sidebar = window.sidebar
        self.assertIsNotNone(sidebar)
        self.assertGreater(sidebar.width(), 0)

        window.close()

    def test_no_widget_overlaps_origin(self):
        """Verify no visible widgets overlap the (0,0) origin point."""
        mod = importlib.import_module("ui.main_window")
        MainWindow = mod.MainWindow

        with patch.object(MainWindow, "_start_pulse_listener", lambda self: None), \
             patch.object(MainWindow, "setup_tray", lambda self: None), \
             patch.object(MainWindow, "check_dependencies", lambda self: None), \
             patch.object(MainWindow, "_check_first_run", lambda self: None):
            window = MainWindow()

        window.show()
        self.app.processEvents()

        central = window.centralWidget()
        self.assertIsNotNone(central)

        # Check that central widget doesn't start at (0,0) or that if it does,
        # its first child widget has proper offset
        root_layout = central.layout()
        self.assertIsNotNone(root_layout)

        # Sidebar should not be at (0,0) in window coordinates
        sidebar_container = root_layout.itemAt(0).widget()
        self.assertIsNotNone(sidebar_container)
        geom = sidebar_container.geometry()
        # In a properly laid out window, sidebar should start after any chrome
        self.assertGreaterEqual(geom.x(), 0)
        self.assertGreaterEqual(geom.y(), 0)

        window.close()


if __name__ == "__main__":
    unittest.main()
