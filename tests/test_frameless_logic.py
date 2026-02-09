"""
Unit tests for frameless mode feature flag logic (without Qt dependencies).
Tests the flag resolution logic in isolation.
"""

import os
import unittest
from unittest.mock import patch


class TestFramelessFlagLogic(unittest.TestCase):
    """Test frameless mode flag resolution logic."""

    def setUp(self):
        """Clear environment before each test."""
        if "LOOFI_FRAMELESS" in os.environ:
            del os.environ["LOOFI_FRAMELESS"]

    def tearDown(self):
        """Clean up environment after each test."""
        if "LOOFI_FRAMELESS" in os.environ:
            del os.environ["LOOFI_FRAMELESS"]

    def _get_frameless_mode_flag_logic(self) -> bool:
        """
        Replica of MainWindow._get_frameless_mode_flag logic for testing.

        Priority:
        1. Config file: ui.frameless_mode key
        2. Environment variable: LOOFI_FRAMELESS=1

        Returns:
            True if frameless mode is enabled, False otherwise (default).
        """
        from utils.config_manager import ConfigManager

        # Check config file first
        config = ConfigManager.load_config()
        if config is not None:
            ui_settings = config.get("ui", {})
            if "frameless_mode" in ui_settings:
                return bool(ui_settings["frameless_mode"])

        # Fallback to environment variable
        env_value = os.environ.get("LOOFI_FRAMELESS", "").strip()
        return env_value == "1"

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_frameless_disabled_by_default(self, mock_config):
        """Test that frameless mode is disabled by default."""
        mock_config.return_value = None
        self.assertFalse(self._get_frameless_mode_flag_logic())

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_frameless_enabled_via_config(self, mock_config):
        """Test frameless mode enabled via config file."""
        mock_config.return_value = {"ui": {"frameless_mode": True}}
        self.assertTrue(self._get_frameless_mode_flag_logic())

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_frameless_disabled_via_config(self, mock_config):
        """Test frameless mode explicitly disabled via config file."""
        mock_config.return_value = {"ui": {"frameless_mode": False}}
        self.assertFalse(self._get_frameless_mode_flag_logic())

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_frameless_enabled_via_env_var(self, mock_config):
        """Test frameless mode enabled via environment variable."""
        mock_config.return_value = None
        os.environ["LOOFI_FRAMELESS"] = "1"
        self.assertTrue(self._get_frameless_mode_flag_logic())

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_frameless_env_var_wrong_value(self, mock_config):
        """Test that only LOOFI_FRAMELESS=1 enables frameless mode."""
        mock_config.return_value = None

        # Test various wrong values
        for wrong_value in ["true", "True", "yes", "enabled", "0", ""]:
            os.environ["LOOFI_FRAMELESS"] = wrong_value
            self.assertFalse(
                self._get_frameless_mode_flag_logic(),
                f"Should be False for LOOFI_FRAMELESS={wrong_value}"
            )

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_config_takes_priority_over_env(self, mock_config):
        """Test that config file takes priority over environment variable."""
        mock_config.return_value = {"ui": {"frameless_mode": False}}
        os.environ["LOOFI_FRAMELESS"] = "1"

        # Config says False, should override env var
        self.assertFalse(self._get_frameless_mode_flag_logic())

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_config_priority_true_over_env_false(self, mock_config):
        """Test config=True overrides env not set."""
        mock_config.return_value = {"ui": {"frameless_mode": True}}
        # No env var set
        self.assertTrue(self._get_frameless_mode_flag_logic())

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_empty_ui_dict_falls_back_to_env(self, mock_config):
        """Test that empty ui dict in config falls back to env var."""
        mock_config.return_value = {"ui": {}}
        os.environ["LOOFI_FRAMELESS"] = "1"

        # No frameless_mode key in ui dict, should check env var
        self.assertTrue(self._get_frameless_mode_flag_logic())

    @patch("utils.config_manager.ConfigManager.load_config")
    def test_no_ui_section_falls_back_to_env(self, mock_config):
        """Test that missing ui section in config falls back to env var."""
        mock_config.return_value = {"other_section": {}}
        os.environ["LOOFI_FRAMELESS"] = "1"

        # No ui section at all, should check env var
        self.assertTrue(self._get_frameless_mode_flag_logic())


if __name__ == "__main__":
    unittest.main()
