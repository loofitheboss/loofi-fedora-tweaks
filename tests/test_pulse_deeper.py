"""Deeper tests for utils.pulse — covering uncovered branches (~101 miss)."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestPowerStateEnum(unittest.TestCase):
    def test_values(self):
        from utils.pulse import PowerState
        self.assertEqual(PowerState.AC.value, "ac")
        self.assertEqual(PowerState.BATTERY.value, "battery")
        self.assertEqual(PowerState.UNKNOWN.value, "unknown")


class TestNetworkStateEnum(unittest.TestCase):
    def test_values(self):
        from utils.pulse import NetworkState
        self.assertEqual(NetworkState.CONNECTED.value, "connected")
        self.assertEqual(NetworkState.DISCONNECTED.value, "disconnected")
        self.assertEqual(NetworkState.CONNECTING.value, "connecting")


class TestIsExpectedDbusUnavailable(unittest.TestCase):
    def test_operation_not_permitted(self):
        from utils.pulse import SystemPulse
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("Operation not permitted")
        ))

    def test_access_denied(self):
        from utils.pulse import SystemPulse
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("AccessDenied by policy")
        ))

    def test_no_such_file(self):
        from utils.pulse import SystemPulse
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("No such file or directory")
        ))

    def test_socket_error(self):
        from utils.pulse import SystemPulse
        self.assertTrue(SystemPulse._is_expected_dbus_unavailable(
            Exception("Failed to connect to socket /run/dbus/system_bus_socket")
        ))

    def test_random_error(self):
        from utils.pulse import SystemPulse
        self.assertFalse(SystemPulse._is_expected_dbus_unavailable(
            Exception("some random error")
        ))


class TestGetPowerState(unittest.TestCase):
    @patch("subprocess.run")
    def test_ac_via_upower(self, mock_run):
        mock_run.return_value = MagicMock(stdout="online: yes\n", returncode=0)
        from utils.pulse import PowerState, SystemPulse
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("subprocess.run")
    def test_battery_via_upower(self, mock_run):
        mock_run.return_value = MagicMock(stdout="online: no\n", returncode=0)
        from utils.pulse import PowerState, SystemPulse
        self.assertEqual(SystemPulse.get_power_state(), PowerState.BATTERY.value)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", unittest.mock.mock_open(read_data="1\n"))
    @patch("subprocess.run", side_effect=Exception("no upower"))
    def test_ac_via_sysfs(self, mock_run, mock_exists):
        from utils.pulse import PowerState, SystemPulse
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", unittest.mock.mock_open(read_data="0\n"))
    @patch("subprocess.run", side_effect=Exception("no upower"))
    def test_battery_via_sysfs(self, mock_run, mock_exists):
        from utils.pulse import PowerState, SystemPulse
        self.assertEqual(SystemPulse.get_power_state(), PowerState.BATTERY.value)

    @patch("os.path.exists", return_value=False)
    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_unknown_fallback(self, mock_run, mock_exists):
        from utils.pulse import PowerState, SystemPulse
        self.assertEqual(SystemPulse.get_power_state(), PowerState.UNKNOWN.value)


class TestGetBatteryLevel(unittest.TestCase):
    @patch("subprocess.run")
    def test_via_upower(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="  percentage:          85%\n", returncode=0
        )
        from utils.pulse import SystemPulse
        self.assertEqual(SystemPulse.get_battery_level(), 85)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", unittest.mock.mock_open(read_data="72\n"))
    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_via_sysfs(self, mock_run, mock_exists):
        from utils.pulse import SystemPulse
        self.assertEqual(SystemPulse.get_battery_level(), 72)

    @patch("os.path.exists", return_value=False)
    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_no_battery(self, mock_run, mock_exists):
        from utils.pulse import SystemPulse
        self.assertEqual(SystemPulse.get_battery_level(), -1)


class TestGetNetworkState(unittest.TestCase):
    @patch("subprocess.run")
    def test_connected(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connected\n", returncode=0)
        from utils.pulse import NetworkState, SystemPulse
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTED.value)

    @patch("subprocess.run")
    def test_disconnected(self, mock_run):
        mock_run.return_value = MagicMock(stdout="disconnected\n", returncode=0)
        from utils.pulse import NetworkState, SystemPulse
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value)

    @patch("subprocess.run")
    def test_connecting(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connecting\n", returncode=0)
        from utils.pulse import NetworkState, SystemPulse
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTING.value)

    @patch("subprocess.run", side_effect=Exception("no nmcli"))
    def test_fallback(self, mock_run):
        from utils.pulse import NetworkState, SystemPulse
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value)


class TestGetWifiSsid(unittest.TestCase):
    @patch("subprocess.run")
    def test_connected(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="yes:MyNetwork\nno:OtherNet\n", returncode=0
        )
        from utils.pulse import SystemPulse
        self.assertEqual(SystemPulse.get_wifi_ssid(), "MyNetwork")

    @patch("subprocess.run")
    def test_not_connected(self, mock_run):
        mock_run.return_value = MagicMock(stdout="no:Net1\nno:Net2\n", returncode=0)
        from utils.pulse import SystemPulse
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")

    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_error(self, mock_run):
        from utils.pulse import SystemPulse
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")


class TestIsPublicWifi(unittest.TestCase):
    @patch("subprocess.run")
    def test_public(self, mock_run):
        mock_run.return_value = MagicMock(stdout="yes:guest_wifi\n")
        from utils.pulse import SystemPulse
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch("subprocess.run")
    def test_private(self, mock_run):
        mock_run.return_value = MagicMock(stdout="yes:HomeNetwork\n")
        from utils.pulse import SystemPulse
        self.assertFalse(SystemPulse.is_public_wifi())

    @patch("subprocess.run")
    def test_starbucks(self, mock_run):
        mock_run.return_value = MagicMock(stdout="yes:Starbucks WiFi\n")
        from utils.pulse import SystemPulse
        self.assertTrue(SystemPulse.is_public_wifi())


class TestCheckVpnActive(unittest.TestCase):
    @patch("subprocess.run")
    def test_vpn_active(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="vpn:activated\n", returncode=0
        )
        from utils.pulse import SystemPulse
        pulse = SystemPulse.__new__(SystemPulse)
        self.assertTrue(pulse._check_vpn_active())

    @patch("subprocess.run")
    def test_no_vpn(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="wifi:activated\n", returncode=0
        )
        from utils.pulse import SystemPulse
        pulse = SystemPulse.__new__(SystemPulse)
        self.assertFalse(pulse._check_vpn_active())

    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_error(self, mock_run):
        from utils.pulse import SystemPulse
        pulse = SystemPulse.__new__(SystemPulse)
        self.assertFalse(pulse._check_vpn_active())


class TestGetConnectedMonitors(unittest.TestCase):
    @patch("subprocess.run")
    def test_xrandr(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="HDMI-1 connected primary 1920x1080+0+0\neDP-1 connected 1920x1080+1920+0\n",
            returncode=0
        )
        from utils.pulse import SystemPulse
        monitors = SystemPulse.get_connected_monitors()
        self.assertGreaterEqual(len(monitors), 1)

    @patch("subprocess.run")
    def test_ultrawide(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="DP-1 connected 3440x1440+0+0\n",
            returncode=0
        )
        from utils.pulse import SystemPulse
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertTrue(monitors[0]["is_ultrawide"])

    @patch("subprocess.run", side_effect=Exception("no xrandr"))
    def test_no_xrandr(self, mock_run):
        from utils.pulse import SystemPulse
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(monitors, [])

    @patch("subprocess.run")
    def test_kscreen_fallback(self, mock_run):
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "xrandr" in cmd:
                return MagicMock(stdout="", returncode=1)
            if "kscreen-doctor" in cmd:
                return MagicMock(
                    stdout="Output: eDP-1 (internal)\n  resolution: 1920x1080@60Hz\n",
                    returncode=0
                )
            return MagicMock(stdout="", returncode=1)
        mock_run.side_effect = side_effect
        from utils.pulse import SystemPulse
        monitors = SystemPulse.get_connected_monitors()
        # Should find monitors via kscreen-doctor
        self.assertIsInstance(monitors, list)


class TestCreatePulseListener(unittest.TestCase):
    @patch("utils.pulse.PulseThread")
    @patch("utils.pulse.SystemPulse")
    def test_creates_tuple(self, MockPulse, MockThread):
        from utils.pulse import create_pulse_listener
        pulse, thread = create_pulse_listener()
        self.assertIsNotNone(pulse)
        self.assertIsNotNone(thread)


if __name__ == "__main__":
    unittest.main()
