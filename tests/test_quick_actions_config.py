"""
Tests for QuickActionsConfig — v31.0 Smart UX
"""
import unittest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.quick_actions_config import QuickActionsConfig


class TestQuickActionsConfig(unittest.TestCase):
    """Tests for QuickActionsConfig."""

    def test_default_actions_has_four(self):
        """Default actions returns 4 actions."""
        actions = QuickActionsConfig.default_actions()
        self.assertEqual(len(actions), 4)

    def test_default_actions_structure(self):
        """Each default action has all required fields."""
        actions = QuickActionsConfig.default_actions()
        for action in actions:
            self.assertIn("id", action)
            self.assertIn("label", action)
            self.assertIn("icon", action)
            self.assertIn("color", action)
            self.assertIn("target_tab", action)

    def test_default_actions_ids_unique(self):
        """All default action IDs are unique."""
        actions = QuickActionsConfig.default_actions()
        ids = [a["id"] for a in actions]
        self.assertEqual(len(ids), len(set(ids)))

    @patch('utils.quick_actions_config.os.path.isfile', return_value=False)
    def test_get_actions_no_file(self, mock_isfile):
        """Returns defaults when no config file exists."""
        result = QuickActionsConfig.get_actions()
        self.assertEqual(len(result), 4)

    @patch('builtins.open', mock_open(read_data='[{"id":"test","label":"Test","icon":"🔥","color":"#fff","target_tab":"Home"}]'))
    @patch('utils.quick_actions_config.os.path.isfile', return_value=True)
    def test_get_actions_from_file(self, mock_isfile):
        """Returns actions from config file."""
        result = QuickActionsConfig.get_actions()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "test")

    @patch('builtins.open', mock_open(read_data='[]'))
    @patch('utils.quick_actions_config.os.path.isfile', return_value=True)
    def test_get_actions_empty_file_returns_defaults(self, mock_isfile):
        """Returns defaults for empty array in config."""
        result = QuickActionsConfig.get_actions()
        self.assertEqual(len(result), 4)

    @patch('builtins.open', mock_open(read_data='invalid json'))
    @patch('utils.quick_actions_config.os.path.isfile', return_value=True)
    def test_get_actions_invalid_json(self, mock_isfile):
        """Returns defaults for invalid JSON."""
        result = QuickActionsConfig.get_actions()
        self.assertEqual(len(result), 4)

    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.quick_actions_config.os.makedirs')
    def test_set_actions_saves(self, mock_makedirs, mock_file):
        """set_actions writes to file."""
        actions = [{"id": "test", "label": "Test", "icon": "🔥", "color": "#fff", "target_tab": "Home"}]
        QuickActionsConfig.set_actions(actions)
        mock_file.assert_called_once()
        mock_makedirs.assert_called_once()

    @patch('builtins.open', side_effect=OSError("denied"))
    @patch('utils.quick_actions_config.os.makedirs')
    def test_set_actions_handles_error(self, mock_makedirs, mock_file):
        """set_actions handles write errors gracefully."""
        QuickActionsConfig.set_actions([])  # Should not raise

    @patch.object(QuickActionsConfig, 'set_actions')
    def test_reset_to_defaults(self, mock_set):
        """reset_to_defaults saves and returns defaults."""
        result = QuickActionsConfig.reset_to_defaults()
        self.assertEqual(len(result), 4)
        mock_set.assert_called_once()

    def test_validate_action_valid(self):
        """Valid action passes validation."""
        action = {"id": "test", "label": "Test", "icon": "🔥", "color": "#fff", "target_tab": "Home"}
        self.assertTrue(QuickActionsConfig.validate_action(action))

    def test_validate_action_missing_field(self):
        """Action missing required field fails validation."""
        action = {"id": "test", "label": "Test", "icon": "🔥"}
        self.assertFalse(QuickActionsConfig.validate_action(action))

    def test_validate_action_empty(self):
        """Empty dict fails validation."""
        self.assertFalse(QuickActionsConfig.validate_action({}))

    def test_default_actions_clean_cache(self):
        """Default actions include Clean Cache."""
        actions = QuickActionsConfig.default_actions()
        ids = [a["id"] for a in actions]
        self.assertIn("clean_cache", ids)

    def test_default_actions_update_all(self):
        """Default actions include Update All."""
        actions = QuickActionsConfig.default_actions()
        ids = [a["id"] for a in actions]
        self.assertIn("update_all", ids)


if __name__ == '__main__':
    unittest.main()
