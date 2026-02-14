"""
Tests for v10.0 "Zenith Update" foundation modules.
Covers: errors hierarchy, command builder, formatting utilities, and hardware profiles.
"""
import io
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.errors import (
    LoofiError, DnfLockedError, PrivilegeError,
    CommandFailedError, HardwareNotFoundError, NetworkError, ConfigError,
)
from utils.commands import PrivilegedCommand
from utils.formatting import bytes_to_human, seconds_to_human, percent_bar, truncate
from services.hardware import (
    detect_hardware_profile, get_profile_label, get_all_profiles, PROFILES,
)


# ---------------------------------------------------------------------------
# TestErrors — error hierarchy
# ---------------------------------------------------------------------------

class TestErrors(unittest.TestCase):
    """Tests for the centralized error hierarchy."""

    def test_loofi_error_base_attributes(self):
        """LoofiError stores code, hint, and recoverable flag."""
        err = LoofiError("boom", code="TEST", hint="try again", recoverable=False)
        self.assertEqual(str(err), "boom")
        self.assertEqual(err.code, "TEST")
        self.assertEqual(err.hint, "try again")
        self.assertFalse(err.recoverable)

    def test_loofi_error_defaults(self):
        """LoofiError uses sensible defaults when optional args are omitted."""
        err = LoofiError("oops")
        self.assertEqual(err.code, "UNKNOWN")
        self.assertEqual(err.hint, "")
        self.assertTrue(err.recoverable)

    def test_loofi_error_is_exception(self):
        """LoofiError is a proper Exception subclass."""
        self.assertTrue(issubclass(LoofiError, Exception))

    def test_dnf_locked_error_attributes(self):
        """DnfLockedError has correct code, is recoverable, mentions package manager."""
        err = DnfLockedError()
        self.assertEqual(err.code, "DNF_LOCKED")
        self.assertTrue(err.recoverable)
        self.assertIn("package manager", str(err))

    def test_dnf_locked_error_hint(self):
        """DnfLockedError provides a useful recovery hint."""
        err = DnfLockedError()
        self.assertIn("dnf.pid", err.hint)

    def test_privilege_error_with_operation(self):
        """PrivilegeError includes the operation name in its message."""
        err = PrivilegeError("installing packages")
        self.assertEqual(err.code, "PERMISSION_DENIED")
        self.assertTrue(err.recoverable)
        self.assertIn("installing packages", str(err))

    def test_privilege_error_without_operation(self):
        """PrivilegeError works without an operation name."""
        err = PrivilegeError()
        self.assertIn("privileges required", str(err))
        self.assertIn("pkexec", err.hint)

    def test_command_failed_error(self):
        """CommandFailedError captures cmd, exit code, and stderr."""
        err = CommandFailedError("dnf install vim", 1, "Error: nothing to do")
        self.assertEqual(err.code, "COMMAND_FAILED")
        self.assertIn("dnf install vim", str(err))
        self.assertIn("exit code 1", str(err))
        self.assertIn("Error: nothing to do", str(err))

    def test_command_failed_error_no_stderr(self):
        """CommandFailedError works when stderr is empty."""
        err = CommandFailedError("rpm --rebuilddb", 2)
        self.assertIn("exit code 2", str(err))
        self.assertNotIn("\n", str(err))

    def test_hardware_not_found_error(self):
        """HardwareNotFoundError is not recoverable."""
        err = HardwareNotFoundError("fingerprint reader")
        self.assertEqual(err.code, "HARDWARE_NOT_FOUND")
        self.assertFalse(err.recoverable)
        self.assertIn("fingerprint reader", str(err))

    def test_hardware_not_found_error_no_component(self):
        """HardwareNotFoundError without component uses generic message."""
        err = HardwareNotFoundError()
        self.assertIn("hardware not found", str(err).lower())

    def test_network_error_attributes(self):
        """NetworkError has correct code and is recoverable."""
        err = NetworkError("DNS resolution failed")
        self.assertEqual(err.code, "NETWORK_ERROR")
        self.assertTrue(err.recoverable)
        self.assertIn("DNS resolution failed", str(err))

    def test_network_error_default_message(self):
        """NetworkError uses a default message when none is provided."""
        err = NetworkError()
        self.assertIn("Network operation failed", str(err))

    def test_config_error_with_path(self):
        """ConfigError includes path and detail in message."""
        err = ConfigError("/etc/loofi/config.json", "invalid JSON")
        self.assertEqual(err.code, "CONFIG_ERROR")
        self.assertIn("/etc/loofi/config.json", str(err))
        self.assertIn("invalid JSON", str(err))

    def test_config_error_no_path(self):
        """ConfigError without path uses generic message."""
        err = ConfigError()
        self.assertIn("Invalid configuration", str(err))

    def test_all_errors_inherit_from_loofi_error(self):
        """All custom exceptions inherit from LoofiError."""
        for cls in (DnfLockedError, PrivilegeError, CommandFailedError,
                    HardwareNotFoundError, NetworkError, ConfigError):
            self.assertTrue(issubclass(cls, LoofiError),
                            f"{cls.__name__} should inherit from LoofiError")


# ---------------------------------------------------------------------------
# TestCommands — PrivilegedCommand builder
# ---------------------------------------------------------------------------

class TestCommands(unittest.TestCase):
    """Tests for the centralized command builder."""

    @patch('utils.commands.SystemManager.get_package_manager', return_value='dnf')
    def test_dnf_install_traditional(self, mock_pm):
        """Traditional system: dnf install with -y flag."""
        cmd, args, desc = PrivilegedCommand.dnf("install", "vim")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("dnf", args)
        self.assertIn("install", args)
        self.assertIn("vim", args)
        self.assertIn("-y", args)
        self.assertIn("vim", desc)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='dnf')
    def test_dnf_remove_traditional(self, mock_pm):
        """Traditional system: dnf remove."""
        cmd, args, desc = PrivilegedCommand.dnf("remove", "nano")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("remove", args)
        self.assertIn("nano", args)
        self.assertIn("-y", args)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='dnf')
    def test_dnf_update_traditional(self, mock_pm):
        """Traditional system: dnf update (no packages)."""
        cmd, args, desc = PrivilegedCommand.dnf("update")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("update", args)
        self.assertIn("Updating", desc)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='dnf')
    def test_dnf_clean_traditional(self, mock_pm):
        """Traditional system: dnf clean."""
        cmd, args, desc = PrivilegedCommand.dnf("clean")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("clean", args)
        self.assertIn("Cleaning", desc)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='rpm-ostree')
    def test_dnf_install_atomic(self, mock_pm):
        """Atomic system: rpm-ostree install instead of dnf."""
        cmd, args, desc = PrivilegedCommand.dnf("install", "vim")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("install", args)
        self.assertIn("vim", args)
        self.assertNotIn("dnf", args)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='rpm-ostree')
    def test_dnf_remove_atomic(self, mock_pm):
        """Atomic system: rpm-ostree uninstall."""
        cmd, args, desc = PrivilegedCommand.dnf("remove", "nano")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("uninstall", args)
        self.assertIn("nano", args)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='rpm-ostree')
    def test_dnf_update_atomic(self, mock_pm):
        """Atomic system: rpm-ostree upgrade."""
        cmd, args, desc = PrivilegedCommand.dnf("update")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("upgrade", args)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='rpm-ostree')
    def test_dnf_clean_atomic(self, mock_pm):
        """Atomic system: rpm-ostree cleanup --base."""
        cmd, args, desc = PrivilegedCommand.dnf("clean")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("cleanup", args)
        self.assertIn("--base", args)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='dnf')
    def test_dnf_install_multiple_packages(self, mock_pm):
        """Traditional system: multiple packages in a single install."""
        cmd, args, desc = PrivilegedCommand.dnf("install", "vim", "git", "htop")
        self.assertIn("vim", args)
        self.assertIn("git", args)
        self.assertIn("htop", args)
        self.assertIn("vim", desc)
        self.assertIn("git", desc)

    @patch('utils.commands.SystemManager.get_package_manager', return_value='dnf')
    def test_dnf_with_flags(self, mock_pm):
        """Custom flags are injected into the dnf command."""
        cmd, args, desc = PrivilegedCommand.dnf("install", "kernel-devel",
                                                 flags=["--best", "--allowerasing"])
        self.assertIn("--best", args)
        self.assertIn("--allowerasing", args)

    def test_systemctl_system_service(self):
        """systemctl for a system service uses pkexec."""
        cmd, args, desc = PrivilegedCommand.systemctl("restart", "sshd")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("systemctl", args)
        self.assertIn("restart", args)
        self.assertIn("sshd", args)

    def test_systemctl_user_service(self):
        """systemctl --user does NOT use pkexec."""
        cmd, args, desc = PrivilegedCommand.systemctl("restart", "pipewire", user=True)
        self.assertEqual(cmd, "systemctl")
        self.assertIn("--user", args)
        self.assertIn("restart", args)
        self.assertIn("pipewire", args)

    def test_sysctl_command(self):
        """sysctl set command builds correctly."""
        cmd, args, desc = PrivilegedCommand.sysctl("vm.swappiness", "10")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("sysctl", args)
        self.assertIn("-w", args)
        self.assertIn("vm.swappiness=10", args)

    def test_fstrim_command(self):
        """fstrim command uses pkexec and -av flags."""
        cmd, args, desc = PrivilegedCommand.fstrim()
        self.assertEqual(cmd, "pkexec")
        self.assertIn("fstrim", args)
        self.assertIn("-av", args)
        self.assertIn("Trimming", desc)

    def test_write_file_command(self):
        """write_file uses pkexec tee."""
        cmd, args, desc = PrivilegedCommand.write_file("/etc/sysctl.d/99-bbr.conf", "net.core.default_qdisc=fq")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("tee", args)
        self.assertIn("/etc/sysctl.d/99-bbr.conf", args)

    def test_flatpak_command(self):
        """flatpak commands do not use pkexec."""
        cmd, args, desc = PrivilegedCommand.flatpak("install", "flathub", "org.keepassxc.KeePassXC")
        self.assertEqual(cmd, "flatpak")
        self.assertIn("install", args)
        self.assertIn("flathub", args)

    def test_fwupd_command(self):
        """fwupdmgr update via pkexec."""
        cmd, args, desc = PrivilegedCommand.fwupd("update")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("fwupdmgr", args)
        self.assertIn("update", args)
        self.assertIn("-y", args)

    def test_journal_vacuum_command(self):
        """journal vacuum builds correct time argument."""
        cmd, args, desc = PrivilegedCommand.journal_vacuum("3weeks")
        self.assertEqual(cmd, "pkexec")
        self.assertIn("journalctl", args)
        self.assertIn("--vacuum-time=3weeks", args)

    def test_journal_vacuum_default(self):
        """journal vacuum defaults to 2weeks."""
        cmd, args, desc = PrivilegedCommand.journal_vacuum()
        self.assertIn("--vacuum-time=2weeks", args)

    def test_rpm_rebuild_command(self):
        """RPM database rebuild uses pkexec."""
        cmd, args, desc = PrivilegedCommand.rpm_rebuild()
        self.assertEqual(cmd, "pkexec")
        self.assertIn("rpm", args)
        self.assertIn("--rebuilddb", args)


# ---------------------------------------------------------------------------
# TestFormatting — shared formatters
# ---------------------------------------------------------------------------

class TestFormatting(unittest.TestCase):
    """Tests for the shared formatting utility functions."""

    def test_bytes_to_human_zero(self):
        self.assertEqual(bytes_to_human(0), "0.0 B")

    def test_bytes_to_human_bytes(self):
        self.assertEqual(bytes_to_human(512), "512.0 B")

    def test_bytes_to_human_kib(self):
        self.assertEqual(bytes_to_human(1024), "1.0 KiB")

    def test_bytes_to_human_mib(self):
        self.assertEqual(bytes_to_human(1048576), "1.0 MiB")

    def test_bytes_to_human_gib(self):
        self.assertEqual(bytes_to_human(1073741824), "1.0 GiB")

    def test_bytes_to_human_tib(self):
        self.assertEqual(bytes_to_human(1099511627776), "1.0 TiB")

    def test_bytes_to_human_pib(self):
        self.assertEqual(bytes_to_human(1125899906842624), "1.0 PiB")

    def test_bytes_to_human_fractional(self):
        result = bytes_to_human(1536)
        self.assertEqual(result, "1.5 KiB")

    def test_seconds_to_human_seconds_only(self):
        self.assertEqual(seconds_to_human(45), "45s")

    def test_seconds_to_human_minutes(self):
        self.assertEqual(seconds_to_human(125), "2m 5s")

    def test_seconds_to_human_hours(self):
        self.assertEqual(seconds_to_human(7384), "2h 3m 4s")

    def test_percent_bar_zero(self):
        bar = percent_bar(0)
        self.assertIn("[", bar)
        self.assertIn("]", bar)
        self.assertIn("0%", bar)

    def test_percent_bar_full(self):
        bar = percent_bar(100, width=10)
        self.assertIn("==========" , bar)
        self.assertIn("100%", bar)

    def test_percent_bar_half(self):
        bar = percent_bar(50, width=10)
        self.assertIn("=====" , bar)

    def test_truncate_short_text(self):
        """Text shorter than max_len is returned unchanged."""
        self.assertEqual(truncate("hello", max_len=80), "hello")

    def test_truncate_long_text(self):
        """Text longer than max_len is truncated with suffix."""
        result = truncate("a" * 100, max_len=20)
        self.assertEqual(len(result), 20)
        self.assertTrue(result.endswith("..."))

    def test_truncate_exact_length(self):
        """Text exactly at max_len is returned unchanged."""
        text = "x" * 80
        self.assertEqual(truncate(text, max_len=80), text)

    def test_truncate_custom_suffix(self):
        """Custom suffix is used when truncating."""
        result = truncate("a" * 50, max_len=10, suffix="~~")
        self.assertTrue(result.endswith("~~"))
        self.assertEqual(len(result), 10)


# ---------------------------------------------------------------------------
# TestHardwareProfiles — hardware detection
# ---------------------------------------------------------------------------

class TestHardwareProfiles(unittest.TestCase):
    """Tests for hardware profile detection via DMI data."""

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_detect_hp_elitebook(self, mock_open, mock_exists):
        """HP EliteBook 840 G7 should match 'hp-elitebook' profile."""
        dmi_data = {
            '/sys/class/dmi/id/product_name': 'HP EliteBook 840 G7',
            '/sys/class/dmi/id/product_family': 'HP EliteBook',
            '/sys/class/dmi/id/sys_vendor': 'HP',
        }
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO(dmi_data.get(f, ''))
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "hp-elitebook")
        self.assertTrue(profile["battery_limit"])
        self.assertTrue(profile["fingerprint"])

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_detect_thinkpad(self, mock_open, mock_exists):
        """Lenovo ThinkPad T14 should match 'thinkpad' profile."""
        dmi_data = {
            '/sys/class/dmi/id/product_name': '20S0S0AB00',
            '/sys/class/dmi/id/product_family': 'ThinkPad T14 Gen 1',
            '/sys/class/dmi/id/sys_vendor': 'LENOVO',
        }
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO(dmi_data.get(f, ''))
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "thinkpad")
        self.assertTrue(profile["battery_limit"])
        self.assertEqual(profile["thermal_management"], "thinkpad_acpi")

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_detect_dell_xps(self, mock_open, mock_exists):
        """Dell XPS 13 9310 should match 'dell-xps' profile."""
        dmi_data = {
            '/sys/class/dmi/id/product_name': 'Dell XPS 13 9310',
            '/sys/class/dmi/id/product_family': 'XPS',
            '/sys/class/dmi/id/sys_vendor': 'Dell Inc.',
        }
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO(dmi_data.get(f, ''))
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "dell-xps")
        self.assertFalse(profile["nbfc"])

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_detect_framework_laptop(self, mock_open, mock_exists):
        """Framework Laptop 13 should match 'framework' profile."""
        dmi_data = {
            '/sys/class/dmi/id/product_name': 'Framework Laptop 13',
            '/sys/class/dmi/id/product_family': 'Framework Laptop',
            '/sys/class/dmi/id/sys_vendor': 'Framework',
        }
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO(dmi_data.get(f, ''))
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "framework")
        self.assertTrue(profile["battery_limit"])

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_detect_asus_zenbook(self, mock_open, mock_exists):
        """ASUS ZenBook should match 'asus-zenbook' profile."""
        dmi_data = {
            '/sys/class/dmi/id/product_name': 'ASUS ZenBook UX425EA',
            '/sys/class/dmi/id/product_family': '',
            '/sys/class/dmi/id/sys_vendor': 'ASUSTeK COMPUTER INC.',
        }
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO(dmi_data.get(f, ''))
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "asus-zenbook")
        self.assertFalse(profile["fingerprint"])

    @patch('services.hardware.hardware_profiles.os.path.exists')
    @patch('builtins.open')
    def test_fallback_generic_laptop(self, mock_open, mock_exists):
        """Unknown hardware with a battery falls back to 'generic-laptop'."""
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO('')
        # os.path.exists: BAT0 exists (laptop), BAT1 does not
        mock_exists.side_effect = lambda p: p == '/sys/class/power_supply/BAT0'
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "generic-laptop")
        self.assertFalse(profile["battery_limit"])

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=False)
    @patch('builtins.open')
    def test_fallback_generic_desktop(self, mock_open, mock_exists):
        """Unknown hardware without battery falls back to 'generic-desktop'."""
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO('')
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "generic-desktop")
        self.assertFalse(profile["battery_limit"])
        self.assertFalse(profile["nbfc"])

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_detect_hp_probook(self, mock_open, mock_exists):
        """HP ProBook should match 'hp-probook' profile."""
        dmi_data = {
            '/sys/class/dmi/id/product_name': 'HP ProBook 450 G8',
            '/sys/class/dmi/id/product_family': '',
            '/sys/class/dmi/id/sys_vendor': 'HP',
        }
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO(dmi_data.get(f, ''))
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "hp-probook")

    @patch('services.hardware.hardware_profiles.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_detect_dell_latitude(self, mock_open, mock_exists):
        """Dell Latitude should match 'dell-latitude' profile."""
        dmi_data = {
            '/sys/class/dmi/id/product_name': 'Dell Latitude 5520',
            '/sys/class/dmi/id/product_family': 'Latitude',
            '/sys/class/dmi/id/sys_vendor': 'Dell Inc.',
        }
        mock_open.side_effect = lambda f, *a, **kw: io.StringIO(dmi_data.get(f, ''))
        key, profile = detect_hardware_profile()
        self.assertEqual(key, "dell-latitude")

    def test_get_profile_label_known(self):
        """get_profile_label returns the human-readable label."""
        self.assertEqual(get_profile_label("thinkpad"), "Lenovo ThinkPad")
        self.assertEqual(get_profile_label("hp-elitebook"), "HP EliteBook")

    def test_get_profile_label_unknown(self):
        """get_profile_label returns the key itself for unknown profiles."""
        self.assertEqual(get_profile_label("alien-laptop"), "alien-laptop")

    def test_get_all_profiles_returns_dict(self):
        """get_all_profiles returns a copy of all known profiles."""
        profiles = get_all_profiles()
        self.assertIsInstance(profiles, dict)
        self.assertIn("hp-elitebook", profiles)
        self.assertIn("thinkpad", profiles)
        self.assertIn("generic-desktop", profiles)

    def test_profiles_have_required_keys(self):
        """Each profile dict has all required capability keys."""
        required_keys = {"label", "battery_limit", "nbfc", "fingerprint",
                         "power_profiles", "thermal_management"}
        for key, profile in PROFILES.items():
            for rk in required_keys:
                self.assertIn(rk, profile,
                              f"Profile '{key}' missing key '{rk}'")

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_detect_handles_missing_dmi(self, mock_open):
        """detect_hardware_profile handles missing DMI files gracefully."""
        with patch('services.hardware.hardware_profiles.os.path.exists', return_value=False):
            key, profile = detect_hardware_profile()
            self.assertIn(key, ("generic-laptop", "generic-desktop"))


if __name__ == '__main__':
    unittest.main()
