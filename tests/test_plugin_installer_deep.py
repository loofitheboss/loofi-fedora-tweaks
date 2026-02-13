"""Tests for utils.plugin_installer — PluginInstaller (93 miss, 65.6%)."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestInstallerResult(unittest.TestCase):
    def test_defaults(self):
        from utils.plugin_installer import InstallerResult
        r = InstallerResult(success=True, plugin_id="test")
        self.assertTrue(r.success)
        self.assertIsNone(r.version)
        self.assertIsNone(r.error)
        self.assertIsNone(r.data)


class TestLoadSaveState(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_load_empty(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        self.assertEqual(inst._load_state(), {})

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_save_and_load(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        state = {"test-plugin": {"version": "1.0", "enabled": True}}
        self.assertTrue(inst._save_state(state))
        loaded = inst._load_state()
        self.assertEqual(loaded["test-plugin"]["version"], "1.0")

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_load_corrupt_json(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        inst.state_file.write_text("not json {{{")
        self.assertEqual(inst._load_state(), {})


class TestExtractArchive(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_extract_valid(self, mock_iv, mock_mp):
        import tarfile

        from utils.plugin_installer import PluginInstaller

        inst = PluginInstaller(self.plugins_dir)
        # Create a valid tar.gz
        archive = Path(self.tmpdir) / "test.tar.gz"
        content_dir = Path(self.tmpdir) / "content"
        content_dir.mkdir()
        (content_dir / "plugin.py").write_text("# plugin")
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(content_dir / "plugin.py", arcname="plugin.py")
        dest = Path(self.tmpdir) / "extracted"
        self.assertTrue(inst._extract_archive(archive, dest))
        self.assertTrue((dest / "plugin.py").exists())

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_extract_invalid(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        bad = Path(self.tmpdir) / "bad.tar.gz"
        bad.write_text("not a tar")
        dest = Path(self.tmpdir) / "extracted"
        self.assertFalse(inst._extract_archive(bad, dest))


class TestValidateManifest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_valid_manifest(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        pdir = Path(self.tmpdir) / "test-plugin"
        pdir.mkdir()
        manifest = {
            "id": "test-plugin", "name": "Test", "version": "1.0.0",
            "description": "desc", "author": "auth", "entrypoint": "plugin.py"
        }
        (pdir / "manifest.json").write_text(json.dumps(manifest))
        result = inst.validate_manifest(pdir)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "test-plugin")

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_missing_manifest(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        pdir = Path(self.tmpdir) / "empty"
        pdir.mkdir()
        self.assertIsNone(inst.validate_manifest(pdir))

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_missing_required_fields(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        pdir = Path(self.tmpdir) / "bad"
        pdir.mkdir()
        (pdir / "manifest.json").write_text('{"id": "x"}')
        self.assertIsNone(inst.validate_manifest(pdir))

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_invalid_json(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        pdir = Path(self.tmpdir) / "badjson"
        pdir.mkdir()
        (pdir / "manifest.json").write_text("not json {{{")
        self.assertIsNone(inst.validate_manifest(pdir))

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_missing_entrypoint(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        pdir = Path(self.tmpdir) / "noentry"
        pdir.mkdir()
        manifest = {
            "id": "x", "name": "X", "version": "1.0",
            "description": "d", "author": "a"
        }
        (pdir / "manifest.json").write_text(json.dumps(manifest))
        self.assertIsNone(inst.validate_manifest(pdir))


class TestUninstall(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_uninstall_success(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        pdir = self.plugins_dir / "test-plugin"
        pdir.mkdir()
        (pdir / "plugin.py").write_text("# code")
        # Save state
        inst._save_state({"test-plugin": {"version": "1.0", "enabled": True}})
        result = inst.uninstall("test-plugin")
        self.assertTrue(result.success)
        self.assertFalse(pdir.exists())

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_uninstall_not_installed(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        result = inst.uninstall("nonexistent")
        self.assertFalse(result.success)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_uninstall_with_backup(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        pdir = self.plugins_dir / "test-plugin"
        pdir.mkdir()
        manifest = {
            "id": "test-plugin", "name": "Test", "version": "1.0.0",
            "description": "d", "author": "a", "entrypoint": "plugin.py"
        }
        (pdir / "manifest.json").write_text(json.dumps(manifest))
        (pdir / "plugin.py").write_text("# code")
        result = inst.uninstall("test-plugin", create_backup=True)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.backup_path)


class TestRollback(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_no_backup(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        result = inst.rollback("nonexistent")
        self.assertFalse(result.success)
        self.assertIn("No backup", result.error)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_rollback_success(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        # Create backup
        backup = inst.backups_dir / "test-plugin-1.0.0"
        backup.mkdir(parents=True)
        manifest = {
            "id": "test-plugin", "name": "Test", "version": "1.0.0",
            "description": "d", "author": "a", "entrypoint": "plugin.py"
        }
        (backup / "manifest.json").write_text(json.dumps(manifest))
        (backup / "plugin.py").write_text("# code")

        result = inst.rollback("test-plugin")
        self.assertTrue(result.success)


class TestCheckUpdate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_not_installed(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        result = inst.check_update("nonexistent")
        self.assertFalse(result.success)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_update_available(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        inst._save_state({"test": {"version": "1.0.0"}})
        meta = MagicMock()
        meta.version = "2.0.0"
        inst.marketplace.get_plugin_info.return_value = meta
        result = inst.check_update("test")
        self.assertTrue(result.success)
        self.assertTrue(result.data["update_available"])

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_no_update(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        inst._save_state({"test": {"version": "1.0.0"}})
        meta = MagicMock()
        meta.version = "1.0.0"
        inst.marketplace.get_plugin_info.return_value = meta
        result = inst.check_update("test")
        self.assertTrue(result.success)
        self.assertFalse(result.data["update_available"])

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_not_in_marketplace(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        inst._save_state({"test": {"version": "1.0.0"}})
        inst.marketplace.get_plugin_info.return_value = None
        result = inst.check_update("test")
        self.assertFalse(result.success)


class TestListInstalled(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_empty(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        result = inst.list_installed()
        self.assertTrue(result.success)
        self.assertEqual(result.data, [])

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_with_plugins(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        # Create a plugin dir with valid manifest
        pdir = self.plugins_dir / "test-plugin"
        pdir.mkdir()
        manifest = {
            "id": "test-plugin", "name": "Test", "version": "1.0.0",
            "description": "d", "author": "a", "entrypoint": "plugin.py"
        }
        (pdir / "manifest.json").write_text(json.dumps(manifest))
        result = inst.list_installed()
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)


class TestInstallAlreadyInstalled(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_already_installed(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        (self.plugins_dir / "test-plugin").mkdir()
        result = inst.install("test-plugin")
        self.assertFalse(result.success)
        self.assertIn("already installed", result.error.lower())

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_not_in_marketplace(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        inst.marketplace.get_plugin_info.return_value = None
        result = inst.install("nonexistent")
        self.assertFalse(result.success)
        self.assertIn("not found", result.error.lower())


class TestUpdateNotInstalled(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.tmpdir) / "plugins"
        self.plugins_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("utils.plugin_installer.PluginMarketplace")
    @patch("utils.plugin_installer.IntegrityVerifier")
    def test_not_installed(self, mock_iv, mock_mp):
        from utils.plugin_installer import PluginInstaller
        inst = PluginInstaller(self.plugins_dir)
        result = inst.update("nonexistent")
        self.assertFalse(result.success)
        self.assertIn("not installed", result.error.lower())


if __name__ == "__main__":
    unittest.main()
