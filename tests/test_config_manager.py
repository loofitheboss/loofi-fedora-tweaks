"""
Tests for utils/config_manager.py — ConfigManager.
Covers: export/import, load/save, system info, repo gathering,
flatpak listing, presets, and error handling.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.config_manager import ConfigManager
from utils.containers import Result


# ---------------------------------------------------------------------------
# TestEnsureDirs — directory creation
# ---------------------------------------------------------------------------

class TestEnsureDirs(unittest.TestCase):
    """Tests for ensure_dirs directory creation."""

    def test_ensure_dirs_creates_config_dir(self):
        """ensure_dirs creates CONFIG_DIR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_config = ConfigManager.CONFIG_DIR
            original_presets = ConfigManager.PRESETS_DIR
            try:
                ConfigManager.CONFIG_DIR = Path(tmpdir) / "config"
                ConfigManager.PRESETS_DIR = ConfigManager.CONFIG_DIR / "presets"
                ConfigManager.ensure_dirs()
                self.assertTrue(ConfigManager.CONFIG_DIR.exists())
            finally:
                ConfigManager.CONFIG_DIR = original_config
                ConfigManager.PRESETS_DIR = original_presets

    def test_ensure_dirs_creates_presets_dir(self):
        """ensure_dirs creates PRESETS_DIR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_config = ConfigManager.CONFIG_DIR
            original_presets = ConfigManager.PRESETS_DIR
            try:
                ConfigManager.CONFIG_DIR = Path(tmpdir) / "config"
                ConfigManager.PRESETS_DIR = ConfigManager.CONFIG_DIR / "presets"
                ConfigManager.ensure_dirs()
                self.assertTrue(ConfigManager.PRESETS_DIR.exists())
            finally:
                ConfigManager.CONFIG_DIR = original_config
                ConfigManager.PRESETS_DIR = original_presets


# ---------------------------------------------------------------------------
# TestGetConfigVersion — version string
# ---------------------------------------------------------------------------

class TestGetConfigVersion(unittest.TestCase):
    """Tests for get_config_version."""

    def test_version_is_string(self):
        """Config version is a non-empty string."""
        version = ConfigManager.get_config_version()
        self.assertIsInstance(version, str)
        self.assertTrue(len(version) > 0)

    def test_version_format(self):
        """Config version follows semver-like format."""
        version = ConfigManager.get_config_version()
        parts = version.split(".")
        self.assertGreaterEqual(len(parts), 2)


# ---------------------------------------------------------------------------
# TestGetSystemInfo — system information gathering
# ---------------------------------------------------------------------------

class TestGetSystemInfo(unittest.TestCase):
    """Tests for get_system_info with mocked filesystem."""

    @patch('builtins.open', mock_open(read_data='PRETTY_NAME="Fedora Linux 41 (Workstation)"\n'))
    @patch('utils.config_manager.platform')
    def test_get_system_info_full(self, mock_platform):
        """get_system_info gathers hostname, kernel, arch, and os."""
        mock_platform.node.return_value = "testhost"
        mock_platform.release.return_value = "6.12.0"
        mock_platform.machine.return_value = "x86_64"

        info = ConfigManager.get_system_info()

        self.assertEqual(info["hostname"], "testhost")
        self.assertEqual(info["kernel"], "6.12.0")
        self.assertEqual(info["arch"], "x86_64")
        self.assertIn("Fedora", info["os"])

    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('utils.config_manager.platform')
    def test_get_system_info_fallback_os(self, mock_platform, mock_file):
        """get_system_info falls back when os-release unreadable."""
        mock_platform.node.return_value = "host"
        mock_platform.release.return_value = "6.12.0"
        mock_platform.machine.return_value = "x86_64"

        info = ConfigManager.get_system_info()

        self.assertEqual(info["os"], "Fedora Linux")
        self.assertEqual(info["hardware"], "Unknown")


# ---------------------------------------------------------------------------
# TestGatherRepoSettings — DNF repo gathering
# ---------------------------------------------------------------------------

class TestGatherRepoSettings(unittest.TestCase):
    """Tests for gather_repo_settings with mocked subprocess."""

    @patch('utils.config_manager.subprocess.run')
    def test_gather_repo_settings_parses_repos(self, mock_run):
        """Repo settings parse enabled repos from dnf output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="repo id            repo name\nfedora             Fedora 41\nrpmfusion-free     RPM Fusion Free\n"
        )

        repos = ConfigManager.gather_repo_settings()

        self.assertIn("fedora", repos["enabled"])
        self.assertIn("rpmfusion-free", repos["enabled"])

    @patch('utils.config_manager.subprocess.run', side_effect=OSError("dnf not found"))
    def test_gather_repo_settings_handles_error(self, mock_run):
        """gather_repo_settings returns empty on OSError."""
        repos = ConfigManager.gather_repo_settings()
        self.assertEqual(repos["enabled"], [])


# ---------------------------------------------------------------------------
# TestGatherFlatpakApps — flatpak listing
# ---------------------------------------------------------------------------

class TestGatherFlatpakApps(unittest.TestCase):
    """Tests for gather_flatpak_apps with mocked subprocess."""

    @patch('utils.config_manager.subprocess.run')
    def test_gather_flatpak_apps_success(self, mock_run):
        """flatpak apps are parsed from output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="com.spotify.Client\norg.mozilla.firefox\n"
        )

        apps = ConfigManager.gather_flatpak_apps()

        self.assertEqual(len(apps), 2)
        self.assertIn("com.spotify.Client", apps)

    @patch('utils.config_manager.subprocess.run', side_effect=OSError("flatpak not found"))
    def test_gather_flatpak_apps_handles_error(self, mock_run):
        """gather_flatpak_apps returns empty list on OSError."""
        apps = ConfigManager.gather_flatpak_apps()
        self.assertEqual(apps, [])


# ---------------------------------------------------------------------------
# TestExportToFile — file export
# ---------------------------------------------------------------------------

class TestExportToFile(unittest.TestCase):
    """Tests for export_to_file."""

    @patch.object(ConfigManager, 'export_all')
    def test_export_to_file_success(self, mock_export):
        """export_to_file writes valid JSON."""
        mock_export.return_value = {"version": "5.5.0", "settings": {}}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmppath = f.name

        try:
            result = ConfigManager.export_to_file(tmppath)
            self.assertTrue(result.success)
            self.assertIn(tmppath, result.message)

            with open(tmppath) as f:
                data = json.load(f)
            self.assertEqual(data["version"], "5.5.0")
        finally:
            os.unlink(tmppath)

    @patch.object(ConfigManager, 'export_all', side_effect=OSError("permission denied"))
    def test_export_to_file_error(self, mock_export):
        """export_to_file returns error Result on OSError."""
        result = ConfigManager.export_to_file("/nonexistent/path.json")
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestImportFromFile — file import
# ---------------------------------------------------------------------------

class TestImportFromFile(unittest.TestCase):
    """Tests for import_from_file."""

    @patch.object(ConfigManager, 'import_all', return_value=Result(True, "Applied"))
    def test_import_from_file_success(self, mock_import):
        """import_from_file reads JSON and calls import_all."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "5.5.0", "settings": {}}, f)
            tmppath = f.name

        try:
            result = ConfigManager.import_from_file(tmppath)
            self.assertTrue(result.success)
            mock_import.assert_called_once()
        finally:
            os.unlink(tmppath)

    def test_import_from_file_not_found(self):
        """import_from_file handles missing file."""
        result = ConfigManager.import_from_file("/nonexistent/file.json")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    def test_import_from_file_invalid_json(self):
        """import_from_file handles corrupted JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{{{")
            tmppath = f.name

        try:
            result = ConfigManager.import_from_file(tmppath)
            self.assertFalse(result.success)
            self.assertIn("Invalid JSON", result.message)
        finally:
            os.unlink(tmppath)


# ---------------------------------------------------------------------------
# TestImportAll — config application
# ---------------------------------------------------------------------------

class TestImportAll(unittest.TestCase):
    """Tests for import_all config application."""

    def test_import_all_missing_version(self):
        """import_all rejects config without version."""
        result = ConfigManager.import_all({"settings": {}})
        self.assertFalse(result.success)
        self.assertIn("missing version", result.message)

    @patch.object(ConfigManager, 'ensure_dirs')
    def test_import_all_empty_settings(self, mock_dirs):
        """import_all with no applicable settings returns success."""
        config = {"version": "5.5.0", "settings": {}}
        result = ConfigManager.import_all(config)
        self.assertTrue(result.success)
        self.assertIn("No settings changed", result.message)


# ---------------------------------------------------------------------------
# TestSaveAndLoadConfig — runtime config persistence
# ---------------------------------------------------------------------------

class TestSaveAndLoadConfig(unittest.TestCase):
    """Tests for save_config and load_config."""

    def test_save_and_load_config_roundtrip(self):
        """Saved config can be loaded back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = ConfigManager.CONFIG_DIR
            original_file = ConfigManager.CONFIG_FILE
            original_presets = ConfigManager.PRESETS_DIR
            try:
                ConfigManager.CONFIG_DIR = Path(tmpdir)
                ConfigManager.CONFIG_FILE = Path(tmpdir) / "config.json"
                ConfigManager.PRESETS_DIR = Path(tmpdir) / "presets"

                data = {"theme": "dark", "version": "5.5.0"}
                result = ConfigManager.save_config(data)
                self.assertTrue(result)

                loaded = ConfigManager.load_config()
                self.assertEqual(loaded["theme"], "dark")
            finally:
                ConfigManager.CONFIG_DIR = original_dir
                ConfigManager.CONFIG_FILE = original_file
                ConfigManager.PRESETS_DIR = original_presets

    def test_load_config_missing_file(self):
        """load_config returns None when file does not exist."""
        original = ConfigManager.CONFIG_FILE
        try:
            ConfigManager.CONFIG_FILE = Path("/nonexistent/config.json")
            loaded = ConfigManager.load_config()
            self.assertIsNone(loaded)
        finally:
            ConfigManager.CONFIG_FILE = original

    @patch.object(ConfigManager, 'ensure_dirs')
    def test_save_config_returns_false_on_error(self, mock_dirs):
        """save_config returns False when write fails."""
        original_file = ConfigManager.CONFIG_FILE
        try:
            ConfigManager.CONFIG_FILE = Path("/nonexistent/dir/config.json")
            result = ConfigManager.save_config({"test": True})
            self.assertFalse(result)
        finally:
            ConfigManager.CONFIG_FILE = original_file


if __name__ == '__main__':
    unittest.main()
