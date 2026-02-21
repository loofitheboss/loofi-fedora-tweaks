"""
Tests for utils/kernel.py — KernelManager.
Covers: get_current_params, get_default_params, add_param, remove_param,
has_param, backup_grub, restore_backup, get_backups, and error handling.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.kernel import KernelManager, KernelResult


# ---------------------------------------------------------------------------
# TestKernelResultDataclass — result dataclass
# ---------------------------------------------------------------------------

class TestKernelResultDataclass(unittest.TestCase):
    """Tests for KernelResult dataclass."""

    def test_kernel_result_creation(self):
        """KernelResult stores all fields."""
        r = KernelResult(success=True, message="OK", output="stdout", backup_path="/tmp/backup")
        self.assertTrue(r.success)
        self.assertEqual(r.message, "OK")
        self.assertEqual(r.output, "stdout")
        self.assertEqual(r.backup_path, "/tmp/backup")

    def test_kernel_result_defaults(self):
        """KernelResult has sensible defaults."""
        r = KernelResult(success=False, message="Error")
        self.assertEqual(r.output, "")
        self.assertIsNone(r.backup_path)


# ---------------------------------------------------------------------------
# TestGetCurrentParams — reading /proc/cmdline
# ---------------------------------------------------------------------------

class TestGetCurrentParams(unittest.TestCase):
    """Tests for get_current_params with mocked /proc/cmdline."""

    @patch('builtins.open', mock_open(read_data='BOOT_IMAGE=/boot/vmlinuz root=UUID=abc ro quiet splash'))
    def test_get_current_params_parses_cmdline(self):
        """get_current_params splits /proc/cmdline into list."""
        params = KernelManager.get_current_params()
        self.assertIn("quiet", params)
        self.assertIn("splash", params)
        self.assertIn("ro", params)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_current_params_handles_error(self, mock_file):
        """get_current_params returns empty list on error."""
        params = KernelManager.get_current_params()
        self.assertEqual(params, [])


# ---------------------------------------------------------------------------
# TestGetDefaultParams — reading GRUB config
# ---------------------------------------------------------------------------

class TestGetDefaultParams(unittest.TestCase):
    """Tests for get_default_params with mocked GRUB config."""

    @patch('builtins.open', mock_open(
        read_data='GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX="quiet splash mitigations=off"\n'
    ))
    def test_get_default_params_parses_grub(self):
        """get_default_params extracts GRUB_CMDLINE_LINUX values."""
        params = KernelManager.get_default_params()
        self.assertIn("quiet", params)
        self.assertIn("splash", params)
        self.assertIn("mitigations=off", params)

    @patch('builtins.open', mock_open(read_data='GRUB_TIMEOUT=5\n'))
    def test_get_default_params_no_cmdline(self):
        """get_default_params returns empty when GRUB_CMDLINE_LINUX absent."""
        params = KernelManager.get_default_params()
        self.assertEqual(params, [])

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_default_params_file_missing(self, mock_file):
        """get_default_params returns empty when grub file missing."""
        params = KernelManager.get_default_params()
        self.assertEqual(params, [])


# ---------------------------------------------------------------------------
# TestHasParam — parameter existence check
# ---------------------------------------------------------------------------

class TestHasParam(unittest.TestCase):
    """Tests for has_param."""

    @patch.object(KernelManager, 'get_current_params',
                  return_value=["quiet", "splash", "intel_iommu=on"])
    def test_has_param_exact_match(self, mock_params):
        """has_param finds exact parameter."""
        self.assertTrue(KernelManager.has_param("quiet"))

    @patch.object(KernelManager, 'get_current_params',
                  return_value=["quiet", "splash", "intel_iommu=on"])
    def test_has_param_key_match(self, mock_params):
        """has_param matches by key prefix."""
        self.assertTrue(KernelManager.has_param("intel_iommu=off"))

    @patch.object(KernelManager, 'get_current_params',
                  return_value=["quiet", "splash"])
    def test_has_param_not_found(self, mock_params):
        """has_param returns False when param not present."""
        self.assertFalse(KernelManager.has_param("mitigations=off"))


# ---------------------------------------------------------------------------
# TestAddParam — adding kernel parameters
# ---------------------------------------------------------------------------

class TestAddParam(unittest.TestCase):
    """Tests for add_param with mocked subprocess."""

    @patch('utils.kernel.subprocess.run')
    @patch.object(KernelManager, 'backup_grub',
                  return_value=KernelResult(True, "Backup OK", backup_path="/tmp/backup"))
    def test_add_param_success(self, mock_backup, mock_run):
        """add_param succeeds when grubby returns 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

        result = KernelManager.add_param("quiet")

        self.assertTrue(result.success)
        self.assertIn("quiet", result.message)
        self.assertIn("Reboot", result.message)

    def test_add_param_empty_string(self):
        """add_param rejects empty parameter."""
        result = KernelManager.add_param("")
        self.assertFalse(result.success)
        self.assertIn("No parameter", result.message)

    @patch('utils.kernel.subprocess.run')
    @patch.object(KernelManager, 'backup_grub',
                  return_value=KernelResult(True, "Backup OK", backup_path="/tmp/backup"))
    def test_add_param_grubby_failure(self, mock_backup, mock_run):
        """add_param returns failure when grubby fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="grubby error")

        result = KernelManager.add_param("invalid_param")

        self.assertFalse(result.success)
        self.assertIn("Failed", result.message)

    @patch.object(KernelManager, 'backup_grub',
                  return_value=KernelResult(False, "Backup failed"))
    def test_add_param_backup_failure(self, mock_backup):
        """add_param returns failure when backup fails."""
        result = KernelManager.add_param("quiet")
        self.assertFalse(result.success)
        self.assertIn("Backup failed", result.message)


# ---------------------------------------------------------------------------
# TestRemoveParam — removing kernel parameters
# ---------------------------------------------------------------------------

class TestRemoveParam(unittest.TestCase):
    """Tests for remove_param with mocked subprocess."""

    @patch('utils.kernel.subprocess.run')
    @patch.object(KernelManager, 'backup_grub',
                  return_value=KernelResult(True, "Backup OK", backup_path="/tmp/backup"))
    def test_remove_param_success(self, mock_backup, mock_run):
        """remove_param succeeds when grubby returns 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

        result = KernelManager.remove_param("quiet")

        self.assertTrue(result.success)
        self.assertIn("Removed", result.message)

    def test_remove_param_empty_string(self):
        """remove_param rejects empty parameter."""
        result = KernelManager.remove_param("")
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestBackupGrub — backup creation
# ---------------------------------------------------------------------------

class TestBackupGrub(unittest.TestCase):
    """Tests for backup_grub with mocked filesystem."""

    @patch('utils.kernel.shutil.copy2')
    @patch('utils.kernel.Path.mkdir')
    def test_backup_grub_success(self, mock_mkdir, mock_copy):
        """backup_grub creates a timestamped backup."""
        result = KernelManager.backup_grub()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.backup_path)
        self.assertIn("grub_backup_", result.backup_path)

    @patch('utils.kernel.shutil.copy2', side_effect=PermissionError("denied"))
    @patch('utils.kernel.Path.mkdir')
    def test_backup_grub_permission_error(self, mock_mkdir, mock_copy):
        """backup_grub returns failure on permission error."""
        result = KernelManager.backup_grub()
        self.assertFalse(result.success)
        self.assertIn("failed", result.message.lower())


# ---------------------------------------------------------------------------
# TestRestoreBackup — backup restoration
# ---------------------------------------------------------------------------

class TestRestoreBackup(unittest.TestCase):
    """Tests for restore_backup with mocked subprocess."""

    def test_restore_backup_nonexistent_file(self):
        """restore_backup returns failure for missing backup."""
        result = KernelManager.restore_backup("/nonexistent/backup")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch('utils.kernel.subprocess.run')
    @patch('utils.kernel.os.path.exists', return_value=True)
    def test_restore_backup_success(self, mock_exists, mock_run):
        """restore_backup succeeds when cp returns 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = KernelManager.restore_backup("/tmp/grub_backup_20250101")

        self.assertTrue(result.success)
        self.assertIn("Reboot", result.message)


# ---------------------------------------------------------------------------
# TestGetBackups — listing available backups
# ---------------------------------------------------------------------------

class TestGetBackups(unittest.TestCase):
    """Tests for get_backups."""

    def test_get_backups_nonexistent_dir(self):
        """get_backups returns empty list when backup dir missing."""
        original = KernelManager.BACKUP_DIR
        try:
            KernelManager.BACKUP_DIR = Path("/nonexistent/backup/dir")
            backups = KernelManager.get_backups()
            self.assertEqual(backups, [])
        finally:
            KernelManager.BACKUP_DIR = original


if __name__ == '__main__':
    unittest.main()
