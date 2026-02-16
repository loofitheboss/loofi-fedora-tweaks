"""
Tests for utils/vscode.py — VSCodeManager.
Coverage-oriented: command detection, extension listing, install,
profile install, settings path, backup, inject settings, available profiles.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.vscode import VSCodeManager


class TestGetVSCodeCommand(unittest.TestCase):
    """Test get_vscode_command."""

    @patch("utils.vscode.shutil.which")
    def test_finds_code(self, mock_which):
        mock_which.side_effect = lambda cmd: "/usr/bin/code" if cmd == "code" else None
        self.assertEqual(VSCodeManager.get_vscode_command(), "code")

    @patch("utils.vscode.shutil.which")
    def test_finds_codium(self, mock_which):
        mock_which.side_effect = lambda cmd: "/usr/bin/codium" if cmd == "codium" else None
        self.assertEqual(VSCodeManager.get_vscode_command(), "codium")

    @patch("utils.vscode.shutil.which")
    @patch("utils.vscode.subprocess.run")
    def test_finds_flatpak(self, mock_run, mock_which):
        mock_which.side_effect = lambda cmd: "/usr/bin/flatpak" if cmd == "flatpak" else None
        mock_run.return_value = MagicMock(returncode=0)
        result = VSCodeManager.get_vscode_command()
        self.assertIn("flatpak run", result)

    @patch("utils.vscode.shutil.which", return_value=None)
    def test_returns_none(self, mock_which):
        self.assertIsNone(VSCodeManager.get_vscode_command())


class TestIsAvailable(unittest.TestCase):
    """Test is_available."""

    @patch.object(VSCodeManager, "get_vscode_command", return_value="code")
    def test_available(self, mock_cmd):
        self.assertTrue(VSCodeManager.is_available())

    @patch.object(VSCodeManager, "get_vscode_command", return_value=None)
    def test_not_available(self, mock_cmd):
        self.assertFalse(VSCodeManager.is_available())


class TestGetInstalledExtensions(unittest.TestCase):
    """Test get_installed_extensions."""

    @patch.object(VSCodeManager, "get_vscode_command", return_value=None)
    def test_no_vscode_returns_empty(self, mock_cmd):
        self.assertEqual(VSCodeManager.get_installed_extensions(), [])

    @patch.object(VSCodeManager, "get_vscode_command", return_value="code")
    @patch("utils.vscode.subprocess.run")
    def test_parses_extensions(self, mock_run, mock_cmd):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ms-python.python\nesbenp.prettier-vscode\n"
        )
        exts = VSCodeManager.get_installed_extensions()
        self.assertEqual(len(exts), 2)
        self.assertIn("ms-python.python", exts)

    @patch.object(VSCodeManager, "get_vscode_command", return_value="code")
    @patch("utils.vscode.subprocess.run")
    def test_nonzero_rc_returns_empty(self, mock_run, mock_cmd):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertEqual(VSCodeManager.get_installed_extensions(), [])

    @patch.object(VSCodeManager, "get_vscode_command", return_value="code")
    @patch("utils.vscode.subprocess.run", side_effect=OSError("fail"))
    def test_exception_returns_empty(self, mock_run, mock_cmd):
        self.assertEqual(VSCodeManager.get_installed_extensions(), [])

    @patch.object(VSCodeManager, "get_vscode_command", return_value="flatpak run com.visualstudio.code")
    @patch("utils.vscode.subprocess.run")
    def test_flatpak_command(self, mock_run, mock_cmd):
        mock_run.return_value = MagicMock(returncode=0, stdout="ext.one\n")
        exts = VSCodeManager.get_installed_extensions()
        self.assertEqual(len(exts), 1)
        # Verify flatpak run used
        args = mock_run.call_args[0][0]
        self.assertIn("flatpak", args)


class TestInstallExtension(unittest.TestCase):
    """Test install_extension."""

    @patch.object(VSCodeManager, "get_vscode_command", return_value=None)
    def test_no_vscode(self, mock_cmd):
        result = VSCodeManager.install_extension("ms-python.python")
        self.assertFalse(result.success)

    @patch.object(VSCodeManager, "get_vscode_command", return_value="code")
    @patch("utils.vscode.subprocess.run")
    def test_install_success(self, mock_run, mock_cmd):
        mock_run.return_value = MagicMock(returncode=0)
        result = VSCodeManager.install_extension("ms-python.python")
        self.assertTrue(result.success)

    @patch.object(VSCodeManager, "get_vscode_command", return_value="code")
    @patch("utils.vscode.subprocess.run")
    def test_install_failure(self, mock_run, mock_cmd):
        mock_run.return_value = MagicMock(returncode=1, stderr="not found")
        result = VSCodeManager.install_extension("bad.ext")
        self.assertFalse(result.success)

    @patch.object(VSCodeManager, "get_vscode_command", return_value="code")
    @patch("utils.vscode.subprocess.run", side_effect=TimeoutError("timeout"))
    def test_install_exception(self, mock_run, mock_cmd):
        result = VSCodeManager.install_extension("slow.ext")
        self.assertFalse(result.success)

    @patch.object(VSCodeManager, "get_vscode_command", return_value="flatpak run com.visualstudio.code")
    @patch("utils.vscode.subprocess.run")
    def test_flatpak_install(self, mock_run, mock_cmd):
        mock_run.return_value = MagicMock(returncode=0)
        result = VSCodeManager.install_extension("ext.id")
        self.assertTrue(result.success)


class TestInstallProfile(unittest.TestCase):
    """Test install_profile."""

    def test_unknown_profile(self):
        result = VSCodeManager.install_profile("nonexistent")
        self.assertFalse(result.success)

    @patch.object(VSCodeManager, "get_installed_extensions", return_value=[
        "ms-python.python", "ms-python.vscode-pylance", "ms-python.debugpy",
        "ms-python.black-formatter", "ms-toolsai.jupyter", "charliermarsh.ruff",
    ])
    def test_all_already_installed(self, mock_exts):
        result = VSCodeManager.install_profile("python")
        self.assertTrue(result.success)
        self.assertIn("6/6", result.message)

    @patch.object(VSCodeManager, "get_installed_extensions", return_value=[])
    @patch.object(VSCodeManager, "install_extension")
    def test_installs_missing(self, mock_install, mock_exts):
        mock_install.return_value = MagicMock(success=True)
        result = VSCodeManager.install_profile("python")
        self.assertTrue(result.success)
        self.assertEqual(mock_install.call_count, 6)

    @patch.object(VSCodeManager, "get_installed_extensions", return_value=[])
    @patch.object(VSCodeManager, "install_extension")
    def test_partial_failure(self, mock_install, mock_exts):
        mock_install.side_effect = [
            MagicMock(success=True),
            MagicMock(success=False),
            MagicMock(success=True),
            MagicMock(success=True),
            MagicMock(success=True),
        ]
        result = VSCodeManager.install_profile("cpp")
        self.assertFalse(result.success)
        self.assertIn("failed", result.message)


class TestGetSettingsPath(unittest.TestCase):
    """Test get_settings_path."""

    def test_finds_standard_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code_dir = Path(tmpdir) / ".config" / "Code" / "User"
            code_dir.mkdir(parents=True)
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                path = VSCodeManager.get_settings_path()
                self.assertIsNotNone(path)
                self.assertIn("Code", str(path))

    def test_returns_none_when_no_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                path = VSCodeManager.get_settings_path()
                self.assertIsNone(path)


class TestBackupSettings(unittest.TestCase):
    """Test backup_settings."""

    @patch.object(VSCodeManager, "get_settings_path", return_value=None)
    def test_no_settings_returns_none(self, mock_path):
        self.assertIsNone(VSCodeManager.backup_settings())

    def test_creates_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Path(tmpdir) / "settings.json"
            settings.write_text('{"foo": "bar"}')
            with patch.object(VSCodeManager, "get_settings_path", return_value=settings):
                backup = VSCodeManager.backup_settings()
                self.assertIsNotNone(backup)
                self.assertTrue(backup.exists())
                self.assertEqual(backup.suffix, ".bak")


class TestInjectSettings(unittest.TestCase):
    """Test inject_settings."""

    @patch.object(VSCodeManager, "get_settings_path", return_value=None)
    def test_no_settings_path(self, mock_path):
        result = VSCodeManager.inject_settings("python")
        self.assertFalse(result.success)

    def test_unknown_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Path(tmpdir) / "settings.json"
            with patch.object(VSCodeManager, "get_settings_path", return_value=settings):
                result = VSCodeManager.inject_settings("nonexistent")
                self.assertFalse(result.success)

    def test_injects_python_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Path(tmpdir) / "settings.json"
            settings.write_text('{"editor.fontSize": 14}')
            with patch.object(VSCodeManager, "get_settings_path", return_value=settings):
                with patch.object(VSCodeManager, "backup_settings"):
                    result = VSCodeManager.inject_settings("python")
                    self.assertTrue(result.success)
                    data = json.loads(settings.read_text())
                    self.assertIn("python.analysis.typeCheckingMode", data)
                    # Original setting preserved
                    self.assertEqual(data["editor.fontSize"], 14)

    def test_creates_new_settings_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Path(tmpdir) / "User" / "settings.json"
            with patch.object(VSCodeManager, "get_settings_path", return_value=settings):
                with patch.object(VSCodeManager, "backup_settings"):
                    result = VSCodeManager.inject_settings("rust")
                    self.assertTrue(result.success)
                    self.assertTrue(settings.exists())

    def test_handles_bad_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Path(tmpdir) / "settings.json"
            settings.write_text("not valid json {{{")
            with patch.object(VSCodeManager, "get_settings_path", return_value=settings):
                with patch.object(VSCodeManager, "backup_settings"):
                    result = VSCodeManager.inject_settings("python")
                    self.assertFalse(result.success)


class TestGetAvailableProfiles(unittest.TestCase):
    """Test get_available_profiles."""

    def test_returns_all_profiles(self):
        profiles = VSCodeManager.get_available_profiles()
        self.assertGreaterEqual(len(profiles), 5)
        keys = [p["key"] for p in profiles]
        self.assertIn("python", keys)
        self.assertIn("rust", keys)
        self.assertIn("web", keys)
        for p in profiles:
            self.assertIn("name", p)
            self.assertIn("extension_count", p)
            self.assertGreater(p["extension_count"], 0)


if __name__ == "__main__":
    unittest.main()
