"""Tests for snapshot manager."""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from subprocess import CalledProcessError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.snapshot_manager import SnapshotManager, SnapshotInfo, SnapshotBackend


# ---------------------------------------------------------------------------
# TestSnapshotInfo
# ---------------------------------------------------------------------------

class TestSnapshotInfo(unittest.TestCase):
    """Tests for SnapshotInfo dataclass."""

    def test_creation(self):
        """Test dataclass creation with all fields."""
        info = SnapshotInfo(
            id="1",
            label="pre-update",
            backend="timeshift",
            timestamp=1700000000.0,
            size_str="1.2 GB",
            description="Pre-update snapshot",
        )
        self.assertEqual(info.id, "1")
        self.assertEqual(info.label, "pre-update")
        self.assertEqual(info.backend, "timeshift")
        self.assertEqual(info.timestamp, 1700000000.0)
        self.assertEqual(info.size_str, "1.2 GB")
        self.assertEqual(info.description, "Pre-update snapshot")

    def test_field_types(self):
        """Test that field types are as expected."""
        info = SnapshotInfo(
            id="42",
            label="snap",
            backend="snapper",
            timestamp=0.0,
            size_str="",
            description="",
        )
        self.assertIsInstance(info.id, str)
        self.assertIsInstance(info.label, str)
        self.assertIsInstance(info.backend, str)
        self.assertIsInstance(info.timestamp, float)
        self.assertIsInstance(info.size_str, str)
        self.assertIsInstance(info.description, str)

    def test_default_values_not_required(self):
        """Test that all fields are positional (no defaults)."""
        # SnapshotInfo has no defaults — all fields are required
        with self.assertRaises(TypeError):
            SnapshotInfo(id="1")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestSnapshotBackend
# ---------------------------------------------------------------------------

class TestSnapshotBackend(unittest.TestCase):
    """Tests for SnapshotBackend dataclass."""

    def test_creation(self):
        """Test dataclass creation with all fields."""
        backend = SnapshotBackend(
            name="snapper",
            available=True,
            command="/usr/bin/snapper",
            version="0.10.0",
        )
        self.assertEqual(backend.name, "snapper")
        self.assertTrue(backend.available)
        self.assertEqual(backend.command, "/usr/bin/snapper")
        self.assertEqual(backend.version, "0.10.0")

    def test_available_state(self):
        """Test backend in available state."""
        backend = SnapshotBackend(
            name="timeshift",
            available=True,
            command="/usr/bin/timeshift",
            version="24.06.3",
        )
        self.assertTrue(backend.available)
        self.assertNotEqual(backend.version, "")

    def test_unavailable_state(self):
        """Test backend in unavailable state."""
        backend = SnapshotBackend(
            name="btrfs",
            available=False,
            command="btrfs",
            version="",
        )
        self.assertFalse(backend.available)
        self.assertEqual(backend.version, "")


# ---------------------------------------------------------------------------
# TestDetectBackends
# ---------------------------------------------------------------------------

class TestDetectBackends(unittest.TestCase):
    """Tests for SnapshotManager.detect_backends."""

    @patch('utils.snapshot_manager.subprocess.run')
    @patch('utils.snapshot_manager.shutil.which')
    def test_all_backends_available(self, mock_which, mock_run):
        """Test detection when snapper, timeshift, and btrfs are all available."""
        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="tool 1.0.0\n",
            stderr="",
        )

        backends = SnapshotManager.detect_backends()

        self.assertEqual(len(backends), 3)
        for b in backends:
            self.assertTrue(b.available)
            self.assertEqual(b.version, "tool 1.0.0")
        names = [b.name for b in backends]
        self.assertEqual(names, ["snapper", "timeshift", "btrfs"])

    @patch('utils.snapshot_manager.subprocess.run')
    @patch('utils.snapshot_manager.shutil.which')
    def test_no_backends(self, mock_which, mock_run):
        """Test detection when no backends are installed."""
        mock_which.return_value = None

        backends = SnapshotManager.detect_backends()

        self.assertEqual(len(backends), 3)
        for b in backends:
            self.assertFalse(b.available)
            self.assertEqual(b.version, "")
        # subprocess.run should not be called when nothing is available
        mock_run.assert_not_called()

    @patch('utils.snapshot_manager.subprocess.run')
    @patch('utils.snapshot_manager.shutil.which')
    def test_snapper_only(self, mock_which, mock_run):
        """Test detection when only snapper is installed."""
        def which_side_effect(name):
            if name == "snapper":
                return "/usr/bin/snapper"
            return None

        mock_which.side_effect = which_side_effect
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="snapper 0.10.0\n",
            stderr="",
        )

        backends = SnapshotManager.detect_backends()

        snapper = [b for b in backends if b.name == "snapper"][0]
        self.assertTrue(snapper.available)
        self.assertEqual(snapper.version, "snapper 0.10.0")

        for b in backends:
            if b.name != "snapper":
                self.assertFalse(b.available)

        # Only one --version call (for snapper)
        mock_run.assert_called_once()

    @patch('utils.snapshot_manager.subprocess.run')
    @patch('utils.snapshot_manager.shutil.which')
    def test_version_detection(self, mock_which, mock_run):
        """Test that --version is called for each available backend."""
        mock_which.side_effect = lambda name: f"/usr/bin/{name}"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="v2.0\n",
            stderr="",
        )

        SnapshotManager.detect_backends()

        self.assertEqual(mock_run.call_count, 3)
        for call_args in mock_run.call_args_list:
            cmd = call_args[0][0]
            self.assertEqual(cmd[1], "--version")

    @patch('utils.snapshot_manager.subprocess.run')
    @patch('utils.snapshot_manager.shutil.which')
    def test_version_detection_failure(self, mock_which, mock_run):
        """Test graceful handling when --version subprocess fails."""
        mock_which.return_value = "/usr/bin/snapper"
        mock_run.side_effect = OSError("No such file or directory")

        backends = SnapshotManager.detect_backends()

        # Should still report as available, but version is "unknown"
        for b in backends:
            self.assertTrue(b.available)
            self.assertEqual(b.version, "unknown")


# ---------------------------------------------------------------------------
# TestGetPreferredBackend
# ---------------------------------------------------------------------------

class TestGetPreferredBackend(unittest.TestCase):
    """Tests for SnapshotManager.get_preferred_backend."""

    @patch('utils.snapshot_manager.shutil.which')
    def test_prefers_snapper(self, mock_which):
        """Test that snapper is preferred when both snapper and timeshift exist."""
        mock_which.side_effect = lambda name: f"/usr/bin/{name}"

        result = SnapshotManager.get_preferred_backend()

        self.assertEqual(result, "snapper")

    @patch('utils.snapshot_manager.shutil.which')
    def test_falls_to_timeshift(self, mock_which):
        """Test fallback to timeshift when snapper is not available."""
        def which_side_effect(name):
            if name == "timeshift":
                return "/usr/bin/timeshift"
            if name == "btrfs":
                return "/usr/sbin/btrfs"
            return None

        mock_which.side_effect = which_side_effect

        result = SnapshotManager.get_preferred_backend()

        self.assertEqual(result, "timeshift")

    @patch('utils.snapshot_manager.shutil.which')
    def test_falls_to_btrfs(self, mock_which):
        """Test fallback to btrfs when snapper and timeshift are not available."""
        def which_side_effect(name):
            if name == "btrfs":
                return "/usr/sbin/btrfs"
            return None

        mock_which.side_effect = which_side_effect

        result = SnapshotManager.get_preferred_backend()

        self.assertEqual(result, "btrfs")

    @patch('utils.snapshot_manager.shutil.which')
    def test_returns_none(self, mock_which):
        """Test returns None when nothing is available."""
        mock_which.return_value = None

        result = SnapshotManager.get_preferred_backend()

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# TestListSnapshots
# ---------------------------------------------------------------------------

class TestListSnapshots(unittest.TestCase):
    """Tests for SnapshotManager.list_snapshots."""

    @patch('utils.snapshot_manager.subprocess.run')
    def test_list_timeshift(self, mock_run):
        """Test parsing of timeshift --list output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Device : /dev/sda2\n"
                "Num     Name                 Tag   Size     Description\n"
                "------------------------------------------------------\n"
                "0  >  2024-01-15_10-00-01  D  1.2 GB  Pre-update snapshot\n"
                "1  >  2024-01-14_08-30-00  O  900 MB  Manual backup\n"
            ),
            stderr="",
        )

        snapshots = SnapshotManager.list_snapshots(backend="timeshift")

        self.assertIsInstance(snapshots, list)
        self.assertGreaterEqual(len(snapshots), 1)
        for snap in snapshots:
            self.assertIsInstance(snap, SnapshotInfo)
            self.assertEqual(snap.backend, "timeshift")

    @patch('utils.snapshot_manager.subprocess.run')
    def test_list_snapper(self, mock_run):
        """Test parsing of snapper list output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                " # | Date                         | Description\n"
                "---+------------------------------+-----------------\n"
                " 1 | 2024-01-15 10:00:01          | first snapshot\n"
                " 2 | 2024-01-16 12:30:00          | second snapshot\n"
            ),
            stderr="",
        )

        snapshots = SnapshotManager.list_snapshots(backend="snapper")

        self.assertIsInstance(snapshots, list)
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0].backend, "snapper")
        # Newest first (snapshot 2 has a later date)
        self.assertGreaterEqual(snapshots[0].timestamp, snapshots[1].timestamp)

    @patch('utils.snapshot_manager.subprocess.run')
    def test_list_empty(self, mock_run):
        """Test handling of no snapshots."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        snapshots = SnapshotManager.list_snapshots(backend="snapper")

        self.assertEqual(snapshots, [])

    @patch('utils.snapshot_manager.shutil.which')
    def test_list_auto_detect_backend(self, mock_which):
        """Test auto-detection when backend is None and nothing is available."""
        mock_which.return_value = None

        snapshots = SnapshotManager.list_snapshots(backend=None)

        self.assertEqual(snapshots, [])

    @patch('utils.snapshot_manager.subprocess.run')
    def test_list_subprocess_error(self, mock_run):
        """Test graceful handling of CalledProcessError during listing."""
        mock_run.side_effect = CalledProcessError(1, "pkexec timeshift --list")

        snapshots = SnapshotManager.list_snapshots(backend="timeshift")

        self.assertEqual(snapshots, [])


# ---------------------------------------------------------------------------
# TestCreateSnapshot
# ---------------------------------------------------------------------------

class TestCreateSnapshot(unittest.TestCase):
    """Tests for SnapshotManager.create_snapshot."""

    def test_create_timeshift(self):
        """Test create returns operation tuple for timeshift backend."""
        cmd, args, desc = SnapshotManager.create_snapshot(
            label="pre-update", backend="timeshift"
        )

        self.assertEqual(cmd, "pkexec")
        self.assertIn("timeshift", args)
        self.assertIn("--create", args)
        self.assertIn("--comments", args)
        self.assertIn("pre-update", args)
        self.assertIsInstance(desc, str)
        self.assertIn("Timeshift", desc)

    def test_create_snapper(self):
        """Test create returns operation tuple for snapper backend."""
        cmd, args, desc = SnapshotManager.create_snapshot(
            label="my-snap", backend="snapper"
        )

        self.assertEqual(cmd, "pkexec")
        self.assertIn("snapper", args)
        self.assertIn("create", args)
        self.assertIn("--description", args)
        self.assertIn("my-snap", args)
        self.assertIn("Snapper", desc)

    def test_create_btrfs(self):
        """Test create returns operation tuple for btrfs backend."""
        cmd, args, desc = SnapshotManager.create_snapshot(
            label="my backup", backend="btrfs"
        )

        self.assertEqual(cmd, "pkexec")
        self.assertIn("btrfs", args)
        self.assertIn("subvolume", args)
        self.assertIn("snapshot", args)
        # Label should be sanitised (spaces → underscores)
        safe = [a for a in args if ".snapshots" in a]
        self.assertTrue(len(safe) > 0)
        self.assertNotIn(" ", safe[0])
        self.assertIn("Btrfs", desc)

    @patch('utils.snapshot_manager.shutil.which')
    def test_create_auto_backend(self, mock_which):
        """Test create auto-detects backend when not specified."""
        mock_which.side_effect = lambda name: "/usr/bin/timeshift" if name == "timeshift" else None

        cmd, args, desc = SnapshotManager.create_snapshot(label="auto-snap")

        self.assertEqual(cmd, "pkexec")
        self.assertIn("timeshift", args)

    @patch('utils.snapshot_manager.shutil.which')
    def test_create_no_backend(self, mock_which):
        """Test create returns echo error when no backend is available."""
        mock_which.return_value = None

        cmd, args, desc = SnapshotManager.create_snapshot(label="fail")

        self.assertEqual(cmd, "echo")
        self.assertIn("No snapshot backend available", args)


# ---------------------------------------------------------------------------
# TestDeleteSnapshot
# ---------------------------------------------------------------------------

class TestDeleteSnapshot(unittest.TestCase):
    """Tests for SnapshotManager.delete_snapshot."""

    def test_delete_returns_tuple(self):
        """Test delete returns a proper operation tuple."""
        result = SnapshotManager.delete_snapshot("5", backend="snapper")

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], str)
        self.assertIsInstance(result[1], list)
        self.assertIsInstance(result[2], str)

    def test_delete_with_id(self):
        """Test delete builds correct arguments for each backend."""
        # Timeshift
        cmd, args, desc = SnapshotManager.delete_snapshot("3", backend="timeshift")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("timeshift", args)
        self.assertIn("--delete", args)
        self.assertIn("3", args)

        # Snapper
        cmd, args, desc = SnapshotManager.delete_snapshot("7", backend="snapper")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("snapper", args)
        self.assertIn("delete", args)
        self.assertIn("7", args)

        # Btrfs
        cmd, args, desc = SnapshotManager.delete_snapshot(
            "/.snapshots/my-snap", backend="btrfs"
        )
        self.assertEqual(cmd, "pkexec")
        self.assertIn("btrfs", args)
        self.assertIn("subvolume", args)
        self.assertIn("delete", args)
        self.assertIn("/.snapshots/my-snap", args)

    @patch('utils.snapshot_manager.shutil.which')
    def test_delete_auto_backend(self, mock_which):
        """Test delete auto-detects backend when not specified."""
        mock_which.side_effect = lambda name: "/usr/bin/snapper" if name == "snapper" else None

        cmd, args, desc = SnapshotManager.delete_snapshot("10")

        self.assertEqual(cmd, "pkexec")
        self.assertIn("snapper", args)
        self.assertIn("10", args)

    @patch('utils.snapshot_manager.shutil.which')
    def test_delete_no_backend(self, mock_which):
        """Test delete returns echo error when no backend is available."""
        mock_which.return_value = None

        cmd, args, desc = SnapshotManager.delete_snapshot("1")

        self.assertEqual(cmd, "echo")
        self.assertIn("No snapshot backend available", args)


# ---------------------------------------------------------------------------
# TestGetSnapshotCount
# ---------------------------------------------------------------------------

class TestGetSnapshotCount(unittest.TestCase):
    """Tests for SnapshotManager.get_snapshot_count."""

    @patch('utils.snapshot_manager.subprocess.run')
    def test_count_with_snapshots(self, mock_run):
        """Test count returns correct number of snapshots."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                " # | Date                         | Description\n"
                "---+------------------------------+-----------------\n"
                " 1 | 2024-01-15 10:00:01          | snap one\n"
                " 2 | 2024-01-16 12:30:00          | snap two\n"
                " 3 | 2024-01-17 09:00:00          | snap three\n"
            ),
            stderr="",
        )

        count = SnapshotManager.get_snapshot_count(backend="snapper")

        self.assertEqual(count, 3)

    @patch('utils.snapshot_manager.subprocess.run')
    def test_count_empty(self, mock_run):
        """Test count returns 0 when no snapshots exist."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        count = SnapshotManager.get_snapshot_count(backend="snapper")

        self.assertEqual(count, 0)


# ---------------------------------------------------------------------------
# TestApplyRetention
# ---------------------------------------------------------------------------

class TestApplyRetention(unittest.TestCase):
    """Tests for SnapshotManager.apply_retention."""

    @patch('utils.snapshot_manager.subprocess.run')
    def test_retention_removes_old(self, mock_run):
        """Test that retention generates delete ops for excess snapshots."""
        # 5 snapshots, keep only 2 → expect 3 delete operations
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                " # | Date                         | Description\n"
                "---+------------------------------+-----------------\n"
                " 1 | 2024-01-11 10:00:00          | oldest\n"
                " 2 | 2024-01-12 10:00:00          | old\n"
                " 3 | 2024-01-13 10:00:00          | mid\n"
                " 4 | 2024-01-14 10:00:00          | recent\n"
                " 5 | 2024-01-15 10:00:00          | newest\n"
            ),
            stderr="",
        )

        ops = SnapshotManager.apply_retention(max_snapshots=2, backend="snapper")

        self.assertIsInstance(ops, list)
        self.assertEqual(len(ops), 3)
        for op in ops:
            self.assertIsInstance(op, tuple)
            self.assertEqual(len(op), 3)
            self.assertEqual(op[0], "pkexec")

    @patch('utils.snapshot_manager.subprocess.run')
    def test_retention_within_limit(self, mock_run):
        """Test that retention returns empty list when within limit."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                " # | Date                         | Description\n"
                "---+------------------------------+-----------------\n"
                " 1 | 2024-01-15 10:00:00          | only one\n"
            ),
            stderr="",
        )

        ops = SnapshotManager.apply_retention(max_snapshots=10, backend="snapper")

        self.assertEqual(ops, [])

    @patch('utils.snapshot_manager.subprocess.run')
    def test_retention_zero_snapshots(self, mock_run):
        """Test retention handles empty snapshot list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        ops = SnapshotManager.apply_retention(max_snapshots=5, backend="snapper")

        self.assertEqual(ops, [])

    @patch('utils.snapshot_manager.shutil.which')
    def test_retention_no_backend(self, mock_which):
        """Test retention returns empty list when no backend is available."""
        mock_which.return_value = None

        ops = SnapshotManager.apply_retention(max_snapshots=5)

        self.assertEqual(ops, [])


# ---------------------------------------------------------------------------
# TestListBtrfsSnapshots
# ---------------------------------------------------------------------------

class TestListBtrfsSnapshots(unittest.TestCase):
    """Tests for btrfs subvolume list parsing."""

    @patch('utils.snapshot_manager.subprocess.run')
    def test_list_btrfs_snapshots(self, mock_run):
        """Test parsing btrfs subvolume list output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "ID 256 gen 100 top level 5 path home\n"
                "ID 258 gen 123 top level 5 path .snapshots/pre-update\n"
                "ID 259 gen 124 top level 5 path .snapshots/daily-backup\n"
            ),
            stderr="",
        )

        snapshots = SnapshotManager.list_snapshots(backend="btrfs")

        # Only .snapshots/ entries should be included
        self.assertEqual(len(snapshots), 2)
        for snap in snapshots:
            self.assertEqual(snap.backend, "btrfs")
            self.assertIn(".snapshots", snap.description)

    @patch('utils.snapshot_manager.subprocess.run')
    def test_list_btrfs_no_snapshots(self, mock_run):
        """Test btrfs listing with no snapshot subvolumes."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "ID 256 gen 100 top level 5 path home\n"
                "ID 257 gen 101 top level 5 path var\n"
            ),
            stderr="",
        )

        snapshots = SnapshotManager.list_snapshots(backend="btrfs")

        self.assertEqual(snapshots, [])


# ---------------------------------------------------------------------------
# TestCreateSnapshotEdgeCases
# ---------------------------------------------------------------------------

class TestCreateSnapshotEdgeCases(unittest.TestCase):
    """Edge-case tests for snapshot creation."""

    def test_create_unknown_backend(self):
        """Test create with an unknown backend name."""
        cmd, args, desc = SnapshotManager.create_snapshot(
            label="test", backend="zfs"
        )

        self.assertEqual(cmd, "echo")
        self.assertIn("Unknown backend", args[0])

    def test_create_btrfs_sanitises_label(self):
        """Test that slashes and spaces in label are sanitised for btrfs."""
        cmd, args, desc = SnapshotManager.create_snapshot(
            label="my/snap shot", backend="btrfs"
        )

        path_arg = [a for a in args if ".snapshots" in a][0]
        self.assertNotIn("/snap", path_arg.split("/.snapshots/")[1])
        self.assertNotIn(" ", path_arg.split("/.snapshots/")[1])

    def test_delete_unknown_backend(self):
        """Test delete with an unknown backend name."""
        cmd, args, desc = SnapshotManager.delete_snapshot("1", backend="zfs")

        self.assertEqual(cmd, "echo")
        self.assertIn("Unknown backend", args[0])


# ---------------------------------------------------------------------------
# TestVersionFromStderr
# ---------------------------------------------------------------------------

class TestVersionFromStderr(unittest.TestCase):
    """Test version detection from stderr (some tools print there)."""

    @patch('utils.snapshot_manager.subprocess.run')
    @patch('utils.snapshot_manager.shutil.which')
    def test_version_from_stderr(self, mock_which, mock_run):
        """Test version is read from stderr when stdout is empty."""
        mock_which.return_value = "/usr/bin/btrfs"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="btrfs-progs v6.7\n",
        )

        backends = SnapshotManager.detect_backends()

        btrfs = [b for b in backends if b.name == "btrfs"][0]
        self.assertEqual(btrfs.version, "btrfs-progs v6.7")


if __name__ == '__main__':
    unittest.main()
