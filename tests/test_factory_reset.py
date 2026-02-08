"""Tests for factory reset and backup management."""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.factory_reset import FactoryReset, BackupInfo


class TestCreateBackup(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._config = os.path.join(self._tmpdir, "config")
        self._backup = os.path.join(self._config, "backups")
        os.makedirs(self._config)
        # Create some fake config files
        for name in ["settings.json", "notifications.json", "profiles.json"]:
            with open(os.path.join(self._config, name), "w") as f:
                json.dump({"test": True}, f)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    @patch("utils.factory_reset.CONFIG_DIR")
    @patch("utils.factory_reset.BACKUP_DIR")
    def test_create_backup_success(self, mock_backup_dir, mock_config_dir):
        mock_config_dir.__str__ = lambda s: self._config
        mock_backup_dir.__str__ = lambda s: self._backup
        # Patch at module level
        with patch("utils.factory_reset.CONFIG_DIR", self._config), \
             patch("utils.factory_reset.BACKUP_DIR", self._backup):
            result = FactoryReset.create_backup("test_backup")
            self.assertTrue(result.success)
            self.assertIn("test_backup", result.message)

    @patch("utils.factory_reset.CONFIG_DIR")
    @patch("utils.factory_reset.BACKUP_DIR")
    def test_auto_name(self, mock_backup_dir, mock_config_dir):
        with patch("utils.factory_reset.CONFIG_DIR", self._config), \
             patch("utils.factory_reset.BACKUP_DIR", self._backup):
            result = FactoryReset.create_backup()
            self.assertTrue(result.success)
            self.assertIn("backup_", result.message)


class TestListBackups(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._backup = os.path.join(self._tmpdir, "backups")
        os.makedirs(self._backup)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_empty_backup_dir(self):
        with patch("utils.factory_reset.BACKUP_DIR", self._backup):
            backups = FactoryReset.list_backups()
            self.assertEqual(len(backups), 0)

    def test_list_with_backups(self):
        # Create fake backup dirs
        for name in ["backup1", "backup2"]:
            bp = os.path.join(self._backup, name)
            os.makedirs(bp)
            with open(os.path.join(bp, "manifest.json"), "w") as f:
                json.dump({"name": name, "created_at": 1000000}, f)
            with open(os.path.join(bp, "settings.json"), "w") as f:
                f.write("{}")

        with patch("utils.factory_reset.BACKUP_DIR", self._backup):
            backups = FactoryReset.list_backups()
            self.assertEqual(len(backups), 2)
            self.assertIsInstance(backups[0], BackupInfo)

    def test_nonexistent_backup_dir(self):
        with patch("utils.factory_reset.BACKUP_DIR", "/nonexistent/path"):
            backups = FactoryReset.list_backups()
            self.assertEqual(len(backups), 0)


class TestRestoreBackup(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._config = os.path.join(self._tmpdir, "config")
        self._backup = os.path.join(self._config, "backups")
        os.makedirs(self._config)
        os.makedirs(self._backup)
        # Create backup
        bp = os.path.join(self._backup, "test_restore")
        os.makedirs(bp)
        with open(os.path.join(bp, "settings.json"), "w") as f:
            json.dump({"restored": True}, f)
        with open(os.path.join(bp, "manifest.json"), "w") as f:
            json.dump({"name": "test_restore"}, f)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_restore_success(self):
        with patch("utils.factory_reset.CONFIG_DIR", self._config), \
             patch("utils.factory_reset.BACKUP_DIR", os.path.join(self._config, "backups")):
            result = FactoryReset.restore_backup("test_restore")
            self.assertTrue(result.success)
            self.assertIn("Restored", result.message)
            # Verify file was copied
            restored = os.path.join(self._config, "settings.json")
            self.assertTrue(os.path.isfile(restored))

    def test_restore_nonexistent(self):
        with patch("utils.factory_reset.BACKUP_DIR", self._backup):
            result = FactoryReset.restore_backup("nonexistent")
            self.assertFalse(result.success)


class TestDeleteBackup(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._backup = os.path.join(self._tmpdir, "backups")
        bp = os.path.join(self._backup, "to_delete")
        os.makedirs(bp)
        with open(os.path.join(bp, "settings.json"), "w") as f:
            f.write("{}")

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_delete_success(self):
        with patch("utils.factory_reset.BACKUP_DIR", self._backup):
            result = FactoryReset.delete_backup("to_delete")
            self.assertTrue(result.success)
            self.assertFalse(os.path.exists(os.path.join(self._backup, "to_delete")))

    def test_delete_nonexistent(self):
        with patch("utils.factory_reset.BACKUP_DIR", self._backup):
            result = FactoryReset.delete_backup("nonexistent")
            self.assertFalse(result.success)


class TestResetConfig(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._config = os.path.join(self._tmpdir, "config")
        self._backup = os.path.join(self._config, "backups")
        os.makedirs(self._config)
        # Create config files
        for name in ["settings.json", "notifications.json"]:
            with open(os.path.join(self._config, name), "w") as f:
                json.dump({"data": True}, f)
        # Create first-run marker
        with open(os.path.join(self._config, "first_run_complete"), "w") as f:
            f.write("")

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_reset_deletes_configs(self):
        with patch("utils.factory_reset.CONFIG_DIR", self._config), \
             patch("utils.factory_reset.BACKUP_DIR", self._backup):
            result = FactoryReset.reset_config()
            self.assertTrue(result.success)
            # Config files should be gone
            self.assertFalse(os.path.isfile(os.path.join(self._config, "settings.json")))
            # First run marker should be gone
            self.assertFalse(os.path.exists(os.path.join(self._config, "first_run_complete")))
            # Auto-backup should exist
            self.assertTrue(os.path.isdir(os.path.join(self._backup, "pre_reset_auto")))


if __name__ == "__main__":
    unittest.main()
