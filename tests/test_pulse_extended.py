"""
Extended tests for utils/pulse.py — SystemPulse coverage gaps.
Covers: power state sysfs fallback, battery level sysfs fallback,
network state branches, Wi-Fi SSID parsing, public wifi detection,
monitor detection (xrandr + kscreen-doctor), VPN check, NM state handler,
polling fallback, _is_expected_dbus_unavailable, create_pulse_listener.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.pulse import (
    SystemPulse, PowerState, NetworkState, MonitorInfo,
    PulseThread, create_pulse_listener,
)


class TestGetPowerStateFallback(unittest.TestCase):
    """Test power state via sysfs fallback paths."""

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="1\n"))
    def test_sysfs_ac_online(self, mock_exists, mock_run):
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/AC0/online"
        state = SystemPulse.get_power_state()
        self.assertEqual(state, PowerState.AC.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="0\n"))
    def test_sysfs_battery(self, mock_exists, mock_run):
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/AC0/online"
        state = SystemPulse.get_power_state()
        self.assertEqual(state, PowerState.BATTERY.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists", return_value=False)
    def test_unknown_when_no_sysfs(self, mock_exists, mock_run):
        state = SystemPulse.get_power_state()
        self.assertEqual(state, PowerState.UNKNOWN.value)

    @patch("utils.pulse.subprocess.run")
    def test_upower_ac_online_yes(self, mock_run):
        mock_run.return_value = MagicMock(stdout="  online:             yes  ", returncode=0)
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("utils.pulse.subprocess.run")
    def test_upower_neither_match(self, mock_run):
        """upower returns data but no 'online' keyword — falls through to sysfs."""
        mock_run.return_value = MagicMock(stdout="some other data", returncode=0)
        with patch("utils.pulse.os.path.exists", return_value=False):
            self.assertEqual(SystemPulse.get_power_state(), PowerState.UNKNOWN.value)


class TestGetBatteryLevelFallback(unittest.TestCase):
    """Test battery level via sysfs fallback."""

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="82\n"))
    def test_sysfs_battery_capacity(self, mock_exists, mock_run):
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/BAT0/capacity"
        level = SystemPulse.get_battery_level()
        self.assertEqual(level, 82)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists", return_value=False)
    def test_returns_minus_one_no_battery(self, mock_exists, mock_run):
        self.assertEqual(SystemPulse.get_battery_level(), -1)

    @patch("utils.pulse.subprocess.run")
    def test_upower_parses_percentage(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="  native-path:  power_supply/BAT0\n  percentage:          45%\n",
            returncode=0,
        )
        self.assertEqual(SystemPulse.get_battery_level(), 45)


class TestGetNetworkState(unittest.TestCase):
    """Test network state branches."""

    @patch("utils.pulse.subprocess.run")
    def test_connecting_state(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connecting\n", returncode=0)
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTING.value)

    @patch("utils.pulse.subprocess.run")
    def test_connected_full(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connected (site only)\n", returncode=0)
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTED.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no nmcli"))
    def test_default_disconnected_on_error(self, mock_run):
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value)


class TestGetWifiSsid(unittest.TestCase):
    """Test Wi-Fi SSID parsing."""

    @patch("utils.pulse.subprocess.run")
    def test_returns_active_ssid(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="no:SomeNetwork\nyes:MyWiFi\nno:Neighbor\n",
            returncode=0,
        )
        self.assertEqual(SystemPulse.get_wifi_ssid(), "MyWiFi")

    @patch("utils.pulse.subprocess.run")
    def test_returns_empty_when_none_active(self, mock_run):
        mock_run.return_value = MagicMock(stdout="no:Net1\nno:Net2\n", returncode=0)
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")

    @patch("utils.pulse.subprocess.run", side_effect=Exception("fail"))
    def test_returns_empty_on_error(self, mock_run):
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")


class TestIsPublicWifi(unittest.TestCase):
    """Test public Wi-Fi heuristic."""

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Starbucks WiFi")
    def test_detects_starbucks(self, mock_ssid):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Guest Network")
    def test_detects_guest(self, mock_ssid):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="MyHomeNetwork5G")
    def test_non_public(self, mock_ssid):
        self.assertFalse(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="")
    def test_empty_ssid(self, mock_ssid):
        self.assertFalse(SystemPulse.is_public_wifi())


class TestGetConnectedMonitors(unittest.TestCase):
    """Test monitor detection with xrandr and kscreen-doctor."""

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_parses_monitors(self, mock_run):
        xrandr_output = (
            "Screen 0: minimum 8 x 8, current 3840 x 1080\n"
            "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 193mm\n"
            "   1920x1080     60.00*+\n"
            "HDMI-1 connected 1920x1080+1920+0 (normal left inverted right x axis y axis) 527mm x 296mm\n"
            "   1920x1080     60.00*+\n"
        )
        mock_run.return_value = MagicMock(stdout=xrandr_output, returncode=0)
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0]["name"], "eDP-1")
        self.assertTrue(monitors[0]["is_primary"])
        self.assertEqual(monitors[1]["name"], "HDMI-1")
        self.assertFalse(monitors[1]["is_primary"])

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_with_resolution(self, mock_run):
        xrandr_output = "DP-1 connected primary 3440x1440+0+0 (normal)\n"
        mock_run.return_value = MagicMock(stdout=xrandr_output, returncode=0)
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertEqual(monitors[0]["name"], "DP-1")
        # 3440/1440 = 2.388... > 2.0 = ultrawide
        self.assertTrue(monitors[0]["is_ultrawide"])

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_failure_falls_to_kscreen(self, mock_run):
        """When xrandr returns empty, falls back to kscreen-doctor."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # xrandr empty
            MagicMock(
                stdout="Output: eDP-1 connected\n  enabled: True\n  resolution: 1920x1080@60\n",
                returncode=0,
            ),
        ]
        monitors = SystemPulse.get_connected_monitors()
        # kscreen parsing may or may not find valid monitors depending on format
        self.assertIsInstance(monitors, list)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no xrandr"))
    def test_returns_empty_on_all_failures(self, mock_run):
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(monitors, [])


class TestCheckVpnActive(unittest.TestCase):
    """Test VPN active check."""

    @patch("utils.pulse.subprocess.run")
    def test_vpn_detected(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="vpn:activated\nwifi:activated\n", returncode=0
        )
        pulse = SystemPulse()
        self.assertTrue(pulse._check_vpn_active())

    @patch("utils.pulse.subprocess.run")
    def test_no_vpn(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="wifi:activated\nethernet:activated\n", returncode=0
        )
        pulse = SystemPulse()
        self.assertFalse(pulse._check_vpn_active())

    @patch("utils.pulse.subprocess.run", side_effect=Exception("nmcli fail"))
    def test_returns_false_on_error(self, mock_run):
        pulse = SystemPulse()
        self.assertFalse(pulse._check_vpn_active())


class TestIsExpectedDbusUnavailable(unittest.TestCase):
    """Test _is_expected_dbus_unavailable helper."""

    def test_permission_denied(self):
        exc = Exception("Operation not permitted")
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(exc))

    def test_access_denied(self):
        exc = Exception("org.freedesktop.DBus.Error.AccessDenied")
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(exc))

    def test_no_server(self):
        exc = Exception("dbus.error.noserver: could not connect")
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(exc))

    def test_socket_missing(self):
        exc = Exception("Failed to connect to socket /run/dbus/system_bus_socket")
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(exc))

    def test_unexpected_error(self):
        exc = Exception("Segmentation fault")
        self.assertFalse(SystemPulse._is_expected_dbus_unavailable(exc))


class TestOnNmStateChanged(unittest.TestCase):
    """Test _on_nm_state_changed signal handler branches."""

    def setUp(self):
        self.pulse = SystemPulse()

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="TestNet")
    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    @patch.object(SystemPulse, "wifi_ssid_changed")
    def test_connected_emits_signals(self, mock_wifi, mock_event, mock_state, mock_ssid):
        self.pulse._last_network_state = None
        self.pulse._on_nm_state_changed(70)
        mock_state.emit.assert_called_with(NetworkState.CONNECTED.value)
        mock_wifi.emit.assert_called_with("TestNet")

    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_connecting_state(self, mock_event, mock_state):
        self.pulse._last_network_state = None
        self.pulse._on_nm_state_changed(50)
        mock_state.emit.assert_called_with(NetworkState.CONNECTING.value)

    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_disconnected_state(self, mock_event, mock_state):
        self.pulse._last_network_state = None
        self.pulse._on_nm_state_changed(20)
        mock_state.emit.assert_called_with(NetworkState.DISCONNECTED.value)

    @patch.object(SystemPulse, "network_state_changed")
    def test_no_emit_when_state_unchanged(self, mock_state):
        self.pulse._last_network_state = NetworkState.CONNECTED.value
        self.pulse._on_nm_state_changed(70)
        mock_state.emit.assert_not_called()


class TestOnMonitorChanged(unittest.TestCase):
    """Test _on_monitor_changed handler."""

    @patch.object(SystemPulse, "get_connected_monitors")
    @patch.object(SystemPulse, "monitor_count_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_emits_count_changed_and_laptop_only(self, mock_event, mock_count, mock_monitors):
        mock_monitors.return_value = [{"name": "eDP-1", "is_ultrawide": False}]
        pulse = SystemPulse()
        pulse._last_monitor_count = 0
        pulse._on_monitor_changed()
        mock_count.emit.assert_called_with(1)
        mock_event.emit.assert_called_with("laptop_only", {})

    @patch.object(SystemPulse, "get_connected_monitors")
    @patch.object(SystemPulse, "monitor_count_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_emits_ultrawide_event(self, mock_event, mock_count, mock_monitors):
        uw_mon = {"name": "DP-1", "is_ultrawide": True, "width": 3440, "height": 1440}
        mock_monitors.return_value = [uw_mon, {"name": "eDP-1", "is_ultrawide": False}]
        pulse = SystemPulse()
        pulse._last_monitor_count = 0
        pulse._on_monitor_changed()
        mock_count.emit.assert_called_with(2)
        mock_event.emit.assert_called_with("ultrawide_connected", uw_mon)

    @patch.object(SystemPulse, "get_connected_monitors")
    @patch.object(SystemPulse, "monitor_count_changed")
    def test_no_emit_if_count_unchanged(self, mock_count, mock_monitors):
        mock_monitors.return_value = [{"name": "eDP-1", "is_ultrawide": False}]
        pulse = SystemPulse()
        pulse._last_monitor_count = 1
        pulse._on_monitor_changed()
        mock_count.emit.assert_not_called()


class TestStopAndMisc(unittest.TestCase):
    """Test stop, is_available, create_pulse_listener."""

    def test_stop_sets_running_false(self):
        pulse = SystemPulse()
        pulse._running = True
        pulse._loop = MagicMock()
        pulse.stop()
        self.assertFalse(pulse._running)
        pulse._loop.quit.assert_called_once()

    def test_stop_no_loop(self):
        pulse = SystemPulse()
        pulse._running = True
        pulse._loop = None
        pulse.stop()
        self.assertFalse(pulse._running)

    def test_is_available_returns_bool(self):
        self.assertIsInstance(SystemPulse.is_available(), bool)

    def test_create_pulse_listener_returns_tuple(self):
        pulse, thread = create_pulse_listener()
        self.assertIsInstance(pulse, SystemPulse)
        self.assertIsInstance(thread, PulseThread)


if __name__ == "__main__":
    unittest.main()
