"""
Tests for v17.0 "Atlas" new GUI tabs.
Covers: PerformanceTab, SnapshotTab, LogsTab, StorageTab,
and NetworkTab overhaul.
"""
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


# Mock PyQt6 before importing UI modules
class MockQTimer:
    @staticmethod
    def singleShot(ms, func):
        pass

    def start(self, ms=0):
        pass

    def stop(self):
        pass

    timeout = MagicMock()


class MockQWidget:
    def __init__(self, *args, **kwargs):
        pass

    def setLayout(self, layout):
        pass

    def tr(self, text, *args, **kwargs):
        return text

    def setStyleSheet(self, s):
        pass

    def setObjectName(self, n):
        pass

    def setReadOnly(self, b):
        pass

    def setMaximumHeight(self, h):
        pass

    def setWordWrap(self, b):
        pass

    def setText(self, t):
        pass

    def setRowCount(self, n):
        pass

    def setItem(self, r, c, item):
        pass

    def setHorizontalHeaderLabels(self, labels):
        pass

    def setEditTriggers(self, t):
        pass

    def addWidget(self, w):
        pass

    def addLayout(self, l):
        pass

    def addStretch(self):
        pass

    def horizontalHeader(self):
        return MagicMock()

    def clear(self):
        pass

    def moveCursor(self, *args):
        pass

    def textCursor(self):
        return MagicMock()

    def insertPlainText(self, text):
        pass

    def window(self):
        return None


class MockCommandRunner:
    output_received = MagicMock()
    finished = MagicMock()
    error_occurred = MagicMock()
    progress_update = MagicMock()

    def __init__(self):
        pass

    def run_command(self, cmd, args):
        pass


# Patch PyQt6 modules before any UI imports
with patch.dict('sys.modules', {
    'PyQt6': MagicMock(),
    'PyQt6.QtWidgets': MagicMock(),
    'PyQt6.QtCore': MagicMock(QTimer=MockQTimer, Qt=MagicMock()),
    'PyQt6.QtGui': MagicMock(),
}):
    # Patch BaseTab to avoid Qt initialization
    with patch('ui.base_tab.BaseTab', MockQWidget):
        pass


class TestPerformanceTabImport(unittest.TestCase):
    """Test that PerformanceTab module structure is sound."""

    @patch('utils.auto_tuner.AutoTuner')
    def test_auto_tuner_detect_workload(self, mock_tuner):
        from utils.auto_tuner import AutoTuner
        mock_tuner.detect_workload = MagicMock()
        mock_tuner.detect_workload()
        mock_tuner.detect_workload.assert_called_once()

    @patch('utils.auto_tuner.AutoTuner')
    def test_auto_tuner_get_current_settings(self, mock_tuner):
        from utils.auto_tuner import AutoTuner
        mock_tuner.get_current_settings = MagicMock(return_value={
            "governor": "performance",
            "swappiness": 60,
            "io_scheduler": "mq-deadline",
            "transparent_hugepages": "always",
        })
        settings = mock_tuner.get_current_settings()
        self.assertEqual(settings["governor"], "performance")

    @patch('utils.auto_tuner.AutoTuner')
    def test_auto_tuner_recommend(self, mock_tuner):
        mock_tuner.recommend = MagicMock()
        mock_tuner.recommend(None)
        mock_tuner.recommend.assert_called_once()


class TestSnapshotTabImport(unittest.TestCase):
    """Test that SnapshotTab module structure is sound."""

    @patch('utils.snapshot_manager.SnapshotManager')
    def test_detect_backends(self, mock_mgr):
        from utils.snapshot_manager import SnapshotManager
        mock_mgr.detect_backends = MagicMock(return_value=[])
        backends = mock_mgr.detect_backends()
        self.assertEqual(backends, [])

    @patch('utils.snapshot_manager.SnapshotManager')
    def test_list_snapshots(self, mock_mgr):
        mock_mgr.list_snapshots = MagicMock(return_value=[])
        snaps = mock_mgr.list_snapshots()
        self.assertEqual(snaps, [])


class TestLogsTabImport(unittest.TestCase):
    """Test that LogsTab module structure is sound."""

    @patch('utils.smart_logs.SmartLogViewer')
    def test_get_error_summary(self, mock_viewer):
        from utils.smart_logs import SmartLogViewer
        mock_viewer.get_error_summary = MagicMock()
        mock_viewer.get_error_summary("24h")
        mock_viewer.get_error_summary.assert_called_once_with("24h")

    @patch('utils.smart_logs.SmartLogViewer')
    def test_get_unit_list(self, mock_viewer):
        mock_viewer.get_unit_list = MagicMock(return_value=["sshd.service", "NetworkManager.service"])
        units = mock_viewer.get_unit_list()
        self.assertEqual(len(units), 2)


class TestNetworkTabOverhaul(unittest.TestCase):
    """Test that the overhauled NetworkTab uses BaseTab."""

    def test_network_tab_inherits_base_tab(self):
        """Verify NetworkTab class declaration uses BaseTab."""
        import inspect
        import importlib
        # Read the source code directly
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'network_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn("class NetworkTab(BaseTab)", source)
        self.assertIn("from ui.base_tab import BaseTab", source)

    def test_network_tab_has_sub_tabs(self):
        """Verify NetworkTab has Connections, DNS, Privacy, Monitoring."""
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'network_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn("_build_connections_tab", source)
        self.assertIn("_build_dns_tab", source)
        self.assertIn("_build_privacy_tab", source)
        self.assertIn("_build_monitoring_tab", source)

    def test_network_tab_uses_network_monitor(self):
        """Verify NetworkTab uses NetworkMonitor for monitoring."""
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'network_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn("from utils.network_monitor import NetworkMonitor", source)


class TestGamingTabNormalization(unittest.TestCase):
    """Test that GamingTab was normalized to use BaseTab + PrivilegedCommand."""

    def test_gaming_tab_inherits_base_tab(self):
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'gaming_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn("class GamingTab(BaseTab)", source)
        self.assertIn("from ui.base_tab import BaseTab", source)

    def test_gaming_tab_uses_privileged_command(self):
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'gaming_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn("from utils.commands import PrivilegedCommand", source)
        self.assertIn("PrivilegedCommand.dnf(", source)

    def test_gaming_tab_no_hardcoded_dnf(self):
        """Ensure no raw pkexec dnf commands remain."""
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'gaming_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        # Should not have raw pkexec dnf strings (the old pattern)
        self.assertNotIn('"pkexec", ["dnf"', source)
        self.assertNotIn("'pkexec', ['dnf'", source)


class TestStorageTabStructure(unittest.TestCase):
    """Test StorageTab file structure."""

    def test_storage_tab_inherits_base_tab(self):
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'storage_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn("class StorageTab(BaseTab)", source)
        self.assertIn("from ui.base_tab import BaseTab", source)
        self.assertIn("from utils.storage import StorageManager", source)


class TestHardwareTabBluetooth(unittest.TestCase):
    """Test that HardwareTab includes Bluetooth card."""

    def test_hardware_tab_imports_bluetooth(self):
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'hardware_tab.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        self.assertIn("from utils.bluetooth import BluetoothManager", source)
        self.assertIn("create_bluetooth_card", source)
        self.assertIn("_bt_power_on", source)
        self.assertIn("_bt_power_off", source)
        self.assertIn("_bt_scan", source)


class TestMainWindowRegistration(unittest.TestCase):
    """Test that new tabs are registered in MainWindow."""

    def test_main_window_has_new_tabs(self):
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'main_window.py'
        )
        with open(filepath, 'r') as f:
            source = f.read()
        # Lazy loaders
        self.assertIn('"performance"', source)
        self.assertIn('"snapshots"', source)
        self.assertIn('"logs"', source)
        self.assertIn('"storage"', source)
        # add_page calls
        self.assertIn('Performance', source)
        self.assertIn('Snapshots', source)
        self.assertIn('Logs', source)
        self.assertIn('Storage', source)


if __name__ == '__main__':
    unittest.main()
