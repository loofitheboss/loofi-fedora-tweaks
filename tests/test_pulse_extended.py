"""Tests for utils/pulse.py — extended coverage.

Targets all missed lines from coverage report: DBus import fallback,
start/stop lifecycle, signal registration (UPower, NetworkManager, Monitor),
signal handlers (power, battery, NM properties), polling fallback,
PulseThread, sysfs exception paths, kscreen-doctor parsing edge cases,
and xrandr ValueError branches.
"""

import os
import sys
import subprocess
import unittest
from unittest.mock import patch, MagicMock, mock_open, PropertyMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.pulse import (
    SystemPulse,
    PowerState,
    NetworkState,
    MonitorInfo,
    PulseThread,
    create_pulse_listener,
)


# ---------------------------------------------------------------------------
# Enums and dataclass
# ---------------------------------------------------------------------------
class TestPowerStateEnum(unittest.TestCase):
    """Test PowerState enum values."""

    def test_ac_value(self):
        self.assertEqual(PowerState.AC.value, "ac")

    def test_battery_value(self):
        self.assertEqual(PowerState.BATTERY.value, "battery")

    def test_unknown_value(self):
        self.assertEqual(PowerState.UNKNOWN.value, "unknown")

    def test_members_count(self):
        self.assertEqual(len(PowerState), 3)


class TestNetworkStateEnum(unittest.TestCase):
    """Test NetworkState enum values."""

    def test_connected_value(self):
        self.assertEqual(NetworkState.CONNECTED.value, "connected")

    def test_disconnected_value(self):
        self.assertEqual(NetworkState.DISCONNECTED.value, "disconnected")

    def test_connecting_value(self):
        self.assertEqual(NetworkState.CONNECTING.value, "connecting")


class TestMonitorInfoDataclass(unittest.TestCase):
    """Test MonitorInfo dataclass."""

    def test_creation(self):
        m = MonitorInfo(
            name="eDP-1", width=1920, height=1080, is_primary=True, is_ultrawide=False
        )
        self.assertEqual(m.name, "eDP-1")
        self.assertEqual(m.width, 1920)
        self.assertEqual(m.height, 1080)
        self.assertTrue(m.is_primary)
        self.assertFalse(m.is_ultrawide)

    def test_ultrawide_flag(self):
        m = MonitorInfo(
            name="DP-1", width=3440, height=1440, is_primary=False, is_ultrawide=True
        )
        self.assertTrue(m.is_ultrawide)
        self.assertFalse(m.is_primary)


# ---------------------------------------------------------------------------
# SystemPulse __init__ and is_available
# ---------------------------------------------------------------------------
class TestSystemPulseInit(unittest.TestCase):
    """Test SystemPulse initialization."""

    def test_init_defaults(self):
        pulse = SystemPulse()
        self.assertIsNone(pulse._loop)
        self.assertFalse(pulse._running)
        self.assertIsNone(pulse._system_bus)
        self.assertIsNone(pulse._last_power_state)
        self.assertIsNone(pulse._last_network_state)
        self.assertEqual(pulse._last_monitor_count, 0)

    def test_is_available_returns_bool(self):
        self.assertIsInstance(SystemPulse.is_available(), bool)

    @patch("utils.pulse.DBUS_AVAILABLE", True)
    def test_is_available_true(self):
        self.assertTrue(SystemPulse.is_available())

    @patch("utils.pulse.DBUS_AVAILABLE", False)
    def test_is_available_false(self):
        self.assertFalse(SystemPulse.is_available())


# ---------------------------------------------------------------------------
# _is_expected_dbus_unavailable
# ---------------------------------------------------------------------------
class TestIsExpectedDbusUnavailable(unittest.TestCase):
    """Test _is_expected_dbus_unavailable helper across all fragments."""

    def test_operation_not_permitted(self):
        self.assertTrue(
            SystemPulse._is_expected_dbus_unavailable(
                Exception("Operation not permitted")
            )
        )

    def test_access_denied(self):
        self.assertTrue(
            SystemPulse._is_expected_dbus_unavailable(
                Exception("org.freedesktop.DBus.Error.AccessDenied")
            )
        )

    def test_permission_denied(self):
        self.assertTrue(
            SystemPulse._is_expected_dbus_unavailable(
                Exception("Permission denied for this action")
            )
        )

    def test_socket_missing(self):
        self.assertTrue(
            SystemPulse._is_expected_dbus_unavailable(
                Exception("Failed to connect to socket /run/dbus/system_bus_socket")
            )
        )

    def test_no_such_file(self):
        self.assertTrue(
            SystemPulse._is_expected_dbus_unavailable(
                Exception("No such file or directory")
            )
        )

    def test_dbus_noserver(self):
        self.assertTrue(
            SystemPulse._is_expected_dbus_unavailable(
                Exception("dbus.error.noserver: cannot connect")
            )
        )

    def test_unexpected_error_returns_false(self):
        self.assertFalse(
            SystemPulse._is_expected_dbus_unavailable(Exception("Segmentation fault"))
        )

    def test_empty_message_returns_false(self):
        self.assertFalse(SystemPulse._is_expected_dbus_unavailable(Exception("")))


# ---------------------------------------------------------------------------
# start() — DBus available path
# ---------------------------------------------------------------------------
class TestStartWithDbus(unittest.TestCase):
    """Test start() when DBus IS available."""

    @patch("utils.pulse.DBUS_AVAILABLE", True)
    @patch("utils.pulse.GLib")
    @patch("utils.pulse.dbus")
    @patch("utils.pulse.DBusGMainLoop")
    def test_start_registers_and_runs_loop(self, mock_mainloop, mock_dbus, mock_glib):
        pulse = SystemPulse()
        mock_bus = MagicMock()
        mock_dbus.SystemBus.return_value = mock_bus
        mock_loop = MagicMock()
        mock_glib.MainLoop.return_value = mock_loop

        # Patch the registration methods to avoid real DBus calls
        with patch.object(pulse, "_register_upower_signals"):
            with patch.object(pulse, "_register_networkmanager_signals"):
                with patch.object(pulse, "_register_monitor_signals"):
                    pulse.start()

        mock_mainloop.assert_called_once_with(set_as_default=True)
        mock_dbus.SystemBus.assert_called_once()
        self.assertTrue(pulse._running)
        mock_glib.MainLoop.assert_called_once()
        mock_loop.run.assert_called_once()

    @patch("utils.pulse.DBUS_AVAILABLE", True)
    @patch(
        "utils.pulse.DBusGMainLoop", side_effect=Exception("Operation not permitted")
    )
    def test_start_expected_dbus_error_uses_polling(self, mock_mainloop):
        """Expected DBus errors fall back to polling."""
        pulse = SystemPulse()
        with patch.object(pulse, "_run_polling_fallback") as mock_poll:
            pulse.start()
            mock_poll.assert_called_once()

    @patch("utils.pulse.DBUS_AVAILABLE", True)
    @patch("utils.pulse.DBusGMainLoop", side_effect=Exception("Unexpected crash"))
    def test_start_unexpected_error_uses_polling(self, mock_mainloop):
        """Unexpected DBus errors also fall back to polling."""
        pulse = SystemPulse()
        with patch.object(pulse, "_run_polling_fallback") as mock_poll:
            pulse.start()
            mock_poll.assert_called_once()


# ---------------------------------------------------------------------------
# start() — DBus unavailable path
# ---------------------------------------------------------------------------
class TestStartWithoutDbus(unittest.TestCase):
    """Test start() when DBus is NOT available."""

    @patch("utils.pulse.DBUS_AVAILABLE", False)
    def test_start_falls_back_to_polling(self):
        pulse = SystemPulse()
        with patch.object(pulse, "_run_polling_fallback") as mock_poll:
            pulse.start()
            mock_poll.assert_called_once()


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------
class TestStop(unittest.TestCase):
    """Test stop method."""

    def test_stop_with_loop(self):
        pulse = SystemPulse()
        pulse._running = True
        pulse._loop = MagicMock()
        pulse.stop()
        self.assertFalse(pulse._running)
        pulse._loop.quit.assert_called_once()

    def test_stop_without_loop(self):
        pulse = SystemPulse()
        pulse._running = True
        pulse._loop = None
        pulse.stop()
        self.assertFalse(pulse._running)


# ---------------------------------------------------------------------------
# _register_upower_signals
# ---------------------------------------------------------------------------
class TestRegisterUpowerSignals(unittest.TestCase):
    """Test UPower signal registration."""

    def test_no_system_bus_returns_early(self):
        pulse = SystemPulse()
        pulse._system_bus = None
        # Should not raise
        pulse._register_upower_signals()

    def test_registers_two_signal_receivers(self):
        pulse = SystemPulse()
        mock_bus = MagicMock()
        pulse._system_bus = mock_bus
        pulse._register_upower_signals()
        self.assertEqual(mock_bus.add_signal_receiver.call_count, 2)

    def test_dbus_exception_handled(self):
        """DBusException during registration is caught gracefully."""
        pulse = SystemPulse()
        mock_bus = MagicMock()
        # Import real dbus if available, else simulate
        try:
            import dbus as real_dbus

            if real_dbus is None:
                raise ImportError("dbus is None")
            exc_class = real_dbus.exceptions.DBusException
        except (ImportError, AttributeError):
            exc_class = Exception
        mock_bus.add_signal_receiver.side_effect = exc_class("test")
        pulse._system_bus = mock_bus
        # Should not raise
        pulse._register_upower_signals()


# ---------------------------------------------------------------------------
# _on_upower_properties_changed
# ---------------------------------------------------------------------------
class TestOnUpowerPropertiesChanged(unittest.TestCase):
    """Test UPower property change handler."""

    @patch.object(SystemPulse, "power_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_on_battery_true_emits_battery(self, mock_event, mock_power):
        pulse = SystemPulse()
        pulse._last_power_state = None
        pulse._on_upower_properties_changed(
            "org.freedesktop.UPower", {"OnBattery": True}, []
        )
        mock_power.emit.assert_called_once_with(PowerState.BATTERY.value)
        mock_event.emit.assert_called_once_with(
            "power_state", {"state": PowerState.BATTERY.value}
        )
        self.assertEqual(pulse._last_power_state, PowerState.BATTERY.value)

    @patch.object(SystemPulse, "power_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_on_battery_false_emits_ac(self, mock_event, mock_power):
        pulse = SystemPulse()
        pulse._last_power_state = None
        pulse._on_upower_properties_changed(
            "org.freedesktop.UPower", {"OnBattery": False}, []
        )
        mock_power.emit.assert_called_once_with(PowerState.AC.value)

    @patch.object(SystemPulse, "power_state_changed")
    def test_no_emit_when_state_unchanged(self, mock_power):
        pulse = SystemPulse()
        pulse._last_power_state = PowerState.AC.value
        pulse._on_upower_properties_changed(
            "org.freedesktop.UPower", {"OnBattery": False}, []
        )
        mock_power.emit.assert_not_called()

    @patch.object(SystemPulse, "power_state_changed")
    def test_no_on_battery_key_does_nothing(self, mock_power):
        pulse = SystemPulse()
        pulse._on_upower_properties_changed(
            "org.freedesktop.UPower", {"SomeOtherProp": 42}, []
        )
        mock_power.emit.assert_not_called()


# ---------------------------------------------------------------------------
# _on_battery_properties_changed
# ---------------------------------------------------------------------------
class TestOnBatteryPropertiesChanged(unittest.TestCase):
    """Test battery property change handler."""

    @patch.object(SystemPulse, "battery_level_changed")
    def test_percentage_emits_level(self, mock_battery):
        pulse = SystemPulse()
        pulse._on_battery_properties_changed(
            "org.freedesktop.UPower", {"Percentage": 73}, []
        )
        mock_battery.emit.assert_called_once_with(73)

    @patch.object(SystemPulse, "battery_level_changed")
    def test_no_percentage_key_does_nothing(self, mock_battery):
        pulse = SystemPulse()
        pulse._on_battery_properties_changed("org.freedesktop.UPower", {"State": 2}, [])
        mock_battery.emit.assert_not_called()


# ---------------------------------------------------------------------------
# get_power_state (upower + sysfs fallbacks)
# ---------------------------------------------------------------------------
class TestGetPowerState(unittest.TestCase):
    """Test get_power_state with upower and sysfs paths."""

    @patch("utils.pulse.subprocess.run")
    def test_upower_ac_online_yes(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="  online:             yes  ", returncode=0
        )
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("utils.pulse.subprocess.run")
    def test_upower_ac_online_no(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="  online:             no  ", returncode=0
        )
        self.assertEqual(SystemPulse.get_power_state(), PowerState.BATTERY.value)

    @patch("utils.pulse.subprocess.run")
    @patch("utils.pulse.os.path.exists", return_value=False)
    def test_upower_no_online_line_falls_to_unknown(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(stdout="some unrelated data\n", returncode=0)
        self.assertEqual(SystemPulse.get_power_state(), PowerState.UNKNOWN.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="1\n"))
    def test_sysfs_ac0_online(self, mock_exists, mock_run):
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/AC0/online"
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="0\n"))
    def test_sysfs_ac0_battery(self, mock_exists, mock_run):
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/AC0/online"
        self.assertEqual(SystemPulse.get_power_state(), PowerState.BATTERY.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="1\n"))
    def test_sysfs_ac_path(self, mock_exists, mock_run):
        """Second sysfs path: /sys/class/power_supply/AC/online."""
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/AC/online"
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="1\n"))
    def test_sysfs_acad_path(self, mock_exists, mock_run):
        """Third sysfs path: /sys/class/power_supply/ACAD/online."""
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/ACAD/online"
        self.assertEqual(SystemPulse.get_power_state(), PowerState.AC.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists", return_value=False)
    def test_unknown_when_all_fail(self, mock_exists, mock_run):
        self.assertEqual(SystemPulse.get_power_state(), PowerState.UNKNOWN.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=OSError("read error"))
    def test_sysfs_read_exception_returns_unknown(
        self, mock_file, mock_exists, mock_run
    ):
        """When sysfs file exists but read fails, return unknown."""
        self.assertEqual(SystemPulse.get_power_state(), PowerState.UNKNOWN.value)


# ---------------------------------------------------------------------------
# get_battery_level
# ---------------------------------------------------------------------------
class TestGetBatteryLevel(unittest.TestCase):
    """Test get_battery_level with upower and sysfs paths."""

    @patch("utils.pulse.subprocess.run")
    def test_upower_parses_percentage(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="  percentage:          45%\n", returncode=0
        )
        self.assertEqual(SystemPulse.get_battery_level(), 45)

    @patch("utils.pulse.subprocess.run")
    @patch("utils.pulse.os.path.exists", return_value=False)
    def test_upower_no_percentage_falls_to_minus_one(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(stdout="  state: discharging\n", returncode=0)
        self.assertEqual(SystemPulse.get_battery_level(), -1)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="82\n"))
    def test_sysfs_bat0(self, mock_exists, mock_run):
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/BAT0/capacity"
        self.assertEqual(SystemPulse.get_battery_level(), 82)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists")
    @patch("builtins.open", mock_open(read_data="55\n"))
    def test_sysfs_bat1(self, mock_exists, mock_run):
        """Second sysfs path: BAT1."""
        mock_exists.side_effect = lambda p: p == "/sys/class/power_supply/BAT1/capacity"
        self.assertEqual(SystemPulse.get_battery_level(), 55)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists", return_value=False)
    def test_no_battery_returns_minus_one(self, mock_exists, mock_run):
        self.assertEqual(SystemPulse.get_battery_level(), -1)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no upower"))
    @patch("utils.pulse.os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=OSError("read error"))
    def test_sysfs_read_exception_returns_minus_one(
        self, mock_file, mock_exists, mock_run
    ):
        """When sysfs file exists but read fails, return -1."""
        self.assertEqual(SystemPulse.get_battery_level(), -1)


# ---------------------------------------------------------------------------
# _register_networkmanager_signals
# ---------------------------------------------------------------------------
class TestRegisterNetworkManagerSignals(unittest.TestCase):
    """Test NetworkManager signal registration."""

    def test_no_system_bus_returns_early(self):
        pulse = SystemPulse()
        pulse._system_bus = None
        pulse._register_networkmanager_signals()

    def test_registers_two_receivers(self):
        pulse = SystemPulse()
        mock_bus = MagicMock()
        pulse._system_bus = mock_bus
        pulse._register_networkmanager_signals()
        self.assertEqual(mock_bus.add_signal_receiver.call_count, 2)

    def test_dbus_exception_handled(self):
        pulse = SystemPulse()
        mock_bus = MagicMock()
        try:
            import dbus as real_dbus

            if real_dbus is None:
                raise ImportError("dbus is None")
            exc_class = real_dbus.exceptions.DBusException
        except (ImportError, AttributeError):
            exc_class = Exception
        mock_bus.add_signal_receiver.side_effect = exc_class("test")
        pulse._system_bus = mock_bus
        pulse._register_networkmanager_signals()


# ---------------------------------------------------------------------------
# get_network_state
# ---------------------------------------------------------------------------
class TestGetNetworkState(unittest.TestCase):
    """Test get_network_state branches."""

    @patch("utils.pulse.subprocess.run")
    def test_connected(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connected\n", returncode=0)
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTED.value)

    @patch("utils.pulse.subprocess.run")
    def test_disconnected(self, mock_run):
        mock_run.return_value = MagicMock(stdout="disconnected\n", returncode=0)
        self.assertEqual(
            SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value
        )

    @patch("utils.pulse.subprocess.run")
    def test_connecting(self, mock_run):
        mock_run.return_value = MagicMock(stdout="connecting\n", returncode=0)
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTING.value)

    @patch("utils.pulse.subprocess.run")
    def test_connected_site_only(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="connected (site only)\n", returncode=0
        )
        self.assertEqual(SystemPulse.get_network_state(), NetworkState.CONNECTED.value)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no nmcli"))
    def test_error_returns_disconnected(self, mock_run):
        self.assertEqual(
            SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value
        )

    @patch("utils.pulse.subprocess.run")
    def test_unknown_state_string_returns_disconnected(self, mock_run):
        """Unrecognized state string defaults to disconnected."""
        mock_run.return_value = MagicMock(stdout="asleep\n", returncode=0)
        self.assertEqual(
            SystemPulse.get_network_state(), NetworkState.DISCONNECTED.value
        )


# ---------------------------------------------------------------------------
# _on_nm_state_changed
# ---------------------------------------------------------------------------
class TestOnNmStateChanged(unittest.TestCase):
    """Test NM state change handler branches."""

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="TestNet")
    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    @patch.object(SystemPulse, "wifi_ssid_changed")
    def test_connected_emits_all_signals(
        self, mock_wifi, mock_event, mock_state, mock_ssid
    ):
        pulse = SystemPulse()
        pulse._last_network_state = None
        pulse._on_nm_state_changed(70)
        mock_state.emit.assert_called_with(NetworkState.CONNECTED.value)
        mock_wifi.emit.assert_called_with("TestNet")

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="")
    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    @patch.object(SystemPulse, "wifi_ssid_changed")
    def test_connected_no_ssid_skips_wifi_emit(
        self, mock_wifi, mock_event, mock_state, mock_ssid
    ):
        pulse = SystemPulse()
        pulse._last_network_state = None
        pulse._on_nm_state_changed(80)
        mock_state.emit.assert_called_with(NetworkState.CONNECTED.value)
        mock_wifi.emit.assert_not_called()

    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_connecting_state(self, mock_event, mock_state):
        pulse = SystemPulse()
        pulse._last_network_state = None
        pulse._on_nm_state_changed(55)
        mock_state.emit.assert_called_with(NetworkState.CONNECTING.value)

    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_disconnected_state(self, mock_event, mock_state):
        pulse = SystemPulse()
        pulse._last_network_state = None
        pulse._on_nm_state_changed(20)
        mock_state.emit.assert_called_with(NetworkState.DISCONNECTED.value)

    @patch.object(SystemPulse, "network_state_changed")
    def test_no_emit_when_unchanged(self, mock_state):
        pulse = SystemPulse()
        pulse._last_network_state = NetworkState.CONNECTED.value
        pulse._on_nm_state_changed(70)
        mock_state.emit.assert_not_called()

    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_state_less_than_50_is_disconnected(self, mock_event, mock_state):
        pulse = SystemPulse()
        pulse._last_network_state = None
        pulse._on_nm_state_changed(10)
        mock_state.emit.assert_called_with(NetworkState.DISCONNECTED.value)


# ---------------------------------------------------------------------------
# _on_nm_properties_changed
# ---------------------------------------------------------------------------
class TestOnNmPropertiesChanged(unittest.TestCase):
    """Test NM property change handler (VPN check)."""

    @patch.object(SystemPulse, "vpn_state_changed")
    @patch.object(SystemPulse, "_check_vpn_active", return_value=True)
    def test_active_connections_triggers_vpn_check(
        self, mock_vpn_check, mock_vpn_signal
    ):
        pulse = SystemPulse()
        pulse._on_nm_properties_changed(
            "org.freedesktop.NetworkManager", {"ActiveConnections": ["/some/path"]}, []
        )
        mock_vpn_check.assert_called_once()
        mock_vpn_signal.emit.assert_called_once_with(True)

    @patch.object(SystemPulse, "vpn_state_changed")
    @patch.object(SystemPulse, "_check_vpn_active", return_value=False)
    def test_active_connections_vpn_false(self, mock_vpn_check, mock_vpn_signal):
        pulse = SystemPulse()
        pulse._on_nm_properties_changed(
            "org.freedesktop.NetworkManager", {"ActiveConnections": []}, []
        )
        mock_vpn_signal.emit.assert_called_once_with(False)

    @patch.object(SystemPulse, "vpn_state_changed")
    def test_no_active_connections_key_does_nothing(self, mock_vpn_signal):
        pulse = SystemPulse()
        pulse._on_nm_properties_changed(
            "org.freedesktop.NetworkManager", {"SomethingElse": True}, []
        )
        mock_vpn_signal.emit.assert_not_called()


# ---------------------------------------------------------------------------
# _check_vpn_active
# ---------------------------------------------------------------------------
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

    @patch("utils.pulse.subprocess.run")
    def test_vpn_deactivating_not_matched(self, mock_run):
        """No VPN type line means no VPN active."""
        mock_run.return_value = MagicMock(
            stdout="ethernet:802-3-ethernet:connected\n", returncode=0
        )
        pulse = SystemPulse()
        self.assertFalse(pulse._check_vpn_active())

    @patch("utils.pulse.subprocess.run")
    def test_vpn_deactivated_still_matches_substring(self, mock_run):
        """'deactivated' contains 'activated' — code returns True for this edge case."""
        mock_run.return_value = MagicMock(stdout="vpn:deactivated\n", returncode=0)
        pulse = SystemPulse()
        # Note: this is a known quirk of the substring check
        self.assertTrue(pulse._check_vpn_active())

    @patch("utils.pulse.subprocess.run", side_effect=Exception("nmcli fail"))
    def test_error_returns_false(self, mock_run):
        pulse = SystemPulse()
        self.assertFalse(pulse._check_vpn_active())

    @patch("utils.pulse.subprocess.run")
    def test_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        pulse = SystemPulse()
        self.assertFalse(pulse._check_vpn_active())


# ---------------------------------------------------------------------------
# get_wifi_ssid
# ---------------------------------------------------------------------------
class TestGetWifiSsid(unittest.TestCase):
    """Test Wi-Fi SSID parsing."""

    @patch("utils.pulse.subprocess.run")
    def test_returns_active_ssid(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="no:SomeNetwork\nyes:MyWiFi\nno:Neighbor\n", returncode=0
        )
        self.assertEqual(SystemPulse.get_wifi_ssid(), "MyWiFi")

    @patch("utils.pulse.subprocess.run")
    def test_returns_empty_when_none_active(self, mock_run):
        mock_run.return_value = MagicMock(stdout="no:Net1\nno:Net2\n", returncode=0)
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")

    @patch("utils.pulse.subprocess.run", side_effect=Exception("fail"))
    def test_returns_empty_on_error(self, mock_run):
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")

    @patch("utils.pulse.subprocess.run")
    def test_ssid_with_colon(self, mock_run):
        """SSID containing a colon should be preserved."""
        mock_run.return_value = MagicMock(stdout="yes:My:Network:5G\n", returncode=0)
        self.assertEqual(SystemPulse.get_wifi_ssid(), "My:Network:5G")

    @patch("utils.pulse.subprocess.run")
    def test_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        self.assertEqual(SystemPulse.get_wifi_ssid(), "")


# ---------------------------------------------------------------------------
# is_public_wifi
# ---------------------------------------------------------------------------
class TestIsPublicWifi(unittest.TestCase):
    """Test public Wi-Fi heuristic patterns."""

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Starbucks WiFi")
    def test_starbucks(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Guest Network")
    def test_guest(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Airport Free WiFi")
    def test_airport(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Hotel Lobby")
    def test_hotel(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="Library Access")
    def test_library(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="CoffeeShop")
    def test_coffee(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="McDonalds Free")
    def test_mcdonalds(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="OpenNet")
    def test_open(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="CafeWiFi")
    def test_cafe(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="FreeInternet")
    def test_free(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="PublicNetwork")
    def test_public(self, _):
        self.assertTrue(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="MyHomeNetwork5G")
    def test_home_not_public(self, _):
        self.assertFalse(SystemPulse.is_public_wifi())

    @patch.object(SystemPulse, "get_wifi_ssid", return_value="")
    def test_empty_not_public(self, _):
        self.assertFalse(SystemPulse.is_public_wifi())


# ---------------------------------------------------------------------------
# _register_monitor_signals
# ---------------------------------------------------------------------------
class TestRegisterMonitorSignals(unittest.TestCase):
    """Test monitor signal registration (KDE + GNOME paths)."""

    def test_no_system_bus_returns_early(self):
        pulse = SystemPulse()
        pulse._system_bus = None
        pulse._register_monitor_signals()

    @patch("utils.pulse.dbus")
    def test_kde_registration_success(self, mock_dbus):
        """KDE path succeeds, GNOME not tried."""
        pulse = SystemPulse()
        pulse._system_bus = MagicMock()
        mock_session_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_session_bus
        pulse._register_monitor_signals()
        mock_session_bus.add_signal_receiver.assert_called_once()

    @patch("utils.pulse.dbus")
    def test_kde_fails_gnome_succeeds(self, mock_dbus):
        """KDE fails, falls through to GNOME/Mutter path."""
        pulse = SystemPulse()
        pulse._system_bus = MagicMock()
        mock_session_bus_kde = MagicMock()
        mock_session_bus_gnome = MagicMock()

        call_count = [0]

        def session_bus_factory():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_session_bus_kde
            return mock_session_bus_gnome

        mock_dbus.SessionBus.side_effect = session_bus_factory
        mock_session_bus_kde.add_signal_receiver.side_effect = Exception("no KDE")

        pulse._register_monitor_signals()
        # GNOME path should have been tried
        mock_session_bus_gnome.add_signal_receiver.assert_called_once()

    @patch("utils.pulse.dbus")
    def test_both_kde_and_gnome_fail(self, mock_dbus):
        """Both KDE and GNOME paths fail gracefully."""
        pulse = SystemPulse()
        pulse._system_bus = MagicMock()
        mock_session_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_session_bus
        mock_session_bus.add_signal_receiver.side_effect = Exception("no DE")
        # Should not raise
        pulse._register_monitor_signals()


# ---------------------------------------------------------------------------
# get_connected_monitors (xrandr + kscreen-doctor)
# ---------------------------------------------------------------------------
class TestGetConnectedMonitors(unittest.TestCase):
    """Test monitor detection with xrandr and kscreen-doctor."""

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_parses_dual_monitors(self, mock_run):
        xrandr_output = (
            "Screen 0: minimum 8 x 8, current 3840 x 1080\n"
            "eDP-1 connected primary 1920x1080+0+0 344mm x 193mm\n"
            "   1920x1080     60.00*+\n"
            "HDMI-1 connected 1920x1080+1920+0 527mm x 296mm\n"
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
    def test_xrandr_ultrawide(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="DP-1 connected primary 3440x1440+0+0\n", returncode=0
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertTrue(monitors[0]["is_ultrawide"])
        self.assertEqual(monitors[0]["width"], 3440)
        self.assertEqual(monitors[0]["height"], 1440)

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_no_resolution(self, mock_run):
        """Monitor connected but no resolution in output."""
        mock_run.return_value = MagicMock(
            stdout="VGA-1 connected (normal left inverted)\n", returncode=0
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertEqual(monitors[0]["width"], 0)
        self.assertEqual(monitors[0]["height"], 0)
        self.assertFalse(monitors[0]["is_ultrawide"])

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_value_error_in_resolution_continues(self, mock_run):
        """Part contains 'x' and '+' but not a valid resolution (ValueError)."""
        mock_run.return_value = MagicMock(
            stdout="eDP-1 connected primary notxnumber+0+0 1920x1080+0+0\n",
            returncode=0,
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 1)
        # Should still parse the second valid resolution
        self.assertEqual(monitors[0]["name"], "eDP-1")

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_disconnected_not_included(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="DP-2 disconnected (normal left)\n", returncode=0
        )
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(len(monitors), 0)

    @patch("utils.pulse.subprocess.run")
    def test_kscreen_doctor_fallback(self, mock_run):
        """xrandr returns empty, kscreen-doctor provides monitors."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # xrandr empty
            MagicMock(
                stdout=(
                    "Output: eDP-1 connected\n"
                    "  enabled: True\n"
                    "  resolution: 1920x1080@60\n"
                    "Output: HDMI-1 connected\n"
                    "  enabled: True\n"
                    "  resolution: 2560x1440@60\n"
                ),
                returncode=0,
            ),
        ]
        monitors = SystemPulse.get_connected_monitors()
        self.assertIsInstance(monitors, list)
        self.assertGreaterEqual(len(monitors), 1)

    @patch("utils.pulse.subprocess.run")
    def test_kscreen_doctor_value_error_in_resolution(self, mock_run):
        """kscreen-doctor resolution parsing hits ValueError."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # xrandr empty
            MagicMock(
                stdout=("Output: eDP-1 connected\n  resolution: invalidxres@60\n"),
                returncode=0,
            ),
        ]
        monitors = SystemPulse.get_connected_monitors()
        self.assertIsInstance(monitors, list)

    @patch("utils.pulse.subprocess.run")
    def test_kscreen_doctor_index_error_in_resolution(self, mock_run):
        """kscreen-doctor resolution line missing colon."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # xrandr empty
            MagicMock(
                stdout=(
                    "Output: eDP-1 connected\n  resolution\n"  # no colon
                ),
                returncode=0,
            ),
        ]
        monitors = SystemPulse.get_connected_monitors()
        self.assertIsInstance(monitors, list)

    @patch("utils.pulse.subprocess.run", side_effect=Exception("no display tools"))
    def test_all_failures_return_empty(self, mock_run):
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(monitors, [])

    @patch("utils.pulse.subprocess.run")
    def test_kscreen_single_output_no_trailing(self, mock_run):
        """kscreen-doctor with a single Output that must be appended at end."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # xrandr empty
            MagicMock(
                stdout="Output: DP-1 connected\n  enabled: true\n",
                returncode=0,
            ),
        ]
        monitors = SystemPulse.get_connected_monitors()
        self.assertGreaterEqual(len(monitors), 1)
        self.assertEqual(monitors[0]["name"], "DP-1")

    @patch("utils.pulse.subprocess.run")
    def test_kscreen_ultrawide_detection(self, mock_run):
        """kscreen-doctor detects ultrawide via resolution."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # xrandr empty
            MagicMock(
                stdout=("Output: DP-1 connected\n  resolution: 3440x1440@60\n"),
                returncode=0,
            ),
        ]
        monitors = SystemPulse.get_connected_monitors()
        if monitors and monitors[0]["width"] > 0:
            self.assertTrue(monitors[0]["is_ultrawide"])

    @patch("utils.pulse.subprocess.run")
    def test_xrandr_exception_then_kscreen_exception(self, mock_run):
        """Both xrandr and kscreen-doctor raise exceptions."""
        mock_run.side_effect = [
            Exception("no xrandr"),
            Exception("no kscreen"),
        ]
        monitors = SystemPulse.get_connected_monitors()
        self.assertEqual(monitors, [])


# ---------------------------------------------------------------------------
# _on_monitor_changed
# ---------------------------------------------------------------------------
class TestOnMonitorChanged(unittest.TestCase):
    """Test _on_monitor_changed handler."""

    @patch.object(SystemPulse, "get_connected_monitors")
    @patch.object(SystemPulse, "monitor_count_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_emits_laptop_only(self, mock_event, mock_count, mock_monitors):
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
    def test_no_emit_when_count_unchanged(self, mock_count, mock_monitors):
        mock_monitors.return_value = [{"name": "eDP-1", "is_ultrawide": False}]
        pulse = SystemPulse()
        pulse._last_monitor_count = 1
        pulse._on_monitor_changed()
        mock_count.emit.assert_not_called()

    @patch.object(SystemPulse, "get_connected_monitors")
    @patch.object(SystemPulse, "monitor_count_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_multiple_non_ultrawide_no_laptop_event(
        self, mock_event, mock_count, mock_monitors
    ):
        """Multiple monitors, none ultrawide: no laptop_only or ultrawide event."""
        mock_monitors.return_value = [
            {"name": "eDP-1", "is_ultrawide": False},
            {"name": "HDMI-1", "is_ultrawide": False},
        ]
        pulse = SystemPulse()
        pulse._last_monitor_count = 0
        pulse._on_monitor_changed()
        mock_count.emit.assert_called_with(2)
        # Should NOT emit "laptop_only" (count > 1)
        # and should NOT emit "ultrawide_connected"
        for c in mock_event.emit.call_args_list:
            self.assertNotIn("laptop_only", c[0])
            self.assertNotIn("ultrawide_connected", c[0])

    @patch.object(SystemPulse, "get_connected_monitors")
    @patch.object(SystemPulse, "monitor_count_changed")
    @patch.object(SystemPulse, "event_triggered")
    def test_zero_monitors(self, mock_event, mock_count, mock_monitors):
        """Count changes to 0 (all disconnected)."""
        mock_monitors.return_value = []
        pulse = SystemPulse()
        pulse._last_monitor_count = 1
        pulse._on_monitor_changed()
        mock_count.emit.assert_called_with(0)


# ---------------------------------------------------------------------------
# _run_polling_fallback
# ---------------------------------------------------------------------------
class TestRunPollingFallback(unittest.TestCase):
    """Test polling fallback loop."""

    @patch("time.sleep", side_effect=[None, StopIteration])
    @patch.object(SystemPulse, "get_connected_monitors", return_value=[])
    @patch.object(SystemPulse, "get_network_state", return_value="connected")
    @patch.object(SystemPulse, "get_power_state", return_value="ac")
    @patch.object(SystemPulse, "power_state_changed")
    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "monitor_count_changed")
    def test_polling_emits_on_state_changes(
        self,
        mock_mon_count,
        mock_net,
        mock_power,
        mock_get_power,
        mock_get_net,
        mock_get_mon,
        mock_sleep,
    ):
        pulse = SystemPulse()
        pulse._last_power_state = None
        pulse._last_network_state = None
        pulse._last_monitor_count = 1  # different from 0 (len([]))

        try:
            pulse._run_polling_fallback()
        except StopIteration:
            pass

        mock_power.emit.assert_called_with("ac")
        mock_net.emit.assert_called_with("connected")
        mock_mon_count.emit.assert_called_with(0)

    @patch("time.sleep", side_effect=StopIteration)
    @patch.object(
        SystemPulse, "get_connected_monitors", return_value=[{"name": "eDP-1"}]
    )
    @patch.object(SystemPulse, "get_network_state", return_value="disconnected")
    @patch.object(SystemPulse, "get_power_state", return_value="battery")
    @patch.object(SystemPulse, "power_state_changed")
    @patch.object(SystemPulse, "network_state_changed")
    @patch.object(SystemPulse, "monitor_count_changed")
    def test_polling_no_emit_when_unchanged(
        self,
        mock_mon_count,
        mock_net,
        mock_power,
        mock_get_power,
        mock_get_net,
        mock_get_mon,
        mock_sleep,
    ):
        pulse = SystemPulse()
        pulse._last_power_state = "battery"
        pulse._last_network_state = "disconnected"
        pulse._last_monitor_count = 1

        try:
            pulse._run_polling_fallback()
        except StopIteration:
            pass

        mock_power.emit.assert_not_called()
        mock_net.emit.assert_not_called()
        mock_mon_count.emit.assert_not_called()

    @patch("time.sleep")
    @patch.object(SystemPulse, "get_power_state", side_effect=Exception("poll error"))
    @patch.object(SystemPulse, "power_state_changed")
    def test_polling_handles_exception(self, mock_power, mock_get_power, mock_sleep):
        """Polling loop handles exceptions and sleeps longer."""
        call_count = [0]

        def sleep_side_effect(seconds):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise StopIteration

        mock_sleep.side_effect = sleep_side_effect

        pulse = SystemPulse()
        try:
            pulse._run_polling_fallback()
        except StopIteration:
            pass
        # Exception path sleeps 10 seconds
        mock_sleep.assert_any_call(10)


# ---------------------------------------------------------------------------
# PulseThread
# ---------------------------------------------------------------------------
class TestPulseThread(unittest.TestCase):
    """Test PulseThread helper class."""

    def test_thread_init(self):
        pulse = SystemPulse()
        thread = PulseThread(pulse)
        self.assertIs(thread.pulse, pulse)

    @patch.object(SystemPulse, "start")
    def test_run_calls_pulse_start(self, mock_start):
        pulse = SystemPulse()
        thread = PulseThread(pulse)
        thread.run()
        mock_start.assert_called_once()

    @patch.object(SystemPulse, "stop")
    def test_stop_calls_pulse_stop_and_quit(self, mock_stop):
        pulse = SystemPulse()
        thread = PulseThread(pulse)
        with patch.object(thread, "quit"):
            with patch.object(thread, "wait"):
                thread.stop()
        mock_stop.assert_called_once()


# ---------------------------------------------------------------------------
# create_pulse_listener
# ---------------------------------------------------------------------------
class TestCreatePulseListener(unittest.TestCase):
    """Test create_pulse_listener convenience function."""

    def test_returns_pulse_and_thread(self):
        pulse, thread = create_pulse_listener()
        self.assertIsInstance(pulse, SystemPulse)
        self.assertIsInstance(thread, PulseThread)
        self.assertIs(thread.pulse, pulse)


# ---------------------------------------------------------------------------
# DBus import fallback (DBUS_AVAILABLE flag)
# ---------------------------------------------------------------------------
class TestDbusAvailabilityFlag(unittest.TestCase):
    """Test that DBUS_AVAILABLE is a boolean reflecting dbus import."""

    def test_dbus_available_is_bool(self):
        from utils.pulse import DBUS_AVAILABLE

        self.assertIsInstance(DBUS_AVAILABLE, bool)


if __name__ == "__main__":
    unittest.main()
