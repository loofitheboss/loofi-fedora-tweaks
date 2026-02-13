"""
Tests for additional CLI handlers with low coverage.
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from cli.main import (
    cmd_service,
    cmd_package,
    cmd_firewall,
    cmd_bluetooth,
    cmd_storage,
    cmd_focus_mode,
    cmd_health_history,
    cmd_tuner,
    cmd_snapshot,
    cmd_logs,
)


class TestCLIExtendedHandlers(unittest.TestCase):
    """Coverage-oriented tests for extended CLI command handlers."""

    @patch('cli.main._print')
    def test_service_start_requires_name(self, mock_print):
        """Service start fails without service name."""
        args = argparse.Namespace(action="start", user=False, filter=None, search=None, name=None, lines=50)
        result = cmd_service(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('cli.main.ServiceExplorer.start_service')
    def test_service_start_success(self, mock_start, mock_print):
        """Service start success path returns 0."""
        mock_start.return_value = MagicMock(success=True, message="started")
        args = argparse.Namespace(action="start", user=False, filter=None, search=None, name="sshd", lines=50)
        result = cmd_service(args)
        self.assertEqual(result, 0)
        self.assertTrue(mock_start.called)

    @patch('cli.main._print')
    def test_package_search_requires_query(self, mock_print):
        """Package search requires query/name."""
        args = argparse.Namespace(action="search", query=None, name=None, source=None, search=None, days=7)
        result = cmd_package(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('cli.main.PackageExplorer.install')
    def test_package_install_success(self, mock_install, mock_print):
        """Install path returns success code."""
        mock_install.return_value = MagicMock(success=True, message="ok")
        args = argparse.Namespace(action="install", name="htop", query=None, source=None, search=None, days=7)
        result = cmd_package(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('cli.main.FirewallManager.is_available', return_value=False)
    def test_firewall_unavailable(self, mock_available, mock_print):
        """Firewall command exits when firewalld is unavailable."""
        args = argparse.Namespace(action="status", spec=None)
        result = cmd_firewall(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('cli.main.FirewallManager.open_port')
    @patch('cli.main.FirewallManager.is_available', return_value=True)
    def test_firewall_open_port_default_proto(self, mock_available, mock_open_port, mock_print):
        """open-port infers tcp when protocol is omitted."""
        mock_open_port.return_value = MagicMock(success=True, message="opened")
        args = argparse.Namespace(action="open-port", spec="8080")
        result = cmd_firewall(args)
        self.assertEqual(result, 0)
        mock_open_port.assert_called_once_with("8080", "tcp")

    @patch('cli.main._print')
    @patch('cli.main.BluetoothManager.get_adapter_status')
    def test_bluetooth_status_no_adapter(self, mock_status, mock_print):
        """Status returns error when no adapter exists."""
        mock_status.return_value = MagicMock(adapter_name="", powered=False, discoverable=False, adapter_address="")
        args = argparse.Namespace(action="status")
        result = cmd_bluetooth(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    def test_bluetooth_connect_requires_address(self, mock_print):
        """Connection actions require a device address."""
        args = argparse.Namespace(action="connect", address=None)
        result = cmd_bluetooth(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    def test_storage_smart_requires_device(self, mock_print):
        """SMART command requires explicit device."""
        args = argparse.Namespace(action="smart", device=None)
        result = cmd_storage(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('cli.main.StorageManager.trim_ssd')
    def test_storage_trim_success(self, mock_trim, mock_print):
        """SSD trim success path returns 0."""
        mock_trim.return_value = MagicMock(success=True, message="trimmed")
        args = argparse.Namespace(action="trim")
        result = cmd_storage(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('cli.main.FocusMode.list_profiles', return_value=["default", "deep-work"])
    @patch('cli.main.FocusMode.get_active_profile', return_value="default")
    @patch('cli.main.FocusMode.is_active', return_value=True)
    def test_focus_mode_status(self, mock_active, mock_active_profile, mock_profiles, mock_print):
        """Focus mode status command returns success."""
        args = argparse.Namespace(action="status", profile="default")
        result = cmd_focus_mode(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('cli.main.HealthTimeline')
    def test_health_history_show_empty(self, mock_timeline_cls, mock_print):
        """health-history show returns 0 for empty summary."""
        mock_timeline_cls.return_value.get_summary.return_value = {}
        args = argparse.Namespace(action="show", path=None)
        result = cmd_health_history(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('cli.main.HealthTimeline')
    def test_health_history_record_success(self, mock_timeline_cls, mock_print):
        """health-history record uses result.success for exit code."""
        mock_timeline_cls.return_value.record_snapshot.return_value = MagicMock(success=True, message="ok", data={})
        args = argparse.Namespace(action="record", path=None)
        result = cmd_health_history(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('cli.main.HealthTimeline')
    def test_health_history_export_requires_path(self, mock_timeline_cls, mock_print):
        """health-history export requires path."""
        args = argparse.Namespace(action="export", path=None)
        result = cmd_health_history(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('utils.auto_tuner.AutoTuner.get_current_settings', return_value={"governor": "balanced"})
    @patch('utils.auto_tuner.AutoTuner.recommend')
    @patch('utils.auto_tuner.AutoTuner.detect_workload')
    def test_tuner_analyze_success(self, mock_detect, mock_recommend, mock_settings, mock_print):
        """tuner analyze succeeds with mocked workload and recommendation."""
        mock_detect.return_value = MagicMock(name="desktop", cpu_percent=10.0, memory_percent=30.0, description="light")
        mock_recommend.return_value = MagicMock(governor="balanced", swappiness=20, io_scheduler="mq-deadline", thp="madvise", reason="ok")
        args = argparse.Namespace(action="analyze")
        result = cmd_tuner(args)
        self.assertEqual(result, 0)

    @patch('cli.main.run_operation', return_value=True)
    @patch('utils.auto_tuner.AutoTuner.apply_swappiness', return_value=("pkexec", ["sysctl", "-w", "vm.swappiness=20"], "set"))
    @patch('utils.auto_tuner.AutoTuner.apply_recommendation', return_value=("pkexec", ["cmd"], "apply"))
    @patch('utils.auto_tuner.AutoTuner.recommend')
    @patch('cli.main._print')
    def test_tuner_apply_runs_two_operations_on_success(self, mock_print, mock_recommend, mock_apply_rec, mock_apply_swap, mock_run_op):
        """tuner apply runs recommendation and swappiness ops when first succeeds."""
        mock_recommend.return_value = MagicMock(governor="performance", swappiness=10)
        args = argparse.Namespace(action="apply")
        result = cmd_tuner(args)
        self.assertEqual(result, 0)
        self.assertEqual(mock_run_op.call_count, 2)

    @patch('cli.main._print')
    @patch('utils.auto_tuner.AutoTuner.get_tuning_history', return_value=[])
    def test_tuner_history_empty(self, mock_history, mock_print):
        """tuner history returns 0 when history is empty."""
        args = argparse.Namespace(action="history")
        result = cmd_tuner(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.snapshot_manager.SnapshotManager.list_snapshots', return_value=[])
    def test_snapshot_list_empty(self, mock_list, mock_print):
        """snapshot list returns 0 with no snapshots."""
        args = argparse.Namespace(action="list", label=None, snapshot_id=None)
        result = cmd_snapshot(args)
        self.assertEqual(result, 0)

    @patch('cli.main.run_operation', return_value=True)
    @patch('utils.snapshot_manager.SnapshotManager.create_snapshot', return_value=("pkexec", ["cmd"], "create"))
    @patch('cli.main._print')
    def test_snapshot_create_success(self, mock_print, mock_create, mock_run_op):
        """snapshot create success path exits 0."""
        args = argparse.Namespace(action="create", label="manual", snapshot_id=None)
        result = cmd_snapshot(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    def test_snapshot_delete_requires_id(self, mock_print):
        """snapshot delete requires snapshot_id."""
        args = argparse.Namespace(action="delete", snapshot_id=None, label=None)
        result = cmd_snapshot(args)
        self.assertEqual(result, 1)

    @patch('utils.smart_logs.SmartLogViewer.get_logs', return_value=[])
    def test_logs_show_empty(self, mock_logs):
        """logs show returns 0 for empty entries."""
        args = argparse.Namespace(action="show", unit=None, priority=None, since=None, lines=50, path=None)
        result = cmd_logs(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.smart_logs.SmartLogViewer.get_error_summary')
    def test_logs_errors_summary(self, mock_summary, mock_print):
        """logs errors returns 0 with summary object."""
        mock_summary.return_value = MagicMock(
            total_entries=1,
            critical_count=0,
            error_count=1,
            warning_count=0,
            top_units=[],
            detected_patterns=[],
        )
        args = argparse.Namespace(action="errors", since="24h ago", lines=50, unit=None, priority=None, path=None)
        result = cmd_logs(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    def test_logs_export_requires_path(self, mock_print):
        """logs export requires destination path."""
        args = argparse.Namespace(action="export", path=None, since=None, lines=100, unit=None, priority=None)
        result = cmd_logs(args)
        self.assertEqual(result, 1)


if __name__ == '__main__':
    unittest.main()
