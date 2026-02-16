"""
Tests for utils/usbguard.py — USBGuardManager.
Coverage-oriented: install check, service status, install, start,
list devices, allow/block, default policy, lock screen rule, generate policy.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.usbguard import USBGuardManager, USBDevice


class TestIsInstalled(unittest.TestCase):
    """Test is_installed."""

    @patch("utils.usbguard.shutil.which", return_value="/usr/bin/usbguard")
    def test_installed(self, mock_which):
        self.assertTrue(USBGuardManager.is_installed())

    @patch("utils.usbguard.shutil.which", return_value=None)
    def test_not_installed(self, mock_which):
        self.assertFalse(USBGuardManager.is_installed())


class TestIsRunning(unittest.TestCase):
    """Test is_running."""

    @patch("utils.usbguard.subprocess.run")
    def test_running(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(USBGuardManager.is_running())

    @patch("utils.usbguard.subprocess.run")
    def test_not_running(self, mock_run):
        mock_run.return_value = MagicMock(returncode=3)
        self.assertFalse(USBGuardManager.is_running())

    @patch("utils.usbguard.subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run):
        self.assertFalse(USBGuardManager.is_running())


class TestInstall(unittest.TestCase):
    """Test install."""

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    def test_already_installed(self, mock_inst):
        result = USBGuardManager.install()
        self.assertTrue(result.success)
        self.assertIn("already", result.message)

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    @patch("utils.usbguard.subprocess.run")
    def test_install_success(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=0)
        result = USBGuardManager.install()
        self.assertTrue(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    @patch("utils.usbguard.subprocess.run")
    def test_install_failure(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=1, stderr="no repo")
        result = USBGuardManager.install()
        self.assertFalse(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    @patch("utils.usbguard.subprocess.run", side_effect=OSError("timeout"))
    def test_install_exception(self, mock_run, mock_inst):
        result = USBGuardManager.install()
        self.assertFalse(result.success)


class TestStartService(unittest.TestCase):
    """Test start_service."""

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    def test_not_installed(self, mock_inst):
        result = USBGuardManager.start_service()
        self.assertFalse(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_start_success(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=0)
        result = USBGuardManager.start_service()
        self.assertTrue(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_start_failure(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=1, stderr="denied")
        result = USBGuardManager.start_service()
        self.assertFalse(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run", side_effect=OSError("err"))
    def test_start_exception(self, mock_run, mock_inst):
        result = USBGuardManager.start_service()
        self.assertFalse(result.success)


class TestListDevices(unittest.TestCase):
    """Test list_devices."""

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    def test_not_installed_returns_empty(self, mock_inst):
        self.assertEqual(USBGuardManager.list_devices(), [])

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_parse_devices(self, mock_run, mock_inst):
        output = (
            '1: allow id 1d6b:0002 serial "0" name "xHCI" hash "abc123"\n'
            '2: block id 0781:5583 serial "AA" name "Ultra" hash "def456"\n'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=output)
        devices = USBGuardManager.list_devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].policy, "allow")
        self.assertEqual(devices[1].policy, "block")

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_nonzero_rc_returns_empty(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertEqual(USBGuardManager.list_devices(), [])

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run", side_effect=OSError("fail"))
    def test_exception_returns_empty(self, mock_run, mock_inst):
        self.assertEqual(USBGuardManager.list_devices(), [])


class TestAllowDevice(unittest.TestCase):
    """Test allow_device."""

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    def test_not_installed(self, mock_inst):
        result = USBGuardManager.allow_device("1")
        self.assertFalse(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_allow_success(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=0)
        result = USBGuardManager.allow_device("1")
        self.assertTrue(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_allow_permanent(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=0)
        result = USBGuardManager.allow_device("1", permanent=True)
        self.assertTrue(result.success)
        args = mock_run.call_args[0][0]
        self.assertIn("-p", args)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_allow_failure(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=1, stderr="denied")
        result = USBGuardManager.allow_device("1")
        self.assertFalse(result.success)


class TestBlockDevice(unittest.TestCase):
    """Test block_device."""

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    def test_not_installed(self, mock_inst):
        result = USBGuardManager.block_device("2")
        self.assertFalse(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_block_success(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=0)
        result = USBGuardManager.block_device("2")
        self.assertTrue(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_block_permanent(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=0)
        result = USBGuardManager.block_device("2", permanent=True)
        args = mock_run.call_args[0][0]
        self.assertIn("-p", args)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run", side_effect=OSError("err"))
    def test_block_exception(self, mock_run, mock_inst):
        result = USBGuardManager.block_device("2")
        self.assertFalse(result.success)


class TestSetDefaultPolicy(unittest.TestCase):
    """Test set_default_policy."""

    def test_invalid_policy(self):
        result = USBGuardManager.set_default_policy("invalid")
        self.assertFalse(result.success)

    def test_valid_policy_returns_instructions(self):
        result = USBGuardManager.set_default_policy("block")
        # Returns instructions (not actual modification)
        self.assertFalse(result.success)
        self.assertIn("block", result.message)


class TestLockScreenRule(unittest.TestCase):
    """Test get_lock_screen_rule."""

    def test_returns_script(self):
        script = USBGuardManager.get_lock_screen_rule()
        self.assertIn("#!/bin/bash", script)
        self.assertIn("dbus-monitor", script)
        self.assertIn("usbguard", script)


class TestGenerateInitialPolicy(unittest.TestCase):
    """Test generate_initial_policy."""

    @patch.object(USBGuardManager, "is_installed", return_value=False)
    def test_not_installed(self, mock_inst):
        result = USBGuardManager.generate_initial_policy()
        self.assertFalse(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_success(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="allow id 1d6b:0002 name xHCI"
        )
        result = USBGuardManager.generate_initial_policy()
        self.assertTrue(result.success)
        self.assertIn("policy", result.data)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run")
    def test_failure(self, mock_run, mock_inst):
        mock_run.return_value = MagicMock(returncode=1, stderr="denied")
        result = USBGuardManager.generate_initial_policy()
        self.assertFalse(result.success)

    @patch.object(USBGuardManager, "is_installed", return_value=True)
    @patch("utils.usbguard.subprocess.run", side_effect=OSError("err"))
    def test_exception(self, mock_run, mock_inst):
        result = USBGuardManager.generate_initial_policy()
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
