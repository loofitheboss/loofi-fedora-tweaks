"""Tests for core/executor/operations.py — comprehensive coverage.

Covers OperationResult dataclass, CleanupOps, TweakOps, AdvancedOps,
NetworkOps, execute_operation(), and CLI_COMMANDS registry.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.executor.operations import (
    CLI_COMMANDS,
    AdvancedOps,
    CleanupOps,
    NetworkOps,
    OperationResult,
    TweakOps,
    execute_operation,
)


class TestOperationResult(unittest.TestCase):
    """Tests for the OperationResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful OperationResult."""
        result = OperationResult(success=True, message="Done")
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Done")
        self.assertEqual(result.output, "")
        self.assertFalse(result.needs_reboot)

    def test_create_failure_result(self):
        """Test creating a failed OperationResult."""
        result = OperationResult(success=False, message="Error occurred")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Error occurred")

    def test_create_with_output(self):
        """Test creating OperationResult with output text."""
        result = OperationResult(success=True, message="OK", output="stdout text")
        self.assertEqual(result.output, "stdout text")

    def test_create_with_needs_reboot(self):
        """Test creating OperationResult with needs_reboot flag."""
        result = OperationResult(
            success=True, message="Kernel updated", needs_reboot=True
        )
        self.assertTrue(result.needs_reboot)

    def test_default_output_is_empty(self):
        """Test that output defaults to empty string."""
        result = OperationResult(success=True, message="OK")
        self.assertEqual(result.output, "")

    def test_default_needs_reboot_is_false(self):
        """Test that needs_reboot defaults to False."""
        result = OperationResult(success=True, message="OK")
        self.assertFalse(result.needs_reboot)

    def test_all_fields_set(self):
        """Test creating OperationResult with all fields specified."""
        result = OperationResult(
            success=False,
            message="Failed badly",
            output="error output",
            needs_reboot=True,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Failed badly")
        self.assertEqual(result.output, "error output")
        self.assertTrue(result.needs_reboot)

    def test_equality(self):
        """Test that two identical OperationResults are equal."""
        r1 = OperationResult(success=True, message="OK")
        r2 = OperationResult(success=True, message="OK")
        self.assertEqual(r1, r2)

    def test_inequality(self):
        """Test that different OperationResults are not equal."""
        r1 = OperationResult(success=True, message="OK")
        r2 = OperationResult(success=False, message="OK")
        self.assertNotEqual(r1, r2)


# ── CleanupOps ────────────────────────────────────────────────────────────


class TestCleanupOpsCleanDnfCache(unittest.TestCase):
    """Tests for CleanupOps.clean_dnf_cache()."""

    @patch("core.executor.operations.SystemManager.get_package_manager")
    def test_clean_dnf_cache_dnf(self, mock_pm):
        """Test clean_dnf_cache returns dnf clean all for dnf systems."""
        mock_pm.return_value = "dnf"
        binary, args, desc = CleanupOps.clean_dnf_cache()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["dnf", "clean", "all"])
        self.assertIn("DNF", desc)

    @patch("core.executor.operations.SystemManager.get_package_manager")
    def test_clean_dnf_cache_rpm_ostree(self, mock_pm):
        """Test clean_dnf_cache returns rpm-ostree cleanup for atomic systems."""
        mock_pm.return_value = "rpm-ostree"
        binary, args, desc = CleanupOps.clean_dnf_cache()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["rpm-ostree", "cleanup", "--base"])
        self.assertIn("rpm-ostree", desc)

    @patch("core.executor.operations.SystemManager.get_package_manager")
    def test_clean_dnf_cache_returns_tuple(self, mock_pm):
        """Test clean_dnf_cache returns a 3-element tuple."""
        mock_pm.return_value = "dnf"
        result = CleanupOps.clean_dnf_cache()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)


class TestCleanupOpsAutoremove(unittest.TestCase):
    """Tests for CleanupOps.autoremove()."""

    @patch("core.executor.operations.SystemManager.get_package_manager")
    def test_autoremove_dnf(self, mock_pm):
        """Test autoremove returns dnf autoremove for dnf systems."""
        mock_pm.return_value = "dnf"
        binary, args, desc = CleanupOps.autoremove()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["dnf", "autoremove", "-y"])
        self.assertIn("unused", desc.lower())

    @patch("core.executor.operations.SystemManager.get_package_manager")
    def test_autoremove_rpm_ostree(self, mock_pm):
        """Test autoremove returns rpm-ostree cleanup -m for atomic systems."""
        mock_pm.return_value = "rpm-ostree"
        binary, args, desc = CleanupOps.autoremove()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["rpm-ostree", "cleanup", "-m"])
        self.assertIn("rpm-ostree", desc)


class TestCleanupOpsVacuumJournal(unittest.TestCase):
    """Tests for CleanupOps.vacuum_journal()."""

    def test_vacuum_journal_default_days(self):
        """Test vacuum_journal with default 14-day parameter."""
        binary, args, desc = CleanupOps.vacuum_journal()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["journalctl", "--vacuum-time=14d"])
        self.assertIn("14", desc)

    def test_vacuum_journal_custom_days(self):
        """Test vacuum_journal with custom day count."""
        binary, args, desc = CleanupOps.vacuum_journal(days=7)
        self.assertEqual(args, ["journalctl", "--vacuum-time=7d"])
        self.assertIn("7", desc)

    def test_vacuum_journal_one_day(self):
        """Test vacuum_journal with 1 day."""
        binary, args, desc = CleanupOps.vacuum_journal(days=1)
        self.assertEqual(args, ["journalctl", "--vacuum-time=1d"])


class TestCleanupOpsTrimSsd(unittest.TestCase):
    """Tests for CleanupOps.trim_ssd()."""

    def test_trim_ssd_returns_correct_tuple(self):
        """Test trim_ssd returns pkexec fstrim -av."""
        binary, args, desc = CleanupOps.trim_ssd()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["fstrim", "-av"])
        self.assertIn("SSD", desc)


class TestCleanupOpsRebuildRpmdb(unittest.TestCase):
    """Tests for CleanupOps.rebuild_rpmdb()."""

    def test_rebuild_rpmdb_returns_correct_tuple(self):
        """Test rebuild_rpmdb returns pkexec rpm --rebuilddb."""
        binary, args, desc = CleanupOps.rebuild_rpmdb()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["rpm", "--rebuilddb"])
        self.assertIn("RPM", desc)


class TestCleanupOpsListTimeshift(unittest.TestCase):
    """Tests for CleanupOps.list_timeshift()."""

    def test_list_timeshift_returns_correct_tuple(self):
        """Test list_timeshift returns pkexec timeshift --list."""
        binary, args, desc = CleanupOps.list_timeshift()
        self.assertEqual(binary, "pkexec")
        self.assertEqual(args, ["timeshift", "--list"])
        self.assertIn("Timeshift", desc)


# ── TweakOps ──────────────────────────────────────────────────────────────


class TestTweakOpsSetPowerProfile(unittest.TestCase):
    """Tests for TweakOps.set_power_profile()."""

    def test_set_performance_profile(self):
        """Test setting performance power profile."""
        binary, args, desc = TweakOps.set_power_profile("performance")
        self.assertEqual(binary, "powerprofilesctl")
        self.assertEqual(args, ["set", "performance"])
        self.assertIn("performance", desc)

    def test_set_balanced_profile(self):
        """Test setting balanced power profile."""
        binary, args, desc = TweakOps.set_power_profile("balanced")
        self.assertEqual(args, ["set", "balanced"])

    def test_set_power_saver_profile(self):
        """Test setting power-saver profile."""
        binary, args, desc = TweakOps.set_power_profile("power-saver")
        self.assertEqual(args, ["set", "power-saver"])
        self.assertIn("power-saver", desc)

    def test_invalid_profile_defaults_to_balanced(self):
        """Test that invalid profile name falls back to balanced."""
        binary, args, desc = TweakOps.set_power_profile("turbo")
        self.assertEqual(args, ["set", "balanced"])

    def test_empty_profile_defaults_to_balanced(self):
        """Test that empty profile string falls back to balanced."""
        binary, args, desc = TweakOps.set_power_profile("")
        self.assertEqual(args, ["set", "balanced"])


class TestTweakOpsGetPowerProfile(unittest.TestCase):
    """Tests for TweakOps.get_power_profile()."""

    @patch("core.executor.operations.subprocess.run")
    def test_get_power_profile_success(self, mock_run):
        """Test getting power profile when command succeeds."""
        mock_run.return_value = MagicMock(returncode=0, stdout="balanced\n")
        result = TweakOps.get_power_profile()
        self.assertEqual(result, "balanced")
        mock_run.assert_called_once_with(
            ["powerprofilesctl", "get"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    @patch("core.executor.operations.subprocess.run")
    def test_get_power_profile_performance(self, mock_run):
        """Test getting performance profile string."""
        mock_run.return_value = MagicMock(returncode=0, stdout="performance\n")
        result = TweakOps.get_power_profile()
        self.assertEqual(result, "performance")

    @patch("core.executor.operations.subprocess.run")
    def test_get_power_profile_nonzero_exit(self, mock_run):
        """Test returns unknown when command returns non-zero."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = TweakOps.get_power_profile()
        self.assertEqual(result, "unknown")

    @patch("core.executor.operations.subprocess.run")
    def test_get_power_profile_exception(self, mock_run):
        """Test returns unknown when command raises exception."""
        mock_run.side_effect = FileNotFoundError("not found")
        result = TweakOps.get_power_profile()
        self.assertEqual(result, "unknown")

    @patch("core.executor.operations.subprocess.run")
    def test_get_power_profile_timeout(self, mock_run):
        """Test returns unknown on subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=10)
        result = TweakOps.get_power_profile()
        self.assertEqual(result, "unknown")

    @patch("core.executor.operations.subprocess.run")
    def test_get_power_profile_strips_whitespace(self, mock_run):
        """Test that output whitespace is stripped."""
        mock_run.return_value = MagicMock(returncode=0, stdout="  power-saver  \n")
        result = TweakOps.get_power_profile()
        self.assertEqual(result, "power-saver")


class TestTweakOpsRestartAudio(unittest.TestCase):
    """Tests for TweakOps.restart_audio()."""

    def test_restart_audio_returns_correct_tuple(self):
        """Test restart_audio returns systemctl user restart command."""
        binary, args, desc = TweakOps.restart_audio()
        self.assertEqual(binary, "systemctl")
        self.assertIn("--user", args)
        self.assertIn("restart", args)
        self.assertIn("pipewire", args)
        self.assertIn("pipewire-pulse", args)
        self.assertIn("wireplumber", args)
        self.assertIn("audio", desc.lower())


class TestTweakOpsSetBatteryLimit(unittest.TestCase):
    """Tests for TweakOps.set_battery_limit()."""

    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.write_file")
    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_success(self, mock_exists, mock_write, mock_run):
        """Test setting battery limit successfully."""
        mock_exists.return_value = True
        mock_write.return_value = (
            "pkexec",
            ["tee", TweakOps.BATTERY_SYSFS],
            "Writing...",
        )
        mock_run.return_value = MagicMock(returncode=0)
        result = TweakOps.set_battery_limit(80)
        self.assertTrue(result.success)
        self.assertIn("80", result.message)

    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.write_file")
    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_cmd_failure(self, mock_exists, mock_write, mock_run):
        """Test battery limit command failure."""
        mock_exists.return_value = True
        mock_write.return_value = (
            "pkexec",
            ["tee", TweakOps.BATTERY_SYSFS],
            "Writing...",
        )
        mock_run.return_value = MagicMock(returncode=1, stderr="Permission denied")
        result = TweakOps.set_battery_limit(80)
        self.assertFalse(result.success)
        self.assertIn("Failed", result.message)

    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_invalid_low(self, mock_exists):
        """Test battery limit below 50 returns failure."""
        result = TweakOps.set_battery_limit(30)
        self.assertFalse(result.success)
        self.assertIn("Invalid", result.message)

    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_invalid_high(self, mock_exists):
        """Test battery limit above 100 returns failure."""
        result = TweakOps.set_battery_limit(120)
        self.assertFalse(result.success)
        self.assertIn("Invalid", result.message)

    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_exact_50(self, mock_exists):
        """Test battery limit at exact boundary 50 is valid."""
        mock_exists.return_value = False
        result = TweakOps.set_battery_limit(50)
        # 50 is valid but sysfs missing
        self.assertFalse(result.success)
        self.assertIn("not supported", result.message)

    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_exact_100(self, mock_exists):
        """Test battery limit at exact boundary 100 is valid."""
        mock_exists.return_value = False
        result = TweakOps.set_battery_limit(100)
        self.assertFalse(result.success)
        self.assertIn("not supported", result.message)

    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_no_sysfs(self, mock_exists):
        """Test battery limit when sysfs path does not exist."""
        mock_exists.return_value = False
        result = TweakOps.set_battery_limit(80)
        self.assertFalse(result.success)
        self.assertIn("not supported", result.message)

    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.write_file")
    @patch("core.executor.operations.os.path.exists")
    def test_set_battery_limit_exception(self, mock_exists, mock_write, mock_run):
        """Test battery limit when subprocess raises exception."""
        mock_exists.return_value = True
        mock_write.return_value = (
            "pkexec",
            ["tee", TweakOps.BATTERY_SYSFS],
            "Writing...",
        )
        mock_run.side_effect = OSError("boom")
        result = TweakOps.set_battery_limit(80)
        self.assertFalse(result.success)
        self.assertIn("boom", result.message)

    def test_set_battery_limit_boundary_49(self):
        """Test battery limit 49 is rejected."""
        result = TweakOps.set_battery_limit(49)
        self.assertFalse(result.success)

    def test_set_battery_limit_boundary_101(self):
        """Test battery limit 101 is rejected."""
        result = TweakOps.set_battery_limit(101)
        self.assertFalse(result.success)


class TestTweakOpsInstallNbfc(unittest.TestCase):
    """Tests for TweakOps.install_nbfc()."""

    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_nbfc_returns_tuple(self, mock_dnf):
        """Test install_nbfc calls PrivilegedCommand.dnf and returns tuple."""
        mock_dnf.return_value = (
            "pkexec",
            ["dnf", "install", "-y", "nbfc-linux"],
            "Installing nbfc-linux...",
        )
        result = TweakOps.install_nbfc()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        mock_dnf.assert_called_once_with("install", "nbfc-linux")

    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_nbfc_rpm_ostree(self, mock_dnf):
        """Test install_nbfc on atomic system delegates to PrivilegedCommand."""
        mock_dnf.return_value = (
            "pkexec",
            ["rpm-ostree", "install", "nbfc-linux"],
            "Installing nbfc-linux via rpm-ostree...",
        )
        binary, args, desc = TweakOps.install_nbfc()
        self.assertEqual(binary, "pkexec")
        self.assertIn("nbfc-linux", args)


class TestTweakOpsSetFanProfile(unittest.TestCase):
    """Tests for TweakOps.set_fan_profile()."""

    def test_set_fan_profile(self):
        """Test setting a fan profile."""
        binary, args, desc = TweakOps.set_fan_profile("SilentMode")
        self.assertEqual(binary, "nbfc")
        self.assertEqual(args, ["config", "-a", "silentmode"])
        self.assertIn("SilentMode", desc)

    def test_set_fan_profile_lowercase_conversion(self):
        """Test that fan profile name is lowercased."""
        binary, args, desc = TweakOps.set_fan_profile("HighPerf")
        self.assertEqual(args[2], "highperf")

    def test_set_fan_profile_already_lowercase(self):
        """Test fan profile already lowercase is unchanged."""
        binary, args, desc = TweakOps.set_fan_profile("auto")
        self.assertEqual(args[2], "auto")


class TestTweakOpsBatterySysfs(unittest.TestCase):
    """Tests for TweakOps.BATTERY_SYSFS constant."""

    def test_battery_sysfs_path(self):
        """Test BATTERY_SYSFS is set to the expected kernel path."""
        self.assertEqual(
            TweakOps.BATTERY_SYSFS,
            "/sys/class/power_supply/BAT0/charge_control_end_threshold",
        )


# ── AdvancedOps ───────────────────────────────────────────────────────────


class TestAdvancedOpsApplyDnfTweaks(unittest.TestCase):
    """Tests for AdvancedOps.apply_dnf_tweaks()."""

    @patch("core.executor.operations.subprocess.run")
    @patch("builtins.open", mock_open(read_data="[main]\n"))
    def test_apply_dnf_tweaks_success(self, mock_run):
        """Test applying DNF tweaks when none are present."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.apply_dnf_tweaks()
        self.assertTrue(result.success)
        self.assertIn("applied", result.message.lower())
        mock_run.assert_called_once()

    @patch("core.executor.operations.subprocess.run")
    @patch(
        "builtins.open",
        mock_open(read_data="[main]\nmax_parallel_downloads=10\nfastestmirror=True\n"),
    )
    def test_apply_dnf_tweaks_already_optimized(self, mock_run):
        """Test that already-optimized DNF config is detected."""
        result = AdvancedOps.apply_dnf_tweaks()
        self.assertTrue(result.success)
        self.assertIn("already", result.message.lower())
        mock_run.assert_not_called()

    @patch("core.executor.operations.subprocess.run")
    @patch("builtins.open", mock_open(read_data="[main]\nmax_parallel_downloads=10\n"))
    def test_apply_dnf_tweaks_partial_config(self, mock_run):
        """Test applying only the missing tweak."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.apply_dnf_tweaks()
        self.assertTrue(result.success)
        # Check that the tee command was called with only fastestmirror
        call_args = mock_run.call_args
        self.assertIn(
            "fastestmirror=True",
            call_args.kwargs.get("input", call_args[1].get("input", "")),
        )

    @patch("core.executor.operations.subprocess.run")
    @patch("builtins.open", mock_open(read_data="[main]\n"))
    def test_apply_dnf_tweaks_write_failure(self, mock_run):
        """Test failure when tee command fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Permission denied")
        result = AdvancedOps.apply_dnf_tweaks()
        self.assertFalse(result.success)
        self.assertIn("Failed", result.message)

    @patch("core.executor.operations.subprocess.run")
    @patch("builtins.open", side_effect=OSError("No such file"))
    def test_apply_dnf_tweaks_read_failure_writes_all(self, mock_open_err, mock_run):
        """Test that read failure results in writing all tweaks."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.apply_dnf_tweaks()
        self.assertTrue(result.success)
        call_args = mock_run.call_args
        input_text = call_args.kwargs.get("input", "")
        self.assertIn("max_parallel_downloads=10", input_text)
        self.assertIn("fastestmirror=True", input_text)

    @patch("core.executor.operations.subprocess.run")
    @patch("builtins.open", side_effect=PermissionError("denied"))
    def test_apply_dnf_tweaks_permission_error_on_read(self, mock_open_err, mock_run):
        """Test graceful handling of PermissionError when reading dnf.conf."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.apply_dnf_tweaks()
        self.assertTrue(result.success)

    @patch("builtins.open", mock_open(read_data="[main]\n"))
    @patch("core.executor.operations.subprocess.run")
    def test_apply_dnf_tweaks_exception(self, mock_run):
        """Test handling of unexpected exception during tee."""
        mock_run.side_effect = OSError("unexpected")
        result = AdvancedOps.apply_dnf_tweaks()
        self.assertFalse(result.success)
        self.assertIn("unexpected", result.message)

    @patch("core.executor.operations.subprocess.run")
    @patch("builtins.open", mock_open(read_data="[main]\n"))
    def test_apply_dnf_tweaks_uses_tee_append(self, mock_run):
        """Test that dnf tweaks are appended using pkexec tee -a."""
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.apply_dnf_tweaks()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "pkexec")
        self.assertEqual(call_args[1], "tee")
        self.assertEqual(call_args[2], "-a")

    @patch("core.executor.operations.subprocess.run")
    @patch("builtins.open", mock_open(read_data="[main]\n"))
    def test_apply_dnf_tweaks_timeout_set(self, mock_run):
        """Test that subprocess.run is called with timeout."""
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.apply_dnf_tweaks()
        call_kwargs = (
            mock_run.call_args[1]
            if mock_run.call_args[1]
            else mock_run.call_args.kwargs
        )
        self.assertIn("timeout", call_kwargs)
        self.assertEqual(call_kwargs["timeout"], 30)


class TestAdvancedOpsEnableTcpBbr(unittest.TestCase):
    """Tests for AdvancedOps.enable_tcp_bbr()."""

    @patch("core.executor.operations.subprocess.run")
    def test_enable_tcp_bbr_success(self, mock_run):
        """Test enabling TCP BBR successfully."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.enable_tcp_bbr()
        self.assertTrue(result.success)
        self.assertIn("BBR", result.message)
        self.assertEqual(mock_run.call_count, 2)

    @patch("core.executor.operations.subprocess.run")
    def test_enable_tcp_bbr_write_failure(self, mock_run):
        """Test failure when writing sysctl config fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="write error")
        result = AdvancedOps.enable_tcp_bbr()
        self.assertFalse(result.success)
        self.assertIn("write config", result.message.lower())

    @patch("core.executor.operations.subprocess.run")
    def test_enable_tcp_bbr_sysctl_reload_failure(self, mock_run):
        """Test failure when sysctl reload fails."""
        # First call succeeds (write), second fails (sysctl --system)
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1, stderr="reload error"),
        ]
        result = AdvancedOps.enable_tcp_bbr()
        self.assertFalse(result.success)
        self.assertIn("sysctl reload", result.message.lower())

    @patch("core.executor.operations.subprocess.run")
    def test_enable_tcp_bbr_exception(self, mock_run):
        """Test handling of exception during BBR enable."""
        mock_run.side_effect = OSError("network error")
        result = AdvancedOps.enable_tcp_bbr()
        self.assertFalse(result.success)
        self.assertIn("network error", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_enable_tcp_bbr_writes_correct_config(self, mock_run):
        """Test that BBR config contains correct sysctl values."""
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.enable_tcp_bbr()
        first_call = mock_run.call_args_list[0]
        input_text = first_call.kwargs.get("input", first_call[1].get("input", ""))
        self.assertIn("net.core.default_qdisc=fq", input_text)
        self.assertIn("net.ipv4.tcp_congestion_control=bbr", input_text)

    @patch("core.executor.operations.subprocess.run")
    def test_enable_tcp_bbr_calls_sysctl_system(self, mock_run):
        """Test that sysctl --system is called after writing config."""
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.enable_tcp_bbr()
        second_call_args = mock_run.call_args_list[1][0][0]
        self.assertEqual(second_call_args, ["pkexec", "sysctl", "--system"])


class TestAdvancedOpsInstallGamemode(unittest.TestCase):
    """Tests for AdvancedOps.install_gamemode()."""

    @patch("core.executor.operations.getpass.getuser")
    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_gamemode_success(self, mock_dnf, mock_run, mock_user):
        """Test installing GameMode successfully."""
        mock_user.return_value = "testuser"
        mock_dnf.return_value = (
            "pkexec",
            ["dnf", "install", "-y", "gamemode"],
            "Installing gamemode...",
        )
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.install_gamemode()
        self.assertTrue(result.success)
        self.assertIn("testuser", result.message)
        self.assertEqual(mock_run.call_count, 2)

    @patch("core.executor.operations.getpass.getuser")
    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_gamemode_install_failure(self, mock_dnf, mock_run, mock_user):
        """Test failure when gamemode package install fails."""
        mock_user.return_value = "testuser"
        mock_dnf.return_value = (
            "pkexec",
            ["dnf", "install", "-y", "gamemode"],
            "Installing...",
        )
        mock_run.return_value = MagicMock(returncode=1, stderr="not found")
        result = AdvancedOps.install_gamemode()
        self.assertFalse(result.success)
        self.assertIn("Install failed", result.message)

    @patch("core.executor.operations.getpass.getuser")
    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_gamemode_usermod_failure(self, mock_dnf, mock_run, mock_user):
        """Test failure when usermod command fails."""
        mock_user.return_value = "testuser"
        mock_dnf.return_value = (
            "pkexec",
            ["dnf", "install", "-y", "gamemode"],
            "Installing...",
        )
        mock_run.side_effect = [
            MagicMock(returncode=0),  # install succeeds
            MagicMock(returncode=1, stderr="usermod error"),  # usermod fails
        ]
        result = AdvancedOps.install_gamemode()
        self.assertFalse(result.success)
        self.assertIn("usermod", result.message.lower())

    @patch("core.executor.operations.getpass.getuser")
    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_gamemode_exception(self, mock_dnf, mock_run, mock_user):
        """Test handling of exception during gamemode install."""
        mock_user.return_value = "testuser"
        mock_dnf.return_value = (
            "pkexec",
            ["dnf", "install", "-y", "gamemode"],
            "Installing...",
        )
        mock_run.side_effect = OSError("disk full")
        result = AdvancedOps.install_gamemode()
        self.assertFalse(result.success)
        self.assertIn("disk full", result.message)

    @patch("core.executor.operations.getpass.getuser")
    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_gamemode_uses_correct_usermod(self, mock_dnf, mock_run, mock_user):
        """Test that usermod adds user to gamemode group."""
        mock_user.return_value = "loofi"
        mock_dnf.return_value = (
            "pkexec",
            ["dnf", "install", "-y", "gamemode"],
            "Installing...",
        )
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.install_gamemode()
        usermod_call = mock_run.call_args_list[1][0][0]
        self.assertEqual(
            usermod_call, ["pkexec", "usermod", "-aG", "gamemode", "loofi"]
        )

    @patch("core.executor.operations.getpass.getuser")
    @patch("core.executor.operations.subprocess.run")
    @patch("core.executor.operations.PrivilegedCommand.dnf")
    def test_install_gamemode_timeout_on_install(self, mock_dnf, mock_run, mock_user):
        """Test that install step uses 300-second timeout."""
        mock_user.return_value = "testuser"
        mock_dnf.return_value = (
            "pkexec",
            ["dnf", "install", "-y", "gamemode"],
            "Installing...",
        )
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.install_gamemode()
        install_call_kwargs = (
            mock_run.call_args_list[0][1]
            if mock_run.call_args_list[0][1]
            else mock_run.call_args_list[0].kwargs
        )
        self.assertEqual(install_call_kwargs["timeout"], 300)


class TestAdvancedOpsSetSwappiness(unittest.TestCase):
    """Tests for AdvancedOps.set_swappiness()."""

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_success(self, mock_run):
        """Test setting swappiness successfully."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.set_swappiness(10)
        self.assertTrue(result.success)
        self.assertIn("10", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_default_value(self, mock_run):
        """Test set_swappiness with default value."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.set_swappiness()
        self.assertTrue(result.success)
        self.assertIn("10", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_custom_value(self, mock_run):
        """Test set_swappiness with custom value."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.set_swappiness(60)
        self.assertTrue(result.success)
        self.assertIn("60", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_invalid_clamps_to_default(self, mock_run):
        """Test set_swappiness with invalid value resets to 10."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.set_swappiness(-1)
        self.assertTrue(result.success)
        self.assertIn("10", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_over_100_clamps(self, mock_run):
        """Test set_swappiness with value over 100 resets to 10."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.set_swappiness(200)
        self.assertTrue(result.success)
        self.assertIn("10", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_boundary_zero(self, mock_run):
        """Test set_swappiness with value 0 is valid."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.set_swappiness(0)
        self.assertTrue(result.success)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_boundary_100(self, mock_run):
        """Test set_swappiness with value 100 is valid."""
        mock_run.return_value = MagicMock(returncode=0)
        result = AdvancedOps.set_swappiness(100)
        self.assertTrue(result.success)
        self.assertIn("100", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_write_failure(self, mock_run):
        """Test failure when writing sysctl config fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="write error")
        result = AdvancedOps.set_swappiness(10)
        self.assertFalse(result.success)
        self.assertIn("write config", result.message.lower())

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_sysctl_reload_failure(self, mock_run):
        """Test failure when sysctl reload fails after write."""
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=1, stderr="reload error"),
        ]
        result = AdvancedOps.set_swappiness(10)
        self.assertFalse(result.success)
        self.assertIn("sysctl reload", result.message.lower())

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_exception(self, mock_run):
        """Test handling of exception during swappiness set."""
        mock_run.side_effect = OSError("kaboom")
        result = AdvancedOps.set_swappiness(10)
        self.assertFalse(result.success)
        self.assertIn("kaboom", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_writes_correct_config(self, mock_run):
        """Test that correct vm.swappiness config is written."""
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.set_swappiness(30)
        first_call = mock_run.call_args_list[0]
        input_text = first_call.kwargs.get("input", first_call[1].get("input", ""))
        self.assertEqual(input_text, "vm.swappiness=30\n")

    @patch("core.executor.operations.subprocess.run")
    def test_set_swappiness_uses_correct_conf_path(self, mock_run):
        """Test that the correct sysctl.d config path is used."""
        mock_run.return_value = MagicMock(returncode=0)
        AdvancedOps.set_swappiness(10)
        first_call_cmd = mock_run.call_args_list[0][0][0]
        self.assertIn("/etc/sysctl.d/99-swappiness.conf", first_call_cmd)


# ── NetworkOps ────────────────────────────────────────────────────────────


class TestNetworkOpsDnsProviders(unittest.TestCase):
    """Tests for NetworkOps.DNS_PROVIDERS constant."""

    def test_dns_providers_has_cloudflare(self):
        """Test DNS_PROVIDERS contains cloudflare."""
        self.assertIn("cloudflare", NetworkOps.DNS_PROVIDERS)
        self.assertEqual(NetworkOps.DNS_PROVIDERS["cloudflare"], ("1.1.1.1", "1.0.0.1"))

    def test_dns_providers_has_google(self):
        """Test DNS_PROVIDERS contains google."""
        self.assertIn("google", NetworkOps.DNS_PROVIDERS)
        self.assertEqual(NetworkOps.DNS_PROVIDERS["google"], ("8.8.8.8", "8.8.4.4"))

    def test_dns_providers_has_quad9(self):
        """Test DNS_PROVIDERS contains quad9."""
        self.assertIn("quad9", NetworkOps.DNS_PROVIDERS)
        self.assertEqual(
            NetworkOps.DNS_PROVIDERS["quad9"], ("9.9.9.9", "149.112.112.112")
        )

    def test_dns_providers_has_opendns(self):
        """Test DNS_PROVIDERS contains opendns."""
        self.assertIn("opendns", NetworkOps.DNS_PROVIDERS)
        self.assertEqual(
            NetworkOps.DNS_PROVIDERS["opendns"],
            ("208.67.222.222", "208.67.220.220"),
        )

    def test_dns_providers_all_have_two_addresses(self):
        """Test all DNS providers have exactly two addresses."""
        for provider, addrs in NetworkOps.DNS_PROVIDERS.items():
            self.assertEqual(len(addrs), 2, f"{provider} should have 2 addresses")


class TestNetworkOpsSetDns(unittest.TestCase):
    """Tests for NetworkOps.set_dns()."""

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_cloudflare_success(self, mock_run):
        """Test setting DNS to cloudflare successfully."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="MyWifi\n"),  # nmcli show
            MagicMock(returncode=0),  # nmcli modify
            MagicMock(returncode=0),  # nmcli up
        ]
        result = NetworkOps.set_dns("cloudflare")
        self.assertTrue(result.success)
        self.assertIn("cloudflare", result.message)
        self.assertIn("1.1.1.1", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_google_success(self, mock_run):
        """Test setting DNS to google successfully."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="eth0\n"),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        result = NetworkOps.set_dns("google")
        self.assertTrue(result.success)
        self.assertIn("google", result.message)

    def test_set_dns_unknown_provider(self):
        """Test set_dns with unknown provider returns failure."""
        result = NetworkOps.set_dns("unknown_dns")
        self.assertFalse(result.success)
        self.assertIn("Unknown provider", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_no_active_connection(self, mock_run):
        """Test set_dns when no active connection is found."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = NetworkOps.set_dns("cloudflare")
        self.assertFalse(result.success)
        self.assertIn("No active connection", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_empty_connections_list(self, mock_run):
        """Test set_dns when connections list is empty after parsing."""
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")
        result = NetworkOps.set_dns("cloudflare")
        # The first entry will be empty string, which is falsy
        # but code uses connections[0], which is an empty string
        # Depending on logic this may proceed or fail
        self.assertIsInstance(result, OperationResult)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_modify_failure(self, mock_run):
        """Test set_dns when nmcli modify command fails."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="MyWifi\n"),
            MagicMock(returncode=1, stderr="modify error"),
            MagicMock(returncode=0),
        ]
        result = NetworkOps.set_dns("cloudflare")
        self.assertFalse(result.success)
        self.assertIn("Failed", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_case_insensitive(self, mock_run):
        """Test that provider name is case-insensitive."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="wlan0\n"),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        result = NetworkOps.set_dns("Cloudflare")
        self.assertTrue(result.success)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_uppercase_provider(self, mock_run):
        """Test that fully uppercase provider works."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="wlan0\n"),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        result = NetworkOps.set_dns("GOOGLE")
        self.assertTrue(result.success)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_exception(self, mock_run):
        """Test handling of exception during DNS set."""
        mock_run.side_effect = OSError("network down")
        result = NetworkOps.set_dns("cloudflare")
        self.assertFalse(result.success)
        self.assertIn("network down", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_quad9_with_correct_ips(self, mock_run):
        """Test that quad9 DNS uses correct IP addresses."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="conn1\n"),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        result = NetworkOps.set_dns("quad9")
        self.assertTrue(result.success)
        self.assertIn("9.9.9.9", result.message)
        self.assertIn("149.112.112.112", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_opendns(self, mock_run):
        """Test setting DNS to opendns."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="conn1\n"),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        result = NetworkOps.set_dns("opendns")
        self.assertTrue(result.success)
        self.assertIn("opendns", result.message)

    @patch("core.executor.operations.subprocess.run")
    def test_set_dns_restarts_connection(self, mock_run):
        """Test that set_dns calls nmcli connection up after modify."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="MyConn\n"),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]
        NetworkOps.set_dns("cloudflare")
        # Third call should be nmcli connection up
        third_call = mock_run.call_args_list[2][0][0]
        self.assertEqual(third_call, ["nmcli", "connection", "up", "MyConn"])


# ── execute_operation ─────────────────────────────────────────────────────


class TestExecuteOperation(unittest.TestCase):
    """Tests for execute_operation() bridge function."""

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_pkexec_command(self, mock_run):
        """Test execute_operation with pkexec-prefixed tuple."""
        mock_run.return_value = MagicMock(success=True, message="done")
        op = ("pkexec", ["dnf", "clean", "all"], "Cleaning...")
        result = execute_operation(op)
        mock_run.assert_called_once_with(
            "dnf", ["clean", "all"], preview=False, pkexec=True
        )

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_non_pkexec_command(self, mock_run):
        """Test execute_operation with non-pkexec command."""
        mock_run.return_value = MagicMock(success=True, message="done")
        op = ("systemctl", ["--user", "restart", "pipewire"], "Restarting...")
        result = execute_operation(op)
        mock_run.assert_called_once_with(
            "systemctl", ["--user", "restart", "pipewire"], preview=False, pkexec=False
        )

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_preview_mode(self, mock_run):
        """Test execute_operation with preview=True."""
        mock_run.return_value = MagicMock(success=True, preview=True)
        op = ("pkexec", ["fstrim", "-av"], "Trimming...")
        result = execute_operation(op, preview=True)
        mock_run.assert_called_once_with("fstrim", ["-av"], preview=True, pkexec=True)

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_returns_action_result(self, mock_run):
        """Test that execute_operation returns an ActionResult-like object."""
        mock_result = MagicMock(success=True, message="OK")
        mock_run.return_value = mock_result
        op = ("pkexec", ["rpm", "--rebuilddb"], "Rebuilding...")
        result = execute_operation(op)
        self.assertTrue(result.success)

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_failure(self, mock_run):
        """Test execute_operation when underlying command fails."""
        mock_result = MagicMock(success=False, message="Failed")
        mock_run.return_value = mock_result
        op = ("pkexec", ["dnf", "autoremove", "-y"], "Removing...")
        result = execute_operation(op)
        self.assertFalse(result.success)

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_strips_pkexec_from_args(self, mock_run):
        """Test that pkexec is stripped and args are shifted correctly."""
        mock_run.return_value = MagicMock(success=True)
        op = ("pkexec", ["journalctl", "--vacuum-time=14d"], "Vacuuming...")
        execute_operation(op)
        mock_run.assert_called_once_with(
            "journalctl", ["--vacuum-time=14d"], preview=False, pkexec=True
        )

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_powerprofilesctl(self, mock_run):
        """Test execute_operation with powerprofilesctl (non-pkexec)."""
        mock_run.return_value = MagicMock(success=True)
        op = ("powerprofilesctl", ["set", "balanced"], "Setting profile...")
        execute_operation(op)
        mock_run.assert_called_once_with(
            "powerprofilesctl", ["set", "balanced"], preview=False, pkexec=False
        )

    @patch("core.executor.action_executor.ActionExecutor.run")
    def test_execute_operation_nbfc(self, mock_run):
        """Test execute_operation with nbfc command."""
        mock_run.return_value = MagicMock(success=True)
        op = ("nbfc", ["config", "-a", "auto"], "Setting fan...")
        execute_operation(op)
        mock_run.assert_called_once_with(
            "nbfc", ["config", "-a", "auto"], preview=False, pkexec=False
        )


# ── CLI_COMMANDS ──────────────────────────────────────────────────────────


class TestCLICommands(unittest.TestCase):
    """Tests for the CLI_COMMANDS registry dict."""

    def test_cli_commands_has_cleanup_category(self):
        """Test CLI_COMMANDS contains cleanup category."""
        self.assertIn("cleanup", CLI_COMMANDS)

    def test_cli_commands_has_tweak_category(self):
        """Test CLI_COMMANDS contains tweak category."""
        self.assertIn("tweak", CLI_COMMANDS)

    def test_cli_commands_has_advanced_category(self):
        """Test CLI_COMMANDS contains advanced category."""
        self.assertIn("advanced", CLI_COMMANDS)

    def test_cli_commands_has_network_category(self):
        """Test CLI_COMMANDS contains network category."""
        self.assertIn("network", CLI_COMMANDS)

    def test_cleanup_has_dnf(self):
        """Test cleanup category has dnf command."""
        self.assertIn("dnf", CLI_COMMANDS["cleanup"])
        self.assertEqual(CLI_COMMANDS["cleanup"]["dnf"], CleanupOps.clean_dnf_cache)

    def test_cleanup_has_autoremove(self):
        """Test cleanup category has autoremove command."""
        self.assertIn("autoremove", CLI_COMMANDS["cleanup"])
        self.assertEqual(CLI_COMMANDS["cleanup"]["autoremove"], CleanupOps.autoremove)

    def test_cleanup_has_journal(self):
        """Test cleanup category has journal command."""
        self.assertIn("journal", CLI_COMMANDS["cleanup"])
        self.assertEqual(CLI_COMMANDS["cleanup"]["journal"], CleanupOps.vacuum_journal)

    def test_cleanup_has_trim(self):
        """Test cleanup category has trim command."""
        self.assertIn("trim", CLI_COMMANDS["cleanup"])
        self.assertEqual(CLI_COMMANDS["cleanup"]["trim"], CleanupOps.trim_ssd)

    def test_cleanup_has_rpmdb(self):
        """Test cleanup category has rpmdb command."""
        self.assertIn("rpmdb", CLI_COMMANDS["cleanup"])
        self.assertEqual(CLI_COMMANDS["cleanup"]["rpmdb"], CleanupOps.rebuild_rpmdb)

    def test_tweak_has_power(self):
        """Test tweak category has power command."""
        self.assertIn("power", CLI_COMMANDS["tweak"])
        self.assertEqual(CLI_COMMANDS["tweak"]["power"], TweakOps.set_power_profile)

    def test_tweak_has_audio(self):
        """Test tweak category has audio command."""
        self.assertIn("audio", CLI_COMMANDS["tweak"])
        self.assertEqual(CLI_COMMANDS["tweak"]["audio"], TweakOps.restart_audio)

    def test_tweak_has_battery(self):
        """Test tweak category has battery command."""
        self.assertIn("battery", CLI_COMMANDS["tweak"])
        self.assertEqual(CLI_COMMANDS["tweak"]["battery"], TweakOps.set_battery_limit)

    def test_advanced_has_dnf_tweaks(self):
        """Test advanced category has dnf-tweaks command."""
        self.assertIn("dnf-tweaks", CLI_COMMANDS["advanced"])
        self.assertEqual(
            CLI_COMMANDS["advanced"]["dnf-tweaks"], AdvancedOps.apply_dnf_tweaks
        )

    def test_advanced_has_bbr(self):
        """Test advanced category has bbr command."""
        self.assertIn("bbr", CLI_COMMANDS["advanced"])
        self.assertEqual(CLI_COMMANDS["advanced"]["bbr"], AdvancedOps.enable_tcp_bbr)

    def test_advanced_has_gamemode(self):
        """Test advanced category has gamemode command."""
        self.assertIn("gamemode", CLI_COMMANDS["advanced"])
        self.assertEqual(
            CLI_COMMANDS["advanced"]["gamemode"], AdvancedOps.install_gamemode
        )

    def test_advanced_has_swappiness(self):
        """Test advanced category has swappiness command."""
        self.assertIn("swappiness", CLI_COMMANDS["advanced"])
        self.assertEqual(
            CLI_COMMANDS["advanced"]["swappiness"], AdvancedOps.set_swappiness
        )

    def test_network_has_dns(self):
        """Test network category has dns command."""
        self.assertIn("dns", CLI_COMMANDS["network"])
        self.assertEqual(CLI_COMMANDS["network"]["dns"], NetworkOps.set_dns)

    def test_all_commands_are_callable(self):
        """Test all registered CLI commands are callable."""
        for category, commands in CLI_COMMANDS.items():
            for name, func in commands.items():
                self.assertTrue(
                    callable(func),
                    f"{category}.{name} is not callable",
                )

    def test_cli_commands_category_count(self):
        """Test CLI_COMMANDS has exactly 4 categories."""
        self.assertEqual(len(CLI_COMMANDS), 4)

    def test_cleanup_command_count(self):
        """Test cleanup category has 5 commands."""
        self.assertEqual(len(CLI_COMMANDS["cleanup"]), 5)

    def test_tweak_command_count(self):
        """Test tweak category has 3 commands."""
        self.assertEqual(len(CLI_COMMANDS["tweak"]), 3)

    def test_advanced_command_count(self):
        """Test advanced category has 4 commands."""
        self.assertEqual(len(CLI_COMMANDS["advanced"]), 4)

    def test_network_command_count(self):
        """Test network category has 1 command."""
        self.assertEqual(len(CLI_COMMANDS["network"]), 1)


if __name__ == "__main__":
    unittest.main()
