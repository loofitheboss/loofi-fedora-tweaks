"""Tests for extended coverage of utils/automation_profiles.py."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.automation_profiles import AutomationProfiles, ActionType, TriggerType


class TestAutomationProfilesExtended(unittest.TestCase):
    """Additional branch coverage for AutomationProfiles."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = AutomationProfiles.CONFIG_DIR
        self.original_config_file = AutomationProfiles.CONFIG_FILE
        AutomationProfiles.CONFIG_DIR = AutomationProfiles.CONFIG_DIR.__class__(self.temp_dir)
        AutomationProfiles.CONFIG_FILE = AutomationProfiles.CONFIG_DIR / "automation.json"

    def tearDown(self):
        AutomationProfiles.CONFIG_DIR = self.original_config_dir
        AutomationProfiles.CONFIG_FILE = self.original_config_file
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_config_invalid_json_returns_default(self):
        """Invalid config JSON returns safe default config."""
        AutomationProfiles.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(AutomationProfiles.CONFIG_FILE, "w", encoding="utf-8") as file_obj:
            file_obj.write("{bad json")

        result = AutomationProfiles.load_config()
        self.assertTrue(result.get("enabled", False))
        self.assertEqual(result.get("rules"), [])

    def test_update_rule_not_found(self):
        """Updating unknown rule returns not found."""
        AutomationProfiles.save_config({"enabled": True, "rules": []})
        result = AutomationProfiles.update_rule("missing", {"name": "new"})
        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"].lower())

    def test_delete_rule_not_found(self):
        """Deleting unknown rule returns not found."""
        AutomationProfiles.save_config({"enabled": True, "rules": []})
        result = AutomationProfiles.delete_rule("missing")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"].lower())

    def test_update_rule_validation_failure(self):
        """Rule update fails if merged rule validation fails."""
        AutomationProfiles.save_config(
            {
                "enabled": True,
                "rules": [
                    {
                        "id": "r1",
                        "name": "Good",
                        "trigger": TriggerType.ON_STARTUP.value,
                        "action": ActionType.RUN_COMMAND.value,
                        "action_params": {"command": "echo ok"},
                        "enabled": True,
                    }
                ],
            }
        )

        result = AutomationProfiles.update_rule("r1", {"action_params": {}})
        self.assertFalse(result["success"])
        self.assertIn("validation", result["message"].lower())

    @patch('utils.automation_profiles.subprocess.run')
    def test_action_enable_vpn_no_vpn_found(self, mock_run):
        """Enable VPN returns graceful error when no VPN exists."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Home WiFi:wifi\n")
        result = AutomationProfiles._action_enable_vpn({})
        self.assertFalse(result["success"])
        self.assertIn("no vpn", result["message"].lower())

    @patch('utils.automation_profiles.subprocess.run')
    def test_action_enable_vpn_named_success(self, mock_run):
        """Enable VPN by explicit name runs nmcli up."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = AutomationProfiles._action_enable_vpn({"vpn_name": "WorkVPN"})
        self.assertTrue(result["success"])
        self.assertIn("WorkVPN", result["message"])

    @patch('utils.automation_profiles.subprocess.run')
    def test_action_disable_vpn_disconnects_active(self, mock_run):
        """Disable VPN disconnects active VPN entries."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="MyVPN:vpn:activated\n"),
            MagicMock(returncode=0),
        ]
        result = AutomationProfiles._action_disable_vpn({})
        self.assertTrue(result["success"])
        self.assertIn("MyVPN", result["message"])

    @patch('utils.automation_profiles.subprocess.run')
    def test_action_set_theme_fallback_to_gnome(self, mock_run):
        """Theme action falls back to gsettings when KDE path fails."""
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=0),
        ]
        result = AutomationProfiles._action_set_theme({"theme": "light"})
        self.assertTrue(result["success"])
        self.assertIn("light", result["message"])

    def test_action_run_command_without_command(self):
        """Run command action rejects empty command."""
        result = AutomationProfiles._action_run_command({})
        self.assertFalse(result["success"])
        self.assertIn("no command", result["message"].lower())

    @patch('utils.automation_profiles.subprocess.run')
    def test_action_run_command_timeout(self, mock_run):
        """Run command action handles timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=1)
        result = AutomationProfiles._action_run_command({"command": "echo hi"})
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["message"].lower())

    @patch('utils.automation_profiles.subprocess.run')
    def test_execute_action_unknown(self, mock_run):
        """Unknown action is rejected."""
        result = AutomationProfiles.execute_action("unknown", {})
        self.assertFalse(result["success"])
        self.assertIn("unknown action", result["message"].lower())
        mock_run.assert_not_called()

    @patch('utils.automation_profiles.subprocess.run')
    def test_execute_rules_for_trigger_runs_matching_rules(self, mock_run):
        """Trigger execution only runs enabled matching rules."""
        AutomationProfiles.save_config(
            {
                "enabled": True,
                "rules": [
                    {
                        "id": "r1",
                        "name": "battery",
                        "trigger": TriggerType.ON_BATTERY.value,
                        "action": ActionType.SET_POWER_PROFILE.value,
                        "action_params": {"profile": "balanced"},
                        "enabled": True,
                    },
                    {
                        "id": "r2",
                        "name": "disabled",
                        "trigger": TriggerType.ON_BATTERY.value,
                        "action": ActionType.SET_POWER_PROFILE.value,
                        "action_params": {"profile": "performance"},
                        "enabled": False,
                    },
                ],
            }
        )
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = AutomationProfiles.execute_rules_for_trigger(TriggerType.ON_BATTERY.value)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 1)

    @patch('utils.automation_profiles.subprocess.run')
    def test_set_power_profile_file_not_found(self, mock_run):
        """Set power profile handles missing binary."""
        mock_run.side_effect = FileNotFoundError("missing")
        result = AutomationProfiles._action_set_power_profile({"profile": "balanced"})
        self.assertFalse(result["success"])
        self.assertIn("not installed", result["message"].lower())

    @patch('utils.automation_profiles.subprocess.run')
    def test_set_power_profile_error_from_command(self, mock_run):
        """Set power profile propagates stderr on command error."""
        mock_run.return_value = MagicMock(returncode=1, stderr="permission denied")
        result = AutomationProfiles._action_set_power_profile({"profile": "balanced"})
        self.assertFalse(result["success"])
        self.assertIn("permission", result["message"].lower())


if __name__ == '__main__':
    unittest.main()
