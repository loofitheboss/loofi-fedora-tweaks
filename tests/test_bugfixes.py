"""
Tests for bug fixes identified in QA review.
Covers: path traversal prevention, signal validation, disk mount filtering,
preset name consistency, and kill_process edge cases.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import shutil

# Add source path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.presets import PresetManager
from services.system import ProcessManager
from services.hardware import DiskManager


class TestPresetPathTraversal(unittest.TestCase):
    """Test that preset names are sanitized to prevent path traversal."""

    def setUp(self):
        self.manager = PresetManager()
        self.original_dir = self.manager.PRESETS_DIR
        self.temp_dir = tempfile.mkdtemp()
        self.manager.PRESETS_DIR = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.manager.PRESETS_DIR = self.original_dir

    def test_sanitize_removes_path_traversal(self):
        result = PresetManager._sanitize_name("../../etc/evil")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_sanitize_removes_slashes(self):
        result = PresetManager._sanitize_name("my/preset/name")
        self.assertNotIn("/", result)

    def test_sanitize_empty_name_gets_default(self):
        result = PresetManager._sanitize_name("")
        self.assertEqual(result, "unnamed_preset")

    def test_sanitize_dotdot_only_gets_default(self):
        result = PresetManager._sanitize_name("../../..")
        self.assertNotEqual(result, "")
        self.assertNotIn("..", result)

    def test_sanitize_normal_name_unchanged(self):
        result = PresetManager._sanitize_name("my_preset")
        self.assertEqual(result, "my_preset")

    @patch.object(PresetManager, '_get_gsettings', return_value="TestTheme")
    @patch.object(PresetManager, '_get_battery_limit', return_value=80)
    @patch.object(PresetManager, '_get_power_profile', return_value="balanced")
    def test_save_preset_uses_sanitized_name(self, *mocks):
        self.manager.save_preset("../../etc/evil")
        # File should be created in temp_dir, not in ../../etc/
        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 1)
        self.assertNotIn("..", files[0])

    def test_save_preset_data_uses_sanitized_name(self):
        data = {"theme": "Adwaita"}
        self.manager.save_preset_data("../../etc/evil", data)
        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 1)
        self.assertNotIn("..", files[0])


class TestPresetNameConsistency(unittest.TestCase):
    """Test that save_preset_data and load_preset use consistent filenames."""

    def setUp(self):
        self.manager = PresetManager()
        self.temp_dir = tempfile.mkdtemp()
        self.manager.PRESETS_DIR = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.object(PresetManager, '_set_gsettings')
    def test_save_data_and_load_use_same_file(self, mock_set):
        """Verify that a preset saved via save_preset_data can be loaded."""
        name = "My Cool Theme"
        data = {"theme": "Adwaita", "icon_theme": "Papirus"}
        self.manager.save_preset_data(name, data)
        
        # The sanitized name should match what load_preset uses
        safe_name = PresetManager._sanitize_name(name)
        path = os.path.join(self.temp_dir, f"{safe_name}.json")
        self.assertTrue(os.path.exists(path))
        
        # load_preset with the SAME name should find it
        result = self.manager.load_preset(name)
        self.assertIsNotNone(result)

    def test_delete_preset_finds_saved_preset(self):
        """Verify delete_preset can find a preset saved by save_preset_data."""
        name = "Test Preset"
        data = {"theme": "Adwaita"}
        self.manager.save_preset_data(name, data)
        
        result = self.manager.delete_preset(name)
        self.assertTrue(result)
        self.assertEqual(os.listdir(self.temp_dir), [])


class TestKillProcessValidation(unittest.TestCase):
    """Test signal and PID validation in kill_process."""

    def test_negative_signal_rejected(self):
        success, msg = ProcessManager.kill_process(1234, -5)
        self.assertFalse(success)
        self.assertIn("Invalid signal", msg)

    def test_signal_too_high_rejected(self):
        success, msg = ProcessManager.kill_process(1234, 65)
        self.assertFalse(success)
        self.assertIn("Invalid signal", msg)

    def test_invalid_pid_zero(self):
        success, msg = ProcessManager.kill_process(0, 15)
        self.assertFalse(success)
        self.assertIn("Invalid PID", msg)

    def test_invalid_pid_negative(self):
        success, msg = ProcessManager.kill_process(-1, 15)
        self.assertFalse(success)
        self.assertIn("Invalid PID", msg)

    @patch('os.kill')
    def test_valid_signal_zero_allowed(self, mock_kill):
        """Signal 0 (probe) should be accepted."""
        success, msg = ProcessManager.kill_process(1234, 0)
        self.assertTrue(success)
        mock_kill.assert_called_once_with(1234, 0)

    @patch('os.kill')
    def test_valid_signal_64_allowed(self, mock_kill):
        """Signal 64 (SIGRTMAX) should be accepted."""
        success, msg = ProcessManager.kill_process(1234, 64)
        self.assertTrue(success)
        mock_kill.assert_called_once_with(1234, 64)


class TestDiskMountFiltering(unittest.TestCase):
    """Test that /run/media USB mounts are not filtered out."""

    @patch('subprocess.run')
    def test_run_media_mounts_included(self, mock_run):
        """USB drives mounted at /run/media should be visible."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Mounted on                       1B-blocks       Used      Avail Use% Filesystem\n"
                "/                             500000000000 50000000000 450000000000  10% /dev/sda1\n"
                "/run/media/user/USBDRIVE      32000000000  16000000000 16000000000  50% /dev/sdb1\n"
                "/run/user/1000                   10000000     1000000    9000000  10% tmpfs\n"
            ),
        )
        results = DiskManager.get_all_mount_points()
        
        mount_points = [r.mount_point for r in results]
        # / and /run/media/user/USBDRIVE should be included
        self.assertIn("/", mount_points)
        self.assertIn("/run/media/user/USBDRIVE", mount_points)
        # /run/user/1000 (tmpfs) should be excluded
        self.assertNotIn("/run/user/1000", mount_points)

    @patch('subprocess.run')
    def test_dev_proc_sys_still_excluded(self, mock_run):
        """Virtual mounts should still be filtered."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Mounted on    1B-blocks  Used  Avail Use% Filesystem\n"
                "/         500000000000 50000000000 450000000000  10% /dev/sda1\n"
                "/dev      10000000   0      10000000   0% devtmpfs\n"
                "/sys      10000000   0      10000000   0% sysfs\n"
                "/proc     10000000   0      10000000   0% proc\n"
            ),
        )
        results = DiskManager.get_all_mount_points()
        mount_points = [r.mount_point for r in results]
        self.assertIn("/", mount_points)
        self.assertNotIn("/dev", mount_points)
        self.assertNotIn("/sys", mount_points)
        self.assertNotIn("/proc", mount_points)


if __name__ == '__main__':
    unittest.main()
