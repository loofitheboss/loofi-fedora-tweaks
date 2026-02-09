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


if __name__ == "__main__":
    unittest.main()
