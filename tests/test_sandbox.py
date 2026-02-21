"""
Tests for utils/sandbox.py — SandboxManager and BubblewrapManager.
Covers: firejail/bwrap detection, run_sandboxed, network restriction,
private home, profile listing, desktop entry creation, and sandbox status.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.sandbox import SandboxManager, BubblewrapManager, PluginIsolationManager


# ---------------------------------------------------------------------------
# TestDetection — tool availability detection
# ---------------------------------------------------------------------------

class TestDetection(unittest.TestCase):
    """Tests for sandbox tool availability detection."""

    @patch('utils.sandbox.shutil.which', return_value='/usr/bin/firejail')
    def test_firejail_installed(self, mock_which):
        """is_firejail_installed returns True when firejail found."""
        self.assertTrue(SandboxManager.is_firejail_installed())

    @patch('utils.sandbox.shutil.which', return_value=None)
    def test_firejail_not_installed(self, mock_which):
        """is_firejail_installed returns False when firejail missing."""
        self.assertFalse(SandboxManager.is_firejail_installed())

    @patch('utils.sandbox.shutil.which', return_value='/usr/bin/bwrap')
    def test_bubblewrap_installed(self, mock_which):
        """is_bubblewrap_installed returns True when bwrap found."""
        self.assertTrue(SandboxManager.is_bubblewrap_installed())

    @patch('utils.sandbox.shutil.which', return_value=None)
    def test_bubblewrap_not_installed(self, mock_which):
        """is_bubblewrap_installed returns False when bwrap missing."""
        self.assertFalse(SandboxManager.is_bubblewrap_installed())


# ---------------------------------------------------------------------------
# TestRunSandboxed — running sandboxed commands
# ---------------------------------------------------------------------------

class TestRunSandboxed(unittest.TestCase):
    """Tests for run_sandboxed with mocked Popen."""

    @patch('utils.sandbox.subprocess.Popen')
    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    def test_run_sandboxed_basic(self, mock_installed, mock_popen):
        """run_sandboxed starts a basic firejail process."""
        mock_popen.return_value = MagicMock(pid=12345)

        result = SandboxManager.run_sandboxed(["firefox"])

        self.assertTrue(result.success)
        self.assertEqual(result.data["pid"], 12345)

    @patch('utils.sandbox.subprocess.Popen')
    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    def test_run_sandboxed_no_network(self, mock_installed, mock_popen):
        """run_sandboxed passes --net=none when no_network is True."""
        mock_popen.return_value = MagicMock(pid=100)

        SandboxManager.run_sandboxed(["firefox"], no_network=True)

        call_args = mock_popen.call_args[0][0]
        self.assertIn("--net=none", call_args)

    @patch('utils.sandbox.subprocess.Popen')
    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    def test_run_sandboxed_private_home(self, mock_installed, mock_popen):
        """run_sandboxed passes --private when private_home is True."""
        mock_popen.return_value = MagicMock(pid=200)

        SandboxManager.run_sandboxed(["chrome"], private_home=True)

        call_args = mock_popen.call_args[0][0]
        self.assertIn("--private", call_args)

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=False)
    def test_run_sandboxed_firejail_not_installed(self, mock_installed):
        """run_sandboxed returns failure when firejail not installed."""
        result = SandboxManager.run_sandboxed(["firefox"])
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    @patch('utils.sandbox.subprocess.Popen', side_effect=OSError("exec failed"))
    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    def test_run_sandboxed_exception(self, mock_installed, mock_popen):
        """run_sandboxed handles exception gracefully."""
        result = SandboxManager.run_sandboxed(["app"])
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestListProfiles — profile listing
# ---------------------------------------------------------------------------

class TestListProfiles(unittest.TestCase):
    """Tests for list_profiles with mocked filesystem."""

    @patch('utils.sandbox.os.listdir', return_value=["firefox.profile", "vlc.profile", "other.txt"])
    @patch('utils.sandbox.os.path.exists', return_value=True)
    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    def test_list_profiles_filters_profiles(self, mock_installed, mock_exists, mock_listdir):
        """list_profiles returns only .profile files without extension."""
        profiles = SandboxManager.list_profiles()
        self.assertIn("firefox", profiles)
        self.assertIn("vlc", profiles)
        self.assertNotIn("other.txt", profiles)

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=False)
    def test_list_profiles_no_firejail(self, mock_installed):
        """list_profiles returns empty when firejail not installed."""
        profiles = SandboxManager.list_profiles()
        self.assertEqual(profiles, [])


# ---------------------------------------------------------------------------
# TestCreateDesktopEntry — desktop entry creation
# ---------------------------------------------------------------------------

class TestCreateDesktopEntry(unittest.TestCase):
    """Tests for create_desktop_entry with mocked file write."""

    @patch('utils.sandbox.os.chmod')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.sandbox.Path.mkdir')
    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    def test_create_desktop_entry_success(self, mock_installed, mock_mkdir, mock_file, mock_chmod):
        """create_desktop_entry creates desktop file."""
        result = SandboxManager.create_desktop_entry("Firefox", "firefox")
        self.assertTrue(result.success)
        self.assertIn("path", result.data)

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=False)
    def test_create_desktop_entry_no_firejail(self, mock_installed):
        """create_desktop_entry returns failure without firejail."""
        result = SandboxManager.create_desktop_entry("App", "app")
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestGetSandboxStatus — process sandbox check
# ---------------------------------------------------------------------------

class TestGetSandboxStatus(unittest.TestCase):
    """Tests for get_sandbox_status with mocked /proc."""

    @patch('utils.sandbox.os.kill')
    @patch('utils.sandbox.os.path.exists', return_value=True)
    @patch('builtins.open', mock_open(read_data=b'firejail\x00--net=none\x00firefox'))
    def test_sandbox_status_firejail_detected(self, mock_exists, mock_kill):
        """get_sandbox_status detects firejail sandbox."""
        status = SandboxManager.get_sandbox_status(12345)
        self.assertTrue(status["running"])
        self.assertTrue(status["sandboxed"])
        self.assertIn("no_network", status["restrictions"])

    @patch('utils.sandbox.os.kill', side_effect=OSError("No such process"))
    def test_sandbox_status_process_not_running(self, mock_kill):
        """get_sandbox_status returns not running for dead process."""
        status = SandboxManager.get_sandbox_status(99999)
        self.assertFalse(status["running"])
        self.assertFalse(status["sandboxed"])


# ---------------------------------------------------------------------------
# TestBubblewrapManager — bubblewrap operations
# ---------------------------------------------------------------------------

class TestBubblewrapManager(unittest.TestCase):
    """Tests for BubblewrapManager."""

    @patch('utils.sandbox.shutil.which', return_value='/usr/bin/bwrap')
    def test_is_installed(self, mock_which):
        """is_installed returns True when bwrap found."""
        self.assertTrue(BubblewrapManager.is_installed())

    @patch('utils.sandbox.subprocess.Popen')
    @patch.object(BubblewrapManager, 'is_installed', return_value=True)
    def test_run_minimal_sandbox_success(self, mock_installed, mock_popen):
        """run_minimal_sandbox starts a bwrap process."""
        mock_popen.return_value = MagicMock(pid=5678)

        result = BubblewrapManager.run_minimal_sandbox(["bash"])

        self.assertTrue(result.success)
        self.assertEqual(result.data["pid"], 5678)

    @patch.object(BubblewrapManager, 'is_installed', return_value=False)
    def test_run_minimal_sandbox_not_installed(self, mock_installed):
        """run_minimal_sandbox returns failure when bwrap not installed."""
        result = BubblewrapManager.run_minimal_sandbox(["bash"])
        self.assertFalse(result.success)


class TestPluginIsolationManager(unittest.TestCase):
    """Tests for policy mode enforcement checks."""

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=False)
    @patch.object(BubblewrapManager, 'is_installed', return_value=False)
    def test_can_enforce_mode_advisory_always_true(self, mock_bwrap, mock_firejail):
        self.assertTrue(PluginIsolationManager.can_enforce_mode("advisory"))

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    @patch.object(BubblewrapManager, 'is_installed', return_value=False)
    def test_can_enforce_mode_process_with_firejail(self, mock_bwrap, mock_firejail):
        self.assertTrue(PluginIsolationManager.can_enforce_mode("process"))

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=False)
    @patch.object(BubblewrapManager, 'is_installed', return_value=False)
    def test_can_enforce_mode_process_without_tools(self, mock_bwrap, mock_firejail):
        self.assertFalse(PluginIsolationManager.can_enforce_mode("process"))

    @patch.object(BubblewrapManager, 'is_installed', return_value=True)
    def test_can_enforce_mode_os_with_bwrap(self, mock_bwrap):
        self.assertTrue(PluginIsolationManager.can_enforce_mode("os"))

    @patch.object(BubblewrapManager, 'is_installed', return_value=False)
    def test_can_enforce_mode_os_without_bwrap(self, mock_bwrap):
        self.assertFalse(PluginIsolationManager.can_enforce_mode("os"))

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=True)
    @patch.object(BubblewrapManager, 'is_installed', return_value=False)
    def test_enforce_policy_success_path(self, mock_bwrap, mock_firejail):
        policy = MagicMock(plugin_id="plugin-a", mode="process")
        result = PluginIsolationManager.enforce_policy(policy)
        self.assertTrue(result.success)
        self.assertIn("enforced", result.message)
        self.assertEqual(result.data["plugin_id"], "plugin-a")

    @patch.object(SandboxManager, 'is_firejail_installed', return_value=False)
    @patch.object(BubblewrapManager, 'is_installed', return_value=False)
    def test_enforce_policy_failure_path(self, mock_bwrap, mock_firejail):
        policy = MagicMock(plugin_id="plugin-a", mode="process")
        result = PluginIsolationManager.enforce_policy(policy)
        self.assertFalse(result.success)
        self.assertIn("cannot be enforced", result.message)
        self.assertEqual(result.data["mode"], "process")


if __name__ == '__main__':
    unittest.main()
