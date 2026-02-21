"""
Tests for utils/automation_profiles.py — AutomationProfiles + AutomationRule.
Covers rule CRUD, validation, dry-run, action execution, and presets.
All subprocess + file I/O mocked.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.automation_profiles import (
    ActionType,
    AutomationProfiles,
    AutomationRule,
    TriggerType,
)


# ---------------------------------------------------------------------------
# AutomationRule dataclass
# ---------------------------------------------------------------------------
class TestAutomationRule(unittest.TestCase):

    def test_to_dict_roundtrip(self):
        r = AutomationRule(id="r1", name="R1", trigger="on_battery",
                           action="set_power_profile", action_params={"profile": "power-saver"})
        d = r.to_dict()
        r2 = AutomationRule.from_dict(d)
        self.assertEqual(r2, r)

    def test_defaults(self):
        r = AutomationRule(id="x", name="X", trigger="on_ac",
                           action="set_theme", action_params={})
        self.assertTrue(r.enabled)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TestEnums(unittest.TestCase):

    def test_trigger_values(self):
        self.assertEqual(TriggerType.ON_BATTERY.value, "on_battery")
        self.assertEqual(TriggerType.ON_STARTUP.value, "on_startup")

    def test_action_values(self):
        self.assertEqual(ActionType.SET_POWER_PROFILE.value, "set_power_profile")
        self.assertEqual(ActionType.RUN_COMMAND.value, "run_command")
        self.assertEqual(ActionType.ENABLE_FOCUS_MODE.value, "enable_focus_mode")


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
class TestConfigHelpers(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data='{"enabled":true,"rules":[]}')
    @patch.object(AutomationProfiles, "CONFIG_FILE")
    @patch.object(AutomationProfiles, "CONFIG_DIR")
    def test_load_config(self, mock_dir, mock_file, _open):
        mock_dir.mkdir = MagicMock()
        mock_file.exists.return_value = True
        cfg = AutomationProfiles.load_config()
        self.assertTrue(cfg["enabled"])

    @patch("builtins.open", new_callable=mock_open, read_data="INVALID")
    @patch.object(AutomationProfiles, "CONFIG_FILE")
    @patch.object(AutomationProfiles, "CONFIG_DIR")
    def test_load_config_corrupt(self, mock_dir, mock_file, _open):
        mock_dir.mkdir = MagicMock()
        mock_file.exists.return_value = True
        cfg = AutomationProfiles.load_config()
        self.assertIn("enabled", cfg)

    @patch.object(AutomationProfiles, "load_config", return_value={"enabled": True})
    def test_is_enabled_true(self, _):
        self.assertTrue(AutomationProfiles.is_enabled())

    @patch.object(AutomationProfiles, "load_config", return_value={"enabled": False})
    def test_is_enabled_false(self, _):
        self.assertFalse(AutomationProfiles.is_enabled())

    @patch.object(AutomationProfiles, "save_config")
    @patch.object(AutomationProfiles, "load_config", return_value={"enabled": True, "rules": []})
    def test_set_enabled(self, _load, mock_save):
        AutomationProfiles.set_enabled(False)
        saved = mock_save.call_args[0][0]
        self.assertFalse(saved["enabled"])


# ---------------------------------------------------------------------------
# Rule CRUD
# ---------------------------------------------------------------------------
class TestRuleCRUD(unittest.TestCase):

    @patch.object(AutomationProfiles, "load_config",
                  return_value={"rules": [{"id": "a", "name": "A"}]})
    def test_list_rules(self, _):
        rules = AutomationProfiles.list_rules()
        self.assertEqual(len(rules), 1)

    @patch.object(AutomationProfiles, "list_rules",
                  return_value=[{"id": "a", "name": "A"}, {"id": "b", "name": "B"}])
    def test_get_rule_found(self, _):
        r = AutomationProfiles.get_rule("b")
        self.assertEqual(r["name"], "B")

    @patch.object(AutomationProfiles, "list_rules", return_value=[])
    def test_get_rule_not_found(self, _):
        self.assertIsNone(AutomationProfiles.get_rule("nope"))

    @patch.object(AutomationProfiles, "save_config")
    @patch.object(AutomationProfiles, "load_config",
                  return_value={"enabled": True, "rules": []})
    @patch.object(AutomationProfiles, "validate_rule",
                  return_value={"success": True, "message": "OK", "errors": [], "warnings": []})
    def test_add_rule_success(self, _val, _load, _save):
        result = AutomationProfiles.add_rule({
            "id": "r1", "name": "R1", "trigger": "on_battery",
            "action": "set_power_profile", "action_params": {"profile": "power-saver"},
        })
        self.assertTrue(result["success"])

    @patch.object(AutomationProfiles, "save_config")
    @patch.object(AutomationProfiles, "load_config",
                  return_value={"enabled": True, "rules": []})
    @patch.object(AutomationProfiles, "validate_rule",
                  return_value={"success": True, "message": "OK", "errors": [], "warnings": []})
    def test_add_rule_generates_id(self, _val, _load, _save):
        result = AutomationProfiles.add_rule({
            "name": "NoID", "trigger": "on_ac",
            "action": "set_theme", "action_params": {"theme": "dark"},
        })
        self.assertTrue(result["success"])
        self.assertIn("id", result)

    @patch.object(AutomationProfiles, "validate_rule",
                  return_value={"success": False, "message": "bad"})
    def test_add_rule_validation_fail(self, _val):
        result = AutomationProfiles.add_rule({"name": "Bad"})
        self.assertFalse(result["success"])

    @patch.object(AutomationProfiles, "save_config")
    @patch.object(AutomationProfiles, "load_config",
                  return_value={"rules": [
                      {"id": "a", "name": "A", "trigger": "on_battery",
                       "action": "set_power_profile", "action_params": {"profile": "balanced"}},
                  ]})
    @patch.object(AutomationProfiles, "validate_rule",
                  return_value={"success": True, "message": "OK", "errors": [], "warnings": []})
    def test_update_rule_success(self, _val, _load, _save):
        result = AutomationProfiles.update_rule("a", {"name": "Updated"})
        self.assertTrue(result["success"])

    @patch.object(AutomationProfiles, "load_config", return_value={"rules": []})
    def test_update_rule_not_found(self, _):
        result = AutomationProfiles.update_rule("nope", {"name": "X"})
        self.assertFalse(result["success"])

    @patch.object(AutomationProfiles, "save_config")
    @patch.object(AutomationProfiles, "load_config",
                  return_value={"rules": [{"id": "a"}, {"id": "b"}]})
    def test_delete_rule_found(self, _load, _save):
        result = AutomationProfiles.delete_rule("a")
        self.assertTrue(result["success"])

    @patch.object(AutomationProfiles, "load_config", return_value={"rules": []})
    def test_delete_rule_not_found(self, _):
        result = AutomationProfiles.delete_rule("nope")
        self.assertFalse(result["success"])

    @patch.object(AutomationProfiles, "update_rule",
                  return_value={"success": True, "message": "ok"})
    def test_enable_rule(self, mock_update):
        AutomationProfiles.enable_rule("a", False)
        mock_update.assert_called_once_with("a", {"enabled": False})


# ---------------------------------------------------------------------------
# Rule matching
# ---------------------------------------------------------------------------
class TestRuleMatching(unittest.TestCase):

    @patch.object(AutomationProfiles, "list_rules", return_value=[
        {"id": "1", "trigger": "on_battery", "enabled": True},
        {"id": "2", "trigger": "on_ac", "enabled": True},
        {"id": "3", "trigger": "on_battery", "enabled": False},
    ])
    def test_get_rules_for_trigger(self, _):
        rules = AutomationProfiles.get_rules_for_trigger("on_battery")
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["id"], "1")

    @patch.object(AutomationProfiles, "save_config")
    @patch.object(AutomationProfiles, "load_config", return_value={"home_wifi_ssids": []})
    def test_set_home_wifi_ssids(self, _load, mock_save):
        AutomationProfiles.set_home_wifi_ssids(["MyNet", "BackupNet"])
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved["home_wifi_ssids"], ["MyNet", "BackupNet"])

    @patch.object(AutomationProfiles, "load_config",
                  return_value={"home_wifi_ssids": ["HomeWifi"]})
    def test_get_home_wifi_ssids(self, _):
        ssids = AutomationProfiles.get_home_wifi_ssids()
        self.assertEqual(ssids, ["HomeWifi"])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class TestValidation(unittest.TestCase):

    def test_valid_rule(self):
        rule = {
            "trigger": "on_battery", "action": "set_power_profile",
            "action_params": {"profile": "power-saver"},
        }
        result = AutomationProfiles.validate_rule(rule)
        self.assertTrue(result["success"])

    def test_invalid_trigger(self):
        rule = {"trigger": "invalid", "action": "set_theme", "action_params": {}}
        result = AutomationProfiles.validate_rule(rule)
        self.assertFalse(result["success"])

    def test_invalid_action(self):
        rule = {"trigger": "on_battery", "action": "fly_to_moon", "action_params": {}}
        result = AutomationProfiles.validate_rule(rule)
        self.assertFalse(result["success"])

    def test_missing_governor(self):
        rule = {
            "trigger": "on_battery", "action": "set_cpu_governor",
            "action_params": {},
        }
        result = AutomationProfiles.validate_rule(rule)
        self.assertFalse(result["success"])

    def test_missing_command(self):
        rule = {
            "trigger": "on_battery", "action": "run_command",
            "action_params": {},
        }
        result = AutomationProfiles.validate_rule(rule)
        self.assertFalse(result["success"])

    def test_power_profile_warning(self):
        rule = {
            "trigger": "on_battery", "action": "set_power_profile",
            "action_params": {"profile": "turbo"},
        }
        result = AutomationProfiles.validate_rule(rule)
        self.assertTrue(result["success"])
        self.assertTrue(len(result["warnings"]) > 0)

    def test_vpn_no_name_warning(self):
        rule = {
            "trigger": "on_public_wifi", "action": "enable_vpn",
            "action_params": {},
        }
        result = AutomationProfiles.validate_rule(rule)
        self.assertTrue(result["success"])
        self.assertTrue(any("vpn_name" in w for w in result["warnings"]))

    def test_tiling_no_script_warning(self):
        rule = {
            "trigger": "on_ultrawide", "action": "enable_tiling",
            "action_params": {},
        }
        result = AutomationProfiles.validate_rule(rule)
        self.assertTrue(result["success"])
        self.assertTrue(len(result["warnings"]) > 0)

    def test_theme_warning(self):
        rule = {
            "trigger": "on_ac", "action": "set_theme",
            "action_params": {"theme": "rainbow"},
        }
        result = AutomationProfiles.validate_rule(rule)
        self.assertTrue(result["success"])
        self.assertTrue(len(result["warnings"]) > 0)


# ---------------------------------------------------------------------------
# Dry-run / simulation
# ---------------------------------------------------------------------------
class TestDryRun(unittest.TestCase):

    def test_set_power_profile(self):
        r = AutomationProfiles.dry_run_action("set_power_profile", {"profile": "performance"})
        self.assertTrue(r["success"])
        self.assertIn("performance", r["message"])

    def test_set_cpu_governor(self):
        r = AutomationProfiles.dry_run_action("set_cpu_governor", {"governor": "ondemand"})
        self.assertTrue(r["success"])

    def test_enable_vpn(self):
        r = AutomationProfiles.dry_run_action("enable_vpn", {"vpn_name": "MyVPN"})
        self.assertTrue(r["success"])

    def test_disable_vpn(self):
        r = AutomationProfiles.dry_run_action("disable_vpn", {})
        self.assertTrue(r["success"])

    def test_enable_tiling(self):
        r = AutomationProfiles.dry_run_action("enable_tiling", {})
        self.assertTrue(r["success"])

    def test_disable_tiling(self):
        r = AutomationProfiles.dry_run_action("disable_tiling", {"script": "myscript"})
        self.assertTrue(r["success"])

    def test_set_theme(self):
        r = AutomationProfiles.dry_run_action("set_theme", {"theme": "light"})
        self.assertTrue(r["success"])

    def test_run_command(self):
        r = AutomationProfiles.dry_run_action("run_command", {"command": "echo hi"})
        self.assertTrue(r["success"])

    def test_enable_focus_mode(self):
        r = AutomationProfiles.dry_run_action("enable_focus_mode", {"profile": "deep-work"})
        self.assertTrue(r["success"])

    def test_disable_focus_mode(self):
        r = AutomationProfiles.dry_run_action("disable_focus_mode", {})
        self.assertTrue(r["success"])

    def test_unknown_action(self):
        r = AutomationProfiles.dry_run_action("fly_away", {})
        self.assertFalse(r["success"])

    @patch.object(AutomationProfiles, "get_rules_for_trigger", return_value=[
        {"id": "1", "name": "R1", "action": "set_power_profile", "action_params": {"profile": "balanced"}},
    ])
    def test_simulate_rules(self, _):
        result = AutomationProfiles.simulate_rules_for_trigger("on_battery")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 1)


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------
class TestActionExecution(unittest.TestCase):

    @patch("subprocess.run")
    def test_set_power_profile_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = AutomationProfiles.execute_action("set_power_profile", {"profile": "balanced"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_set_power_profile_fail(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        r = AutomationProfiles.execute_action("set_power_profile", {"profile": "bad"})
        self.assertFalse(r["success"])

    @patch("subprocess.run", side_effect=FileNotFoundError("no powerprofilesctl"))
    def test_set_power_profile_not_installed(self, _):
        r = AutomationProfiles.execute_action("set_power_profile", {"profile": "balanced"})
        self.assertFalse(r["success"])
        self.assertIn("not installed", r["message"])

    @patch("services.hardware.HardwareManager.set_governor",
           return_value={"success": True, "message": "done"})
    def test_set_cpu_governor_via_hardware_manager(self, _):
        r = AutomationProfiles.execute_action("set_cpu_governor", {"governor": "performance"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_enable_vpn_with_name(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = AutomationProfiles.execute_action("enable_vpn", {"vpn_name": "MyVPN"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_enable_vpn_auto_discover(self, mock_run):
        mock_run.side_effect = [
            MagicMock(stdout="MyVPN:vpn\nEthernet:802-3-ethernet\n"),  # list
            MagicMock(returncode=0),  # connect
        ]
        r = AutomationProfiles.execute_action("enable_vpn", {})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_enable_vpn_no_vpn_found(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Ethernet:802-3-ethernet\n")
        r = AutomationProfiles.execute_action("enable_vpn", {})
        self.assertFalse(r["success"])

    @patch("subprocess.run")
    def test_disable_vpn_with_active(self, mock_run):
        mock_run.side_effect = [
            MagicMock(stdout="MyVPN:vpn:activated\n"),  # list
            MagicMock(returncode=0),  # disconnect
        ]
        r = AutomationProfiles.execute_action("disable_vpn", {})
        self.assertTrue(r["success"])
        self.assertIn("MyVPN", r["message"])

    @patch("subprocess.run")
    def test_disable_vpn_none_active(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Ethernet:802-3-ethernet:activated\n")
        r = AutomationProfiles.execute_action("disable_vpn", {})
        self.assertTrue(r["success"])
        self.assertIn("No active", r["message"])

    @patch("subprocess.run")
    def test_set_theme_dark_kde(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = AutomationProfiles.execute_action("set_theme", {"theme": "dark"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_set_theme_light_kde(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = AutomationProfiles.execute_action("set_theme", {"theme": "light"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_set_theme_kde_fails_gnome_succeeds(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # KDE fails
            MagicMock(returncode=0),  # GNOME succeeds
        ]
        r = AutomationProfiles.execute_action("set_theme", {"theme": "dark"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_set_theme_both_fail(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # KDE fails
            MagicMock(returncode=1),  # GNOME fails
        ]
        r = AutomationProfiles.execute_action("set_theme", {"theme": "dark"})
        self.assertFalse(r["success"])

    @patch("subprocess.run")
    def test_run_command_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")
        r = AutomationProfiles.execute_action("run_command", {"command": "echo hello"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_run_command_fail(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        r = AutomationProfiles.execute_action("run_command", {"command": "false"})
        self.assertFalse(r["success"])

    def test_run_command_no_command(self):
        r = AutomationProfiles.execute_action("run_command", {})
        self.assertFalse(r["success"])

    @patch("subprocess.run", side_effect=TimeoutError("timeout"))
    def test_run_command_timeout(self, _):
        # subprocess.TimeoutExpired is caught by execute_action wrapper
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.TimeoutExpired("cmd", 60)):
            r = AutomationProfiles.execute_action("run_command", {"command": "sleep 999"})
            self.assertFalse(r["success"])

    @patch("utils.focus_mode.FocusMode.enable",
           return_value={"success": True, "message": "enabled"})
    def test_enable_focus_mode(self, _):
        r = AutomationProfiles.execute_action("enable_focus_mode", {"profile": "deep"})
        self.assertTrue(r["success"])

    @patch("utils.focus_mode.FocusMode.disable",
           return_value={"success": True, "message": "disabled"})
    def test_disable_focus_mode(self, _):
        r = AutomationProfiles.execute_action("disable_focus_mode", {})
        self.assertTrue(r["success"])

    def test_unknown_action(self):
        r = AutomationProfiles.execute_action("fly_to_mars", {})
        self.assertFalse(r["success"])

    @patch("utils.focus_mode.FocusMode.enable", side_effect=ImportError("no module"))
    def test_focus_mode_import_error(self, _):
        r = AutomationProfiles.execute_action("enable_focus_mode", {})
        self.assertFalse(r["success"])


# ---------------------------------------------------------------------------
# execute_rules_for_trigger
# ---------------------------------------------------------------------------
class TestExecuteRulesForTrigger(unittest.TestCase):

    @patch.object(AutomationProfiles, "is_enabled", return_value=False)
    def test_disabled(self, _):
        r = AutomationProfiles.execute_rules_for_trigger("on_battery")
        self.assertTrue(r["success"])
        self.assertIn("disabled", r["message"])

    @patch.object(AutomationProfiles, "execute_action",
                  return_value={"success": True, "message": "ok"})
    @patch.object(AutomationProfiles, "get_rules_for_trigger", return_value=[
        {"id": "1", "name": "R1", "action": "set_power_profile",
         "action_params": {"profile": "power-saver"}},
    ])
    @patch.object(AutomationProfiles, "is_enabled", return_value=True)
    def test_executes_matching_rules(self, _en, _rules, _exec):
        r = AutomationProfiles.execute_rules_for_trigger("on_battery")
        self.assertEqual(len(r["results"]), 1)


# ---------------------------------------------------------------------------
# Tiling actions
# ---------------------------------------------------------------------------
class TestTilingActions(unittest.TestCase):

    @patch("subprocess.run")
    def test_enable_tiling_fallback(self, mock_run):
        """KWinTiling module doesn't exist, so ImportError fallback always runs."""
        mock_run.return_value = MagicMock(returncode=0)
        r = AutomationProfiles.execute_action("enable_tiling", {})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    def test_disable_tiling_fallback(self, mock_run):
        """KWinTiling module doesn't exist, so ImportError fallback always runs."""
        mock_run.return_value = MagicMock(returncode=0)
        r = AutomationProfiles.execute_action("disable_tiling", {})
        self.assertTrue(r["success"])


# ---------------------------------------------------------------------------
# CPU governor fallback
# ---------------------------------------------------------------------------
class TestCPUGovernorFallback(unittest.TestCase):

    @patch("subprocess.run")
    @patch("services.hardware.HardwareManager.set_governor", side_effect=ImportError("no module"))
    def test_fallback_success(self, _, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = AutomationProfiles.execute_action("set_cpu_governor", {"governor": "performance"})
        self.assertTrue(r["success"])

    @patch("subprocess.run")
    @patch("services.hardware.HardwareManager.set_governor", side_effect=ImportError("no module"))
    def test_fallback_failure(self, _, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        r = AutomationProfiles.execute_action("set_cpu_governor", {"governor": "performance"})
        self.assertFalse(r["success"])


# ---------------------------------------------------------------------------
# Quick presets
# ---------------------------------------------------------------------------
class TestQuickPresets(unittest.TestCase):

    @patch.object(AutomationProfiles, "add_rule",
                  return_value={"success": True, "message": "ok", "id": "x"})
    def test_battery_saver_preset(self, mock_add):
        result = AutomationProfiles.create_battery_saver_preset()
        self.assertTrue(result["success"])
        self.assertEqual(mock_add.call_count, 2)

    @patch.object(AutomationProfiles, "add_rule",
                  return_value={"success": True, "message": "ok", "id": "x"})
    def test_tiling_preset(self, mock_add):
        result = AutomationProfiles.create_tiling_preset()
        self.assertTrue(result["success"])
        self.assertEqual(mock_add.call_count, 2)


if __name__ == "__main__":
    unittest.main()
