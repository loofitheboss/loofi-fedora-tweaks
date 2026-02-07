"""
Tests for v9.1 Pulse Update - Event-driven automation system.
Tests SystemPulse, FocusMode, and AutomationProfiles.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
import tempfile
from pathlib import Path

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.pulse import SystemPulse, PowerState, NetworkState
from utils.focus_mode import FocusMode
from utils.automation_profiles import AutomationProfiles, TriggerType, ActionType


# ---------------------------------------------------------------------------
# TestSystemPulse
# ---------------------------------------------------------------------------

class TestSystemPulse(unittest.TestCase):
    """Tests for the SystemPulse DBus event listener."""
    
    def test_dbus_availability_check(self):
        """Verify is_available() returns boolean."""
        result = SystemPulse.is_available()
        self.assertIsInstance(result, bool)
    
    @patch('utils.pulse.subprocess.run')
    def test_get_power_state_ac(self, mock_run):
        """Test power state detection returns AC."""
        mock_run.return_value = MagicMock(
            stdout="online: yes",
            returncode=0
        )
        state = SystemPulse.get_power_state()
        self.assertEqual(state, PowerState.AC.value)
    
    @patch('utils.pulse.subprocess.run')
    def test_get_power_state_battery(self, mock_run):
        """Test power state detection returns battery."""
        mock_run.return_value = MagicMock(
            stdout="online: no",
            returncode=0
        )
        state = SystemPulse.get_power_state()
        self.assertEqual(state, PowerState.BATTERY.value)
    
    @patch('utils.pulse.subprocess.run')
    def test_get_battery_level(self, mock_run):
        """Test battery level percentage reading."""
        mock_run.return_value = MagicMock(
            stdout="percentage: 75%",
            returncode=0
        )
        level = SystemPulse.get_battery_level()
        self.assertEqual(level, 75)
    
    @patch('utils.pulse.subprocess.run')
    def test_get_network_state_connected(self, mock_run):
        """Test network state detection returns connected."""
        mock_run.return_value = MagicMock(
            stdout="connected",
            returncode=0
        )
        state = SystemPulse.get_network_state()
        self.assertEqual(state, NetworkState.CONNECTED.value)
    
    @patch('utils.pulse.subprocess.run')
    def test_get_network_state_disconnected(self, mock_run):
        """Test network state detection returns disconnected."""
        mock_run.return_value = MagicMock(
            stdout="disconnected",
            returncode=0
        )
        state = SystemPulse.get_network_state()
        self.assertEqual(state, NetworkState.DISCONNECTED.value)
    
    @patch('utils.pulse.subprocess.run')
    def test_get_wifi_ssid(self, mock_run):
        """Test Wi-Fi SSID retrieval."""
        mock_run.return_value = MagicMock(
            stdout="yes:MyHomeWiFi\nno:NeighborWiFi",
            returncode=0
        )
        ssid = SystemPulse.get_wifi_ssid()
        self.assertEqual(ssid, "MyHomeWiFi")
    
    def test_is_public_wifi_detection(self):
        """Test public Wi-Fi heuristic detection."""
        with patch.object(SystemPulse, 'get_wifi_ssid', return_value="Starbucks WiFi"):
            self.assertTrue(SystemPulse.is_public_wifi())
        
        with patch.object(SystemPulse, 'get_wifi_ssid', return_value="MySecureHome5G"):
            self.assertFalse(SystemPulse.is_public_wifi())
    
    @patch('utils.pulse.subprocess.run')
    def test_get_connected_monitors(self, mock_run):
        """Test monitor detection via xrandr."""
        mock_run.return_value = MagicMock(
            stdout="eDP-1 connected primary 1920x1080+0+0\nHDMI-1 connected 3440x1440+1920+0",
            returncode=0
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 2)
        
        # Check for ultrawide detection (3440/1440 = 2.38 > 2.0)
        hdmi = next((m for m in monitors if m["name"] == "HDMI-1"), None)
        if hdmi and hdmi["width"] > 0:
            self.assertTrue(hdmi["is_ultrawide"])


# ---------------------------------------------------------------------------
# TestFocusMode
# ---------------------------------------------------------------------------

class TestFocusMode(unittest.TestCase):
    """Tests for the FocusMode productivity feature."""
    
    def setUp(self):
        """Create temp config directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = FocusMode.CONFIG_DIR
        self.original_config_file = FocusMode.CONFIG_FILE
        FocusMode.CONFIG_DIR = Path(self.temp_dir)
        FocusMode.CONFIG_FILE = Path(self.temp_dir) / "focus_mode.json"
    
    def tearDown(self):
        """Restore original config paths."""
        FocusMode.CONFIG_DIR = self.original_config_dir
        FocusMode.CONFIG_FILE = self.original_config_file
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ensure_config_creates_default(self):
        """Test that ensure_config creates default profile."""
        FocusMode.ensure_config()
        self.assertTrue(FocusMode.CONFIG_FILE.exists())
        
        config = FocusMode.load_config()
        self.assertIn("profiles", config)
        self.assertIn("default", config["profiles"])
    
    def test_list_profiles(self):
        """Test listing available profiles."""
        FocusMode.ensure_config()
        profiles = FocusMode.list_profiles()
        self.assertIn("default", profiles)
    
    def test_get_profile(self):
        """Test retrieving a specific profile."""
        FocusMode.ensure_config()
        profile = FocusMode.get_profile("default")
        self.assertIsNotNone(profile)
        self.assertIn("blocked_domains", profile)
    
    def test_save_and_load_profile(self):
        """Test saving and loading custom profile."""
        FocusMode.ensure_config()
        
        custom_profile = {
            "name": "Deep Work",
            "blocked_domains": ["news.ycombinator.com"],
            "kill_processes": [],
            "enable_dnd": True
        }
        
        success = FocusMode.save_profile("deep_work", custom_profile)
        self.assertTrue(success)
        
        loaded = FocusMode.get_profile("deep_work")
        self.assertEqual(loaded["name"], "Deep Work")
    
    def test_delete_profile(self):
        """Test deleting a profile."""
        FocusMode.ensure_config()
        FocusMode.save_profile("temp", {"name": "Temp", "blocked_domains": []})
        
        success = FocusMode.delete_profile("temp")
        self.assertTrue(success)
        
        self.assertIsNone(FocusMode.get_profile("temp"))
    
    def test_is_active_default_false(self):
        """Test that focus mode is inactive by default."""
        FocusMode.ensure_config()
        self.assertFalse(FocusMode.is_active())
    
    def test_remove_focus_entries_from_hosts(self):
        """Test hosts file cleaning."""
        hosts_content = """
127.0.0.1 localhost
::1 localhost
# LOOFI-FOCUS-MODE-START
127.0.0.1 reddit.com
127.0.0.1 twitter.com
# LOOFI-FOCUS-MODE-END
192.168.1.1 router.local
"""
        cleaned = FocusMode._remove_focus_entries(hosts_content)
        self.assertNotIn("reddit.com", cleaned)
        self.assertNotIn("twitter.com", cleaned)
        self.assertIn("localhost", cleaned)
        self.assertIn("router.local", cleaned)
    
    def test_default_blocked_domains(self):
        """Test default blocked domains are set."""
        self.assertIn("reddit.com", FocusMode.DEFAULT_BLOCKED)
        self.assertIn("twitter.com", FocusMode.DEFAULT_BLOCKED)
        self.assertIn("youtube.com", FocusMode.DEFAULT_BLOCKED)


# ---------------------------------------------------------------------------
# TestAutomationProfiles
# ---------------------------------------------------------------------------

class TestAutomationProfiles(unittest.TestCase):
    """Tests for the AutomationProfiles event-triggered system."""
    
    def setUp(self):
        """Create temp config directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = AutomationProfiles.CONFIG_DIR
        self.original_config_file = AutomationProfiles.CONFIG_FILE
        AutomationProfiles.CONFIG_DIR = Path(self.temp_dir)
        AutomationProfiles.CONFIG_FILE = Path(self.temp_dir) / "automation.json"
    
    def tearDown(self):
        """Restore original config paths."""
        AutomationProfiles.CONFIG_DIR = self.original_config_dir
        AutomationProfiles.CONFIG_FILE = self.original_config_file
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ensure_config_creates_file(self):
        """Test config file is created."""
        AutomationProfiles.ensure_config()
        self.assertTrue(AutomationProfiles.CONFIG_FILE.exists())
    
    def test_is_enabled_default_true(self):
        """Test automation is enabled by default."""
        AutomationProfiles.ensure_config()
        self.assertTrue(AutomationProfiles.is_enabled())
    
    def test_set_enabled(self):
        """Test enabling/disabling automation."""
        AutomationProfiles.ensure_config()
        
        AutomationProfiles.set_enabled(False)
        self.assertFalse(AutomationProfiles.is_enabled())
        
        AutomationProfiles.set_enabled(True)
        self.assertTrue(AutomationProfiles.is_enabled())
    
    def test_add_rule(self):
        """Test adding an automation rule."""
        AutomationProfiles.ensure_config()
        
        rule = {
            "name": "Test Rule",
            "trigger": TriggerType.ON_BATTERY.value,
            "action": ActionType.SET_POWER_PROFILE.value,
            "action_params": {"profile": "power-saver"},
            "enabled": True
        }
        
        result = AutomationProfiles.add_rule(rule)
        self.assertTrue(result["success"])
        self.assertIn("id", result)
        
        rules = AutomationProfiles.list_rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["name"], "Test Rule")
    
    def test_delete_rule(self):
        """Test deleting an automation rule."""
        AutomationProfiles.ensure_config()
        
        rule = {"name": "To Delete", "trigger": "on_battery", "action": "set_power_profile"}
        result = AutomationProfiles.add_rule(rule)
        rule_id = result["id"]
        
        delete_result = AutomationProfiles.delete_rule(rule_id)
        self.assertTrue(delete_result["success"])
        
        self.assertEqual(len(AutomationProfiles.list_rules()), 0)
    
    def test_get_rules_for_trigger(self):
        """Test filtering rules by trigger."""
        AutomationProfiles.ensure_config()
        
        # Add rules with different triggers
        AutomationProfiles.add_rule({
            "name": "Battery Rule",
            "trigger": TriggerType.ON_BATTERY.value,
            "action": ActionType.SET_POWER_PROFILE.value,
            "enabled": True
        })
        AutomationProfiles.add_rule({
            "name": "AC Rule",
            "trigger": TriggerType.ON_AC.value,
            "action": ActionType.SET_POWER_PROFILE.value,
            "enabled": True
        })
        
        battery_rules = AutomationProfiles.get_rules_for_trigger(TriggerType.ON_BATTERY.value)
        self.assertEqual(len(battery_rules), 1)
        self.assertEqual(battery_rules[0]["name"], "Battery Rule")
    
    def test_enable_rule(self):
        """Test enabling/disabling a rule."""
        AutomationProfiles.ensure_config()
        
        result = AutomationProfiles.add_rule({
            "name": "Toggle Test",
            "trigger": "on_battery",
            "action": "set_power_profile",
            "enabled": True
        })
        rule_id = result["id"]
        
        AutomationProfiles.enable_rule(rule_id, False)
        rule = AutomationProfiles.get_rule(rule_id)
        self.assertFalse(rule["enabled"])
    
    def test_execute_rules_when_disabled(self):
        """Test execution does nothing when automation disabled."""
        AutomationProfiles.ensure_config()
        AutomationProfiles.set_enabled(False)
        
        result = AutomationProfiles.execute_rules_for_trigger(TriggerType.ON_BATTERY.value)
        self.assertTrue(result["success"])
        self.assertIn("disabled", result["message"].lower())
    
    @patch('utils.automation_profiles.subprocess.run')
    def test_action_set_power_profile(self, mock_run):
        """Test power profile action execution."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = AutomationProfiles._action_set_power_profile({"profile": "performance"})
        self.assertTrue(result["success"])
        mock_run.assert_called_once()
    
    def test_create_battery_saver_preset(self):
        """Test preset creation adds rules."""
        AutomationProfiles.ensure_config()
        
        result = AutomationProfiles.create_battery_saver_preset()
        self.assertTrue(result["success"])
        
        rules = AutomationProfiles.list_rules()
        self.assertGreater(len(rules), 0)
        
        # Check for both battery and AC rules
        triggers = [r["trigger"] for r in rules]
        self.assertIn(TriggerType.ON_BATTERY.value, triggers)
        self.assertIn(TriggerType.ON_AC.value, triggers)


# ---------------------------------------------------------------------------
# TestTriggerTypes
# ---------------------------------------------------------------------------

class TestTriggerTypes(unittest.TestCase):
    """Tests for trigger type enums."""
    
    def test_trigger_types_values(self):
        """Verify trigger type string values."""
        self.assertEqual(TriggerType.ON_BATTERY.value, "on_battery")
        self.assertEqual(TriggerType.ON_AC.value, "on_ac")
        self.assertEqual(TriggerType.ON_PUBLIC_WIFI.value, "on_public_wifi")
        self.assertEqual(TriggerType.ON_ULTRAWIDE.value, "on_ultrawide")
    
    def test_action_types_values(self):
        """Verify action type string values."""
        self.assertEqual(ActionType.SET_POWER_PROFILE.value, "set_power_profile")
        self.assertEqual(ActionType.SET_CPU_GOVERNOR.value, "set_cpu_governor")
        self.assertEqual(ActionType.ENABLE_VPN.value, "enable_vpn")
        self.assertEqual(ActionType.ENABLE_FOCUS_MODE.value, "enable_focus_mode")


if __name__ == '__main__':
    unittest.main()
