"""
Tests for utils/devtools.py — Developer tools manager.

Covers:
- DevToolsManager.get_tool_status (pyenv, nvm, rustup, unknown)
- get_all_status
- install_pyenv (already installed, success, failure)
- install_nvm (already installed, success, failure)
- install_rustup (already installed, success, failure)
- _add_shell_config
- get_available_tools
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.devtools import DevToolsManager


class TestGetToolStatus(unittest.TestCase):

    def test_unknown_tool(self):
        installed, msg = DevToolsManager.get_tool_status("nonexistent")
        self.assertFalse(installed)
        self.assertEqual(msg, "Unknown tool")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/pyenv")
    def test_pyenv_installed(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="pyenv 2.3.0\n"
        )
        installed, version = DevToolsManager.get_tool_status("pyenv")
        self.assertTrue(installed)
        self.assertIn("2.3.0", version)

    @patch("shutil.which", return_value=None)
    def test_pyenv_not_installed(self, mock_which):
        installed, version = DevToolsManager.get_tool_status("pyenv")
        self.assertFalse(installed)

    @patch("shutil.which", return_value="/home/user/.cargo/bin/rustup")
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_rustup_installed_version_fail(self, mock_run, mock_which):
        installed, version = DevToolsManager.get_tool_status("rustup")
        self.assertTrue(installed)
        self.assertEqual(version, "installed")

    @patch("pathlib.Path.exists", return_value=True)
    @patch("shutil.which", return_value=None)
    def test_nvm_installed_by_dir(self, mock_which, mock_exists):
        installed, version = DevToolsManager.get_tool_status("nvm")
        self.assertTrue(installed)

    @patch("pathlib.Path.exists", return_value=False)
    @patch("shutil.which", return_value=None)
    def test_nvm_not_installed(self, mock_which, mock_exists):
        installed, version = DevToolsManager.get_tool_status("nvm")
        self.assertFalse(installed)


class TestGetAllStatus(unittest.TestCase):

    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, "not installed"))
    def test_returns_all_tools(self, mock_status):
        result = DevToolsManager.get_all_status()
        self.assertIn("pyenv", result)
        self.assertIn("nvm", result)
        self.assertIn("rustup", result)


class TestInstallPyenv(unittest.TestCase):

    @patch.object(DevToolsManager, "get_tool_status", return_value=(True, "2.3.0"))
    def test_already_installed(self, mock_status):
        r = DevToolsManager.install_pyenv()
        self.assertTrue(r.success)
        self.assertIn("already installed", r.message)

    @patch.object(DevToolsManager, "_download_and_execute")
    @patch.object(DevToolsManager, "_add_shell_config")
    @patch("subprocess.run")
    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, "not installed"))
    def test_success(self, mock_status, mock_run, mock_config, mock_download):
        mock_run.return_value = MagicMock(returncode=0)
        r = DevToolsManager.install_pyenv()
        self.assertTrue(r.success)
        self.assertIn("PyEnv installed", r.message)

    @patch("subprocess.run", side_effect=__import__("subprocess").CalledProcessError(1, "dnf"))
    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, ""))
    def test_failure(self, mock_status, mock_run):
        r = DevToolsManager.install_pyenv()
        self.assertFalse(r.success)

    @patch("subprocess.run", side_effect=OSError("network error"))
    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, ""))
    def test_exception(self, mock_status, mock_run):
        r = DevToolsManager.install_pyenv()
        self.assertFalse(r.success)


class TestInstallNvm(unittest.TestCase):

    @patch.object(DevToolsManager, "get_tool_status", return_value=(True, "installed"))
    def test_already_installed(self, mock_status):
        r = DevToolsManager.install_nvm()
        self.assertTrue(r.success)

    @patch.object(DevToolsManager, "_download_and_execute")
    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, ""))
    def test_success(self, mock_status, mock_download):
        r = DevToolsManager.install_nvm()
        self.assertTrue(r.success)

    @patch("subprocess.run", side_effect=__import__("subprocess").CalledProcessError(1, "bash"))
    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, ""))
    def test_failure(self, mock_status, mock_run):
        r = DevToolsManager.install_nvm()
        self.assertFalse(r.success)


class TestInstallRustup(unittest.TestCase):

    @patch.object(DevToolsManager, "get_tool_status", return_value=(True, "rustup 1.26"))
    def test_already_installed(self, mock_status):
        r = DevToolsManager.install_rustup()
        self.assertTrue(r.success)

    @patch.object(DevToolsManager, "_download_and_execute")
    @patch.object(DevToolsManager, "_add_shell_config")
    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, ""))
    def test_success(self, mock_status, mock_config, mock_download):
        r = DevToolsManager.install_rustup()
        self.assertTrue(r.success)

    @patch("subprocess.run", side_effect=__import__("subprocess").CalledProcessError(1, "bash"))
    @patch.object(DevToolsManager, "get_tool_status", return_value=(False, ""))
    def test_failure(self, mock_status, mock_run):
        r = DevToolsManager.install_rustup()
        self.assertFalse(r.success)


class TestAddShellConfig(unittest.TestCase):

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="# existing config\n")
    @patch("builtins.open", mock_open())
    def test_appends_config(self, mock_exists, mock_read):
        DevToolsManager._add_shell_config("# new config")

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="# new config\n")
    @patch("builtins.open", mock_open())
    def test_avoids_duplicate(self, mock_exists, mock_read):
        # Config already present — should not write again
        DevToolsManager._add_shell_config("# new config")


class TestGetAvailableTools(unittest.TestCase):

    @patch.object(DevToolsManager, "get_tool_status", return_value=(True, "1.0"))
    def test_returns_list(self, mock_status):
        tools = DevToolsManager.get_available_tools()
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 3)
        for t in tools:
            self.assertIn("key", t)
            self.assertIn("name", t)
            self.assertIn("installed", t)
            self.assertTrue(t["installed"])


if __name__ == '__main__':
    unittest.main()
