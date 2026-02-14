"""
Enhanced CLI tests for Loofi Fedora Tweaks.
Tests all CLI subcommands with mocked subprocess and system calls.
"""
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os
from io import StringIO

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from cli.main import (
    main, cmd_info, cmd_health, cmd_disk, cmd_processes,
    cmd_temperature, cmd_netmon, cmd_cleanup, cmd_tweak,
    cmd_advanced, cmd_network, run_operation,
)
from utils.operations import OperationResult
from services.system import ProcessInfo
from services.hardware import TemperatureSensor
from utils.network_monitor import InterfaceStats


class TestCLIArgParsing(unittest.TestCase):
    """Tests that the CLI arg parser routes to the correct subcommand."""

    @patch('cli.main.cmd_info', return_value=0)
    def test_info_command_dispatched(self, mock_cmd):
        """'info' subcommand is dispatched to cmd_info."""
        result = main(["info"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_health', return_value=0)
    def test_health_command_dispatched(self, mock_cmd):
        """'health' subcommand is dispatched to cmd_health."""
        result = main(["health"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_disk', return_value=0)
    def test_disk_command_dispatched(self, mock_cmd):
        """'disk' subcommand is dispatched to cmd_disk."""
        result = main(["disk"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_processes', return_value=0)
    def test_processes_command_dispatched(self, mock_cmd):
        """'processes' subcommand is dispatched to cmd_processes."""
        result = main(["processes"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_temperature', return_value=0)
    def test_temperature_command_dispatched(self, mock_cmd):
        """'temperature' subcommand is dispatched to cmd_temperature."""
        result = main(["temperature"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_netmon', return_value=0)
    def test_netmon_command_dispatched(self, mock_cmd):
        """'netmon' subcommand is dispatched to cmd_netmon."""
        result = main(["netmon"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_cleanup', return_value=0)
    def test_cleanup_command_dispatched(self, mock_cmd):
        """'cleanup' subcommand is dispatched to cmd_cleanup."""
        result = main(["cleanup"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_tweak', return_value=0)
    def test_tweak_command_dispatched(self, mock_cmd):
        """'tweak power' subcommand is dispatched to cmd_tweak."""
        result = main(["tweak", "power"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_advanced', return_value=0)
    def test_advanced_command_dispatched(self, mock_cmd):
        """'advanced bbr' subcommand is dispatched to cmd_advanced."""
        result = main(["advanced", "bbr"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    @patch('cli.main.cmd_network', return_value=0)
    def test_network_command_dispatched(self, mock_cmd):
        """'network dns' subcommand is dispatched to cmd_network."""
        result = main(["network", "dns"])
        mock_cmd.assert_called_once()
        self.assertEqual(result, 0)

    def test_no_command_prints_help(self):
        """No subcommand prints help and returns 0."""
        result = main([])
        self.assertEqual(result, 0)


class TestCLIRunOperation(unittest.TestCase):
    """Tests for the run_operation helper that executes command tuples."""

    @patch('subprocess.run')
    def test_run_operation_success(self, mock_run):
        """Successful command returns True."""
        mock_run.return_value = MagicMock(returncode=0, stdout="done\n", stderr="")
        result = run_operation(("pkexec", ["dnf", "clean", "all"], "Cleaning..."))
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pkexec", "dnf", "clean", "all"],
            capture_output=True, text=True, check=False,
            timeout=300,
        )

    @patch('subprocess.run')
    def test_run_operation_failure(self, mock_run):
        """Failed command returns False."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error occurred")
        result = run_operation(("pkexec", ["fstrim", "-av"], "Trimming..."))
        self.assertFalse(result)

    @patch('subprocess.run', side_effect=FileNotFoundError("pkexec not found"))
    def test_run_operation_exception(self, mock_run):
        """Exception during command execution returns False."""
        result = run_operation(("pkexec", ["dnf", "update"], "Updating..."))
        self.assertFalse(result)


class TestCLIInfoCommand(unittest.TestCase):
    """Tests for the 'info' CLI subcommand."""

    @patch('cli.main.SystemManager.has_pending_deployment', return_value=False)
    @patch('cli.main.SystemManager.is_atomic', return_value=False)
    @patch('cli.main.SystemManager.get_package_manager', return_value='dnf')
    @patch('cli.main.TweakOps.get_power_profile', return_value='balanced')
    def test_info_traditional_system(self, mock_power, mock_pm, mock_atomic,
                                      mock_pending):
        """cmd_info prints system info for traditional Fedora."""
        import argparse
        args = argparse.Namespace()
        result = cmd_info(args)
        self.assertEqual(result, 0)


class TestCLICleanupCommand(unittest.TestCase):
    """Tests for the 'cleanup' CLI subcommand."""

    @patch('subprocess.run')
    @patch('cli.main.CleanupOps.clean_dnf_cache',
           return_value=("pkexec", ["dnf", "clean", "all"], "Cleaning..."))
    @patch('cli.main.CleanupOps.vacuum_journal',
           return_value=("pkexec", ["journalctl", "--vacuum-time=14d"], "Vacuuming..."))
    @patch('cli.main.CleanupOps.trim_ssd',
           return_value=("pkexec", ["fstrim", "-av"], "Trimming..."))
    def test_cleanup_all(self, mock_trim, mock_journal, mock_dnf, mock_run):
        """'cleanup all' runs dnf + journal + trim in sequence."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n", stderr="")
        import argparse
        args = argparse.Namespace(action="all", days=14)
        result = cmd_cleanup(args)
        self.assertEqual(result, 0)
        # Should have called subprocess.run 3 times (dnf, journal, trim)
        self.assertEqual(mock_run.call_count, 3)

    @patch('subprocess.run')
    @patch('cli.main.CleanupOps.clean_dnf_cache',
           return_value=("pkexec", ["dnf", "clean", "all"], "Cleaning..."))
    def test_cleanup_dnf_only(self, mock_dnf, mock_run):
        """'cleanup dnf' runs only DNF cache clean."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        import argparse
        args = argparse.Namespace(action="dnf", days=14)
        result = cmd_cleanup(args)
        self.assertEqual(result, 0)
        self.assertEqual(mock_run.call_count, 1)


class TestCLITweakCommand(unittest.TestCase):
    """Tests for the 'tweak' CLI subcommand."""

    @patch('subprocess.run')
    @patch('cli.main.TweakOps.set_power_profile',
           return_value=("powerprofilesctl", ["set", "performance"], "Setting..."))
    def test_tweak_power(self, mock_tweak, mock_run):
        """'tweak power --profile performance' sets power profile."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        import argparse
        args = argparse.Namespace(action="power", profile="performance", limit=80)
        result = cmd_tweak(args)
        self.assertEqual(result, 0)

    @patch('cli.main.TweakOps.get_power_profile', return_value='balanced')
    @patch('cli.main.SystemManager.is_atomic', return_value=False)
    def test_tweak_status(self, mock_atomic, mock_profile):
        """'tweak status' prints current power profile and system type."""
        import argparse
        args = argparse.Namespace(action="status", profile="balanced", limit=80)
        result = cmd_tweak(args)
        self.assertEqual(result, 0)

    @patch('cli.main.TweakOps.set_battery_limit')
    def test_tweak_battery(self, mock_battery):
        """'tweak battery --limit 80' sets battery charge limit."""
        mock_battery.return_value = OperationResult(True, "Battery limit set to 80%")
        import argparse
        args = argparse.Namespace(action="battery", profile="balanced", limit=80)
        result = cmd_tweak(args)
        self.assertEqual(result, 0)


class TestCLIProcessesCommand(unittest.TestCase):
    """Tests for the 'processes' CLI subcommand."""

    @patch('cli.main.ProcessManager.get_top_by_cpu')
    @patch('cli.main.ProcessManager.get_process_count',
           return_value={"total": 150, "running": 3, "sleeping": 145, "zombie": 2})
    def test_processes_default_cpu_sort(self, mock_count, mock_top):
        """'processes' defaults to top-by-CPU with count 10."""
        mock_top.return_value = [
            ProcessInfo(pid=1, name="systemd", user="root", cpu_percent=5.0,
                        memory_percent=1.0, memory_bytes=8192, state="S",
                        command="/usr/lib/systemd/systemd", nice=0),
        ]
        import argparse
        args = argparse.Namespace(count=10, sort="cpu")
        result = cmd_processes(args)
        self.assertEqual(result, 0)
        mock_top.assert_called_once_with(10)

    @patch('cli.main.ProcessManager.get_top_by_memory')
    @patch('cli.main.ProcessManager.get_process_count',
           return_value={"total": 100, "running": 2, "sleeping": 97, "zombie": 1})
    def test_processes_memory_sort(self, mock_count, mock_top):
        """'processes --sort memory' calls get_top_by_memory."""
        mock_top.return_value = []
        import argparse
        args = argparse.Namespace(count=5, sort="memory")
        result = cmd_processes(args)
        self.assertEqual(result, 0)
        mock_top.assert_called_once_with(5)


class TestCLITemperatureCommand(unittest.TestCase):
    """Tests for the 'temperature' CLI subcommand."""

    @patch('cli.main.TemperatureManager.get_all_sensors')
    def test_temperature_with_sensors(self, mock_sensors):
        """'temperature' prints sensor readings when sensors are present."""
        mock_sensors.return_value = [
            TemperatureSensor(name="coretemp", label="Core 0", current=55.0,
                              high=80.0, critical=100.0, sensor_type="cpu"),
            TemperatureSensor(name="amdgpu", label="GPU Edge", current=62.0,
                              high=90.0, critical=105.0, sensor_type="gpu"),
        ]
        import argparse
        args = argparse.Namespace()
        result = cmd_temperature(args)
        self.assertEqual(result, 0)

    @patch('cli.main.TemperatureManager.get_all_sensors', return_value=[])
    def test_temperature_no_sensors(self, mock_sensors):
        """'temperature' returns 1 when no sensors are found."""
        import argparse
        args = argparse.Namespace()
        result = cmd_temperature(args)
        self.assertEqual(result, 1)


class TestCLINetmonCommand(unittest.TestCase):
    """Tests for the 'netmon' CLI subcommand."""

    @patch('cli.main.NetworkMonitor.get_bandwidth_summary',
           return_value={"total_sent": 5000, "total_recv": 10000,
                         "total_send_rate": 100.0, "total_recv_rate": 200.0})
    @patch('cli.main.NetworkMonitor.get_all_interfaces')
    def test_netmon_with_interfaces(self, mock_ifaces, mock_summary):
        """'netmon' prints interface stats when interfaces are present."""
        mock_ifaces.return_value = [
            InterfaceStats(name="enp3s0", type="ethernet", is_up=True,
                           ip_address="192.168.1.100",
                           bytes_sent=5000, bytes_recv=10000,
                           packets_sent=50, packets_recv=100,
                           send_rate=100.0, recv_rate=200.0),
        ]
        import argparse
        args = argparse.Namespace(connections=False)
        result = cmd_netmon(args)
        self.assertEqual(result, 0)

    @patch('cli.main.NetworkMonitor.get_all_interfaces', return_value=[])
    def test_netmon_no_interfaces(self, mock_ifaces):
        """'netmon' returns 1 when no interfaces are found."""
        import argparse
        args = argparse.Namespace(connections=False)
        result = cmd_netmon(args)
        self.assertEqual(result, 1)


class TestCLIAdvancedCommand(unittest.TestCase):
    """Tests for the 'advanced' CLI subcommand."""

    @patch('subprocess.run')
    @patch('cli.main.AdvancedOps.enable_tcp_bbr',
           return_value=("pkexec", ["sh", "-c", "echo bbr"], "Enabling BBR..."))
    def test_advanced_bbr(self, mock_bbr, mock_run):
        """'advanced bbr' enables TCP BBR."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        import argparse
        args = argparse.Namespace(action="bbr", value=10)
        result = cmd_advanced(args)
        self.assertEqual(result, 0)

    @patch('subprocess.run')
    @patch('cli.main.AdvancedOps.set_swappiness',
           return_value=("pkexec", ["sh", "-c", "echo 10"], "Setting swappiness..."))
    def test_advanced_swappiness(self, mock_swap, mock_run):
        """'advanced swappiness --value 10' sets swappiness."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        import argparse
        args = argparse.Namespace(action="swappiness", value=10)
        result = cmd_advanced(args)
        self.assertEqual(result, 0)


class TestCLINetworkCommand(unittest.TestCase):
    """Tests for the 'network' CLI subcommand."""

    @patch('cli.main.NetworkOps.set_dns')
    def test_network_dns_success(self, mock_dns):
        """'network dns --provider cloudflare' sets DNS successfully."""
        mock_dns.return_value = OperationResult(True, "DNS set to cloudflare")
        import argparse
        args = argparse.Namespace(action="dns", provider="cloudflare")
        result = cmd_network(args)
        self.assertEqual(result, 0)
        mock_dns.assert_called_once_with("cloudflare")

    @patch('cli.main.NetworkOps.set_dns')
    def test_network_dns_failure(self, mock_dns):
        """'network dns' failure returns exit code 1."""
        mock_dns.return_value = OperationResult(False, "No active connection")
        import argparse
        args = argparse.Namespace(action="dns", provider="google")
        result = cmd_network(args)
        self.assertEqual(result, 1)


class TestCLIDiskCommand(unittest.TestCase):
    """Tests for the 'disk' CLI subcommand."""

    @patch('cli.main.DiskManager.check_disk_health', return_value=("ok", "Disk OK"))
    @patch('cli.main.DiskManager.get_disk_usage')
    def test_disk_basic(self, mock_usage, mock_health):
        """'disk' prints root filesystem usage."""
        mock_usage_obj = MagicMock()
        mock_usage_obj.total_human = "500.0 GB"
        mock_usage_obj.used_human = "50.0 GB"
        mock_usage_obj.free_human = "450.0 GB"
        mock_usage_obj.percent_used = 10.0
        mock_usage_obj.mount_point = "/"
        mock_usage.return_value = mock_usage_obj
        import argparse
        args = argparse.Namespace(details=False)
        result = cmd_disk(args)
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
