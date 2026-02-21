"""
Extended tests for DriftDetector - Configuration drift detection.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.drift import DriftDetector, DriftItem, DriftReport, SystemSnapshot


class TestDriftItemDataclass(unittest.TestCase):
    """Tests for DriftItem dataclass."""

    def test_drift_item_creation(self):
        """DriftItem stores all required fields."""
        item = DriftItem(
            category="kernel",
            setting="quiet",
            expected="set",
            actual="not set",
            severity="warning"
        )

        self.assertEqual(item.category, "kernel")
        self.assertEqual(item.setting, "quiet")
        self.assertEqual(item.expected, "set")
        self.assertEqual(item.actual, "not set")
        self.assertEqual(item.severity, "warning")


class TestDriftReportDataclass(unittest.TestCase):
    """Tests for DriftReport dataclass."""

    def test_drift_report_creation(self):
        """DriftReport stores all required fields."""
        items = [DriftItem("kernel", "test", "a", "b", "info")]
        report = DriftReport(
            preset_name="gaming",
            applied_at="2024-01-01T00:00:00",
            checked_at="2024-01-02T00:00:00",
            is_drifted=True,
            drift_count=1,
            items=items
        )

        self.assertEqual(report.preset_name, "gaming")
        self.assertTrue(report.is_drifted)
        self.assertEqual(report.drift_count, 1)
        self.assertEqual(len(report.items), 1)


class TestSystemSnapshotDataclass(unittest.TestCase):
    """Tests for SystemSnapshot dataclass."""

    def test_system_snapshot_creation(self):
        """SystemSnapshot stores all required fields."""
        snapshot = SystemSnapshot(
            timestamp="2024-01-01T00:00:00",
            preset_name="test",
            preset_hash="abc123",
            kernel_params_hash="hash1",
            installed_packages_hash="hash2",
            enabled_services_hash="hash3",
            dnf_config_hash="hash4",
            sysctl_hash="hash5",
            kernel_params=["quiet", "splash"],
            layered_packages=["vim", "git"],
            user_services=["ssh-agent.service"]
        )

        self.assertEqual(snapshot.preset_name, "test")
        self.assertEqual(len(snapshot.kernel_params), 2)
        self.assertEqual(len(snapshot.layered_packages), 2)


class TestDriftDetectorInit(unittest.TestCase):
    """Tests for DriftDetector initialization."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_snapshots_dir = DriftDetector.SNAPSHOTS_DIR
        self.original_current_snapshot = DriftDetector.CURRENT_SNAPSHOT

        DriftDetector.SNAPSHOTS_DIR = Path(self.temp_dir) / "snapshots"
        DriftDetector.CURRENT_SNAPSHOT = DriftDetector.SNAPSHOTS_DIR / "current.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        DriftDetector.SNAPSHOTS_DIR = self.original_snapshots_dir
        DriftDetector.CURRENT_SNAPSHOT = self.original_current_snapshot

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_snapshots_directory(self):
        """__init__ creates the snapshots directory."""
        self.assertFalse(DriftDetector.SNAPSHOTS_DIR.exists())
        DriftDetector()
        self.assertTrue(DriftDetector.SNAPSHOTS_DIR.exists())


class TestCaptureSnapshot(unittest.TestCase):
    """Tests for capture_snapshot method."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_snapshots_dir = DriftDetector.SNAPSHOTS_DIR
        self.original_current_snapshot = DriftDetector.CURRENT_SNAPSHOT

        DriftDetector.SNAPSHOTS_DIR = Path(self.temp_dir) / "snapshots"
        DriftDetector.CURRENT_SNAPSHOT = DriftDetector.SNAPSHOTS_DIR / "current.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        DriftDetector.SNAPSHOTS_DIR = self.original_snapshots_dir
        DriftDetector.CURRENT_SNAPSHOT = self.original_current_snapshot

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.object(DriftDetector, '_get_kernel_params', return_value=['quiet', 'splash'])
    @patch.object(DriftDetector, '_get_layered_packages', return_value=['vim'])
    @patch.object(DriftDetector, '_get_user_services', return_value=['ssh-agent.service'])
    @patch.object(DriftDetector, '_get_dnf_config', return_value='[main]\nmax_parallel_downloads=10')
    @patch.object(DriftDetector, '_get_sysctl_values', return_value='vm.swappiness=60')
    def test_capture_snapshot_returns_snapshot(self, mock_sysctl, mock_dnf, mock_services, mock_packages, mock_kernel):
        """capture_snapshot returns a complete SystemSnapshot."""
        detector = DriftDetector()
        snapshot = detector.capture_snapshot("test_preset")

        self.assertIsInstance(snapshot, SystemSnapshot)
        self.assertEqual(snapshot.preset_name, "test_preset")
        self.assertEqual(snapshot.kernel_params, ['quiet', 'splash'])
        self.assertEqual(snapshot.layered_packages, ['vim'])
        self.assertEqual(snapshot.user_services, ['ssh-agent.service'])

    @patch.object(DriftDetector, '_get_kernel_params', return_value=[])
    @patch.object(DriftDetector, '_get_layered_packages', return_value=[])
    @patch.object(DriftDetector, '_get_user_services', return_value=[])
    @patch.object(DriftDetector, '_get_dnf_config', return_value='')
    @patch.object(DriftDetector, '_get_sysctl_values', return_value='')
    def test_capture_snapshot_handles_empty_state(self, mock_sysctl, mock_dnf, mock_services, mock_packages, mock_kernel):
        """capture_snapshot handles empty system state."""
        detector = DriftDetector()
        snapshot = detector.capture_snapshot()

        self.assertIsInstance(snapshot, SystemSnapshot)
        self.assertEqual(snapshot.preset_name, "manual")


class TestSaveAndLoadSnapshot(unittest.TestCase):
    """Tests for save_snapshot and load_snapshot methods."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_snapshots_dir = DriftDetector.SNAPSHOTS_DIR
        self.original_current_snapshot = DriftDetector.CURRENT_SNAPSHOT

        DriftDetector.SNAPSHOTS_DIR = Path(self.temp_dir) / "snapshots"
        DriftDetector.CURRENT_SNAPSHOT = DriftDetector.SNAPSHOTS_DIR / "current.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        DriftDetector.SNAPSHOTS_DIR = self.original_snapshots_dir
        DriftDetector.CURRENT_SNAPSHOT = self.original_current_snapshot

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_snapshot_roundtrip(self):
        """save_snapshot and load_snapshot preserve snapshot data."""
        snapshot = SystemSnapshot(
            timestamp="2024-01-01T00:00:00",
            preset_name="test",
            preset_hash="abc123",
            kernel_params_hash="hash1",
            installed_packages_hash="hash2",
            enabled_services_hash="hash3",
            dnf_config_hash="hash4",
            sysctl_hash="hash5",
            kernel_params=["quiet"],
            layered_packages=["vim"],
            user_services=["test.service"]
        )

        detector = DriftDetector()
        result = detector.save_snapshot(snapshot)
        self.assertTrue(result)

        loaded = detector.load_snapshot()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.preset_name, "test")
        self.assertEqual(loaded.kernel_params, ["quiet"])

    def test_load_snapshot_returns_none_when_missing(self):
        """load_snapshot returns None when no snapshot exists."""
        detector = DriftDetector()
        result = detector.load_snapshot()
        self.assertIsNone(result)


class TestCheckDrift(unittest.TestCase):
    """Tests for check_drift method."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_snapshots_dir = DriftDetector.SNAPSHOTS_DIR
        self.original_current_snapshot = DriftDetector.CURRENT_SNAPSHOT

        DriftDetector.SNAPSHOTS_DIR = Path(self.temp_dir) / "snapshots"
        DriftDetector.CURRENT_SNAPSHOT = DriftDetector.SNAPSHOTS_DIR / "current.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        DriftDetector.SNAPSHOTS_DIR = self.original_snapshots_dir
        DriftDetector.CURRENT_SNAPSHOT = self.original_current_snapshot

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_drift_returns_none_without_baseline(self):
        """check_drift returns None when no baseline exists."""
        detector = DriftDetector()
        result = detector.check_drift()
        self.assertIsNone(result)

    @patch.object(DriftDetector, '_get_kernel_params', return_value=['quiet', 'splash'])
    @patch.object(DriftDetector, '_get_layered_packages', return_value=['vim'])
    @patch.object(DriftDetector, '_get_user_services', return_value=['test.service'])
    @patch.object(DriftDetector, '_get_dnf_config', return_value='')
    @patch.object(DriftDetector, '_get_sysctl_values', return_value='')
    def test_check_drift_no_drift(self, mock_sysctl, mock_dnf, mock_services, mock_packages, mock_kernel):
        """check_drift returns report with no drift when state unchanged."""
        detector = DriftDetector()

        # Capture and save baseline
        baseline = detector.capture_snapshot("test")
        detector.save_snapshot(baseline)

        # Check drift (same state)
        report = detector.check_drift()

        self.assertIsNotNone(report)
        self.assertFalse(report.is_drifted)
        self.assertEqual(report.drift_count, 0)

    @patch.object(DriftDetector, '_get_dnf_config', return_value='')
    @patch.object(DriftDetector, '_get_sysctl_values', return_value='')
    def test_check_drift_detects_kernel_param_added(self, mock_sysctl, mock_dnf):
        """check_drift detects added kernel parameter."""
        detector = DriftDetector()

        # Create baseline
        baseline = SystemSnapshot(
            timestamp="2024-01-01T00:00:00",
            preset_name="test",
            preset_hash="abc",
            kernel_params_hash="oldhash",
            installed_packages_hash="pkghash",
            enabled_services_hash="svchash",
            dnf_config_hash="dnfhash",
            sysctl_hash="sysctlhash",
            kernel_params=["quiet"],
            layered_packages=["vim"],
            user_services=[]
        )
        detector.save_snapshot(baseline)

        # Mock current state with new param
        with patch.object(DriftDetector, '_get_kernel_params', return_value=['quiet', 'nouveau.modeset=0']):
            with patch.object(DriftDetector, '_get_layered_packages', return_value=['vim']):
                with patch.object(DriftDetector, '_get_user_services', return_value=[]):
                    report = detector.check_drift()

        self.assertTrue(report.is_drifted)
        self.assertGreater(report.drift_count, 0)
        kernel_drifts = [d for d in report.items if d.category == "kernel"]
        self.assertGreater(len(kernel_drifts), 0)

    @patch.object(DriftDetector, '_get_dnf_config', return_value='')
    @patch.object(DriftDetector, '_get_sysctl_values', return_value='')
    def test_check_drift_detects_package_removed(self, mock_sysctl, mock_dnf):
        """check_drift detects removed package."""
        detector = DriftDetector()

        # Create baseline with package
        baseline = SystemSnapshot(
            timestamp="2024-01-01T00:00:00",
            preset_name="test",
            preset_hash="abc",
            kernel_params_hash="khash",
            installed_packages_hash="oldhash",
            enabled_services_hash="svchash",
            dnf_config_hash="dnfhash",
            sysctl_hash="sysctlhash",
            kernel_params=["quiet"],
            layered_packages=["vim", "git"],
            user_services=[]
        )
        detector.save_snapshot(baseline)

        # Mock current state with package removed
        with patch.object(DriftDetector, '_get_kernel_params', return_value=['quiet']):
            with patch.object(DriftDetector, '_get_layered_packages', return_value=['vim']):
                with patch.object(DriftDetector, '_get_user_services', return_value=[]):
                    report = detector.check_drift()

        self.assertTrue(report.is_drifted)
        pkg_drifts = [d for d in report.items if d.category == "packages"]
        self.assertGreater(len(pkg_drifts), 0)


class TestClearBaseline(unittest.TestCase):
    """Tests for clear_baseline method."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_snapshots_dir = DriftDetector.SNAPSHOTS_DIR
        self.original_current_snapshot = DriftDetector.CURRENT_SNAPSHOT

        DriftDetector.SNAPSHOTS_DIR = Path(self.temp_dir) / "snapshots"
        DriftDetector.CURRENT_SNAPSHOT = DriftDetector.SNAPSHOTS_DIR / "current.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        DriftDetector.SNAPSHOTS_DIR = self.original_snapshots_dir
        DriftDetector.CURRENT_SNAPSHOT = self.original_current_snapshot

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clear_baseline_removes_snapshot(self):
        """clear_baseline removes the current snapshot file."""
        detector = DriftDetector()

        # Create a snapshot file
        DriftDetector.CURRENT_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        DriftDetector.CURRENT_SNAPSHOT.write_text("{}")

        self.assertTrue(DriftDetector.CURRENT_SNAPSHOT.exists())
        result = detector.clear_baseline()
        self.assertTrue(result)
        self.assertFalse(DriftDetector.CURRENT_SNAPSHOT.exists())

    def test_clear_baseline_returns_true_when_no_file(self):
        """clear_baseline returns True even when no snapshot exists."""
        detector = DriftDetector()
        result = detector.clear_baseline()
        self.assertTrue(result)


class TestSystemStateGathering(unittest.TestCase):
    """Tests for system state gathering methods."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_snapshots_dir = DriftDetector.SNAPSHOTS_DIR
        self.original_current_snapshot = DriftDetector.CURRENT_SNAPSHOT

        DriftDetector.SNAPSHOTS_DIR = Path(self.temp_dir) / "snapshots"
        DriftDetector.CURRENT_SNAPSHOT = DriftDetector.SNAPSHOTS_DIR / "current.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        DriftDetector.SNAPSHOTS_DIR = self.original_snapshots_dir
        DriftDetector.CURRENT_SNAPSHOT = self.original_current_snapshot

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('builtins.open', new_callable=MagicMock)
    def test_get_kernel_params_reads_cmdline(self, mock_open):
        """_get_kernel_params reads from /proc/cmdline."""
        mock_file = MagicMock()
        mock_file.read.return_value = "BOOT_IMAGE=... quiet splash"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_file

        detector = DriftDetector()
        params = detector._get_kernel_params()

        self.assertIn("quiet", params)
        self.assertIn("splash", params)

    @patch('builtins.open')
    def test_get_kernel_params_returns_empty_on_error(self, mock_open):
        """_get_kernel_params returns empty list on error."""
        mock_open.side_effect = OSError("Read error")

        detector = DriftDetector()
        params = detector._get_kernel_params()

        self.assertEqual(params, [])

    @patch('utils.drift.subprocess.run')
    def test_get_layered_packages_parses_rpm_ostree(self, mock_run):
        """_get_layered_packages parses rpm-ostree output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "deployments": [
                    {"requested-packages": ["vim", "git", "htop"]}
                ]
            })
        )

        detector = DriftDetector()
        packages = detector._get_layered_packages()

        self.assertIn("vim", packages)
        self.assertIn("git", packages)

    @patch('utils.drift.subprocess.run')
    def test_get_user_services_parses_systemctl(self, mock_run):
        """_get_user_services parses systemctl output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ssh-agent.service enabled\ngpg-agent.service enabled\n"
        )

        detector = DriftDetector()
        services = detector._get_user_services()

        self.assertIn("ssh-agent.service", services)

    @patch('builtins.open', new_callable=MagicMock)
    def test_get_dnf_config_reads_config_file(self, mock_open):
        """_get_dnf_config reads from /etc/dnf/dnf.conf."""
        mock_file = MagicMock()
        mock_file.read.return_value = "[main]\nmax_parallel_downloads=10"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_file

        detector = DriftDetector()
        config = detector._get_dnf_config()

        self.assertIn("max_parallel_downloads", config)


class TestHashFunctions(unittest.TestCase):
    """Tests for hash helper functions."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_snapshots_dir = DriftDetector.SNAPSHOTS_DIR
        self.original_current_snapshot = DriftDetector.CURRENT_SNAPSHOT

        DriftDetector.SNAPSHOTS_DIR = Path(self.temp_dir) / "snapshots"
        DriftDetector.CURRENT_SNAPSHOT = DriftDetector.SNAPSHOTS_DIR / "current.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        DriftDetector.SNAPSHOTS_DIR = self.original_snapshots_dir
        DriftDetector.CURRENT_SNAPSHOT = self.original_current_snapshot

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hash_string_deterministic(self):
        """_hash_string produces deterministic output."""
        detector = DriftDetector()
        hash1 = detector._hash_string("test")
        hash2 = detector._hash_string("test")
        self.assertEqual(hash1, hash2)

    def test_hash_string_different_inputs(self):
        """_hash_string produces different output for different inputs."""
        detector = DriftDetector()
        hash1 = detector._hash_string("test1")
        hash2 = detector._hash_string("test2")
        self.assertNotEqual(hash1, hash2)

    def test_hash_string_length(self):
        """_hash_string returns first 16 characters of SHA256."""
        detector = DriftDetector()
        result = detector._hash_string("test")
        self.assertEqual(len(result), 16)

    def test_hash_list_deterministic(self):
        """_hash_list produces deterministic output."""
        detector = DriftDetector()
        hash1 = detector._hash_list(["a", "b", "c"])
        hash2 = detector._hash_list(["a", "b", "c"])
        self.assertEqual(hash1, hash2)

    def test_hash_list_order_independent(self):
        """_hash_list produces same hash regardless of order (sorted)."""
        detector = DriftDetector()
        hash1 = detector._hash_list(["c", "a", "b"])
        hash2 = detector._hash_list(["a", "b", "c"])
        self.assertEqual(hash1, hash2)


if __name__ == '__main__':
    unittest.main()
