"""
Tests for BluetoothManager (v17.0 Atlas).
Covers adapter status, device listing, scan, pairing,
connect/disconnect, trust/block, and power on/off.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from services.hardware import (
    BluetoothManager, BluetoothDevice, BluetoothResult,
    BluetoothStatus, BluetoothDeviceType,
)


class TestBluetoothAdapterStatus(unittest.TestCase):
    """Tests for get_adapter_status()."""

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_adapter_powered_on(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Controller 00:11:22:33:44:55 (public)\n"
                "\tName: BlueZ\n"
                "\tPowered: yes\n"
                "\tDiscoverable: no\n"
                "\tPairable: yes\n"
            )
        )
        status = BluetoothManager.get_adapter_status()
        self.assertTrue(status.powered)
        self.assertFalse(status.discoverable)
        self.assertEqual(status.adapter_name, "BlueZ")
        self.assertEqual(status.adapter_address, "00:11:22:33:44:55")

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_adapter_powered_off(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Controller 00:11:22:33:44:55\n\tPowered: no\n"
        )
        status = BluetoothManager.get_adapter_status()
        self.assertFalse(status.powered)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_adapter_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        status = BluetoothManager.get_adapter_status()
        self.assertFalse(status.powered)
        self.assertEqual(status.adapter_name, "")

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_adapter_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("bluetoothctl", 10)
        status = BluetoothManager.get_adapter_status()
        self.assertFalse(status.powered)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_adapter_oserror(self, mock_run):
        mock_run.side_effect = OSError("bluetoothctl not found")
        status = BluetoothManager.get_adapter_status()
        self.assertFalse(status.powered)


class TestBluetoothListDevices(unittest.TestCase):
    """Tests for list_devices()."""

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_list_paired_devices(self, mock_run):
        # First call: list, second call: info per device
        def side_effect(cmd, **kwargs):
            if "devices" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="Device AA:BB:CC:DD:EE:FF MyHeadphones\n"
                           "Device 11:22:33:44:55:66 MyKeyboard\n"
                )
            elif "info" in cmd:
                addr = cmd[2]
                if addr == "AA:BB:CC:DD:EE:FF":
                    return MagicMock(
                        returncode=0,
                        stdout="\tPaired: yes\n\tConnected: yes\n"
                               "\tTrusted: yes\n\tBlocked: no\n"
                               "\tIcon: audio-headset\n"
                    )
                return MagicMock(
                    returncode=0,
                    stdout="\tPaired: yes\n\tConnected: no\n"
                           "\tTrusted: no\n\tBlocked: no\n"
                           "\tIcon: input-keyboard\n"
                )
            return MagicMock(returncode=1, stdout="")

        mock_run.side_effect = side_effect
        devices = BluetoothManager.list_devices(paired_only=True)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].name, "MyHeadphones")
        self.assertTrue(devices[0].connected)
        self.assertEqual(devices[0].device_type, BluetoothDeviceType.AUDIO)
        self.assertEqual(devices[1].device_type, BluetoothDeviceType.INPUT)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_list_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        devices = BluetoothManager.list_devices()
        self.assertEqual(devices, [])

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_list_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        devices = BluetoothManager.list_devices()
        self.assertEqual(devices, [])


class TestBluetoothDeviceClassification(unittest.TestCase):
    """Tests for _classify_device()."""

    def test_audio_headset(self):
        self.assertEqual(BluetoothManager._classify_device("audio-headset"),
                         BluetoothDeviceType.AUDIO)

    def test_audio_headphone(self):
        self.assertEqual(BluetoothManager._classify_device("audio-headphones"),
                         BluetoothDeviceType.AUDIO)

    def test_input_keyboard(self):
        self.assertEqual(BluetoothManager._classify_device("input-keyboard"),
                         BluetoothDeviceType.INPUT)

    def test_input_mouse(self):
        self.assertEqual(BluetoothManager._classify_device("input-mouse"),
                         BluetoothDeviceType.INPUT)

    def test_phone(self):
        self.assertEqual(BluetoothManager._classify_device("phone"),
                         BluetoothDeviceType.PHONE)

    def test_computer(self):
        self.assertEqual(BluetoothManager._classify_device("computer"),
                         BluetoothDeviceType.COMPUTER)

    def test_unknown(self):
        self.assertEqual(BluetoothManager._classify_device("other-thing"),
                         BluetoothDeviceType.UNKNOWN)


class TestBluetoothActions(unittest.TestCase):
    """Tests for pair/unpair/connect/disconnect/trust/block/unblock."""

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_pair_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Pairing successful", stderr=""
        )
        result = BluetoothManager.pair("AA:BB:CC:DD:EE:FF")
        self.assertTrue(result.success)
        self.assertIn("OK", result.message)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_pair_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Failed to pair"
        )
        result = BluetoothManager.pair("AA:BB:CC:DD:EE:FF")
        self.assertFalse(result.success)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_connect_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Connection successful", stderr=""
        )
        result = BluetoothManager.connect("AA:BB:CC:DD:EE:FF")
        self.assertTrue(result.success)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_disconnect_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Successful", stderr=""
        )
        result = BluetoothManager.disconnect("AA:BB:CC:DD:EE:FF")
        self.assertTrue(result.success)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_trust_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="trust successful", stderr=""
        )
        result = BluetoothManager.trust("AA:BB:CC:DD:EE:FF")
        self.assertTrue(result.success)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_block_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="block successful", stderr=""
        )
        result = BluetoothManager.block("AA:BB:CC:DD:EE:FF")
        self.assertTrue(result.success)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_unblock_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="unblock successful", stderr=""
        )
        result = BluetoothManager.unblock("AA:BB:CC:DD:EE:FF")
        self.assertTrue(result.success)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_action_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("bluetoothctl", 15)
        result = BluetoothManager.pair("AA:BB:CC:DD:EE:FF")
        self.assertFalse(result.success)
        self.assertIn("Timed out", result.message)

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_action_oserror(self, mock_run):
        mock_run.side_effect = OSError("not found")
        result = BluetoothManager.connect("AA:BB:CC:DD:EE:FF")
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)


class TestBluetoothPower(unittest.TestCase):
    """Tests for power_on/power_off."""

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_power_on(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Changing power on succeeded", stderr=""
        )
        result = BluetoothManager.power_on()
        self.assertTrue(result.success)
        mock_run.assert_called_once_with(
            ["bluetoothctl", "power", "on"],
            capture_output=True, text=True, timeout=15
        )

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_power_off(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Changing power off succeeded", stderr=""
        )
        result = BluetoothManager.power_off()
        self.assertTrue(result.success)
        mock_run.assert_called_once_with(
            ["bluetoothctl", "power", "off"],
            capture_output=True, text=True, timeout=15
        )


class TestBluetoothScan(unittest.TestCase):
    """Tests for scan()."""

    @patch('services.hardware.bluetooth.subprocess.run')
    def test_scan_returns_devices(self, mock_run):
        def side_effect(cmd, **kwargs):
            if "scan" in cmd:
                return MagicMock(returncode=0, stdout="")
            elif "devices" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="Device AA:BB:CC:DD:EE:FF SomeDevice\n"
                )
            elif "info" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="\tPaired: no\n\tConnected: no\n"
                )
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect
        devices = BluetoothManager.scan(timeout=5)
        self.assertGreaterEqual(len(devices), 1)


class TestBluetoothDataclasses(unittest.TestCase):
    """Tests for dataclass to_dict methods."""

    def test_device_to_dict(self):
        device = BluetoothDevice(
            address="AA:BB:CC:DD:EE:FF",
            name="Test",
            paired=True,
            connected=False,
            device_type=BluetoothDeviceType.AUDIO,
        )
        d = device.to_dict()
        self.assertEqual(d["address"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(d["device_type"], "audio")
        self.assertTrue(d["paired"])

    def test_result_fields(self):
        r = BluetoothResult(success=True, message="OK")
        self.assertTrue(r.success)
        self.assertEqual(r.message, "OK")

    def test_status_defaults(self):
        s = BluetoothStatus()
        self.assertFalse(s.powered)
        self.assertEqual(s.adapter_name, "")


if __name__ == '__main__':
    unittest.main()
