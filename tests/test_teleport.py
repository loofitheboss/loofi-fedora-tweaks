"""
Tests for utils/state_teleport.py — State Teleport feature.
Covers: capture (VS Code, git, terminal, full), serialization, restore,
file I/O, security filtering, and error handling.
"""
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
import unittest
from dataclasses import asdict
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.state_teleport import (
    StateTeleportManager,
    WorkspaceState,
    TeleportPackage,
    _SECRET_PATTERNS,
    _CREDENTIAL_FILES,
)
from utils.containers import Result


def _make_workspace_state(**overrides) -> WorkspaceState:
    """Helper to build a minimal WorkspaceState for tests."""
    defaults = {
        "workspace_id": "test-uuid-1234",
        "timestamp": 1700000000.0,
        "hostname": "dev-laptop",
        "vscode_workspace": {
            "workspace_path": "/home/user/project",
            "extensions": ["ms-python.python"],
            "settings_json": {"editor.fontSize": 14},
            "open_editors": ["main.py", "README.md"],
        },
        "git_state": {
            "branch": "feature/teleport",
            "remote_url": "git@github.com:user/project.git",
            "status": "clean",
            "last_commit_hash": "abc123def456",
            "stash_count": 0,
            "unpushed_count": 2,
        },
        "terminal_state": {
            "cwd": "/home/user/project",
            "shell": "bash",
            "recent_history": ["git status", "python main.py"],
        },
        "open_files": ["/home/user/project/main.py"],
        "environment": {"EDITOR": "vim", "LANG": "en_US.UTF-8"},
    }
    defaults.update(overrides)
    return WorkspaceState(**defaults)


# ---------------------------------------------------------------------------
# TestCaptureVSCode — VS Code state capture
# ---------------------------------------------------------------------------

class TestCaptureVSCode(unittest.TestCase):
    """Tests for VS Code state capture."""

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/code')
    @patch('utils.state_teleport.subprocess.run')
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    @patch('utils.state_teleport.os.listdir', return_value=['app.py', 'test.py'])
    @patch('utils.state_teleport.os.path.isfile')
    def test_capture_vscode_with_extensions(self, mock_isfile2, mock_listdir,
                                             mock_isfile, mock_run, mock_which):
        """Extensions are captured when VS Code is installed."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ms-python.python\nms-vscode.cpptools\n",
        )
        # os.path.isfile for non-settings check: workspace files
        mock_isfile2.return_value = True

        state = StateTeleportManager.capture_vscode_state("/tmp/project")

        self.assertIn("ms-python.python", state["extensions"])
        self.assertIn("ms-vscode.cpptools", state["extensions"])
        self.assertEqual(state["workspace_path"], "/tmp/project")

    @patch('utils.state_teleport.shutil.which', return_value=None)
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    @patch('utils.state_teleport.os.listdir', return_value=[])
    def test_capture_vscode_not_installed(self, mock_listdir, mock_isfile,
                                          mock_which):
        """Falls back gracefully if VS Code not installed."""
        state = StateTeleportManager.capture_vscode_state("/tmp/project")

        self.assertEqual(state["extensions"], [])
        self.assertEqual(state["workspace_path"], "/tmp/project")

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/code')
    @patch('utils.state_teleport.subprocess.run')
    @patch('utils.state_teleport.os.path.isfile', return_value=True)
    @patch('builtins.open', mock_open(read_data='{"editor.fontSize": 16}'))
    @patch('utils.state_teleport.os.listdir', return_value=[])
    def test_capture_vscode_reads_settings(self, mock_listdir, mock_isfile,
                                            mock_run, mock_which):
        """Settings from .vscode/settings.json are read."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        state = StateTeleportManager.capture_vscode_state("/tmp/project")

        self.assertEqual(state["settings_json"]["editor.fontSize"], 16)

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/code')
    @patch('utils.state_teleport.subprocess.run',
           side_effect=OSError("command failed"))
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    @patch('utils.state_teleport.os.listdir', return_value=[])
    def test_capture_vscode_command_failure(self, mock_listdir, mock_isfile,
                                            mock_run, mock_which):
        """Handles VS Code command failure gracefully."""
        state = StateTeleportManager.capture_vscode_state("/tmp/project")

        self.assertEqual(state["extensions"], [])

    @patch('utils.state_teleport.shutil.which', return_value=None)
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    @patch('utils.state_teleport.os.listdir', return_value=[])
    @patch('utils.state_teleport.os.getcwd', return_value="/home/user/auto")
    def test_capture_vscode_defaults_to_cwd(self, mock_getcwd, mock_listdir,
                                             mock_isfile, mock_which):
        """Uses CWD when no workspace_path is provided."""
        state = StateTeleportManager.capture_vscode_state()

        self.assertEqual(state["workspace_path"], "/home/user/auto")


# ---------------------------------------------------------------------------
# TestCaptureGit — git state capture
# ---------------------------------------------------------------------------

class TestCaptureGit(unittest.TestCase):
    """Tests for git repository state capture."""

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/git')
    @patch('utils.state_teleport.subprocess.run')
    def test_capture_git_clean_repo(self, mock_run, mock_which):
        """Captures correct state for a clean git repository."""
        def side_effect(args, **kwargs):
            cmd_str = " ".join(args)
            result = MagicMock(returncode=0)
            if "rev-parse --abbrev-ref" in cmd_str:
                result.stdout = "main"
            elif "remote get-url" in cmd_str:
                result.stdout = "git@github.com:user/repo.git"
            elif "status --porcelain" in cmd_str:
                result.stdout = ""
            elif "rev-parse HEAD" in cmd_str:
                result.stdout = "abc123"
            elif "stash list" in cmd_str:
                result.stdout = ""
            elif "rev-list --count" in cmd_str:
                result.stdout = "0"
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        state = StateTeleportManager.capture_git_state("/tmp/repo")

        self.assertEqual(state["branch"], "main")
        self.assertEqual(state["remote_url"], "git@github.com:user/repo.git")
        self.assertEqual(state["status"], "clean")
        self.assertEqual(state["last_commit_hash"], "abc123")
        self.assertEqual(state["stash_count"], 0)

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/git')
    @patch('utils.state_teleport.subprocess.run')
    def test_capture_git_dirty_repo(self, mock_run, mock_which):
        """Detects dirty working tree correctly."""
        def side_effect(args, **kwargs):
            result = MagicMock(returncode=0)
            cmd_str = " ".join(args)
            if "status --porcelain" in cmd_str:
                result.stdout = " M src/main.py\n?? new_file.txt"
            elif "rev-parse --abbrev-ref" in cmd_str:
                result.stdout = "dev"
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        state = StateTeleportManager.capture_git_state("/tmp/repo")

        self.assertEqual(state["status"], "dirty")

    @patch('utils.state_teleport.shutil.which', return_value=None)
    def test_capture_git_not_installed(self, mock_which):
        """Returns empty state when git is not installed."""
        state = StateTeleportManager.capture_git_state("/tmp/repo")

        self.assertEqual(state["branch"], "")
        self.assertEqual(state["status"], "unknown")

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/git')
    @patch('utils.state_teleport.subprocess.run')
    def test_capture_git_with_stashes(self, mock_run, mock_which):
        """Counts stashes correctly."""
        def side_effect(args, **kwargs):
            result = MagicMock(returncode=0)
            cmd_str = " ".join(args)
            if "stash list" in cmd_str:
                result.stdout = "stash@{0}: WIP\nstash@{1}: Save"
            elif "rev-parse --abbrev-ref" in cmd_str:
                result.stdout = "main"
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        state = StateTeleportManager.capture_git_state("/tmp/repo")

        self.assertEqual(state["stash_count"], 2)

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/git')
    @patch('utils.state_teleport.subprocess.run')
    def test_capture_git_with_unpushed(self, mock_run, mock_which):
        """Counts unpushed commits."""
        def side_effect(args, **kwargs):
            result = MagicMock(returncode=0)
            cmd_str = " ".join(args)
            if "rev-list --count" in cmd_str:
                result.stdout = "3"
            elif "rev-parse --abbrev-ref" in cmd_str:
                result.stdout = "feature"
            elif "stash list" in cmd_str:
                result.stdout = ""
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        state = StateTeleportManager.capture_git_state("/tmp/repo")

        self.assertEqual(state["unpushed_count"], 3)

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/git')
    @patch('utils.state_teleport.subprocess.run',
           side_effect=OSError("git failed"))
    def test_capture_git_subprocess_error(self, mock_run, mock_which):
        """Handles subprocess errors gracefully."""
        state = StateTeleportManager.capture_git_state("/tmp/repo")

        self.assertEqual(state["branch"], "")
        self.assertEqual(state["status"], "unknown")


# ---------------------------------------------------------------------------
# TestCaptureTerminal — terminal state capture
# ---------------------------------------------------------------------------

class TestCaptureTerminal(unittest.TestCase):
    """Tests for terminal state capture."""

    @patch('utils.state_teleport.os.getcwd', return_value='/home/user/project')
    @patch('utils.state_teleport.os.environ',
           {"SHELL": "/bin/bash"})
    @patch('utils.state_teleport.os.path.isfile', return_value=True)
    @patch('builtins.open',
           mock_open(read_data="git status\npython main.py\nls -la\n"))
    def test_capture_terminal_bash(self, mock_isfile, mock_getcwd):
        """Captures bash terminal state with history."""
        state = StateTeleportManager.capture_terminal_state()

        self.assertEqual(state["cwd"], "/home/user/project")
        self.assertEqual(state["shell"], "bash")
        self.assertIn("git status", state["recent_history"])

    @patch('utils.state_teleport.os.getcwd', return_value='/home/user')
    @patch('utils.state_teleport.os.environ',
           {"SHELL": "/bin/zsh"})
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    def test_capture_terminal_zsh_no_history(self, mock_isfile, mock_getcwd):
        """Handles missing history file gracefully."""
        state = StateTeleportManager.capture_terminal_state()

        self.assertEqual(state["shell"], "zsh")
        self.assertEqual(state["recent_history"], [])

    @patch('utils.state_teleport.os.getcwd', return_value='/home/user')
    @patch('utils.state_teleport.os.environ',
           {"SHELL": "/usr/bin/fish"})
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    def test_capture_terminal_fish_detection(self, mock_isfile, mock_getcwd):
        """Detects fish shell correctly."""
        state = StateTeleportManager.capture_terminal_state()

        self.assertEqual(state["shell"], "fish")

    @patch('utils.state_teleport.os.getcwd', return_value='/tmp')
    @patch('utils.state_teleport.os.environ', {})
    @patch('utils.state_teleport.os.path.isfile', return_value=False)
    def test_capture_terminal_unknown_shell(self, mock_isfile, mock_getcwd):
        """Falls back to bash for unknown shell."""
        state = StateTeleportManager.capture_terminal_state()

        self.assertEqual(state["shell"], "bash")


# ---------------------------------------------------------------------------
# TestSecurityFiltering — secret and credential filtering
# ---------------------------------------------------------------------------

class TestSecurityFiltering(unittest.TestCase):
    """Tests for security: env var and file filtering."""

    @patch('utils.state_teleport.os.environ', {
        "EDITOR": "vim",
        "AWS_SECRET_KEY": "supersecret",
        "API_TOKEN": "tok123",
        "LANG": "en_US.UTF-8",
        "DB_PASSWORD": "pass",
        "GIT_CREDENTIAL_HELPER": "cache",
        "HOME": "/home/user",
        "PATH": "/usr/bin:/bin",
    })
    def test_env_var_filtering_removes_secrets(self):
        """Environment variables containing secret keywords are excluded."""
        filtered = StateTeleportManager._filter_environment()

        self.assertIn("EDITOR", filtered)
        self.assertIn("LANG", filtered)
        self.assertIn("HOME", filtered)
        self.assertNotIn("AWS_SECRET_KEY", filtered)
        self.assertNotIn("API_TOKEN", filtered)
        self.assertNotIn("DB_PASSWORD", filtered)
        self.assertNotIn("GIT_CREDENTIAL_HELPER", filtered)
        self.assertNotIn("PATH", filtered)

    @patch('utils.state_teleport.os.environ', {
        "MY_KEY": "value",
        "SECRET_SAUCE": "hidden",
        "CREDENTIAL_FILE": "/path",
    })
    def test_env_var_filtering_case_insensitive(self):
        """Secret pattern matching works case-insensitively."""
        filtered = StateTeleportManager._filter_environment()

        self.assertNotIn("MY_KEY", filtered)
        self.assertNotIn("SECRET_SAUCE", filtered)
        self.assertNotIn("CREDENTIAL_FILE", filtered)

    def test_credential_file_filtering(self):
        """Credential files are removed from open_files list."""
        files = [
            "/home/user/project/main.py",
            "/home/user/project/.env",
            "/home/user/project/.env.local",
            "/home/user/project/credentials.json",
            "/home/user/project/src/app.py",
            "/home/user/.ssh/id_rsa",
            "/home/user/project/.netrc",
        ]
        filtered = StateTeleportManager._filter_open_files(files)

        self.assertIn("/home/user/project/main.py", filtered)
        self.assertIn("/home/user/project/src/app.py", filtered)
        self.assertNotIn("/home/user/project/.env", filtered)
        self.assertNotIn("/home/user/project/.env.local", filtered)
        self.assertNotIn("/home/user/project/credentials.json", filtered)
        self.assertNotIn("/home/user/.ssh/id_rsa", filtered)
        self.assertNotIn("/home/user/project/.netrc", filtered)

    def test_credential_file_filtering_empty_list(self):
        """Handling an empty files list returns empty."""
        filtered = StateTeleportManager._filter_open_files([])

        self.assertEqual(filtered, [])


# ---------------------------------------------------------------------------
# TestFullCapture — full state capture
# ---------------------------------------------------------------------------

class TestFullCapture(unittest.TestCase):
    """Tests for full workspace state capture."""

    @patch.object(StateTeleportManager, 'capture_vscode_state')
    @patch.object(StateTeleportManager, 'capture_git_state')
    @patch.object(StateTeleportManager, 'capture_terminal_state')
    @patch.object(StateTeleportManager, '_filter_environment')
    @patch('utils.state_teleport.platform.node', return_value='test-host')
    def test_capture_full_state_combines_all(self, mock_node, mock_env,
                                              mock_term, mock_git, mock_vscode):
        """Full capture combines all sub-captures into a WorkspaceState."""
        mock_vscode.return_value = {
            "workspace_path": "/tmp/project",
            "extensions": [],
            "settings_json": {},
            "open_editors": ["safe_file.py"],
        }
        mock_git.return_value = {"branch": "main", "status": "clean"}
        mock_term.return_value = {"cwd": "/tmp/project", "shell": "bash",
                                   "recent_history": []}
        mock_env.return_value = {"EDITOR": "vim"}

        state = StateTeleportManager.capture_full_state("/tmp/project")

        self.assertIsInstance(state, WorkspaceState)
        self.assertEqual(state.hostname, "test-host")
        self.assertEqual(state.vscode_workspace["workspace_path"], "/tmp/project")
        self.assertEqual(state.git_state["branch"], "main")
        self.assertIsInstance(state.workspace_id, str)
        self.assertIsInstance(state.timestamp, float)


# ---------------------------------------------------------------------------
# TestSerialization — serialize / deserialize
# ---------------------------------------------------------------------------

class TestSerialization(unittest.TestCase):
    """Tests for WorkspaceState serialization and deserialization."""

    def test_serialize_produces_bytes(self):
        """serialize_state returns UTF-8 bytes."""
        state = _make_workspace_state()
        data = StateTeleportManager.serialize_state(state)

        self.assertIsInstance(data, bytes)
        # Should be valid JSON
        parsed = json.loads(data.decode("utf-8"))
        self.assertEqual(parsed["workspace_id"], "test-uuid-1234")

    def test_deserialize_roundtrip(self):
        """Serialize then deserialize produces equivalent state."""
        original = _make_workspace_state()
        data = StateTeleportManager.serialize_state(original)
        restored = StateTeleportManager.deserialize_state(data)

        self.assertEqual(restored.workspace_id, original.workspace_id)
        self.assertEqual(restored.hostname, original.hostname)
        self.assertEqual(restored.git_state["branch"],
                         original.git_state["branch"])
        self.assertEqual(restored.open_files, original.open_files)

    def test_deserialize_corrupt_data(self):
        """Corrupt bytes raise ValueError."""
        with self.assertRaises(ValueError):
            StateTeleportManager.deserialize_state(b"not json at all")

    def test_deserialize_missing_fields(self):
        """Missing required fields raise ValueError."""
        incomplete = json.dumps({"workspace_id": "x"}).encode("utf-8")

        with self.assertRaises(ValueError) as ctx:
            StateTeleportManager.deserialize_state(incomplete)
        self.assertIn("Missing fields", str(ctx.exception))

    def test_deserialize_invalid_utf8(self):
        """Invalid UTF-8 bytes raise ValueError."""
        with self.assertRaises(ValueError):
            StateTeleportManager.deserialize_state(b'\xff\xfe')


# ---------------------------------------------------------------------------
# TestPackage — package creation and checksum
# ---------------------------------------------------------------------------

class TestPackage(unittest.TestCase):
    """Tests for TeleportPackage creation."""

    def test_create_teleport_package(self):
        """Package is created with correct metadata."""
        state = _make_workspace_state()
        package = StateTeleportManager.create_teleport_package(
            state, target_device="office-pc"
        )

        self.assertIsInstance(package, TeleportPackage)
        self.assertEqual(package.source_device, "dev-laptop")
        self.assertEqual(package.target_device, "office-pc")
        self.assertIsInstance(package.package_id, str)
        self.assertGreater(package.size_bytes, 0)
        self.assertEqual(len(package.checksum), 64)  # SHA-256 hex

    def test_package_checksum_is_sha256(self):
        """Package checksum matches SHA-256 of serialized data."""
        state = _make_workspace_state()
        package = StateTeleportManager.create_teleport_package(state, "target")

        serialized = StateTeleportManager.serialize_state(state)
        expected = hashlib.sha256(serialized).hexdigest()

        self.assertEqual(package.checksum, expected)

    def test_package_size_matches_serialized(self):
        """Package size_bytes matches length of serialized data."""
        state = _make_workspace_state()
        package = StateTeleportManager.create_teleport_package(state, "target")

        serialized = StateTeleportManager.serialize_state(state)
        self.assertEqual(package.size_bytes, len(serialized))


# ---------------------------------------------------------------------------
# TestFileIO — save / load from file
# ---------------------------------------------------------------------------

class TestFileIO(unittest.TestCase):
    """Tests for saving and loading packages to/from files."""

    def test_save_and_load_roundtrip(self):
        """Save then load produces equivalent package."""
        state = _make_workspace_state()
        package = StateTeleportManager.create_teleport_package(state, "target")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmpfile = f.name

        try:
            result = StateTeleportManager.save_package_to_file(package, tmpfile)
            self.assertTrue(result.success)

            loaded = StateTeleportManager.load_package_from_file(tmpfile)
            self.assertEqual(loaded.package_id, package.package_id)
            self.assertEqual(loaded.source_device, package.source_device)
            self.assertEqual(loaded.workspace.workspace_id,
                             package.workspace.workspace_id)
            self.assertEqual(loaded.checksum, package.checksum)
        finally:
            os.unlink(tmpfile)

    def test_save_to_invalid_path(self):
        """Saving to invalid path returns failure Result."""
        state = _make_workspace_state()
        package = StateTeleportManager.create_teleport_package(state, "target")

        result = StateTeleportManager.save_package_to_file(
            package, "/nonexistent/dir/file.json"
        )
        self.assertFalse(result.success)

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            StateTeleportManager.load_package_from_file("/no/such/file.json")

    def test_load_corrupt_file(self):
        """Loading corrupt JSON raises ValueError or JSONDecodeError."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix=".json", delete=False
        ) as f:
            f.write("not valid json{{{")
            tmpfile = f.name

        try:
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                StateTeleportManager.load_package_from_file(tmpfile)
        finally:
            os.unlink(tmpfile)

    def test_load_missing_fields(self):
        """Loading file with missing fields raises ValueError."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix=".json", delete=False
        ) as f:
            json.dump({"package_id": "x"}, f)
            tmpfile = f.name

        try:
            with self.assertRaises(ValueError):
                StateTeleportManager.load_package_from_file(tmpfile)
        finally:
            os.unlink(tmpfile)


# ---------------------------------------------------------------------------
# TestRestore — VS Code and git restore
# ---------------------------------------------------------------------------

class TestRestore(unittest.TestCase):
    """Tests for workspace restore operations."""

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/code')
    @patch('utils.state_teleport.subprocess.run')
    def test_restore_vscode_success(self, mock_run, mock_which):
        """VS Code restore opens workspace and returns success."""
        mock_run.return_value = MagicMock(returncode=0)

        result = StateTeleportManager.restore_vscode_state(
            {"workspace_path": "/tmp/project"}
        )

        self.assertTrue(result.success)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertIn("code", call_args)
        self.assertIn("/tmp/project", call_args)

    @patch('utils.state_teleport.shutil.which', return_value=None)
    def test_restore_vscode_not_installed(self, mock_which):
        """Returns failure when VS Code is not installed."""
        result = StateTeleportManager.restore_vscode_state(
            {"workspace_path": "/tmp/project"}
        )

        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)
        self.assertIn("pkexec", result.message)
        self.assertNotIn("sudo ", result.message)

    def test_restore_vscode_no_path(self):
        """Returns failure when no workspace path is provided."""
        result = StateTeleportManager.restore_vscode_state({})

        self.assertFalse(result.success)

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/git')
    @patch('utils.state_teleport.subprocess.run')
    def test_restore_git_success(self, mock_run, mock_which):
        """Git restore checks out branch and returns success."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # status --porcelain (clean)
            MagicMock(returncode=0, stdout=""),  # checkout
        ]

        result = StateTeleportManager.restore_git_state(
            {"branch": "feature/test"}, "/tmp/repo"
        )

        self.assertTrue(result.success)
        self.assertIn("feature/test", result.message)

    @patch('utils.state_teleport.shutil.which', return_value='/usr/bin/git')
    @patch('utils.state_teleport.subprocess.run')
    def test_restore_git_dirty_warns(self, mock_run, mock_which):
        """Warns about dirty working tree without forcing."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=" M dirty_file.py",
        )

        result = StateTeleportManager.restore_git_state(
            {"branch": "main"}, "/tmp/repo"
        )

        self.assertFalse(result.success)
        self.assertIn("Local changes", result.message)

    @patch('utils.state_teleport.shutil.which', return_value=None)
    def test_restore_git_not_installed(self, mock_which):
        """Returns failure when git is not installed."""
        result = StateTeleportManager.restore_git_state(
            {"branch": "main"}, "/tmp/repo"
        )

        self.assertFalse(result.success)

    def test_restore_git_no_branch(self):
        """Returns failure when no branch is specified."""
        result = StateTeleportManager.restore_git_state({}, "/tmp/repo")

        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestApplyTeleport — full teleport application
# ---------------------------------------------------------------------------

class TestApplyTeleport(unittest.TestCase):
    """Tests for full teleport application."""

    @patch.object(StateTeleportManager, 'restore_git_state')
    @patch.object(StateTeleportManager, 'restore_vscode_state')
    def test_apply_teleport_full_success(self, mock_vscode, mock_git):
        """Full apply with both git and VS Code succeeding."""
        mock_git.return_value = Result(True, "Checked out main")
        mock_vscode.return_value = Result(True, "VS Code opened")

        state = _make_workspace_state()
        package = StateTeleportManager.create_teleport_package(state, "target")

        result = StateTeleportManager.apply_teleport(package)

        self.assertTrue(result.success)
        mock_git.assert_called_once()
        mock_vscode.assert_called_once()

    @patch.object(StateTeleportManager, 'restore_git_state')
    @patch.object(StateTeleportManager, 'restore_vscode_state')
    def test_apply_teleport_git_fails(self, mock_vscode, mock_git):
        """Apply reports failure when git restore fails."""
        mock_git.return_value = Result(False, "Dirty working tree")
        mock_vscode.return_value = Result(True, "VS Code opened")

        state = _make_workspace_state()
        package = StateTeleportManager.create_teleport_package(state, "target")

        result = StateTeleportManager.apply_teleport(package)

        self.assertFalse(result.success)
        self.assertIn("Dirty working tree", result.message)


# ---------------------------------------------------------------------------
# TestPackageDir and ListPackages
# ---------------------------------------------------------------------------

class TestPackageManagement(unittest.TestCase):
    """Tests for package directory and listing."""

    def test_get_package_dir_creates_directory(self):
        """get_package_dir creates the directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            pkg_dir = Path(tmpdir) / "teleport"
            original = StateTeleportManager.PACKAGE_DIR
            try:
                StateTeleportManager.PACKAGE_DIR = pkg_dir
                result = StateTeleportManager.get_package_dir()
                self.assertIsInstance(result, str)
                self.assertTrue(pkg_dir.exists())
            finally:
                StateTeleportManager.PACKAGE_DIR = original

    def test_list_saved_packages_with_files(self):
        """list_saved_packages returns metadata for each JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake package file
            pkg_data = {
                "package_id": "test-pkg-1",
                "source_device": "laptop",
                "target_device": "desktop",
                "created_at": 1700000000.0,
                "size_bytes": 512,
                "workspace": {},
            }
            filepath = os.path.join(tmpdir, "test_pkg.json")
            with open(filepath, "w") as f:
                json.dump(pkg_data, f)

            original_dir = StateTeleportManager.PACKAGE_DIR
            try:
                StateTeleportManager.PACKAGE_DIR = type(original_dir)(tmpdir)
                packages = StateTeleportManager.list_saved_packages()

                self.assertEqual(len(packages), 1)
                self.assertEqual(packages[0]["package_id"], "test-pkg-1")
                self.assertEqual(packages[0]["source_device"], "laptop")
            finally:
                StateTeleportManager.PACKAGE_DIR = original_dir


if __name__ == '__main__':
    unittest.main()
