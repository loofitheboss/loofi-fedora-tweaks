"""Tests for services/system/services.py — extended coverage.

Comprehensive tests for UnitScope, UnitState, ServiceUnit, Result,
and all ServiceManager classmethods including list_units, get_failed_units,
get_gaming_units, start/stop/restart/mask/unmask_unit, and get_unit_status.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from services.system.services import (
    Result,
    ServiceManager,
    ServiceUnit,
    UnitScope,
    UnitState,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

SAMPLE_SYSTEMCTL_OUTPUT = (
    "gamemoded.service        loaded active   running GameMode daemon\n"
    "sshd.service             loaded active   running OpenSSH server daemon\n"
    "bluetooth.service        loaded failed   failed  Bluetooth service\n"
    "tracker-miner.service    loaded inactive dead    Tracker Miner FS\n"
    "steam.service            loaded active   running Steam client service\n"
    "nvidia-persistenced.service loaded active running NVIDIA Persistence Daemon\n"
)

SAMPLE_GAMING_ONLY_OUTPUT = (
    "gamemoded.service        loaded active   running GameMode daemon\n"
    "steam.service            loaded active   running Steam client\n"
)

SAMPLE_MIXED_STATES_OUTPUT = (
    "a.service  loaded active      running Alpha service\n"
    "b.service  loaded failed      failed  Beta service\n"
    "c.service  loaded inactive    dead    Charlie service\n"
    "d.service  loaded activating  start   Delta service\n"
    "e.service  loaded deactivating stop   Echo service\n"
    "f.service  loaded whatever    idle    Foxtrot service\n"
)


def _mock_result(returncode=0, stdout="", stderr=""):
    """Create a mock subprocess result."""
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# TestUnitScope — enum values
# ---------------------------------------------------------------------------


class TestUnitScope(unittest.TestCase):
    """Tests for UnitScope enum."""

    def test_system_value(self):
        """SYSTEM scope has value 'system'."""
        self.assertEqual(UnitScope.SYSTEM.value, "system")

    def test_user_value(self):
        """USER scope has value 'user'."""
        self.assertEqual(UnitScope.USER.value, "user")

    def test_scope_members(self):
        """UnitScope has exactly two members."""
        self.assertEqual(len(UnitScope), 2)

    def test_scope_from_value(self):
        """UnitScope can be constructed from string value."""
        self.assertEqual(UnitScope("system"), UnitScope.SYSTEM)
        self.assertEqual(UnitScope("user"), UnitScope.USER)


# ---------------------------------------------------------------------------
# TestUnitState — enum values
# ---------------------------------------------------------------------------


class TestUnitState(unittest.TestCase):
    """Tests for UnitState enum."""

    def test_active_value(self):
        """ACTIVE state has value 'active'."""
        self.assertEqual(UnitState.ACTIVE.value, "active")

    def test_inactive_value(self):
        """INACTIVE state has value 'inactive'."""
        self.assertEqual(UnitState.INACTIVE.value, "inactive")

    def test_failed_value(self):
        """FAILED state has value 'failed'."""
        self.assertEqual(UnitState.FAILED.value, "failed")

    def test_activating_value(self):
        """ACTIVATING state has value 'activating'."""
        self.assertEqual(UnitState.ACTIVATING.value, "activating")

    def test_deactivating_value(self):
        """DEACTIVATING state has value 'deactivating'."""
        self.assertEqual(UnitState.DEACTIVATING.value, "deactivating")

    def test_unknown_value(self):
        """UNKNOWN state has value 'unknown'."""
        self.assertEqual(UnitState.UNKNOWN.value, "unknown")

    def test_state_member_count(self):
        """UnitState has exactly six members."""
        self.assertEqual(len(UnitState), 6)


# ---------------------------------------------------------------------------
# TestServiceUnit — dataclass
# ---------------------------------------------------------------------------


class TestServiceUnit(unittest.TestCase):
    """Tests for ServiceUnit dataclass."""

    def test_all_fields(self):
        """ServiceUnit stores all fields correctly."""
        unit = ServiceUnit(
            name="gamemoded",
            state=UnitState.ACTIVE,
            scope=UnitScope.USER,
            description="GameMode daemon",
            is_gaming=True,
        )
        self.assertEqual(unit.name, "gamemoded")
        self.assertEqual(unit.state, UnitState.ACTIVE)
        self.assertEqual(unit.scope, UnitScope.USER)
        self.assertEqual(unit.description, "GameMode daemon")
        self.assertTrue(unit.is_gaming)

    def test_default_description(self):
        """ServiceUnit description defaults to empty string."""
        unit = ServiceUnit(name="foo", state=UnitState.UNKNOWN, scope=UnitScope.SYSTEM)
        self.assertEqual(unit.description, "")

    def test_default_is_gaming(self):
        """ServiceUnit is_gaming defaults to False."""
        unit = ServiceUnit(name="foo", state=UnitState.UNKNOWN, scope=UnitScope.SYSTEM)
        self.assertFalse(unit.is_gaming)

    def test_system_scope_unit(self):
        """ServiceUnit with SYSTEM scope."""
        unit = ServiceUnit(name="sshd", state=UnitState.ACTIVE, scope=UnitScope.SYSTEM)
        self.assertEqual(unit.scope, UnitScope.SYSTEM)


# ---------------------------------------------------------------------------
# TestResult — dataclass
# ---------------------------------------------------------------------------


class TestResult(unittest.TestCase):
    """Tests for Result dataclass."""

    def test_success_result(self):
        """Result success=True stores message."""
        r = Result(success=True, message="Done")
        self.assertTrue(r.success)
        self.assertEqual(r.message, "Done")

    def test_failure_result(self):
        """Result success=False stores error message."""
        r = Result(success=False, message="Failed to start")
        self.assertFalse(r.success)
        self.assertIn("Failed", r.message)


# ---------------------------------------------------------------------------
# TestGamingServicesAttribute — class attribute
# ---------------------------------------------------------------------------


class TestGamingServicesAttribute(unittest.TestCase):
    """Tests for ServiceManager.GAMING_SERVICES class attribute."""

    def test_gaming_services_is_list(self):
        """GAMING_SERVICES is a list."""
        self.assertIsInstance(ServiceManager.GAMING_SERVICES, list)

    def test_gaming_services_contains_gamemoded(self):
        """GAMING_SERVICES includes gamemoded."""
        self.assertIn("gamemoded", ServiceManager.GAMING_SERVICES)

    def test_gaming_services_contains_steam(self):
        """GAMING_SERVICES includes steam."""
        self.assertIn("steam", ServiceManager.GAMING_SERVICES)

    def test_gaming_services_contains_nvidia(self):
        """GAMING_SERVICES includes nvidia-persistenced."""
        self.assertIn("nvidia-persistenced", ServiceManager.GAMING_SERVICES)

    def test_gaming_services_not_empty(self):
        """GAMING_SERVICES is non-empty."""
        self.assertGreater(len(ServiceManager.GAMING_SERVICES), 0)


# ---------------------------------------------------------------------------
# TestListUnits — list_units()
# ---------------------------------------------------------------------------


class TestListUnits(unittest.TestCase):
    """Tests for ServiceManager.list_units()."""

    @patch("services.system.services.subprocess.run")
    def test_list_units_user_scope_command(self, mock_run):
        """list_units builds correct command for USER scope."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.list_units(UnitScope.USER, "all")
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)
        self.assertIn("list-units", args)
        self.assertIn("--type=service", args)

    @patch("services.system.services.subprocess.run")
    def test_list_units_system_scope_command(self, mock_run):
        """list_units builds correct command for SYSTEM scope (no --user)."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.list_units(UnitScope.SYSTEM, "all")
        args = mock_run.call_args[0][0]
        self.assertNotIn("--user", args)
        self.assertIn("systemctl", args)

    @patch("services.system.services.subprocess.run")
    def test_list_units_parses_all(self, mock_run):
        """list_units returns all parsed units for filter_type='all'."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_SYSTEMCTL_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(len(units), 6)

    @patch("services.system.services.subprocess.run")
    def test_list_units_names_stripped(self, mock_run):
        """list_units strips '.service' suffix from names."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_SYSTEMCTL_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        for unit in units:
            self.assertNotIn(".service", unit.name)

    @patch("services.system.services.subprocess.run")
    def test_list_units_state_active(self, mock_run):
        """list_units parses 'active' state correctly."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_MIXED_STATES_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        a = [u for u in units if u.name == "a"][0]
        self.assertEqual(a.state, UnitState.ACTIVE)

    @patch("services.system.services.subprocess.run")
    def test_list_units_state_failed(self, mock_run):
        """list_units parses 'failed' state correctly."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_MIXED_STATES_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        b = [u for u in units if u.name == "b"][0]
        self.assertEqual(b.state, UnitState.FAILED)

    @patch("services.system.services.subprocess.run")
    def test_list_units_state_inactive(self, mock_run):
        """list_units parses 'inactive' state correctly."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_MIXED_STATES_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        c = [u for u in units if u.name == "c"][0]
        self.assertEqual(c.state, UnitState.INACTIVE)

    @patch("services.system.services.subprocess.run")
    def test_list_units_state_activating(self, mock_run):
        """list_units parses 'activating' state correctly."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_MIXED_STATES_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        d = [u for u in units if u.name == "d"][0]
        self.assertEqual(d.state, UnitState.ACTIVATING)

    @patch("services.system.services.subprocess.run")
    def test_list_units_state_unknown_for_unrecognized(self, mock_run):
        """list_units maps unrecognized states to UNKNOWN."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_MIXED_STATES_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        # 'deactivating' is NOT handled as its own branch (no elif for it)
        # and 'whatever' also falls through to UNKNOWN
        f = [u for u in units if u.name == "f"][0]
        self.assertEqual(f.state, UnitState.UNKNOWN)

    @patch("services.system.services.subprocess.run")
    def test_list_units_filter_gaming(self, mock_run):
        """list_units with filter_type='gaming' returns only gaming units."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_SYSTEMCTL_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "gaming")
        for unit in units:
            self.assertTrue(unit.is_gaming)

    @patch("services.system.services.subprocess.run")
    def test_list_units_filter_failed(self, mock_run):
        """list_units with filter_type='failed' returns only failed units."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_SYSTEMCTL_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "failed")
        for unit in units:
            self.assertEqual(unit.state, UnitState.FAILED)

    @patch("services.system.services.subprocess.run")
    def test_list_units_filter_active(self, mock_run):
        """list_units with filter_type='active' returns only active units."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_SYSTEMCTL_OUTPUT)
        units = ServiceManager.list_units(UnitScope.USER, "active")
        for unit in units:
            self.assertEqual(unit.state, UnitState.ACTIVE)

    @patch("services.system.services.subprocess.run")
    def test_list_units_nonzero_returncode(self, mock_run):
        """list_units returns empty list on non-zero returncode."""
        mock_run.return_value = _mock_result(returncode=1, stdout="error")
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(units, [])

    @patch("services.system.services.subprocess.run")
    def test_list_units_empty_stdout(self, mock_run):
        """list_units returns empty list on empty stdout."""
        mock_run.return_value = _mock_result(stdout="")
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(units, [])

    @patch("services.system.services.subprocess.run")
    def test_list_units_skips_blank_lines(self, mock_run):
        """list_units skips blank lines in output."""
        output = "\ngamemoded.service loaded active running GameMode\n\n"
        mock_run.return_value = _mock_result(stdout=output)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(len(units), 1)

    @patch("services.system.services.subprocess.run")
    def test_list_units_skips_short_lines(self, mock_run):
        """list_units skips lines with fewer than 4 parts."""
        output = "short line\ngamemoded.service loaded active running GameMode\n"
        mock_run.return_value = _mock_result(stdout=output)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(len(units), 1)

    @patch("services.system.services.subprocess.run")
    def test_list_units_description_parsed(self, mock_run):
        """list_units parses multi-word descriptions."""
        output = "sshd.service loaded active running OpenSSH server daemon\n"
        mock_run.return_value = _mock_result(stdout=output)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(units[0].description, "OpenSSH server daemon")

    @patch("services.system.services.subprocess.run")
    def test_list_units_no_description(self, mock_run):
        """list_units handles lines with exactly 4 parts (no description)."""
        output = "foo.service loaded active running\n"
        mock_run.return_value = _mock_result(stdout=output)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(units[0].description, "")

    @patch("services.system.services.subprocess.run")
    def test_list_units_scope_set_on_units(self, mock_run):
        """list_units sets the scope on returned units."""
        mock_run.return_value = _mock_result(
            stdout="foo.service loaded active running Test\n"
        )
        units = ServiceManager.list_units(UnitScope.SYSTEM, "all")
        self.assertEqual(units[0].scope, UnitScope.SYSTEM)

    @patch("services.system.services.subprocess.run")
    def test_list_units_gaming_detection_gamemoded(self, mock_run):
        """list_units detects gamemoded as gaming service."""
        mock_run.return_value = _mock_result(
            stdout="gamemoded.service loaded active running GameMode\n"
        )
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertTrue(units[0].is_gaming)

    @patch("services.system.services.subprocess.run")
    def test_list_units_gaming_detection_non_gaming(self, mock_run):
        """list_units marks non-gaming service correctly."""
        mock_run.return_value = _mock_result(
            stdout="sshd.service loaded active running OpenSSH\n"
        )
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertFalse(units[0].is_gaming)

    @patch("services.system.services.subprocess.run")
    def test_list_units_timeout_exception(self, mock_run):
        """list_units returns empty list on TimeoutExpired."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=30)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(units, [])

    @patch("services.system.services.subprocess.run")
    def test_list_units_oserror_exception(self, mock_run):
        """list_units returns empty list on OSError."""
        mock_run.side_effect = OSError("No such file")
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(units, [])

    @patch("services.system.services.subprocess.run")
    def test_list_units_subprocess_error(self, mock_run):
        """list_units returns empty list on SubprocessError."""
        mock_run.side_effect = subprocess.SubprocessError("fail")
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertEqual(units, [])

    @patch("services.system.services.subprocess.run")
    def test_list_units_uses_timeout(self, mock_run):
        """list_units passes timeout=30 to subprocess.run."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.list_units(UnitScope.USER, "all")
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 30)

    @patch("services.system.services.subprocess.run")
    def test_list_units_passes_plain_and_no_legend(self, mock_run):
        """list_units passes --plain and --no-legend flags."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.list_units(UnitScope.USER, "all")
        args = mock_run.call_args[0][0]
        self.assertIn("--plain", args)
        self.assertIn("--no-legend", args)

    @patch("services.system.services.subprocess.run")
    def test_list_units_nvidia_powerd_is_gaming(self, mock_run):
        """list_units detects nvidia-powerd as gaming."""
        output = "nvidia-powerd.service loaded active running NVIDIA Power\n"
        mock_run.return_value = _mock_result(stdout=output)
        units = ServiceManager.list_units(UnitScope.USER, "all")
        self.assertTrue(units[0].is_gaming)


# ---------------------------------------------------------------------------
# TestGetFailedUnits — get_failed_units()
# ---------------------------------------------------------------------------


class TestGetFailedUnits(unittest.TestCase):
    """Tests for ServiceManager.get_failed_units()."""

    @patch("services.system.services.subprocess.run")
    def test_get_failed_units_combines_scopes(self, mock_run):
        """get_failed_units returns failed units from both scopes."""
        user_out = "bad.service loaded failed failed User bad svc\n"
        sys_out = "sysbad.service loaded failed failed System bad svc\n"
        mock_run.side_effect = [
            _mock_result(stdout=user_out),
            _mock_result(stdout=sys_out),
        ]
        failed = ServiceManager.get_failed_units()
        names = [u.name for u in failed]
        self.assertIn("bad", names)
        self.assertIn("sysbad", names)

    @patch("services.system.services.subprocess.run")
    def test_get_failed_units_empty_when_none_failed(self, mock_run):
        """get_failed_units returns empty list if no failures."""
        output = "sshd.service loaded active running OpenSSH\n"
        mock_run.return_value = _mock_result(stdout=output)
        failed = ServiceManager.get_failed_units()
        self.assertEqual(failed, [])

    @patch("services.system.services.subprocess.run")
    def test_get_failed_units_user_only(self, mock_run):
        """get_failed_units returns user-scope failures even if system empty."""
        user_out = "bad.service loaded failed failed User bad\n"
        sys_out = "ok.service loaded active running System ok\n"
        mock_run.side_effect = [
            _mock_result(stdout=user_out),
            _mock_result(stdout=sys_out),
        ]
        failed = ServiceManager.get_failed_units()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].name, "bad")

    @patch("services.system.services.subprocess.run")
    def test_get_failed_units_system_exception_handled(self, mock_run):
        """get_failed_units handles exception from system-scope listing."""
        user_out = "bad.service loaded failed failed User bad\n"
        # First call for user succeeds, second for system raises
        mock_run.side_effect = [
            _mock_result(stdout=user_out),
            subprocess.SubprocessError("denied"),
        ]
        # list_units catches exceptions internally, so this returns []
        # for the system scope call, and get_failed_units still works
        failed = ServiceManager.get_failed_units()
        self.assertEqual(len(failed), 1)

    @patch("services.system.services.subprocess.run")
    def test_get_failed_units_all_states_returned_are_failed(self, mock_run):
        """get_failed_units only returns units with FAILED state."""
        output = (
            "ok.service loaded active running OK\n"
            "bad.service loaded failed failed Bad\n"
        )
        mock_run.return_value = _mock_result(stdout=output)
        failed = ServiceManager.get_failed_units()
        for unit in failed:
            self.assertEqual(unit.state, UnitState.FAILED)


# ---------------------------------------------------------------------------
# TestGetGamingUnits — get_gaming_units()
# ---------------------------------------------------------------------------


class TestGetGamingUnits(unittest.TestCase):
    """Tests for ServiceManager.get_gaming_units()."""

    @patch("services.system.services.subprocess.run")
    def test_get_gaming_units_returns_gaming(self, mock_run):
        """get_gaming_units returns gaming-related units."""
        mock_run.return_value = _mock_result(stdout=SAMPLE_SYSTEMCTL_OUTPUT)
        units = ServiceManager.get_gaming_units()
        for unit in units:
            self.assertTrue(unit.is_gaming)

    @patch("services.system.services.subprocess.run")
    def test_get_gaming_units_deduplicates(self, mock_run):
        """get_gaming_units removes duplicates by name."""
        output = "gamemoded.service loaded active running GameMode\n"
        # Both user and system scopes return the same unit
        mock_run.return_value = _mock_result(stdout=output)
        units = ServiceManager.get_gaming_units()
        names = [u.name for u in units]
        self.assertEqual(names.count("gamemoded"), 1)

    @patch("services.system.services.subprocess.run")
    def test_get_gaming_units_both_scopes(self, mock_run):
        """get_gaming_units queries both USER and SYSTEM scopes."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_gaming_units()
        self.assertEqual(mock_run.call_count, 2)

    @patch("services.system.services.subprocess.run")
    def test_get_gaming_units_empty_when_no_gaming(self, mock_run):
        """get_gaming_units returns empty list if no gaming services found."""
        output = "sshd.service loaded active running OpenSSH\n"
        mock_run.return_value = _mock_result(stdout=output)
        units = ServiceManager.get_gaming_units()
        self.assertEqual(units, [])

    @patch("services.system.services.subprocess.run")
    def test_get_gaming_units_preserves_first_occurrence(self, mock_run):
        """get_gaming_units keeps the first occurrence on dedup."""
        user_output = "gamemoded.service loaded active running GameMode user\n"
        sys_output = "gamemoded.service loaded inactive dead GameMode system\n"
        mock_run.side_effect = [
            _mock_result(stdout=user_output),
            _mock_result(stdout=sys_output),
        ]
        units = ServiceManager.get_gaming_units()
        self.assertEqual(len(units), 1)
        # First seen is from user scope
        self.assertEqual(units[0].scope, UnitScope.USER)


# ---------------------------------------------------------------------------
# TestStartUnit — start_unit()
# ---------------------------------------------------------------------------


class TestStartUnit(unittest.TestCase):
    """Tests for ServiceManager.start_unit()."""

    @patch("services.system.services.subprocess.run")
    def test_start_unit_user_success(self, mock_run):
        """start_unit returns success=True for user scope on rc=0."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.start_unit("gamemoded", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Started", result.message)

    @patch("services.system.services.subprocess.run")
    def test_start_unit_user_command(self, mock_run):
        """start_unit builds --user command for USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.start_unit("foo", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["systemctl", "--user", "start", "foo.service"])

    @patch("services.system.services.subprocess.run")
    def test_start_unit_system_uses_pkexec(self, mock_run):
        """start_unit prepends pkexec for SYSTEM scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.start_unit("sshd", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "pkexec")
        self.assertNotIn("--user", args)

    @patch("services.system.services.subprocess.run")
    def test_start_unit_system_command(self, mock_run):
        """start_unit builds correct command for SYSTEM scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.start_unit("sshd", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["pkexec", "systemctl", "start", "sshd.service"])

    @patch("services.system.services.subprocess.run")
    def test_start_unit_failure(self, mock_run):
        """start_unit returns success=False on non-zero rc."""
        mock_run.return_value = _mock_result(returncode=1, stderr="denied")
        result = ServiceManager.start_unit("sshd", UnitScope.SYSTEM)
        self.assertFalse(result.success)
        self.assertIn("denied", result.message)

    @patch("services.system.services.subprocess.run")
    def test_start_unit_exception(self, mock_run):
        """start_unit returns success=False on exception."""
        mock_run.side_effect = OSError("binary not found")
        result = ServiceManager.start_unit("sshd", UnitScope.USER)
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch("services.system.services.subprocess.run")
    def test_start_unit_timeout_exception(self, mock_run):
        """start_unit handles TimeoutExpired gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=30)
        result = ServiceManager.start_unit("sshd", UnitScope.USER)
        self.assertFalse(result.success)

    @patch("services.system.services.subprocess.run")
    def test_start_unit_uses_timeout(self, mock_run):
        """start_unit passes timeout=30."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.start_unit("foo", UnitScope.USER)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 30)


# ---------------------------------------------------------------------------
# TestStopUnit — stop_unit()
# ---------------------------------------------------------------------------


class TestStopUnit(unittest.TestCase):
    """Tests for ServiceManager.stop_unit()."""

    @patch("services.system.services.subprocess.run")
    def test_stop_unit_user_success(self, mock_run):
        """stop_unit returns success=True for user scope."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.stop_unit("gamemoded", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Stopped", result.message)

    @patch("services.system.services.subprocess.run")
    def test_stop_unit_user_command(self, mock_run):
        """stop_unit builds correct command for USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.stop_unit("foo", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["systemctl", "--user", "stop", "foo.service"])

    @patch("services.system.services.subprocess.run")
    def test_stop_unit_system_uses_pkexec(self, mock_run):
        """stop_unit prepends pkexec for SYSTEM scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.stop_unit("sshd", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["pkexec", "systemctl", "stop", "sshd.service"])

    @patch("services.system.services.subprocess.run")
    def test_stop_unit_failure(self, mock_run):
        """stop_unit returns success=False on non-zero rc."""
        mock_run.return_value = _mock_result(returncode=1, stderr="not loaded")
        result = ServiceManager.stop_unit("sshd", UnitScope.SYSTEM)
        self.assertFalse(result.success)
        self.assertIn("not loaded", result.message)

    @patch("services.system.services.subprocess.run")
    def test_stop_unit_exception(self, mock_run):
        """stop_unit returns success=False on exception."""
        mock_run.side_effect = subprocess.SubprocessError("fail")
        result = ServiceManager.stop_unit("sshd", UnitScope.USER)
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch("services.system.services.subprocess.run")
    def test_stop_unit_uses_timeout(self, mock_run):
        """stop_unit passes timeout=30."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.stop_unit("foo", UnitScope.USER)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 30)


# ---------------------------------------------------------------------------
# TestRestartUnit — restart_unit()
# ---------------------------------------------------------------------------


class TestRestartUnit(unittest.TestCase):
    """Tests for ServiceManager.restart_unit()."""

    @patch("services.system.services.subprocess.run")
    def test_restart_unit_user_success(self, mock_run):
        """restart_unit returns success=True for user scope."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.restart_unit("gamemoded", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Restarted", result.message)

    @patch("services.system.services.subprocess.run")
    def test_restart_unit_user_command(self, mock_run):
        """restart_unit builds correct command for USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.restart_unit("foo", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["systemctl", "--user", "restart", "foo.service"])

    @patch("services.system.services.subprocess.run")
    def test_restart_unit_system_uses_pkexec(self, mock_run):
        """restart_unit prepends pkexec for SYSTEM scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.restart_unit("sshd", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["pkexec", "systemctl", "restart", "sshd.service"])

    @patch("services.system.services.subprocess.run")
    def test_restart_unit_failure(self, mock_run):
        """restart_unit returns success=False on non-zero rc."""
        mock_run.return_value = _mock_result(returncode=1, stderr="timeout")
        result = ServiceManager.restart_unit("sshd", UnitScope.SYSTEM)
        self.assertFalse(result.success)
        self.assertIn("timeout", result.message)

    @patch("services.system.services.subprocess.run")
    def test_restart_unit_exception(self, mock_run):
        """restart_unit returns success=False on exception."""
        mock_run.side_effect = OSError("unexpected")
        result = ServiceManager.restart_unit("foo", UnitScope.USER)
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch("services.system.services.subprocess.run")
    def test_restart_unit_uses_timeout(self, mock_run):
        """restart_unit passes timeout=30."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.restart_unit("foo", UnitScope.USER)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 30)


# ---------------------------------------------------------------------------
# TestMaskUnit — mask_unit()
# ---------------------------------------------------------------------------


class TestMaskUnit(unittest.TestCase):
    """Tests for ServiceManager.mask_unit()."""

    @patch("services.system.services.subprocess.run")
    def test_mask_unit_user_success(self, mock_run):
        """mask_unit returns success=True for user scope."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.mask_unit("tracker-miner", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Masked", result.message)

    @patch("services.system.services.subprocess.run")
    def test_mask_unit_user_command(self, mock_run):
        """mask_unit builds correct command for USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.mask_unit("foo", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["systemctl", "--user", "mask", "foo.service"])

    @patch("services.system.services.subprocess.run")
    def test_mask_unit_system_uses_pkexec(self, mock_run):
        """mask_unit prepends pkexec for SYSTEM scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.mask_unit("bluetooth", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["pkexec", "systemctl", "mask", "bluetooth.service"])

    @patch("services.system.services.subprocess.run")
    def test_mask_unit_failure(self, mock_run):
        """mask_unit returns success=False on non-zero rc."""
        mock_run.return_value = _mock_result(returncode=1, stderr="access denied")
        result = ServiceManager.mask_unit("sshd", UnitScope.SYSTEM)
        self.assertFalse(result.success)
        self.assertIn("access denied", result.message)

    @patch("services.system.services.subprocess.run")
    def test_mask_unit_exception(self, mock_run):
        """mask_unit returns success=False on exception."""
        mock_run.side_effect = PermissionError("no auth")
        result = ServiceManager.mask_unit("sshd", UnitScope.USER)
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch("services.system.services.subprocess.run")
    def test_mask_unit_uses_timeout(self, mock_run):
        """mask_unit passes timeout=30."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.mask_unit("foo", UnitScope.USER)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 30)


# ---------------------------------------------------------------------------
# TestUnmaskUnit — unmask_unit()
# ---------------------------------------------------------------------------


class TestUnmaskUnit(unittest.TestCase):
    """Tests for ServiceManager.unmask_unit()."""

    @patch("services.system.services.subprocess.run")
    def test_unmask_unit_user_success(self, mock_run):
        """unmask_unit returns success=True for user scope."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.unmask_unit("tracker-miner", UnitScope.USER)
        self.assertTrue(result.success)
        self.assertIn("Unmasked", result.message)

    @patch("services.system.services.subprocess.run")
    def test_unmask_unit_user_command(self, mock_run):
        """unmask_unit builds correct command for USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.unmask_unit("foo", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["systemctl", "--user", "unmask", "foo.service"])

    @patch("services.system.services.subprocess.run")
    def test_unmask_unit_system_uses_pkexec(self, mock_run):
        """unmask_unit prepends pkexec for SYSTEM scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.unmask_unit("bluetooth", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["pkexec", "systemctl", "unmask", "bluetooth.service"])

    @patch("services.system.services.subprocess.run")
    def test_unmask_unit_failure(self, mock_run):
        """unmask_unit returns success=False on non-zero rc."""
        mock_run.return_value = _mock_result(returncode=1, stderr="not masked")
        result = ServiceManager.unmask_unit("sshd", UnitScope.SYSTEM)
        self.assertFalse(result.success)
        self.assertIn("not masked", result.message)

    @patch("services.system.services.subprocess.run")
    def test_unmask_unit_exception(self, mock_run):
        """unmask_unit returns success=False on exception."""
        mock_run.side_effect = FileNotFoundError("pkexec missing")
        result = ServiceManager.unmask_unit("sshd", UnitScope.USER)
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch("services.system.services.subprocess.run")
    def test_unmask_unit_uses_timeout(self, mock_run):
        """unmask_unit passes timeout=30."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.unmask_unit("foo", UnitScope.USER)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 30)


# ---------------------------------------------------------------------------
# TestGetUnitStatus — get_unit_status()
# ---------------------------------------------------------------------------


class TestGetUnitStatus(unittest.TestCase):
    """Tests for ServiceManager.get_unit_status()."""

    STATUS_OUTPUT = (
        "● sshd.service - OpenSSH server daemon\n"
        "   Loaded: loaded (/usr/lib/systemd/system/sshd.service; enabled)\n"
        "   Active: active (running) since Mon 2025-01-01 00:00:00 UTC\n"
        "   Main PID: 1234 (sshd)\n"
    )

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_user_success(self, mock_run):
        """get_unit_status returns stdout for user scope."""
        mock_run.return_value = _mock_result(stdout=self.STATUS_OUTPUT)
        status = ServiceManager.get_unit_status("sshd", UnitScope.USER)
        self.assertIn("OpenSSH", status)

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_user_command(self, mock_run):
        """get_unit_status builds correct command for USER scope."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_unit_status("foo", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertEqual(
            args, ["systemctl", "--user", "status", "foo.service", "--no-pager"]
        )

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_system_command(self, mock_run):
        """get_unit_status builds correct command for SYSTEM scope (no pkexec)."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_unit_status("sshd", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        # Note: get_unit_status does NOT use pkexec, unlike start/stop
        self.assertEqual(args, ["systemctl", "status", "sshd.service", "--no-pager"])

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_system_no_pkexec(self, mock_run):
        """get_unit_status does not prepend pkexec for SYSTEM scope."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_unit_status("sshd", UnitScope.SYSTEM)
        args = mock_run.call_args[0][0]
        self.assertNotIn("pkexec", args)

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_exception_returns_empty(self, mock_run):
        """get_unit_status returns empty string on exception."""
        mock_run.side_effect = OSError("fail")
        status = ServiceManager.get_unit_status("sshd", UnitScope.USER)
        self.assertEqual(status, "")

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_timeout_returns_empty(self, mock_run):
        """get_unit_status returns empty string on TimeoutExpired."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=10)
        status = ServiceManager.get_unit_status("sshd", UnitScope.USER)
        self.assertEqual(status, "")

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_nonzero_rc_still_returns_stdout(self, mock_run):
        """get_unit_status returns stdout even on non-zero rc (systemctl status exits 3 for inactive)."""
        mock_run.return_value = _mock_result(returncode=3, stdout="inactive")
        status = ServiceManager.get_unit_status("sshd", UnitScope.USER)
        self.assertEqual(status, "inactive")

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_uses_timeout_10(self, mock_run):
        """get_unit_status passes timeout=10 (shorter than other methods)."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_unit_status("foo", UnitScope.USER)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 10)

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_passes_no_pager(self, mock_run):
        """get_unit_status passes --no-pager flag."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_unit_status("foo", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertIn("--no-pager", args)


# ---------------------------------------------------------------------------
# TestDefaultScopes — default parameter values
# ---------------------------------------------------------------------------


class TestDefaultScopes(unittest.TestCase):
    """Tests verifying default scope parameter values."""

    @patch("services.system.services.subprocess.run")
    def test_start_unit_default_scope_user(self, mock_run):
        """start_unit defaults to USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.start_unit("foo")
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)

    @patch("services.system.services.subprocess.run")
    def test_stop_unit_default_scope_user(self, mock_run):
        """stop_unit defaults to USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.stop_unit("foo")
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)

    @patch("services.system.services.subprocess.run")
    def test_restart_unit_default_scope_user(self, mock_run):
        """restart_unit defaults to USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.restart_unit("foo")
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)

    @patch("services.system.services.subprocess.run")
    def test_mask_unit_default_scope_user(self, mock_run):
        """mask_unit defaults to USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.mask_unit("foo")
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)

    @patch("services.system.services.subprocess.run")
    def test_unmask_unit_default_scope_user(self, mock_run):
        """unmask_unit defaults to USER scope."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.unmask_unit("foo")
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_default_scope_user(self, mock_run):
        """get_unit_status defaults to USER scope."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_unit_status("foo")
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)

    @patch("services.system.services.subprocess.run")
    def test_list_units_default_scope_user(self, mock_run):
        """list_units defaults to USER scope."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.list_units()
        args = mock_run.call_args[0][0]
        self.assertIn("--user", args)


# ---------------------------------------------------------------------------
# TestServiceNameAppendSuffix — .service suffix
# ---------------------------------------------------------------------------


class TestServiceNameAppendSuffix(unittest.TestCase):
    """Tests that action methods append '.service' suffix to the unit name."""

    @patch("services.system.services.subprocess.run")
    def test_start_appends_service_suffix(self, mock_run):
        """start_unit appends .service to unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.start_unit("myunit", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertIn("myunit.service", args)

    @patch("services.system.services.subprocess.run")
    def test_stop_appends_service_suffix(self, mock_run):
        """stop_unit appends .service to unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.stop_unit("myunit", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertIn("myunit.service", args)

    @patch("services.system.services.subprocess.run")
    def test_restart_appends_service_suffix(self, mock_run):
        """restart_unit appends .service to unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.restart_unit("myunit", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertIn("myunit.service", args)

    @patch("services.system.services.subprocess.run")
    def test_mask_appends_service_suffix(self, mock_run):
        """mask_unit appends .service to unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.mask_unit("myunit", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertIn("myunit.service", args)

    @patch("services.system.services.subprocess.run")
    def test_unmask_appends_service_suffix(self, mock_run):
        """unmask_unit appends .service to unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        ServiceManager.unmask_unit("myunit", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertIn("myunit.service", args)

    @patch("services.system.services.subprocess.run")
    def test_get_unit_status_appends_service_suffix(self, mock_run):
        """get_unit_status appends .service to unit name."""
        mock_run.return_value = _mock_result(stdout="")
        ServiceManager.get_unit_status("myunit", UnitScope.USER)
        args = mock_run.call_args[0][0]
        self.assertIn("myunit.service", args)


# ---------------------------------------------------------------------------
# TestMessageContent — result message text
# ---------------------------------------------------------------------------


class TestMessageContent(unittest.TestCase):
    """Tests that result messages contain the unit name."""

    @patch("services.system.services.subprocess.run")
    def test_start_message_contains_name(self, mock_run):
        """start_unit success message contains unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.start_unit("gamemoded", UnitScope.USER)
        self.assertIn("gamemoded", result.message)

    @patch("services.system.services.subprocess.run")
    def test_stop_message_contains_name(self, mock_run):
        """stop_unit success message contains unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.stop_unit("gamemoded", UnitScope.USER)
        self.assertIn("gamemoded", result.message)

    @patch("services.system.services.subprocess.run")
    def test_restart_message_contains_name(self, mock_run):
        """restart_unit success message contains unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.restart_unit("gamemoded", UnitScope.USER)
        self.assertIn("gamemoded", result.message)

    @patch("services.system.services.subprocess.run")
    def test_mask_message_contains_name(self, mock_run):
        """mask_unit success message contains unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.mask_unit("gamemoded", UnitScope.USER)
        self.assertIn("gamemoded", result.message)

    @patch("services.system.services.subprocess.run")
    def test_unmask_message_contains_name(self, mock_run):
        """unmask_unit success message contains unit name."""
        mock_run.return_value = _mock_result(returncode=0)
        result = ServiceManager.unmask_unit("gamemoded", UnitScope.USER)
        self.assertIn("gamemoded", result.message)

    @patch("services.system.services.subprocess.run")
    def test_start_failure_message_contains_stderr(self, mock_run):
        """start_unit failure message includes stderr content."""
        mock_run.return_value = _mock_result(returncode=1, stderr="auth required")
        result = ServiceManager.start_unit("sshd", UnitScope.SYSTEM)
        self.assertIn("auth required", result.message)


if __name__ == "__main__":
    unittest.main()
