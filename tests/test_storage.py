"""
Tests for StorageManager (v17.0 Atlas).
Covers block device listing, SMART health, mount listing,
filesystem check, SSD trim, and usage summary.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.storage import (
    StorageManager, BlockDevice, SmartHealth,
    MountInfo, StorageResult,
)


SAMPLE_LSBLK_JSON = json.dumps({
    "blockdevices": [
        {
            "name": "sda", "path": "/dev/sda", "size": "500G",
            "type": "disk", "fstype": None, "mountpoint": None,
            "label": None, "uuid": None, "model": "Samsung SSD 870",
            "serial": "S123", "ro": False, "rm": False, "hotplug": False,
            "children": [
                {
                    "name": "sda1", "path": "/dev/sda1", "size": "512M",
                    "type": "part", "fstype": "vfat", "mountpoint": "/boot/efi",
                    "label": "EFI", "uuid": "1234", "model": None,
                    "serial": None, "ro": False, "rm": False, "hotplug": False,
                },
                {
                    "name": "sda2", "path": "/dev/sda2", "size": "499.5G",
                    "type": "part", "fstype": "ext4", "mountpoint": "/",
                    "label": "root", "uuid": "5678", "model": None,
                    "serial": None, "ro": False, "rm": False, "hotplug": False,
                },
            ]
        },
        {
            "name": "loop0", "path": "/dev/loop0", "size": "100M",
            "type": "disk", "fstype": "squashfs", "mountpoint": "/snap/core",
            "label": None, "uuid": None, "model": None,
            "serial": None, "ro": True, "rm": False, "hotplug": False,
        },
    ]
})


class TestStorageListBlockDevices(unittest.TestCase):
    """Tests for list_block_devices()."""

    @patch('utils.storage.subprocess.run')
    def test_list_all_devices(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_LSBLK_JSON
        )
        devices = StorageManager.list_block_devices()
        # sda + sda1 + sda2 + loop0 = 4
        self.assertEqual(len(devices), 4)
        self.assertEqual(devices[0].name, "sda")
        self.assertEqual(devices[0].device_type, "disk")
        self.assertEqual(devices[0].model, "Samsung SSD 870")

    @patch('utils.storage.subprocess.run')
    def test_list_disks_excludes_loop(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_LSBLK_JSON
        )
        disks = StorageManager.list_disks()
        self.assertEqual(len(disks), 1)
        self.assertEqual(disks[0].name, "sda")

    @patch('utils.storage.subprocess.run')
    def test_list_partitions(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_LSBLK_JSON
        )
        parts = StorageManager.list_partitions()
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0].fstype, "vfat")
        self.assertEqual(parts[1].fstype, "ext4")

    @patch('utils.storage.subprocess.run')
    def test_lsblk_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        devices = StorageManager.list_block_devices()
        self.assertEqual(devices, [])

    @patch('utils.storage.subprocess.run')
    def test_lsblk_invalid_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")
        devices = StorageManager.list_block_devices()
        self.assertEqual(devices, [])

    @patch('utils.storage.subprocess.run')
    def test_lsblk_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("lsblk", 10)
        devices = StorageManager.list_block_devices()
        self.assertEqual(devices, [])


class TestStorageSmartHealth(unittest.TestCase):
    """Tests for get_smart_health()."""

    SMARTCTL_OUTPUT = """
smartctl 7.3 2022-02-28 r5338 [x86_64-linux-6.5.0]
=== START OF INFORMATION SECTION ===
Device Model:     Samsung SSD 870 EVO 500GB
Serial Number:    S1234567890
=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      RAW_VALUE
  5 Reallocated_Sector_Ct   0x0033   100   100   010    Pre-fail  0
194 Temperature_Celsius     0x0022   070   060   000    Old_age   30
  9 Power_On_Hours          0x0032   099   099   000    Old_age   1234
"""

    @patch('utils.storage.subprocess.run')
    def test_smart_health_parsed(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=self.SMARTCTL_OUTPUT
        )
        health = StorageManager.get_smart_health("/dev/sda")
        self.assertEqual(health.device, "/dev/sda")
        self.assertEqual(health.model, "Samsung SSD 870 EVO 500GB")
        self.assertEqual(health.serial, "S1234567890")
        self.assertTrue(health.health_passed)
        self.assertEqual(health.temperature_c, 30)
        self.assertEqual(health.power_on_hours, 1234)
        self.assertEqual(health.reallocated_sectors, 0)

    @patch('utils.storage.subprocess.run')
    def test_smart_health_failed(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="SMART overall-health self-assessment test result: FAILED\n"
        )
        health = StorageManager.get_smart_health("/dev/sda")
        self.assertFalse(health.health_passed)

    @patch('utils.storage.subprocess.run')
    def test_smart_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("smartctl", 30)
        health = StorageManager.get_smart_health("/dev/sda")
        self.assertEqual(health.model, "")

    @patch('utils.storage.subprocess.run')
    def test_smart_oserror(self, mock_run):
        mock_run.side_effect = OSError("smartctl not found")
        health = StorageManager.get_smart_health("/dev/sda")
        self.assertEqual(health.device, "/dev/sda")
        self.assertEqual(health.model, "")


class TestStorageMounts(unittest.TestCase):
    """Tests for list_mounts()."""

    DF_OUTPUT = (
        "Filesystem     Mounted on     Type     Size  Used Avail Use%\n"
        "/dev/sda2      /              ext4     460G  120G  320G  28%\n"
        "/dev/sda1      /boot/efi      vfat     510M  5.0M  505M   1%\n"
        "tmpfs          /tmp           tmpfs    8.0G  100M  7.9G   2%\n"
    )

    @patch('utils.storage.subprocess.run')
    def test_list_mounts_filters_tmpfs(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=self.DF_OUTPUT
        )
        mounts = StorageManager.list_mounts()
        # tmpfs is filtered because source doesn't start with /dev
        self.assertEqual(len(mounts), 2)
        self.assertEqual(mounts[0].target, "/")
        self.assertEqual(mounts[1].target, "/boot/efi")

    @patch('utils.storage.subprocess.run')
    def test_list_mounts_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        mounts = StorageManager.list_mounts()
        self.assertEqual(mounts, [])

    @patch('utils.storage.subprocess.run')
    def test_list_mounts_empty(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Filesystem     Mounted on     Type     Size  Used Avail Use%\n"
        )
        mounts = StorageManager.list_mounts()
        self.assertEqual(mounts, [])


class TestStorageFilesystemCheck(unittest.TestCase):
    """Tests for check_filesystem()."""

    @patch('utils.storage.subprocess.run')
    def test_fsck_clean(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="/dev/sda2: clean", stderr=""
        )
        result = StorageManager.check_filesystem("/dev/sda2")
        self.assertTrue(result.success)
        self.assertIn("OK", result.message)

    @patch('utils.storage.subprocess.run')
    def test_fsck_issues(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=4, stdout="", stderr="Errors found"
        )
        result = StorageManager.check_filesystem("/dev/sda2")
        self.assertFalse(result.success)

    @patch('utils.storage.subprocess.run')
    def test_fsck_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("fsck", 120)
        result = StorageManager.check_filesystem("/dev/sda2")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)

    @patch('utils.storage.subprocess.run')
    def test_fsck_oserror(self, mock_run):
        mock_run.side_effect = OSError("fsck not found")
        result = StorageManager.check_filesystem("/dev/sda2")
        self.assertFalse(result.success)


class TestStorageTrim(unittest.TestCase):
    """Tests for trim_ssd()."""

    @patch('utils.storage.subprocess.run')
    def test_trim_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="/: 1.5 GiB trimmed\n/boot/efi: 0 B trimmed",
            stderr=""
        )
        result = StorageManager.trim_ssd()
        self.assertTrue(result.success)
        self.assertIn("Trim complete", result.message)

    @patch('utils.storage.subprocess.run')
    def test_trim_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fstrim: failed"
        )
        result = StorageManager.trim_ssd()
        self.assertFalse(result.success)

    @patch('utils.storage.subprocess.run')
    def test_trim_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("fstrim", 120)
        result = StorageManager.trim_ssd()
        self.assertFalse(result.success)


class TestStorageUsageSummary(unittest.TestCase):
    """Tests for get_usage_summary()."""

    @patch('utils.storage.subprocess.run')
    def test_usage_summary(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Filesystem     Mounted on     Type     Size  Used Avail Use%\n"
                "/dev/sda2      /              ext4     460G  120G  320G  28%\n"
            )
        )
        summary = StorageManager.get_usage_summary()
        self.assertIn("/", summary)
        self.assertIn("120G", summary["/"])

    @patch('utils.storage.subprocess.run')
    def test_usage_summary_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        summary = StorageManager.get_usage_summary()
        self.assertEqual(summary, {})


class TestStorageDataclasses(unittest.TestCase):
    """Tests for dataclass to_dict methods."""

    def test_block_device_to_dict(self):
        bd = BlockDevice(
            name="sda", path="/dev/sda", size="500G",
            device_type="disk", model="Samsung"
        )
        d = bd.to_dict()
        self.assertEqual(d["name"], "sda")
        self.assertEqual(d["type"], "disk")

    def test_smart_health_to_dict(self):
        sh = SmartHealth(device="/dev/sda", model="Test", health_passed=True)
        d = sh.to_dict()
        self.assertEqual(d["model"], "Test")
        self.assertTrue(d["health_passed"])

    def test_mount_info_to_dict(self):
        mi = MountInfo(source="/dev/sda2", target="/", fstype="ext4", options="")
        d = mi.to_dict()
        self.assertEqual(d["source"], "/dev/sda2")
        self.assertEqual(d["fstype"], "ext4")

    def test_storage_result(self):
        r = StorageResult(success=True, message="OK")
        self.assertTrue(r.success)


if __name__ == '__main__':
    unittest.main()
