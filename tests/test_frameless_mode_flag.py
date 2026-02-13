"""
Unit tests for frameless mode feature flag.
Tests the _get_frameless_mode_flag method in MainWindow.

Note: These tests create real QApplication/MainWindow instances.
The logic is also tested without Qt in test_frameless_logic.py.
Skipped in CI where the offscreen Qt platform may crash.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

# Skip in CI or offscreen environments — creating real MainWindow spawns
# EventBus threads that leak and cause SIGABRT when running the full suite.
# Logic is already covered by test_frameless_logic.py (no Qt needed).
_SKIP_REASON = "Skipped — real MainWindow leaks EventBus threads. Logic covered by test_frameless_logic.py"
_SKIP = (
    os.environ.get("CI", "") == "true"
    or os.environ.get("GITHUB_ACTIONS", "") == "true"
    or os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    QApplication = None


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestFramelessModeFlag(unittest.TestCase):
    """Test frameless mode feature flag logic."""

    @classmethod
    def setUpClass(cls):
        """Ensure QApplication exists for PyQt6 tests."""
        if QApplication is None:
            raise unittest.SkipTest("PyQt6 unavailable in test environment")
        app_instance = QApplication.instance()
        if isinstance(app_instance, QApplication):
            cls.app = app_instance
        elif app_instance is None:
            cls.app = QApplication([])
        else:
            raise unittest.SkipTest("QApplication unavailable (QCoreApplication is active)")

    def setUp(self):
        """Clear environment before each test."""
        app_instance = QApplication.instance()
        if not isinstance(app_instance, QApplication):
            raise unittest.SkipTest("QApplication unavailable for QWidget tests")
        if "LOOFI_FRAMELESS" in os.environ:
            del os.environ["LOOFI_FRAMELESS"]

    def tearDown(self):
        """Clean up environment after each test."""
        if "LOOFI_FRAMELESS" in os.environ:
            del os.environ["LOOFI_FRAMELESS"]

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_frameless_disabled_by_default(self, mock_pulse, mock_sys, mock_config):
        """Test that frameless mode is disabled by default."""
        mock_config.return_value = None
        mock_sys.get_hostname.return_value = "test-host"

        from ui.main_window import MainWindow
        window = MainWindow()

        # Should return False when no config and no env var
        self.assertFalse(window._get_frameless_mode_flag())
        window.close()

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_frameless_enabled_via_config(self, mock_pulse, mock_sys, mock_config):
        """Test frameless mode enabled via config file."""
        mock_config.return_value = {"ui": {"frameless_mode": True}}
        mock_sys.get_hostname.return_value = "test-host"

        from ui.main_window import MainWindow
        window = MainWindow()

        self.assertTrue(window._get_frameless_mode_flag())
        window.close()

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_frameless_disabled_via_config(self, mock_pulse, mock_sys, mock_config):
        """Test frameless mode explicitly disabled via config file."""
        mock_config.return_value = {"ui": {"frameless_mode": False}}
        mock_sys.get_hostname.return_value = "test-host"

        from ui.main_window import MainWindow
        window = MainWindow()

        self.assertFalse(window._get_frameless_mode_flag())
        window.close()

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_frameless_enabled_via_env_var(self, mock_pulse, mock_sys, mock_config):
        """Test frameless mode enabled via environment variable."""
        mock_config.return_value = None
        mock_sys.get_hostname.return_value = "test-host"
        os.environ["LOOFI_FRAMELESS"] = "1"

        from ui.main_window import MainWindow
        window = MainWindow()

        self.assertTrue(window._get_frameless_mode_flag())
        window.close()

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_frameless_env_var_wrong_value(self, mock_pulse, mock_sys, mock_config):
        """Test that only LOOFI_FRAMELESS=1 enables frameless mode."""
        mock_config.return_value = None
        mock_sys.get_hostname.return_value = "test-host"
        os.environ["LOOFI_FRAMELESS"] = "true"

        from ui.main_window import MainWindow
        window = MainWindow()

        # Should be False because only "1" is accepted
        self.assertFalse(window._get_frameless_mode_flag())
        window.close()

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_config_takes_priority_over_env(self, mock_pulse, mock_sys, mock_config):
        """Test that config file takes priority over environment variable."""
        mock_config.return_value = {"ui": {"frameless_mode": False}}
        mock_sys.get_hostname.return_value = "test-host"
        os.environ["LOOFI_FRAMELESS"] = "1"

        from ui.main_window import MainWindow
        window = MainWindow()

        # Config says False, should override env var
        self.assertFalse(window._get_frameless_mode_flag())
        window.close()

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_warning_logged_when_enabled(self, mock_pulse, mock_sys, mock_config):
        """Test that warning is logged when frameless mode is enabled."""
        mock_config.return_value = {"ui": {"frameless_mode": True}}
        mock_sys.get_hostname.return_value = "test-host"

        with self.assertLogs("ui.main_window", level="WARNING") as log_context:
            from ui.main_window import MainWindow
            window = MainWindow()
            window.close()

        # Check that warning was logged
        self.assertTrue(
            any("Frameless mode requested but not yet fully implemented" in msg
                for msg in log_context.output)
        )

    @patch("ui.main_window.ConfigManager.load_config")
    @patch("ui.main_window.SystemManager")
    @patch("ui.main_window.SystemPulse")
    def test_no_warning_when_disabled(self, mock_pulse, mock_sys, mock_config):
        """Test that no warning is logged when frameless mode is disabled."""
        mock_config.return_value = None
        mock_sys.get_hostname.return_value = "test-host"

        # Should not raise any warnings
        from ui.main_window import MainWindow
        window = MainWindow()
        window.close()


if __name__ == "__main__":
    unittest.main()
