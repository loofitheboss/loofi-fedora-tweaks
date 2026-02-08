"""
Tests for utils/services.py — ServiceManager.
Covers: list_units, filter_type, start/stop/restart,
mask/unmask, get_unit_status, gaming detection, failed detection.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.services import ServiceManager, UnitScope, UnitState, ServiceUnit, Result


# ---------------------------------------------------------------------------
# TestServiceUnitDataclass — dataclass tests
# ---------------------------------------------------------------------------

class TestServiceUnitDataclass(unittest.TestCase):
    """Tests for ServiceUnit dataclass."""

    def test_service_unit_creation(self):
        """ServiceUnit stores all required fields."""
        unit = ServiceUnit(
            name="gamemoded",
            state=UnitState.ACTIVE,
            scope=UnitScope.USER,
            description="GameMode daemon",
            is_gaming=True,
        )
        self.assertEqual(unit.name, "gamemoded")
        self.assertEqual(unit.state, UnitState.ACTIVE)
        self.assertTrue(unit.is_gaming)

    def test_service_unit_defaults(self):
        """ServiceUnit has correct defaults."""
        unit = ServiceUnit(name="test", state=UnitState.UNKNOWN, scope=UnitScope.SYSTEM)
        self.assertEqual(unit.description, "")
        self.assertFalse(unit.is_gaming)


# ---------------------------------------------------------------------------
# TestListUnits — listing systemd units
# ---------------------------------------------------------------------------

class TestListUnits(unittest.TestCase):
    """Tests for list_units with mocked systemctl output."""

    SAMPLE_OUTPUT = (
        "gamemoded.service        loaded active running GameMode daemon\n"
        "sshd.service             loaded active running OpenSSH server\n"
        "bluetooth.service        loaded failed failed  Bluetooth service\n"
        "tracker-miner.service    loaded inactive dead   Tracker Miner\n"
    )

    @patch('utils.services.subprocess.run')
    def test_list_units_parses_output(self, mock_run):
        """list_units parses systemctl output into ServiceUnit list."""
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SAMPLE_OUTPUT)

        units = ServiceManager.list_units(UnitScope.USER, "all")

        self.assertEqual(len(units), 4)
        names = [u.name for u in units]
        self.assertIn("gamemoded", names)

    @patch('utils.services.subprocess.run')
    def test_list_units_filter_active(self, mock_run):
        """list_units filters by active state."""
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SAMPLE_OUTPUT)

        units = ServiceManager.list_units(UnitScope.USER, "active")

        for unit in units:
            self.assertEqual(unit.state, UnitState.ACTIVE)

    @patch('utils.services.subprocess.run')
    def test_list_units_filter_failed(self, mock_run):
        """list_units filters by failed state."""
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SAMPLE_OUTPUT)

        units = ServiceManager.list_units(UnitScope.USER, "failed")

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].name, "bluetooth")
        self.assertEqual(units[0].state, UnitState.FAILED)

    @patch('utils.services.subprocess.run')
    def test_list_units_filter_gaming(self, mock_run):
        """list_units filters for gaming-related services."""
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SAMPLE_OUTPUT)

        units = ServiceManager.list_units(UnitScope.USER, "gaming")

        self.assertTrue(all(u.is_gaming for u in units))

    @patch('utils.services.subprocess.run')
    def test_list_units_nonzero_exit(self, mock_run):
        """list_units returns empty list on error."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        units = ServiceManager.list_units()
        self.assertEqual(units, [])

    @patch('utils.services.subprocess.run', side_effect=Exception("systemctl not found"))
    def test_list_units_exception(self, mock_run):
        """list_units returns empty list on exception."""
        units = ServiceManager.list_units()
        self.assertEqual(units, [])


# ---------------------------------------------------------------------------
# TestStartStopRestart — unit control operations
# ---------------------------------------------------------------------------

class TestStartStopRestart(unittest.TestCase):
    """Tests for start_unit, stop_unit, restart_unit."""

    @patch('utils.services.subprocess.run')
    def test_start_unit_success(self, mock_run):
        """start_unit returns success on returncode 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceManager.start_unit("gamemoded", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Started", result.message)

    @patch('utils.services.subprocess.run')
    def test_stop_unit_success(self, mock_run):
        """stop_unit returns success on returncode 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceManager.stop_unit("gamemoded", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Stopped", result.message)

    @patch('utils.services.subprocess.run')
    def test_restart_unit_success(self, mock_run):
        """restart_unit returns success on returncode 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceManager.restart_unit("sshd", UnitScope.SYSTEM)
        self.assertTrue(result.success)
        self.assertIn("Restarted", result.message)

    @patch('utils.services.subprocess.run')
    def test_start_unit_failure(self, mock_run):
        """start_unit returns failure on non-zero exit."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="unit not found")

        result = ServiceManager.start_unit("nonexistent")
        self.assertFalse(result.success)

    @patch('utils.services.subprocess.run', side_effect=Exception("timeout"))
    def test_start_unit_exception(self, mock_run):
        """start_unit handles exception gracefully."""
        result = ServiceManager.start_unit("test")
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)


# ---------------------------------------------------------------------------
# TestMaskUnmask — masking and unmasking units
# ---------------------------------------------------------------------------

class TestMaskUnmask(unittest.TestCase):
    """Tests for mask_unit and unmask_unit."""

    @patch('utils.services.subprocess.run')
    def test_mask_unit_success(self, mock_run):
        """mask_unit returns success on returncode 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceManager.mask_unit("bluetooth", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Masked", result.message)

    @patch('utils.services.subprocess.run')
    def test_unmask_unit_success(self, mock_run):
        """unmask_unit returns success on returncode 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = ServiceManager.unmask_unit("bluetooth", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Unmasked", result.message)


# ---------------------------------------------------------------------------
# TestGetUnitStatus — detailed status
# ---------------------------------------------------------------------------

class TestGetUnitStatus(unittest.TestCase):
    """Tests for get_unit_status."""

    @patch('utils.services.subprocess.run')
    def test_get_unit_status_returns_output(self, mock_run):
        """get_unit_status returns systemctl status output."""
        expected = "gamemoded.service - GameMode daemon\n   Active: active (running)\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=expected)

        status = ServiceManager.get_unit_status("gamemoded")
        self.assertIn("active", status)

    @patch('utils.services.subprocess.run', side_effect=Exception("fail"))
    def test_get_unit_status_handles_exception(self, mock_run):
        """get_unit_status returns empty string on exception."""
        status = ServiceManager.get_unit_status("bad")
        self.assertEqual(status, "")


# ---------------------------------------------------------------------------
# TestGamingAndFailedDetection — convenience methods
# ---------------------------------------------------------------------------

class TestGamingAndFailedDetection(unittest.TestCase):
    """Tests for get_gaming_units and get_failed_units."""

    @patch.object(ServiceManager, 'list_units')
    def test_get_failed_units(self, mock_list):
        """get_failed_units collects from both scopes."""
        mock_list.return_value = [
            ServiceUnit("broken", UnitState.FAILED, UnitScope.USER),
        ]

        failed = ServiceManager.get_failed_units()
        # Called for both USER and SYSTEM scopes
        self.assertEqual(mock_list.call_count, 2)

    @patch.object(ServiceManager, 'list_units')
    def test_get_gaming_units_deduplicates(self, mock_list):
        """get_gaming_units removes duplicates by name."""
        unit = ServiceUnit("gamemoded", UnitState.ACTIVE, UnitScope.USER, is_gaming=True)
        mock_list.return_value = [unit]

        gaming = ServiceManager.get_gaming_units()
        names = [u.name for u in gaming]
        self.assertEqual(names.count("gamemoded"), 1)


if __name__ == '__main__':
    unittest.main()
