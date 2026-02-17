"""Tests for Settings tab experience level selector (v47.0)."""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.experience_level import ExperienceLevel


class TestSettingsExperienceLevel(unittest.TestCase):
    """Tests for experience level integration in settings."""

    @patch('utils.experience_level.SettingsManager')
    def test_experience_description_beginner(self, mock_sm):
        """Beginner description should mention simplified view."""
        from ui.settings_tab import SettingsTab
        tab = SettingsTab.__new__(SettingsTab)
        tab._main_window = None
        tab._mgr = MagicMock()
        tab._ui_initialized = False
        tab.tr = lambda s: s
        desc = tab._experience_description(ExperienceLevel.BEGINNER)
        self.assertIn("Simplified", desc)

    @patch('utils.experience_level.SettingsManager')
    def test_experience_description_intermediate(self, mock_sm):
        """Intermediate description should mention development."""
        from ui.settings_tab import SettingsTab
        tab = SettingsTab.__new__(SettingsTab)
        tab._main_window = None
        tab._mgr = MagicMock()
        tab._ui_initialized = False
        tab.tr = lambda s: s
        desc = tab._experience_description(ExperienceLevel.INTERMEDIATE)
        self.assertIn("development", desc)

    @patch('utils.experience_level.SettingsManager')
    def test_experience_description_advanced(self, mock_sm):
        """Advanced description should mention full access."""
        from ui.settings_tab import SettingsTab
        tab = SettingsTab.__new__(SettingsTab)
        tab._main_window = None
        tab._mgr = MagicMock()
        tab._ui_initialized = False
        tab.tr = lambda s: s
        desc = tab._experience_description(ExperienceLevel.ADVANCED)
        self.assertIn("Full access", desc)

    @patch('utils.experience_level.SettingsManager')
    def test_on_experience_level_changed_sets_level(self, mock_sm):
        """Changing experience level combo should update settings."""
        from ui.settings_tab import SettingsTab
        tab = SettingsTab.__new__(SettingsTab)
        tab._main_window = None
        tab._mgr = MagicMock()
        tab._ui_initialized = False
        tab.tr = lambda s: s
        tab._experience_desc = MagicMock()

        with patch('utils.experience_level.ExperienceLevelManager.set_level') as mock_set:
            tab._on_experience_level_changed(2)  # Advanced
            mock_set.assert_called_once_with(ExperienceLevel.ADVANCED)


class TestSettingsExperienceLevelEdgeCases(unittest.TestCase):
    """Edge case tests for experience level in settings."""

    @patch('utils.experience_level.SettingsManager')
    def test_on_experience_level_changed_invalid_index(self, mock_sm):
        """Invalid combo index should default to BEGINNER."""
        from ui.settings_tab import SettingsTab
        tab = SettingsTab.__new__(SettingsTab)
        tab._main_window = None
        tab._mgr = MagicMock()
        tab._ui_initialized = False
        tab.tr = lambda s: s
        tab._experience_desc = MagicMock()

        with patch('utils.experience_level.ExperienceLevelManager.set_level') as mock_set:
            tab._on_experience_level_changed(99)
            mock_set.assert_called_once_with(ExperienceLevel.BEGINNER)


if __name__ == '__main__':
    unittest.main()
