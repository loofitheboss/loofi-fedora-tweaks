"""Tests for utils/state_teleport.py — Workspace state capture and restore."""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Pre-mock PyQt6 if not installed (transitive dep via services.system → command_runner)
for mod_name in [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui',
    'PyQt6.QtNetwork', 'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets',
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from utils.state_teleport import (  # noqa: E402
    StateTeleportManager,
    WorkspaceState,
    TeleportPackage,
    _SECRET_PATTERNS,
    _CREDENTIAL_FILES,
)


def _make_workspace_state(**overrides) -> WorkspaceState:
    """Create a minimal WorkspaceState for testing."""
    defaults = {
        "workspace_id": "test-id",
        "timestamp": 1700000000.0,
        "hostname": "testhost",
        "vscode_workspace": {"workspace_path": "/tmp/ws", "extensions": []},
        "git_state": {"branch": "main", "status": "clean"},
        "terminal_state": {"cwd": "/tmp", "shell": "bash"},
        "open_files": ["/tmp/ws/main.py"],
        "environment": {"HOME": "/home/test"},
    }
    defaults.update(overrides)
    return WorkspaceState(**defaults)


class TestCaptureVscodeState(unittest.TestCase):
    """Tests for capture_vscode_state."""

    @patch('utils.state_teleport.shutil.which', return_value=None)
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    @patch('utils.state_teleport.os.listdir', return_value=[])
    def test_no_vscode_returns_empty_state(self, _mock_listdir, _mock_isfile, _mock_which):
        result = StateTeleportManager.capture_vscode_state("/tmp/ws")
        self.assertEqual(result["workspace_path"], "/tmp/ws")
        self.assertEqual(result["extensions"], [])
        self.assertIsInstance(result["settings_json"], dict)

    @patch('utils.state_teleport.shutil.which', return_value="/usr/bin/code")
    @patch('utils.state_teleport.subprocess.run')
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    @patch('utils.state_teleport.os.listdir', return_value=[])
    def test_lists_extensions_via_code_cli(self, _mock_listdir, _mock_isfile, mock_run, _mock_which):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ext1\next2\next3\n"
        )
        result = StateTeleportManager.capture_vscode_state("/tmp/ws")
        self.assertEqual(result["extensions"], ["ext1", "ext2", "ext3"])

    @patch('utils.state_teleport.shutil.which', return_value="/usr/bin/code")
    @patch('utils.state_teleport.subprocess.run')
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    @patch('utils.state_teleport.os.listdir', return_value=[])
    def test_code_cli_timeout(self, _mock_listdir, _mock_isfile, mock_run, _mock_which):
        mock_run.side_effect = OSError("timeout")
        result = StateTeleportManager.capture_vscode_state("/tmp/ws")
        self.assertEqual(result["extensions"], [])

    @patch('utils.state_teleport.shutil.which', return_value=None)
    @patch('utils.state_teleport.os.path.isfile', return_value=True)
    @patch('utils.state_teleport.os.listdir', return_value=["main.py", "utils.py"])
    @patch('builtins.open', mock_open(read_data='{"editor.fontSize": 14}'))
    def test_reads_settings_json(self, _mock_listdir, _mock_isfile, _mock_which):
        result = StateTeleportManager.capture_vscode_state("/tmp/ws")
        self.assertEqual(result["settings_json"], {"editor.fontSize": 14})


class TestCaptureGitState(unittest.TestCase):
    """Tests for capture_git_state."""

    @patch('utils.state_teleport.shutil.which', return_value=None)
    def test_no_git_returns_defaults(self, _mock_which):
        result = StateTeleportManager.capture_git_state("/tmp/repo")
        self.assertEqual(result["branch"], "")
        self.assertEqual(result["status"], "unknown")

    @patch('utils.state_teleport.shutil.which', return_value="/usr/bin/git")
    @patch('utils.state_teleport.subprocess.run')
    def test_captures_branch_and_status(self, mock_run, _mock_which):
        def run_side_effect(cmd, **kwargs):
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                return MagicMock(returncode=0, stdout="feature-branch\n")
            if "status" in cmd and "--porcelain" in cmd:
                return MagicMock(returncode=0, stdout="")
            if "rev-parse" in cmd and "HEAD" in cmd:
                return MagicMock(returncode=0, stdout="abc123\n")
            if "remote" in cmd:
                return MagicMock(returncode=0, stdout="https://github.com/user/repo.git\n")
            if "stash" in cmd:
                return MagicMock(returncode=0, stdout="")
            if "rev-list" in cmd:
                return MagicMock(returncode=0, stdout="0\n")
            return MagicMock(returncode=1, stdout="")

        mock_run.side_effect = run_side_effect
        result = StateTeleportManager.capture_git_state("/tmp/repo")
        self.assertEqual(result["branch"], "feature-branch")
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["last_commit_hash"], "abc123")

    @patch('utils.state_teleport.shutil.which', return_value="/usr/bin/git")
    @patch('utils.state_teleport.subprocess.run')
    def test_dirty_status(self, mock_run, _mock_which):
        def run_side_effect(cmd, **kwargs):
            if "status" in cmd and "--porcelain" in cmd:
                return MagicMock(returncode=0, stdout="M file.py\n")
            return MagicMock(returncode=0, stdout="main\n")

        mock_run.side_effect = run_side_effect
        result = StateTeleportManager.capture_git_state("/tmp/repo")
        self.assertEqual(result["status"], "dirty")


class TestCaptureTerminalState(unittest.TestCase):
    """Tests for capture_terminal_state."""

    @patch.dict(os.environ, {"SHELL": "/bin/bash"}, clear=False)
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    def test_bash_no_history(self, _mock_isfile):
        result = StateTeleportManager.capture_terminal_state()
        self.assertEqual(result["shell"], "bash")
        self.assertEqual(result["recent_history"], [])

    @patch.dict(os.environ, {"SHELL": "/bin/zsh"}, clear=False)
    @patch('utils.state_teleport.os.path.isfile', return_value=True)
    @patch('builtins.open', mock_open(read_data="cmd1\ncmd2\ncmd3\n"))
    def test_zsh_reads_history(self, _mock_isfile):
        result = StateTeleportManager.capture_terminal_state()
        self.assertEqual(result["shell"], "zsh")
        self.assertEqual(len(result["recent_history"]), 3)


class TestFilterEnvironment(unittest.TestCase):
    """Tests for _filter_environment."""

    @patch.dict(os.environ, {
        "HOME": "/home/test",
        "PATH": "/usr/bin",
        "AWS_SECRET_KEY": "hidden",
        "EDITOR": "vim",
        "API_TOKEN": "also_hidden",
    }, clear=True)
    def test_filters_path_and_secrets(self):
        result = StateTeleportManager._filter_environment()
        self.assertIn("HOME", result)
        self.assertIn("EDITOR", result)
        self.assertNotIn("PATH", result)
        self.assertNotIn("AWS_SECRET_KEY", result)
        self.assertNotIn("API_TOKEN", result)


class TestFilterOpenFiles(unittest.TestCase):
    """Tests for _filter_open_files."""

    def test_filters_credential_files(self):
        files = ["/tmp/.env", "/tmp/main.py", "/tmp/id_rsa", "/tmp/config.json"]
        result = StateTeleportManager._filter_open_files(files)
        self.assertIn("/tmp/main.py", result)
        self.assertIn("/tmp/config.json", result)
        self.assertNotIn("/tmp/.env", result)
        self.assertNotIn("/tmp/id_rsa", result)

    def test_filters_dotenv_variants(self):
        files = ["/tmp/.env.local", "/tmp/.env.production"]
        result = StateTeleportManager._filter_open_files(files)
        self.assertEqual(result, [])


class TestSerializeDeserialize(unittest.TestCase):
    """Tests for serialize_state and deserialize_state."""

    def test_roundtrip(self):
        state = _make_workspace_state()
        serialized = StateTeleportManager.serialize_state(state)
        restored = StateTeleportManager.deserialize_state(serialized)
        self.assertEqual(restored.workspace_id, state.workspace_id)
        self.assertEqual(restored.hostname, state.hostname)

    def test_serialize_returns_bytes(self):
        state = _make_workspace_state()
        result = StateTeleportManager.serialize_state(state)
        self.assertIsInstance(result, bytes)

    def test_deserialize_corrupt_data(self):
        with self.assertRaises(ValueError):
            StateTeleportManager.deserialize_state(b"not json{{{")

    def test_deserialize_missing_fields(self):
        data = json.dumps({"workspace_id": "x"}).encode("utf-8")
        with self.assertRaises(ValueError) as ctx:
            StateTeleportManager.deserialize_state(data)
        self.assertIn("Missing fields", str(ctx.exception))


class TestCreateTeleportPackage(unittest.TestCase):
    """Tests for create_teleport_package."""

    def test_creates_package(self):
        state = _make_workspace_state()
        pkg = StateTeleportManager.create_teleport_package(state, "target-device")
        self.assertIsInstance(pkg, TeleportPackage)
        self.assertEqual(pkg.source_device, "testhost")
        self.assertEqual(pkg.target_device, "target-device")
        self.assertGreater(pkg.size_bytes, 0)
        self.assertIsNotNone(pkg.checksum)

    def test_checksum_is_sha256_hex(self):
        state = _make_workspace_state()
        pkg = StateTeleportManager.create_teleport_package(state, "dest")
        self.assertEqual(len(pkg.checksum), 64)
        # Verify it's valid hex
        int(pkg.checksum, 16)


class TestRestoreVscodeState(unittest.TestCase):
    """Tests for restore_vscode_state."""

    @patch('utils.state_teleport.shutil.which', return_value="/usr/bin/code")
    @patch('utils.state_teleport.subprocess.run')
    def test_restore_success(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(returncode=0)
        result = StateTeleportManager.restore_vscode_state(
            {"workspace_path": "/tmp/ws"}
        )
        self.assertTrue(result.success)

    def test_restore_no_workspace_path(self):
        result = StateTeleportManager.restore_vscode_state({"workspace_path": ""})
        self.assertFalse(result.success)

    @patch('utils.state_teleport.shutil.which', return_value=None)
    def test_restore_no_vscode(self, _mock_which):
        result = StateTeleportManager.restore_vscode_state(
            {"workspace_path": "/tmp/ws"}
        )
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    @patch('utils.state_teleport.shutil.which', return_value="/usr/bin/code")
    @patch('utils.state_teleport.subprocess.run')
    def test_restore_timeout(self, mock_run, _mock_which):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="code", timeout=15)
        result = StateTeleportManager.restore_vscode_state(
            {"workspace_path": "/tmp/ws"}
        )
        self.assertFalse(result.success)


class TestCaptureFullState(unittest.TestCase):
    """Tests for capture_full_state."""

    @patch.object(StateTeleportManager, '_filter_open_files', return_value=[])
    @patch.object(StateTeleportManager, '_filter_environment', return_value={})
    @patch.object(StateTeleportManager, 'capture_terminal_state', return_value={"cwd": "/", "shell": "bash", "recent_history": []})
    @patch.object(StateTeleportManager, 'capture_git_state', return_value={"branch": "main"})
    @patch.object(StateTeleportManager, 'capture_vscode_state', return_value={"workspace_path": "/tmp", "open_editors": []})
    def test_returns_workspace_state(self, _vs, _git, _term, _env, _filter):
        result = StateTeleportManager.capture_full_state("/tmp/ws")
        self.assertIsInstance(result, WorkspaceState)
        self.assertIsNotNone(result.workspace_id)
        self.assertGreater(result.timestamp, 0)


class TestSecretPatterns(unittest.TestCase):
    """Tests for secret filtering constants."""

    def test_patterns_cover_common_secrets(self):
        for pat in ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL"):
            self.assertIn(pat, _SECRET_PATTERNS)

    def test_credential_files_include_dotenv(self):
        self.assertIn(".env", _CREDENTIAL_FILES)
        self.assertIn(".env.local", _CREDENTIAL_FILES)


if __name__ == "__main__":
    unittest.main()
