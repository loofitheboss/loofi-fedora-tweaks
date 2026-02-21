"""
Tests for services/hardware/battery.py — BatteryManager.
"""
import unittest
import sys
import os
import subprocess
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from services.hardware.battery import BatteryManager


class TestBatteryManagerSetLimit(unittest.TestCase):
    """Tests for BatteryManager.set_limit()."""

    def setUp(self):
        self.mgr = BatteryManager()

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_success_80(self, mock_makedirs, mock_file, mock_run):
        """Setting limit to 80% succeeds through all steps."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        cmd, args = self.mgr.set_limit(80)
        self.assertEqual(cmd, "echo")
        self.assertIn("80%", args[0])
        # 4 subprocess calls: mv, daemon-reload, enable, tee
        self.assertEqual(mock_run.call_count, 4)

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_success_100(self, mock_makedirs, mock_file, mock_run):
        """Setting limit to 100% succeeds."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        cmd, args = self.mgr.set_limit(100)
        self.assertEqual(cmd, "echo")
        self.assertIn("100%", args[0])

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_mv_failure(self, mock_makedirs, mock_file, mock_run):
        """Failure to move service file returns None."""
        mock_run.return_value = MagicMock(returncode=1, stderr='Permission denied')
        cmd, args = self.mgr.set_limit(80)
        self.assertIsNone(cmd)
        self.assertIsNone(args)

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_daemon_reload_failure(self, mock_makedirs, mock_file, mock_run):
        """Failure on daemon-reload returns None."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # mv succeeds
            MagicMock(returncode=1, stderr='reload failed'),  # daemon-reload fails
        ]
        cmd, args = self.mgr.set_limit(80)
        self.assertIsNone(cmd)
        self.assertIsNone(args)

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_enable_failure(self, mock_makedirs, mock_file, mock_run):
        """Failure on systemctl enable returns None."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # mv succeeds
            MagicMock(returncode=0),  # daemon-reload succeeds
            MagicMock(returncode=1, stderr='enable failed'),  # enable fails
        ]
        cmd, args = self.mgr.set_limit(80)
        self.assertIsNone(cmd)
        self.assertIsNone(args)

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_tee_failure_returns_reboot_msg(self, mock_makedirs, mock_file, mock_run):
        """Failure on sysfs tee returns reboot message instead of None."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # mv
            MagicMock(returncode=0),  # daemon-reload
            MagicMock(returncode=0),  # enable
            MagicMock(returncode=1, stderr='write failed'),  # tee fails
        ]
        cmd, args = self.mgr.set_limit(80)
        self.assertEqual(cmd, "echo")
        self.assertIn("reboot", args[0].lower())

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_subprocess_error(self, mock_makedirs, mock_file, mock_run):
        """SubprocessError during execution returns None."""
        mock_run.side_effect = subprocess.SubprocessError("command failed")
        cmd, args = self.mgr.set_limit(80)
        self.assertIsNone(cmd)
        self.assertIsNone(args)

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_os_error(self, mock_makedirs, mock_file, mock_run):
        """OSError during execution returns None."""
        mock_run.side_effect = OSError("disk error")
        cmd, args = self.mgr.set_limit(80)
        self.assertIsNone(cmd)
        self.assertIsNone(args)

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', side_effect=IOError("cannot write"))
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_config_write_failure_continues(self, mock_makedirs, mock_file, mock_run):
        """Config write failure logs but continues to service setup."""
        # The open for config fails, but the service tmp open also fails
        # since all open() calls are mocked with side_effect
        # The function catches IOError on config, then tries to write tmp
        # Since all opens fail, subprocess is never reached
        cmd, args = self.mgr.set_limit(80)
        # Due to IOError on tmp file write, subprocess.run isn't called,
        # so we end up in the except block
        self.assertIsNone(cmd)

    @patch('services.hardware.battery.subprocess.run')
    @patch('services.hardware.battery.os.makedirs', side_effect=OSError("no dir"))
    def test_set_limit_makedirs_failure_continues(self, mock_makedirs, mock_run):
        """makedirs failure is caught and execution continues."""
        # makedirs fails but is caught, then open is called which will
        # also need to be mocked
        mock_run.return_value = MagicMock(returncode=0)
        with patch('builtins.open', mock_open()):
            cmd, args = self.mgr.set_limit(80)
            self.assertEqual(cmd, "echo")

    def test_class_constants(self):
        """BatteryManager has expected class constants."""
        self.assertEqual(BatteryManager.SCRIPT_PATH, "/usr/local/bin/loofi-battery-limit.sh")
        self.assertEqual(BatteryManager.SERVICE_PATH, "/etc/systemd/system/loofi-battery.service")
        self.assertEqual(BatteryManager.CONFIG_PATH, "/etc/loofi-fedora-tweaks/battery.conf")

    @patch('services.hardware.battery.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('services.hardware.battery.os.makedirs')
    def test_set_limit_subprocess_calls_have_timeout(self, mock_makedirs, mock_file, mock_run):
        """All subprocess calls include timeout parameter."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        self.mgr.set_limit(80)
        for c in mock_run.call_args_list:
            self.assertIn('timeout', c.kwargs, f"Missing timeout in call: {c}")


if __name__ == '__main__':
    unittest.main()
