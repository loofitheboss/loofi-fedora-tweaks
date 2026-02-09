"""
Tests for utils/service_explorer.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call
from subprocess import CalledProcessError

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.service_explorer import (
    ServiceExplorer, ServiceInfo, ServiceResult,
    ServiceScope, ServiceState,
)


class TestServiceInfo(unittest.TestCase):
    """Tests for the ServiceInfo dataclass."""

    def test_is_running_active(self):
        """Active service reports is_running True."""
        info = ServiceInfo(name="test", state=ServiceState.ACTIVE)
        self.assertTrue(info.is_running)

    def test_is_running_inactive(self):
        """Inactive service reports is_running False."""
        info = ServiceInfo(name="test", state=ServiceState.INACTIVE)
        self.assertFalse(info.is_running)

    def test_is_failed(self):
        """Failed service reports is_failed True."""
        info = ServiceInfo(name="test", state=ServiceState.FAILED)
        self.assertTrue(info.is_failed)

    def test_is_enabled(self):
        """Enabled service reports is_enabled True."""
        info = ServiceInfo(name="test", enabled="enabled")
        self.assertTrue(info.is_enabled)

    def test_is_enabled_runtime(self):
        """Runtime-enabled service reports is_enabled True."""
        info = ServiceInfo(name="test", enabled="enabled-runtime")
        self.assertTrue(info.is_enabled)

    def test_is_not_enabled_disabled(self):
        """Disabled service reports is_enabled False."""
        info = ServiceInfo(name="test", enabled="disabled")
        self.assertFalse(info.is_enabled)

    def test_is_masked(self):
        """Masked service reports is_masked True."""
        info = ServiceInfo(name="test", enabled="masked")
        self.assertTrue(info.is_masked)

    def test_is_not_masked(self):
        """Non-masked service reports is_masked False."""
        info = ServiceInfo(name="test", enabled="enabled")
        self.assertFalse(info.is_masked)

    def test_memory_human_zero(self):
        """Zero memory shows dash."""
        info = ServiceInfo(name="test", memory_bytes=0)
        self.assertEqual(info.memory_human, "—")

    def test_memory_human_bytes(self):
        """Small memory shows bytes."""
        info = ServiceInfo(name="test", memory_bytes=512)
        self.assertEqual(info.memory_human, "512 B")

    def test_memory_human_kilobytes(self):
        """Kilobyte-range memory."""
        info = ServiceInfo(name="test", memory_bytes=2048)
        self.assertEqual(info.memory_human, "2.0 KB")

    def test_memory_human_megabytes(self):
        """Megabyte-range memory."""
        info = ServiceInfo(name="test", memory_bytes=5 * 1024 * 1024)
        self.assertEqual(info.memory_human, "5.0 MB")

    def test_memory_human_gigabytes(self):
        """Gigabyte-range memory."""
        info = ServiceInfo(name="test", memory_bytes=2 * 1024 ** 3)
        self.assertEqual(info.memory_human, "2.00 GB")

    def test_to_dict(self):
        """Serialization to dict works."""
        info = ServiceInfo(
            name="sshd", description="OpenSSH",
            state=ServiceState.ACTIVE, sub_state="running",
            enabled="enabled", scope=ServiceScope.SYSTEM,
            memory_bytes=1024, main_pid=1234,
        )
        d = info.to_dict()
        self.assertEqual(d["name"], "sshd")
        self.assertEqual(d["state"], "active")
        self.assertEqual(d["enabled"], "enabled")
        self.assertEqual(d["scope"], "system")
        self.assertEqual(d["main_pid"], 1234)

    def test_to_dict_contains_all_keys(self):
        """to_dict returns all expected keys."""
        info = ServiceInfo(name="test")
        d = info.to_dict()
        expected = {"name", "description", "state", "sub_state", "enabled",
                    "scope", "memory", "memory_bytes", "main_pid",
                    "active_enter", "fragment_path"}
        self.assertEqual(set(d.keys()), expected)


class TestServiceExplorerList(unittest.TestCase):
    """Tests for ServiceExplorer.list_services()."""

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_success(self, mock_run):
        """List services parses systemctl output correctly."""
        list_output = (
            "sshd.service          loaded active running OpenSSH server daemon\n"
            "crond.service         loaded active running Command Scheduler\n"
            "bluetooth.service     loaded inactive dead    Bluetooth service\n"
        )
        enabled_output = "enabled\nenabled\ndisabled\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output, stderr=""),
            MagicMock(returncode=0, stdout=enabled_output, stderr=""),
        ]

        services = ServiceExplorer.list_services()

        self.assertEqual(len(services), 3)
        names = [s.name for s in services]
        self.assertIn("bluetooth", names)
        self.assertIn("crond", names)
        self.assertIn("sshd", names)

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_filter_active(self, mock_run):
        """Filter_state='active' only returns active services."""
        list_output = (
            "sshd.service          loaded active running OpenSSH\n"
            "bluetooth.service     loaded inactive dead    Bluetooth\n"
        )
        enabled_output = "enabled\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output, stderr=""),
            MagicMock(returncode=0, stdout=enabled_output, stderr=""),
        ]

        services = ServiceExplorer.list_services(filter_state="active")

        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].name, "sshd")
        self.assertEqual(services[0].state, ServiceState.ACTIVE)

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_search_filter(self, mock_run):
        """Search filter narrows results by name or description."""
        list_output = (
            "sshd.service          loaded active running OpenSSH server daemon\n"
            "crond.service         loaded active running Command Scheduler\n"
        )
        enabled_output = "enabled\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output, stderr=""),
            MagicMock(returncode=0, stdout=enabled_output, stderr=""),
        ]

        services = ServiceExplorer.list_services(search="ssh")

        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].name, "sshd")

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_user_scope(self, mock_run):
        """User scope passes --user flag."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        ServiceExplorer.list_services(scope=ServiceScope.USER)

        cmd = mock_run.call_args_list[0][0][0]
        self.assertIn("--user", cmd)

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_systemctl_failure(self, mock_run):
        """Returns empty list on systemctl failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        services = ServiceExplorer.list_services()

        self.assertEqual(services, [])

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_timeout(self, mock_run):
        """Returns empty list on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=30)

        services = ServiceExplorer.list_services()

        self.assertEqual(services, [])

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_os_error(self, mock_run):
        """Returns empty list on OSError."""
        mock_run.side_effect = OSError("No such file")

        services = ServiceExplorer.list_services()

        self.assertEqual(services, [])

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_failed_state(self, mock_run):
        """Failed services are parsed with correct state."""
        list_output = "bad.service loaded failed failed A broken thing\n"
        enabled_output = "enabled\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output, stderr=""),
            MagicMock(returncode=0, stdout=enabled_output, stderr=""),
        ]

        services = ServiceExplorer.list_services()

        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].state, ServiceState.FAILED)
        self.assertTrue(services[0].is_failed)

    @patch('utils.service_explorer.subprocess.run')
    def test_list_services_empty_output(self, mock_run):
        """Empty output produces empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        services = ServiceExplorer.list_services()

        self.assertEqual(services, [])


class TestServiceExplorerDetails(unittest.TestCase):
    """Tests for ServiceExplorer.get_service_details()."""

    @patch('utils.service_explorer.subprocess.run')
    def test_get_details_success(self, mock_run):
        """Parses systemctl show output correctly."""
        show_output = (
            "Description=OpenSSH server daemon\n"
            "ActiveState=active\n"
            "SubState=running\n"
            "UnitFileState=enabled\n"
            "MemoryCurrent=12345678\n"
            "MainPID=1234\n"
            "ActiveEnterTimestamp=Mon 2025-01-01 12:00:00 UTC\n"
            "FragmentPath=/usr/lib/systemd/system/sshd.service\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=show_output, stderr="")

        info = ServiceExplorer.get_service_details("sshd")

        self.assertEqual(info.name, "sshd")
        self.assertEqual(info.description, "OpenSSH server daemon")
        self.assertEqual(info.state, ServiceState.ACTIVE)
        self.assertEqual(info.sub_state, "running")
        self.assertEqual(info.enabled, "enabled")
        self.assertEqual(info.memory_bytes, 12345678)
        self.assertEqual(info.main_pid, 1234)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_details_failure(self, mock_run):
        """Returns default ServiceInfo on failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")

        info = ServiceExplorer.get_service_details("nonexistent")

        self.assertEqual(info.name, "nonexistent")
        self.assertEqual(info.state, ServiceState.UNKNOWN)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_details_memory_not_set(self, mock_run):
        """Handles [not set] memory value."""
        show_output = (
            "Description=Test\n"
            "ActiveState=inactive\n"
            "SubState=dead\n"
            "UnitFileState=disabled\n"
            "MemoryCurrent=[not set]\n"
            "MainPID=0\n"
            "ActiveEnterTimestamp=\n"
            "FragmentPath=\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=show_output, stderr="")

        info = ServiceExplorer.get_service_details("test")

        self.assertEqual(info.memory_bytes, 0)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_details_user_scope(self, mock_run):
        """User scope includes --user flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        ServiceExplorer.get_service_details("test", scope=ServiceScope.USER)

        cmd = mock_run.call_args[0][0]
        self.assertIn("--user", cmd)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_details_timeout(self, mock_run):
        """Returns default ServiceInfo on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=10)

        info = ServiceExplorer.get_service_details("test")

        self.assertEqual(info.name, "test")
        self.assertEqual(info.state, ServiceState.UNKNOWN)


class TestServiceExplorerLogs(unittest.TestCase):
    """Tests for ServiceExplorer.get_service_logs()."""

    @patch('utils.service_explorer.subprocess.run')
    def test_get_logs_success(self, mock_run):
        """Returns journal output on success."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Jan 01 sshd: Started", stderr=""
        )

        logs = ServiceExplorer.get_service_logs("sshd")

        self.assertIn("sshd", logs)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_logs_failure(self, mock_run):
        """Returns stderr on failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="No data"
        )

        logs = ServiceExplorer.get_service_logs("nonexistent")

        self.assertEqual(logs, "No data")

    @patch('utils.service_explorer.subprocess.run')
    def test_get_logs_user_scope(self, mock_run):
        """User scope passes --user flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="log", stderr="")

        ServiceExplorer.get_service_logs("test", scope=ServiceScope.USER)

        cmd = mock_run.call_args[0][0]
        self.assertIn("--user", cmd)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_logs_custom_lines(self, mock_run):
        """Respects lines parameter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        ServiceExplorer.get_service_logs("test", lines=100)

        cmd = mock_run.call_args[0][0]
        self.assertIn("100", cmd)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_logs_timeout(self, mock_run):
        """Returns error message on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="journalctl", timeout=15)

        logs = ServiceExplorer.get_service_logs("test")

        self.assertIn("Error", logs)

    @patch('utils.service_explorer.subprocess.run')
    def test_get_logs_os_error(self, mock_run):
        """Returns error message on OSError."""
        mock_run.side_effect = OSError("No such file")

        logs = ServiceExplorer.get_service_logs("test")

        self.assertIn("Error", logs)


class TestServiceExplorerActions(unittest.TestCase):
    """Tests for ServiceExplorer start/stop/restart/enable/disable/mask/unmask."""

    @patch('utils.service_explorer.subprocess.run')
    def test_start_service_success(self, mock_run):
        """Start returns success result."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceExplorer.start_service("sshd")

        self.assertTrue(result.success)
        self.assertIn("Started", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_stop_service_success(self, mock_run):
        """Stop returns success result."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceExplorer.stop_service("sshd")

        self.assertTrue(result.success)
        self.assertIn("Stopped", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_restart_service_success(self, mock_run):
        """Restart returns success result."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceExplorer.restart_service("sshd")

        self.assertTrue(result.success)
        self.assertIn("Restarted", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_enable_service_success(self, mock_run):
        """Enable returns success result."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceExplorer.enable_service("sshd")

        self.assertTrue(result.success)
        self.assertIn("Enabled", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_disable_service_success(self, mock_run):
        """Disable returns success result."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceExplorer.disable_service("sshd")

        self.assertTrue(result.success)
        self.assertIn("Disabled", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_mask_service_success(self, mock_run):
        """Mask returns success result."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceExplorer.mask_service("sshd")

        self.assertTrue(result.success)
        self.assertIn("Masked", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_unmask_service_success(self, mock_run):
        """Unmask returns success result."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceExplorer.unmask_service("sshd")

        self.assertTrue(result.success)
        self.assertIn("Unmasked", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_action_failure(self, mock_run):
        """Failing action returns failure result."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Permission denied"
        )

        result = ServiceExplorer.start_service("sshd")

        self.assertFalse(result.success)
        self.assertIn("Failed", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_action_timeout(self, mock_run):
        """Timeout returns failure result."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=30)

        result = ServiceExplorer.start_service("sshd")

        self.assertFalse(result.success)
        self.assertIn("Timed out", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_action_os_error(self, mock_run):
        """OSError returns failure result."""
        mock_run.side_effect = OSError("No such file")

        result = ServiceExplorer.start_service("sshd")

        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch('utils.service_explorer.subprocess.run')
    def test_system_scope_uses_pkexec(self, mock_run):
        """System scope actions use pkexec (PrivilegedCommand)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        ServiceExplorer.start_service("sshd", scope=ServiceScope.SYSTEM)

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "pkexec")

    @patch('utils.service_explorer.subprocess.run')
    def test_user_scope_no_pkexec(self, mock_run):
        """User scope actions don't use pkexec."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        ServiceExplorer.start_service("test", scope=ServiceScope.USER)

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "systemctl")
        self.assertIn("--user", cmd)


class TestServiceExplorerSummary(unittest.TestCase):
    """Tests for ServiceExplorer.get_summary()."""

    @patch('utils.service_explorer.subprocess.run')
    def test_get_summary(self, mock_run):
        """Summary returns correct counts."""
        list_output = (
            "sshd.service          loaded active running OpenSSH\n"
            "crond.service         loaded active running Cron\n"
            "bluetooth.service     loaded inactive dead    Bluetooth\n"
            "bad.service           loaded failed failed   Broken\n"
        )
        enabled_output = "enabled\nenabled\ndisabled\nenabled\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=list_output, stderr=""),
            MagicMock(returncode=0, stdout=enabled_output, stderr=""),
        ]

        summary = ServiceExplorer.get_summary()

        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["active"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["inactive"], 1)
        self.assertEqual(summary["scope"], "system")


class TestServiceResult(unittest.TestCase):
    """Tests for the ServiceResult dataclass."""

    def test_success_result(self):
        """Success result has correct attributes."""
        r = ServiceResult(success=True, message="OK")
        self.assertTrue(r.success)
        self.assertEqual(r.message, "OK")

    def test_failure_result(self):
        """Failure result has correct attributes."""
        r = ServiceResult(success=False, message="Bad")
        self.assertFalse(r.success)


class TestServiceScope(unittest.TestCase):
    """Tests for ServiceScope enum."""

    def test_system_value(self):
        """SYSTEM scope has correct value."""
        self.assertEqual(ServiceScope.SYSTEM.value, "system")

    def test_user_value(self):
        """USER scope has correct value."""
        self.assertEqual(ServiceScope.USER.value, "user")


class TestServiceState(unittest.TestCase):
    """Tests for ServiceState enum."""

    def test_all_states(self):
        """All expected states exist."""
        states = {s.value for s in ServiceState}
        self.assertIn("active", states)
        self.assertIn("inactive", states)
        self.assertIn("failed", states)
        self.assertIn("activating", states)
        self.assertIn("deactivating", states)
        self.assertIn("unknown", states)


if __name__ == '__main__':
    unittest.main()
