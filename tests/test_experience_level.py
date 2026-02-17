"""Tests for utils/experience_level.py"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.experience_level import ExperienceLevel, ExperienceLevelManager


class TestExperienceLevel(unittest.TestCase):
    """Tests for ExperienceLevel enum."""

    def test_enum_values(self):
        """Test enum has all three levels."""
        self.assertEqual(ExperienceLevel.BEGINNER.value, "beginner")
        self.assertEqual(ExperienceLevel.INTERMEDIATE.value, "intermediate")
        self.assertEqual(ExperienceLevel.ADVANCED.value, "advanced")

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        self.assertEqual(ExperienceLevel("beginner"), ExperienceLevel.BEGINNER)
        self.assertEqual(ExperienceLevel("intermediate"), ExperienceLevel.INTERMEDIATE)
        self.assertEqual(ExperienceLevel("advanced"), ExperienceLevel.ADVANCED)

    def test_enum_invalid_value(self):
        """Test that invalid value raises ValueError."""
        with self.assertRaises(ValueError):
            ExperienceLevel("expert")


class TestExperienceLevelManagerGetLevel(unittest.TestCase):
    """Tests for ExperienceLevelManager.get_level()."""

    @patch('utils.experience_level.SettingsManager')
    def test_get_level_beginner(self, mock_settings_cls):
        """Test getting beginner level from settings."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = "beginner"
        mock_settings_cls.instance.return_value = mock_mgr

        result = ExperienceLevelManager.get_level()

        self.assertEqual(result, ExperienceLevel.BEGINNER)
        mock_mgr.get.assert_called_once_with("experience_level", "beginner")

    @patch('utils.experience_level.SettingsManager')
    def test_get_level_advanced(self, mock_settings_cls):
        """Test getting advanced level from settings."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = "advanced"
        mock_settings_cls.instance.return_value = mock_mgr

        result = ExperienceLevelManager.get_level()

        self.assertEqual(result, ExperienceLevel.ADVANCED)

    @patch('utils.experience_level.SettingsManager')
    def test_get_level_default_on_missing(self, mock_settings_cls):
        """Test that missing setting defaults to BEGINNER."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = "beginner"
        mock_settings_cls.instance.return_value = mock_mgr

        result = ExperienceLevelManager.get_level()

        self.assertEqual(result, ExperienceLevel.BEGINNER)

    @patch('utils.experience_level.SettingsManager')
    def test_get_level_invalid_defaults_beginner(self, mock_settings_cls):
        """Test that invalid stored value defaults to BEGINNER."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = "invalid_level"
        mock_settings_cls.instance.return_value = mock_mgr

        result = ExperienceLevelManager.get_level()

        self.assertEqual(result, ExperienceLevel.BEGINNER)


class TestExperienceLevelManagerSetLevel(unittest.TestCase):
    """Tests for ExperienceLevelManager.set_level()."""

    @patch('utils.experience_level.SettingsManager')
    def test_set_level_persists(self, mock_settings_cls):
        """Test that set_level saves to settings."""
        mock_mgr = MagicMock()
        mock_settings_cls.instance.return_value = mock_mgr

        ExperienceLevelManager.set_level(ExperienceLevel.ADVANCED)

        mock_mgr.set.assert_called_once_with("experience_level", "advanced")
        mock_mgr.save.assert_called_once()

    @patch('utils.experience_level.SettingsManager')
    def test_set_level_intermediate(self, mock_settings_cls):
        """Test setting intermediate level."""
        mock_mgr = MagicMock()
        mock_settings_cls.instance.return_value = mock_mgr

        ExperienceLevelManager.set_level(ExperienceLevel.INTERMEDIATE)

        mock_mgr.set.assert_called_once_with("experience_level", "intermediate")


class TestExperienceLevelManagerVisibleTabs(unittest.TestCase):
    """Tests for ExperienceLevelManager.get_visible_tabs()."""

    def test_beginner_tabs(self):
        """Test beginner level returns limited tab set."""
        tabs = ExperienceLevelManager.get_visible_tabs(ExperienceLevel.BEGINNER)

        self.assertIsInstance(tabs, list)
        self.assertIn("dashboard", tabs)
        self.assertIn("settings", tabs)
        self.assertIn("software", tabs)
        self.assertIn("hardware", tabs)
        self.assertIn("security", tabs)
        self.assertNotIn("development", tabs)
        self.assertNotIn("gaming", tabs)
        self.assertNotIn("virtualization", tabs)

    def test_intermediate_tabs_superset(self):
        """Test intermediate includes all beginner tabs plus more."""
        beginner = ExperienceLevelManager.get_visible_tabs(ExperienceLevel.BEGINNER)
        intermediate = ExperienceLevelManager.get_visible_tabs(ExperienceLevel.INTERMEDIATE)

        for tab in beginner:
            self.assertIn(tab, intermediate)
        self.assertGreater(len(intermediate), len(beginner))
        self.assertIn("development", intermediate)
        self.assertIn("gaming", intermediate)

    def test_advanced_returns_empty(self):
        """Test advanced level returns empty list (show all)."""
        tabs = ExperienceLevelManager.get_visible_tabs(ExperienceLevel.ADVANCED)

        self.assertEqual(tabs, [])

    def test_returns_copy(self):
        """Test that returned list is a copy, not a reference."""
        tabs1 = ExperienceLevelManager.get_visible_tabs(ExperienceLevel.BEGINNER)
        tabs2 = ExperienceLevelManager.get_visible_tabs(ExperienceLevel.BEGINNER)

        self.assertEqual(tabs1, tabs2)
        self.assertIsNot(tabs1, tabs2)


class TestExperienceLevelManagerIsTabVisible(unittest.TestCase):
    """Tests for ExperienceLevelManager.is_tab_visible()."""

    def test_beginner_visible_tab(self):
        """Test that core tab is visible in beginner mode."""
        self.assertTrue(ExperienceLevelManager.is_tab_visible("dashboard", ExperienceLevel.BEGINNER))

    def test_beginner_hidden_tab(self):
        """Test that advanced tab is hidden in beginner mode."""
        self.assertFalse(ExperienceLevelManager.is_tab_visible("development", ExperienceLevel.BEGINNER))

    def test_advanced_all_visible(self):
        """Test that all tabs are visible in advanced mode."""
        self.assertTrue(ExperienceLevelManager.is_tab_visible("development", ExperienceLevel.ADVANCED))
        self.assertTrue(ExperienceLevelManager.is_tab_visible("any-tab-id", ExperienceLevel.ADVANCED))

    def test_favorites_override(self):
        """Test that favorited tabs are always visible regardless of level."""
        result = ExperienceLevelManager.is_tab_visible(
            "development", ExperienceLevel.BEGINNER, favorites=["development"]
        )
        self.assertTrue(result)

    def test_favorites_none(self):
        """Test behavior when favorites is None."""
        result = ExperienceLevelManager.is_tab_visible("dashboard", ExperienceLevel.BEGINNER, favorites=None)
        self.assertTrue(result)

    def test_favorites_empty(self):
        """Test behavior when favorites is empty list."""
        result = ExperienceLevelManager.is_tab_visible("development", ExperienceLevel.BEGINNER, favorites=[])
        self.assertFalse(result)


class TestExperienceLevelManagerDefaultProfile(unittest.TestCase):
    """Tests for ExperienceLevelManager.get_default_for_profile()."""

    def test_server_profile(self):
        """Test server profile defaults to ADVANCED."""
        self.assertEqual(
            ExperienceLevelManager.get_default_for_profile("server"),
            ExperienceLevel.ADVANCED,
        )

    def test_development_profile(self):
        """Test development profile defaults to INTERMEDIATE."""
        self.assertEqual(
            ExperienceLevelManager.get_default_for_profile("development"),
            ExperienceLevel.INTERMEDIATE,
        )

    def test_daily_profile(self):
        """Test daily profile defaults to BEGINNER."""
        self.assertEqual(
            ExperienceLevelManager.get_default_for_profile("daily"),
            ExperienceLevel.BEGINNER,
        )

    def test_gaming_profile(self):
        """Test gaming profile defaults to INTERMEDIATE."""
        self.assertEqual(
            ExperienceLevelManager.get_default_for_profile("gaming"),
            ExperienceLevel.INTERMEDIATE,
        )

    def test_unknown_profile(self):
        """Test unknown profile defaults to BEGINNER."""
        self.assertEqual(
            ExperienceLevelManager.get_default_for_profile("unknown"),
            ExperienceLevel.BEGINNER,
        )

    def test_case_insensitive(self):
        """Test profile name is case-insensitive."""
        self.assertEqual(
            ExperienceLevelManager.get_default_for_profile("Server"),
            ExperienceLevel.ADVANCED,
        )


if __name__ == '__main__':
    unittest.main()
