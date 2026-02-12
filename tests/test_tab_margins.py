"""Tab margin regression tests - verify content margins are properly set."""

import importlib
import os
import sys
import unittest
from unittest.mock import patch, MagicMock


# Allow Qt to initialize in headless CI/dev environments.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Add source path so that 'ui.*' imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

try:
    from PyQt6.QtWidgets import QApplication, QWidget
    _HAS_QT_WIDGETS = True
except ImportError:
    _HAS_QT_WIDGETS = False


def _stub_widget(*_args, **_kwargs):
    """Return a lightweight QWidget for tab-builder stubs."""
    return QWidget()


@unittest.skipUnless(_HAS_QT_WIDGETS, "PyQt6.QtWidgets not available (headless environment)")
class TestTabMargins(unittest.TestCase):
    """Verify that tab root layouts have proper content margins set."""

    @classmethod
    def setUpClass(cls):
        app_instance = QApplication.instance()
        if isinstance(app_instance, QApplication):
            cls.app = app_instance
        elif app_instance is None:
            cls.app = QApplication([])
        else:
            raise unittest.SkipTest("QApplication unavailable (QCoreApplication is active)")

    def setUp(self):
        if not isinstance(QApplication.instance(), QApplication):
            raise unittest.SkipTest("QApplication unavailable for QWidget tests")

    def _get_root_layout_margins(self, tab_widget):
        """Helper to extract content margins from a tab's root layout."""
        layout = tab_widget.layout()
        if layout is None:
            return None
        margins = layout.getContentsMargins()
        return margins  # Returns (left, top, right, bottom)

    def _assert_positive_root_margins(self, tab, tab_name):
        """Assert positive margins without forcing GUI event processing in CI."""
        margins = self._get_root_layout_margins(tab)
        self.assertIsNotNone(margins, f"{tab_name} should have a root layout")

        left, top, right, bottom = margins
        self.assertGreater(left, 0, "Left margin should be > 0")
        self.assertGreater(top, 0, "Top margin should be > 0")
        self.assertGreater(right, 0, "Right margin should be > 0")
        self.assertGreater(bottom, 0, "Bottom margin should be > 0")

    def test_diagnostics_tab_margins(self):
        """Verify diagnostics tab has positive content margins."""
        mod = importlib.import_module("ui.diagnostics_tab")
        DiagnosticsTab = mod.DiagnosticsTab

        tab = DiagnosticsTab()
        self._assert_positive_root_margins(tab, "DiagnosticsTab")

        tab.close()

    def test_desktop_tab_margins(self):
        """Verify desktop tab has positive content margins."""
        mod = importlib.import_module("ui.desktop_tab")
        DesktopTab = mod.DesktopTab

        tab = DesktopTab()
        self._assert_positive_root_margins(tab, "DesktopTab")

        tab.close()

    def test_security_tab_margins(self):
        """Verify security tab has positive content margins."""
        mod = importlib.import_module("ui.security_tab")
        SecurityTab = mod.SecurityTab

        tab = SecurityTab()
        self._assert_positive_root_margins(tab, "SecurityTab")

        tab.close()

    @patch("ui.ai_enhanced_tab.AIEnhancedTab._create_models_tab", side_effect=_stub_widget)
    @patch("ui.ai_enhanced_tab.AIEnhancedTab._create_voice_tab", side_effect=_stub_widget)
    @patch("ui.ai_enhanced_tab.AIEnhancedTab._create_knowledge_tab", side_effect=_stub_widget)
    def test_ai_enhanced_tab_margins(self, *_mocks):
        """Verify AI Lab tab has positive content margins."""
        mod = importlib.import_module("ui.ai_enhanced_tab")
        AIEnhancedTab = mod.AIEnhancedTab

        tab = AIEnhancedTab()
        self._assert_positive_root_margins(tab, "AIEnhancedTab")

        tab.close()

    def test_settings_tab_margins(self):
        """Verify settings tab has positive content margins."""
        # Mock SettingsManager with proper return types per key
        defaults = {
            "theme": "dark",
            "follow_system_theme": False,
            "start_minimized": False,
            "show_notifications": True,
            "confirm_dangerous_actions": True,
            "restore_last_tab": False,
            "log_level": "INFO",
            "check_updates_on_start": True,
        }
        mock_settings_mgr = MagicMock()
        mock_settings_mgr.get.side_effect = lambda key, *a, **kw: defaults.get(key, "")

        with patch("ui.settings_tab.SettingsManager") as mock_mgr_class:
            mock_mgr_class.instance.return_value = mock_settings_mgr

            mod = importlib.import_module("ui.settings_tab")
            SettingsTab = mod.SettingsTab

            tab = SettingsTab()
            self._assert_positive_root_margins(tab, "SettingsTab")

            tab.close()


if __name__ == "__main__":
    unittest.main()
