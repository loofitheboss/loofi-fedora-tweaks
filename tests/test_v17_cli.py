"""
Tests for v17.0 Atlas CLI commands: bluetooth and storage.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.bluetooth import (
    BluetoothManager, BluetoothDevice, BluetoothResult,
    BluetoothStatus, BluetoothDeviceType,
)
from utils.storage import (
    StorageManager, BlockDevice, SmartHealth,
    MountInfo, StorageResult,
)


class TestCLIBluetoothCommand(unittest.TestCase):
    """Tests for the CLI bluetooth subcommand handler."""

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_status(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.get_adapter_status.return_value = BluetoothStatus(
            powered=True, discoverable=False,
            adapter_name="BlueZ", adapter_address="00:11:22:33:44:55"
        )
        args = MagicMock(action="status")
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_status_no_adapter(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.get_adapter_status.return_value = BluetoothStatus(
            powered=False, adapter_name=""
        )
        args = MagicMock(action="status")
        import cli.main
        cli.main._json_output = False
        # Returns 1 when no adapter_name detected
        result = cmd_bluetooth(args)
        self.assertEqual(result, 1)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_devices_empty(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.list_devices.return_value = []
        args = MagicMock(action="devices", paired=False)
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_devices_json(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.list_devices.return_value = [
            BluetoothDevice(
                address="AA:BB:CC:DD:EE:FF", name="TestDevice",
                paired=True, connected=False,
                device_type=BluetoothDeviceType.AUDIO
            )
        ]
        args = MagicMock(action="devices", paired=True)
        import cli.main
        cli.main._json_output = True
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)
        cli.main._json_output = False

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_power_on(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.power_on.return_value = BluetoothResult(True, "OK")
        args = MagicMock(action="power-on")
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_power_off(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.power_off.return_value = BluetoothResult(True, "OK")
        args = MagicMock(action="power-off")
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_connect(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.connect.return_value = BluetoothResult(True, "Connected")
        args = MagicMock(action="connect", address="AA:BB:CC:DD:EE:FF")
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_connect_no_address(self, mock_bt):
        from cli.main import cmd_bluetooth
        args = MagicMock(action="connect", address=None)
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 1)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_pair(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.pair.return_value = BluetoothResult(True, "Paired")
        args = MagicMock(action="pair", address="AA:BB:CC:DD:EE:FF")
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_unpair(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.unpair.return_value = BluetoothResult(True, "Removed")
        args = MagicMock(action="unpair", address="AA:BB:CC:DD:EE:FF")
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)

    @patch('cli.main.BluetoothManager')
    def test_bluetooth_scan(self, mock_bt):
        from cli.main import cmd_bluetooth
        mock_bt.scan.return_value = [
            BluetoothDevice(address="11:22:33:44:55:66", name="Nearby",
                            device_type=BluetoothDeviceType.UNKNOWN)
        ]
        args = MagicMock(action="scan", timeout=5)
        import cli.main
        cli.main._json_output = False
        result = cmd_bluetooth(args)
        self.assertEqual(result, 0)


class TestCLIStorageCommand(unittest.TestCase):
    """Tests for the CLI storage subcommand handler."""

    @patch('cli.main.StorageManager')
    def test_storage_disks(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.list_disks.return_value = [
            BlockDevice(name="sda", path="/dev/sda", size="500G",
                        device_type="disk", model="Samsung SSD")
        ]
        args = MagicMock(action="disks")
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 0)

    @patch('cli.main.StorageManager')
    def test_storage_disks_json(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.list_disks.return_value = [
            BlockDevice(name="sda", path="/dev/sda", size="500G",
                        device_type="disk", model="Samsung")
        ]
        args = MagicMock(action="disks")
        import cli.main
        cli.main._json_output = True
        result = cmd_storage(args)
        self.assertEqual(result, 0)
        cli.main._json_output = False

    @patch('cli.main.StorageManager')
    def test_storage_disks_empty(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.list_disks.return_value = []
        args = MagicMock(action="disks")
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 0)

    @patch('cli.main.StorageManager')
    def test_storage_mounts(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.list_mounts.return_value = [
            MountInfo(source="/dev/sda2", target="/", fstype="ext4",
                      options="", size="460G", used="120G",
                      avail="320G", use_percent="28%")
        ]
        args = MagicMock(action="mounts")
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 0)

    @patch('cli.main.StorageManager')
    def test_storage_smart(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.get_smart_health.return_value = SmartHealth(
            device="/dev/sda", model="Samsung",
            serial="S123", health_passed=True,
            temperature_c=30, power_on_hours=1000
        )
        args = MagicMock(action="smart", device="/dev/sda")
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 0)

    @patch('cli.main.StorageManager')
    def test_storage_smart_no_device(self, mock_sm):
        from cli.main import cmd_storage
        args = MagicMock(action="smart", device=None)
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 1)

    @patch('cli.main.StorageManager')
    def test_storage_usage(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.get_usage_summary.return_value = {
            "total_size": "500G", "total_used": "120G",
            "total_available": "380G", "disk_count": 1,
            "mount_count": 2,
        }
        args = MagicMock(action="usage")
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 0)

    @patch('cli.main.StorageManager')
    def test_storage_trim_success(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.trim_ssd.return_value = StorageResult(True, "Trimmed OK")
        args = MagicMock(action="trim")
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 0)

    @patch('cli.main.StorageManager')
    def test_storage_trim_failure(self, mock_sm):
        from cli.main import cmd_storage
        mock_sm.trim_ssd.return_value = StorageResult(False, "Failed")
        args = MagicMock(action="trim")
        import cli.main
        cli.main._json_output = False
        result = cmd_storage(args)
        self.assertEqual(result, 1)


class TestCLIArgparse(unittest.TestCase):
    """Test that bluetooth and storage subcommands parse correctly."""

    def test_bluetooth_in_cli_main(self):
        """Verify bluetooth command is registered."""
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'cli', 'main.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn('"bluetooth": cmd_bluetooth', source)
        self.assertIn('subparsers.add_parser("bluetooth"', source)

    def test_storage_in_cli_main(self):
        """Verify storage command is registered."""
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'cli', 'main.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn('"storage": cmd_storage', source)
        self.assertIn('subparsers.add_parser("storage"', source)


if __name__ == '__main__':
    unittest.main()
