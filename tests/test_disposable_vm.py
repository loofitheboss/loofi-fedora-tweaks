"""Tests for utils/disposable_vm.py"""
import sys
import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Pre-mock PyQt6 for import chain: containers -> install_hints -> services.system -> command_runner -> PyQt6
for _mod in ('PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'):
    sys.modules.setdefault(_mod, MagicMock())

from utils.disposable_vm import DisposableVMManager


class TestDisposableVMPaths(unittest.TestCase):
    """Tests for storage directory and base image path helpers."""

    @patch('utils.disposable_vm.os.makedirs')
    @patch('utils.disposable_vm.os.path.expanduser', return_value="/home/test/.local/share/loofi-vms/disposable")
    def test_get_storage_dir(self, mock_expand, mock_makedirs):
        result = DisposableVMManager._get_storage_dir()
        self.assertEqual(result, "/home/test/.local/share/loofi-vms/disposable")
        mock_makedirs.assert_called_once()

    @patch('utils.disposable_vm.DisposableVMManager._get_storage_dir', return_value="/tmp/vms")
    def test_get_base_image_path(self, mock_storage):
        result = DisposableVMManager.get_base_image_path()
        self.assertIn("loofi-disposable-base.qcow2", result)
        self.assertTrue(result.startswith("/tmp/vms"))


class TestBaseImageAvailable(unittest.TestCase):
    """Tests for is_base_image_available()."""

    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.os.path.isfile', return_value=True)
    def test_base_image_exists(self, mock_isfile, mock_path):
        self.assertTrue(DisposableVMManager.is_base_image_available())

    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.os.path.isfile', return_value=False)
    def test_base_image_missing(self, mock_isfile, mock_path):
        self.assertFalse(DisposableVMManager.is_base_image_available())


class TestCreateBaseImage(unittest.TestCase):
    """Tests for create_base_image()."""

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.os.path.isfile', return_value=True)
    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_base_image_success(self, mock_which, mock_path, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = DisposableVMManager.create_base_image("/tmp/fedora.iso", size_gb=20)
        self.assertTrue(result.success)
        self.assertIn("Base image created", result.message)

    @patch('utils.disposable_vm.shutil.which', return_value=None)
    def test_create_base_image_no_qemu_img(self, mock_which):
        result = DisposableVMManager.create_base_image("/tmp/fedora.iso")
        self.assertFalse(result.success)
        self.assertIn("qemu-img", result.message)

    @patch('utils.disposable_vm.os.path.isfile', return_value=False)
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_base_image_iso_not_found(self, mock_which, mock_isfile):
        result = DisposableVMManager.create_base_image("/nonexistent.iso")
        self.assertFalse(result.success)
        self.assertIn("ISO file not found", result.message)

    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_base_image_empty_iso(self, mock_which):
        result = DisposableVMManager.create_base_image("")
        self.assertFalse(result.success)

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.os.path.isfile', return_value=True)
    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_base_image_command_failure(self, mock_which, mock_path, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="Error", stdout="")
        result = DisposableVMManager.create_base_image("/tmp/fedora.iso")
        self.assertFalse(result.success)
        self.assertIn("Failed to create", result.message)

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.os.path.isfile', return_value=True)
    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_base_image_timeout(self, mock_which, mock_path, mock_isfile, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="qemu-img", timeout=30)
        result = DisposableVMManager.create_base_image("/tmp/fedora.iso")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.os.path.isfile', return_value=True)
    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_base_image_os_error(self, mock_which, mock_path, mock_isfile, mock_run):
        mock_run.side_effect = OSError("disk full")
        result = DisposableVMManager.create_base_image("/tmp/fedora.iso")
        self.assertFalse(result.success)


class TestCreateSnapshotOverlay(unittest.TestCase):
    """Tests for create_snapshot_overlay()."""

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.DisposableVMManager._get_storage_dir', return_value="/tmp/vms")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_overlay_success(self, mock_which, mock_storage, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = DisposableVMManager.create_snapshot_overlay("/tmp/base.qcow2")
        self.assertTrue(result.endswith(".qcow2"))
        self.assertIn("disposable-", result)

    @patch('utils.disposable_vm.shutil.which', return_value=None)
    def test_create_overlay_no_qemu_img(self, mock_which):
        result = DisposableVMManager.create_snapshot_overlay("/tmp/base.qcow2")
        self.assertEqual(result, "")

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.DisposableVMManager._get_storage_dir', return_value="/tmp/vms")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_overlay_command_failure(self, mock_which, mock_storage, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        result = DisposableVMManager.create_snapshot_overlay("/tmp/base.qcow2")
        self.assertEqual(result, "")

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.DisposableVMManager._get_storage_dir', return_value="/tmp/vms")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_overlay_timeout(self, mock_which, mock_storage, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="qemu-img", timeout=15)
        result = DisposableVMManager.create_snapshot_overlay("/tmp/base.qcow2")
        self.assertEqual(result, "")

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.DisposableVMManager._get_storage_dir', return_value="/tmp/vms")
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/qemu-img")
    def test_create_overlay_os_error(self, mock_which, mock_storage, mock_run):
        mock_run.side_effect = OSError("fail")
        result = DisposableVMManager.create_snapshot_overlay("/tmp/base.qcow2")
        self.assertEqual(result, "")


class TestLaunchDisposable(unittest.TestCase):
    """Tests for launch_disposable()."""

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.shutil.which')
    @patch('utils.disposable_vm.DisposableVMManager.create_snapshot_overlay', return_value="/tmp/overlay.qcow2")
    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.DisposableVMManager.is_base_image_available', return_value=True)
    def test_launch_success(self, mock_base, mock_path, mock_overlay, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0)
        result = DisposableVMManager.launch_disposable(name="testvm")
        self.assertTrue(result.success)
        self.assertIn("testvm", result.message)

    @patch('utils.disposable_vm.DisposableVMManager.is_base_image_available', return_value=False)
    def test_launch_no_base_image(self, mock_base):
        result = DisposableVMManager.launch_disposable()
        self.assertFalse(result.success)
        self.assertIn("No base image", result.message)

    @patch('utils.disposable_vm.shutil.which', return_value=None)
    @patch('utils.disposable_vm.DisposableVMManager.is_base_image_available', return_value=True)
    def test_launch_no_virsh(self, mock_base, mock_which):
        result = DisposableVMManager.launch_disposable()
        self.assertFalse(result.success)
        self.assertIn("virsh", result.message)

    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/virsh")
    @patch('utils.disposable_vm.DisposableVMManager.is_base_image_available', return_value=True)
    def test_launch_invalid_name(self, mock_base, mock_which):
        result = DisposableVMManager.launch_disposable(name="bad name!@#")
        self.assertFalse(result.success)
        self.assertIn("Invalid VM name", result.message)

    @patch('utils.disposable_vm.shutil.which')
    @patch('utils.disposable_vm.DisposableVMManager.create_snapshot_overlay', return_value="")
    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.DisposableVMManager.is_base_image_available', return_value=True)
    def test_launch_overlay_failure(self, mock_base, mock_path, mock_overlay, mock_which):
        mock_which.return_value = "/usr/bin/virsh"
        result = DisposableVMManager.launch_disposable(name="testvm")
        self.assertFalse(result.success)
        self.assertIn("overlay", result.message.lower())

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.shutil.which')
    @patch('utils.disposable_vm.DisposableVMManager.create_snapshot_overlay', return_value="/tmp/overlay.qcow2")
    @patch('utils.disposable_vm.DisposableVMManager.get_base_image_path', return_value="/tmp/base.qcow2")
    @patch('utils.disposable_vm.DisposableVMManager.is_base_image_available', return_value=True)
    def test_launch_timeout(self, mock_base, mock_path, mock_overlay, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virt-install", timeout=60)
        result = DisposableVMManager.launch_disposable(name="testvm")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)


class TestCleanupDisposable(unittest.TestCase):
    """Tests for cleanup_disposable()."""

    @patch('utils.disposable_vm.os.remove')
    @patch('utils.disposable_vm.os.path.isfile', return_value=True)
    def test_cleanup_success(self, mock_isfile, mock_remove):
        result = DisposableVMManager.cleanup_disposable("/tmp/overlay.qcow2")
        self.assertTrue(result.success)
        mock_remove.assert_called_once_with("/tmp/overlay.qcow2")

    def test_cleanup_empty_path(self):
        result = DisposableVMManager.cleanup_disposable("")
        self.assertFalse(result.success)

    @patch('utils.disposable_vm.os.path.isfile', return_value=False)
    def test_cleanup_file_not_found(self, mock_isfile):
        result = DisposableVMManager.cleanup_disposable("/tmp/nonexistent.qcow2")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch('utils.disposable_vm.os.remove')
    @patch('utils.disposable_vm.os.path.isfile', return_value=True)
    def test_cleanup_os_error(self, mock_isfile, mock_remove):
        mock_remove.side_effect = OSError("permission denied")
        result = DisposableVMManager.cleanup_disposable("/tmp/overlay.qcow2")
        self.assertFalse(result.success)
        self.assertIn("Failed to delete", result.message)


class TestListActiveDisposables(unittest.TestCase):
    """Tests for list_active_disposables()."""

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/virsh")
    def test_list_active_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="disposable-abc12345\ndisposable-def67890\nmy-other-vm\n"
        )
        result = DisposableVMManager.list_active_disposables()
        self.assertEqual(len(result), 2)
        self.assertTrue(all(n.startswith("disposable-") for n in result))

    @patch('utils.disposable_vm.shutil.which', return_value=None)
    def test_list_active_no_virsh(self, mock_which):
        result = DisposableVMManager.list_active_disposables()
        self.assertEqual(result, [])

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/virsh")
    def test_list_active_command_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = DisposableVMManager.list_active_disposables()
        self.assertEqual(result, [])

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/virsh")
    def test_list_active_timeout(self, mock_which, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virsh", timeout=10)
        result = DisposableVMManager.list_active_disposables()
        self.assertEqual(result, [])

    @patch('utils.disposable_vm.subprocess.run')
    @patch('utils.disposable_vm.shutil.which', return_value="/usr/bin/virsh")
    def test_list_active_empty(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")
        result = DisposableVMManager.list_active_disposables()
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
