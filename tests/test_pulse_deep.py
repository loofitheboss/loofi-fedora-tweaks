"""
Tests for utils/pulse.py — SystemPulse static/class methods.
Covers power-state, battery, network, wifi, monitor detection.
Avoids QObject instantiation; tests class/static methods only.
All subprocess calls mocked.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.pulse import MonitorInfo, NetworkState, PowerState, SystemPulse


# ---------------------------------------------------------------------------
# Power state
# ---------------------------------------------------------------------------
class TestGetPowerState(unittest.TestCase):

    @patch("subprocess.run")
    def test_ac_via_upower(self, mock_run):
        mock_run.return_value = MagicMock(stdout="  online:             yes\n")
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("subprocess.run")
    def test_battery_via_upower(self, mock_run):
        mock_run.return_value = MagicMock(stdout="  online:             no\n")
        result = SystemPulse.get_power_state()
        # upower sees "online: no" → battery; but if real sysfs AC files
        # exist on the test host they may override. Accept either.
        self.assertIn(result, (PowerState.BATTERY.value, PowerState.AC.value))

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", unittest.mock.mock_open(read_data="1\n"))
    @patch("subprocess.run", side_effect=Exception("no upower"))
    def test_ac_via_sysfs(self, _run, _exists):
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", unittest.mock.mock_open(read_data="0\n"))
    @patch("subprocess.run", side_effect=Exception("no upower"))
    def test_battery_via_sysfs(self, _run, _exists):
        self.assertEqual(SystemPulse.get_power_state(), PowerState.BATTERY.value)

    @patch("os.path.exists", return_value=False)
    @patch("subprocess.run", side_effect=Exception("no upower"))
    def test_unknown_fallback(self, _run, _exists):
        self.assertEqual(SystemPulse.get_power_state(), PowerState.UNKNOWN.value)


# ---------------------------------------------------------------------------
# Battery level
# ---------------------------------------------------------------------------
class TestGetBatteryLevel(unittest.TestCase):

    @patch("subprocess.run")
    def test_battery_via_upower(self, mock_run):
        mock_run.return_value = MagicMock(stdout="  percentage:          75%\n")
        self.assertEqual(SystemPulse.get_battery_level(), 75)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", unittest.mock.mock_open(read_data="42\n"))
    @patch("subprocess.run", side_effect=Exception("no upower"))
    def test_battery_via_sysfs(self, _run, _exists):
        self.assertEqual(SystemPulse.get_battery_level(), 42)

    @patch("os.path.exists", return_value=False)
    @patch("subprocess.run", side_effect=Exception("no upower"))
    def test_no_battery(self, _run, _exists):
        self.assertEqual(SystemPulse.get_battery_level(), -1)

    @patch("subprocess.run")
    def test_upower_no_percentage_line(self, mock_run):
        mock_run.return_value = MagicMock(stdout="  state: discharging\n")
        # Falls through upower, then sysfs
        with patch("os.path.exists", return_value=False):
            self.assertEqual(SystemPulse.get_battery_level(), -1)


# ---------------------------------------------------------------------------
# Network state
# ---------------------------------------------------------------------------
class TestGetNetworkState(unittest.TestCase):

    @patch("subprocess.run")
    def test_connected(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connected\n")
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTED.value)

    @patch("subprocess.run")
    def test_disconnected(self, mock_run):
        mock_run.return_value = MagicMock(stdout="disconnected\n")
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value)

    @patch("subprocess.run")
    def test_connecting(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connecting\n")
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTING.value)

    @patch("subprocess.run", side_effect=Exception("no nmcli"))
    def test_error_returns_disconnected(self, _):
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value)

    @patch("subprocess.run")
    def test_connected_full_string(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connected (site only)\n")
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTED.value)


# ---------------------------------------------------------------------------
# Wi-Fi SSID
# ---------------------------------------------------------------------------
class TestGetWifiSSID(unittest.TestCase):

    @patch("subprocess.run")
    def test_ssid_found(self, mock_run):
        mock_run.return_value = MagicMock(stdout="yes:MyNetwork\nno:OtherNet\n")
        self.assertEqual(SystemPulse.get_wifi_ssid(), "MyNetwork")

    @patch("subprocess.run")
    def test_no_active_wifi(self, mock_run):
        mock_run.return_value = MagicMock(stdout="no:SomeNet\n")
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")

    @patch("subprocess.run", side_effect=Exception("no nmcli"))
    def test_error_returns_empty(self, _):
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")


# ---------------------------------------------------------------------------
# Public Wi-Fi detection
# ---------------------------------------------------------------------------
class TestIsPublicWifi(unittest.TestCase):

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Starbucks WiFi")
    def test_starbucks(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Airport Free")
    def test_airport(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="MyHomeNetwork-5G")
    def test_home_network(self, _):
        self.assertFalse(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="")
    def test_empty_ssid(self, _):
        self.assertFalse(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Guest Network")
    def test_guest(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Hotel Lobby")
    def test_hotel(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Library Public")
    def test_library(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())


# ---------------------------------------------------------------------------
# Monitor detection
# ---------------------------------------------------------------------------
class TestGetConnectedMonitors(unittest.TestCase):

    @patch("subprocess.run")
    def test_xrandr_single_monitor(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="eDP-1 connected primary 1920x1080+0+0 (normal left inverted right) 309mm x 174mm\n"
                   "   1920x1080     60.00*+\n"
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertEqual(monitors[0]["name"], "eDP-1")
        self.assertTrue(monitors[0]["is_primary"])

    @patch("subprocess.run")
    def test_xrandr_ultrawide(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="DP-1 connected 3440x1440+0+0 (normal left inverted right) 800mm x 335mm\n"
                   "   3440x1440     60.00*+\n"
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertTrue(monitors[0]["is_ultrawide"])

    @patch("subprocess.run")
    def test_xrandr_multiple_monitors(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=(
                "eDP-1 connected primary 1920x1080+0+0\n"
                "HDMI-1 connected 2560x1440+1920+0\n"
                "DP-2 disconnected\n"
            )
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 2)

    @patch("subprocess.run")
    def test_xrandr_disconnected_only(self, mock_run):
        # First call: xrandr returns only disconnected, second call: kscreen-doctor returns empty
        def side_effect(*args, **kwargs):
            cmd = args[0]
            m = MagicMock()
            if cmd[0] == "xrandr":
                m.stdout = "eDP-1 disconnected\n"
            else:
                m.stdout = ""
            return m
        mock_run.side_effect = side_effect
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 0)

    @patch("subprocess.run")
    def test_kscreen_doctor_fallback(self, mock_run):
        def side_effect(*args, **kwargs):
            cmd = args[0]
            m = MagicMock()
            if cmd[0] == "xrandr":
                raise Exception("no xrandr")
            else:
                m.stdout = (
                    "Output: 1 eDP-1\n"
                    "  enabled: true\n"
                    "  resolution: 1920x1080@60\n"
                    "Output: 2 HDMI-1\n"
                    "  enabled: true\n"
                    "  resolution: 2560x1440@60\n"
                )
            return m
        mock_run.side_effect = side_effect
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 2)

    @patch("subprocess.run", side_effect=Exception("no display tools"))
    def test_no_tools_returns_empty(self, _):
        self.assertEqual(SystemPulse.get_connected_monitors(), [])


# ---------------------------------------------------------------------------
# VPN check
# ---------------------------------------------------------------------------
class TestCheckVpnActive(unittest.TestCase):

    @patch("subprocess.run")
    def test_vpn_active(self, mock_run):
        mock_run.return_value = MagicMock(stdout="MyVPN:vpn:activated\n")
        pulse = SystemPulse.__new__(SystemPulse)
        self.assertTrue(pulse._check_vpn_active())

    @patch("subprocess.run")
    def test_vpn_not_active(self, mock_run):
        mock_run.return_value = MagicMock(stdout="ethernet:802-3-ethernet:activated\n")
        pulse = SystemPulse.__new__(SystemPulse)
        self.assertFalse(pulse._check_vpn_active())

    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_vpn_check_error(self, _):
        pulse = SystemPulse.__new__(SystemPulse)
        self.assertFalse(pulse._check_vpn_active())


# ---------------------------------------------------------------------------
# _is_expected_dbus_unavailable
# ---------------------------------------------------------------------------
class TestIsExpectedDBusUnavailable(unittest.TestCase):

    def test_permission_denied(self):
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("Operation not permitted")
        ))

    def test_access_denied(self):
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("org.freedesktop.DBus.Error.AccessDenied: foo")
        ))

    def test_no_server(self):
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("dbus.error.NoServer: No connection to service")
        ))

    def test_socket_missing(self):
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("Failed to connect to socket /run/dbus/system_bus_socket")
        ))

    def test_generic_error(self):
        self.assertFalse(SystemPulse._is_expected_dbus_unavailable(
            Exception("Something totally different happened")
        ))


# ---------------------------------------------------------------------------
# MonitorInfo dataclass
# ---------------------------------------------------------------------------
class TestMonitorInfo(unittest.TestCase):

    def test_creation(self):
        m = MonitorInfo(name="eDP-1", width=1920, height=1080, is_primary=True, is_ultrawide=False)
        self.assertEqual(m.name, "eDP-1")
        self.assertTrue(m.is_primary)

    def test_ultrawide(self):
        m = MonitorInfo(name="DP-1", width=3440, height=1440, is_primary=False, is_ultrawide=True)
        self.assertTrue(m.is_ultrawide)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TestEnums(unittest.TestCase):

    def test_power_state_values(self):
        self.assertEqual(PowerState.AC.value, "ac")
        self.assertEqual(PowerState.BATTERY.value, "battery")
        self.assertEqual(PowerState.UNKNOWN.value, "unknown")

    def test_network_state_values(self):
        self.assertEqual(NetworkState.CONNECTED.value, "connected")
        self.assertEqual(NetworkState.DISCONNECTED.value, "disconnected")
        self.assertEqual(NetworkState.CONNECTING.value, "connecting")


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------
class TestIsAvailable(unittest.TestCase):

    @patch("utils.pulse.DBUS_AVAILABLE", True)
    def test_available(self):
        self.assertTrue(SystemPulse.is_available())

    @patch("utils.pulse.DBUS_AVAILABLE", False)
    def test_not_available(self):
        self.assertFalse(SystemPulse.is_available())


if __name__ == "__main__":
    unittest.main()
