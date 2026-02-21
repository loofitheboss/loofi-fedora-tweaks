"""
Test PrivilegedCommand — v35.0.0 "Fortress"

Tests for parameter validation, audit integration, POLKIT_MAP,
execute_and_log, and all builder methods.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), '..', 'loofi-fedora-tweaks'))


class TestPrivilegedCommandBuilders(unittest.TestCase):
    """Test command tuple builder methods."""

    @patch("services.system.SystemManager.get_package_manager", return_value="dnf")
    def test_dnf_install(self, mock_pm):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.dnf("install", "vim")
        self.assertEqual(binary, "pkexec")
        self.assertIn("dnf", args)
        self.assertIn("install", args)
        self.assertIn("-y", args)
        self.assertIn("vim", args)

    @patch("services.system.SystemManager.get_package_manager", return_value="rpm-ostree")
    def test_dnf_atomic_install(self, mock_pm):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.dnf("install", "vim")
        self.assertEqual(binary, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("install", args)

    @patch("services.system.SystemManager.get_package_manager", return_value="dnf")
    def test_dnf_clean(self, mock_pm):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.dnf("clean")
        self.assertEqual(binary, "pkexec")
        self.assertIn("clean", args)

    def test_systemctl(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.systemctl("restart", "sshd")
        self.assertEqual(binary, "pkexec")
        self.assertIn("systemctl", args)
        self.assertIn("restart", args)
        self.assertIn("sshd", args)

    def test_systemctl_user(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.systemctl(
            "start", "myservice", user=True)
        self.assertEqual(binary, "systemctl")
        self.assertIn("--user", args)

    def test_sysctl(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.sysctl("vm.swappiness", "10")
        self.assertEqual(binary, "pkexec")
        self.assertIn("sysctl", args)

    def test_write_file(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.write_file(
            "/etc/test.conf", "content")
        self.assertEqual(binary, "pkexec")
        self.assertIn("tee", args)

    def test_flatpak(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.flatpak(
            "install", "com.example.App")
        self.assertEqual(binary, "flatpak")

    def test_fwupd(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.fwupd("update")
        self.assertEqual(binary, "pkexec")
        self.assertIn("fwupdmgr", args)

    def test_journal_vacuum(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.journal_vacuum("1week")
        self.assertEqual(binary, "pkexec")
        self.assertIn("journalctl", args)

    def test_fstrim(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.fstrim()
        self.assertEqual(binary, "pkexec")
        self.assertIn("fstrim", args)

    def test_rpm_rebuild(self):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.rpm_rebuild()
        self.assertEqual(binary, "pkexec")
        self.assertIn("--rebuilddb", args)


class TestParameterValidation(unittest.TestCase):
    """Test @validated_action decorator on PrivilegedCommand methods."""

    @patch("services.system.SystemManager.get_package_manager", return_value="dnf")
    @patch("utils.audit.AuditLogger.log_validation_failure")
    def test_dnf_rejects_invalid_action(self, mock_log_fail, mock_pm):
        from utils.commands import PrivilegedCommand
        from utils.errors import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            PrivilegedCommand.dnf("INVALID_ACTION", "vim")
        self.assertIn("action", str(ctx.exception).lower())

    @patch("services.system.SystemManager.get_package_manager", return_value="dnf")
    @patch("utils.audit.AuditLogger.log_validation_failure")
    def test_dnf_rejects_empty_action(self, mock_log_fail, mock_pm):
        from utils.commands import PrivilegedCommand
        from utils.errors import ValidationError
        with self.assertRaises(ValidationError):
            PrivilegedCommand.dnf("", "vim")

    @patch("utils.audit.AuditLogger.log_validation_failure")
    def test_systemctl_rejects_empty_service(self, mock_log_fail):
        from utils.commands import PrivilegedCommand
        from utils.errors import ValidationError
        with self.assertRaises(ValidationError):
            PrivilegedCommand.systemctl("restart", "")

    @patch("utils.audit.AuditLogger.log_validation_failure")
    def test_sysctl_rejects_empty_key(self, mock_log_fail):
        from utils.commands import PrivilegedCommand
        from utils.errors import ValidationError
        with self.assertRaises(ValidationError):
            PrivilegedCommand.sysctl("", "10")

    @patch("utils.audit.AuditLogger.log_validation_failure")
    def test_write_file_rejects_path_traversal(self, mock_log_fail):
        from utils.commands import PrivilegedCommand
        from utils.errors import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            PrivilegedCommand.write_file("../../etc/shadow", "pwned")
        self.assertIn("traversal", str(ctx.exception).lower())

    @patch("utils.audit.AuditLogger.log_validation_failure")
    def test_write_file_rejects_empty_path(self, mock_log_fail):
        from utils.commands import PrivilegedCommand
        from utils.errors import ValidationError
        with self.assertRaises(ValidationError):
            PrivilegedCommand.write_file("", "content")

    @patch("utils.audit.AuditLogger.log_validation_failure")
    def test_validation_failure_is_audit_logged(self, mock_log_fail):
        from utils.commands import PrivilegedCommand
        from utils.errors import ValidationError
        try:
            PrivilegedCommand.systemctl("restart", "")
        except ValidationError:
            pass
        mock_log_fail.assert_called_once()
        call_kwargs = mock_log_fail.call_args
        self.assertIn(
            "service", call_kwargs[1]["param"] if call_kwargs[1] else call_kwargs[0][1])

    @patch("services.system.SystemManager.get_package_manager", return_value="dnf")
    def test_valid_dnf_action_passes(self, mock_pm):
        from utils.commands import PrivilegedCommand
        binary, args, desc = PrivilegedCommand.dnf("install", "vim")
        self.assertEqual(binary, "pkexec")


class TestPolkitMap(unittest.TestCase):
    """Test POLKIT_MAP and get_polkit_action_id."""

    def test_polkit_map_has_core_entries(self):
        from utils.commands import POLKIT_MAP
        self.assertIn("dnf", POLKIT_MAP)
        self.assertIn("rpm-ostree", POLKIT_MAP)
        self.assertIn("systemctl", POLKIT_MAP)
        self.assertIn("firewall-cmd", POLKIT_MAP)

    def test_get_polkit_action_id_pkexec_dnf(self):
        from utils.commands import PrivilegedCommand
        cmd_tuple = ("pkexec", ["dnf", "install",
                     "-y", "vim"], "Installing vim...")
        action_id = PrivilegedCommand.get_polkit_action_id(cmd_tuple)
        self.assertEqual(action_id, "org.loofi.fedora-tweaks.package-manage")

    def test_get_polkit_action_id_systemctl(self):
        from utils.commands import PrivilegedCommand
        cmd_tuple = ("pkexec", ["systemctl", "restart",
                     "sshd"], "Restarting sshd...")
        action_id = PrivilegedCommand.get_polkit_action_id(cmd_tuple)
        self.assertEqual(action_id, "org.loofi.fedora-tweaks.service-manage")

    def test_get_polkit_action_id_unknown(self):
        from utils.commands import PrivilegedCommand
        cmd_tuple = ("pkexec", ["unknown-tool", "arg"], "Unknown...")
        action_id = PrivilegedCommand.get_polkit_action_id(cmd_tuple)
        self.assertIsNone(action_id)

    def test_get_polkit_action_id_flatpak(self):
        from utils.commands import PrivilegedCommand
        cmd_tuple = (
            "flatpak", ["install", "com.example.App"], "Installing...")
        action_id = PrivilegedCommand.get_polkit_action_id(cmd_tuple)
        self.assertEqual(action_id, "org.loofi.fedora-tweaks.package-manage")


class TestExecuteAndLog(unittest.TestCase):
    """Test PrivilegedCommand.execute_and_log."""

    @patch("subprocess.run")
    @patch("utils.audit.AuditLogger.log")
    def test_execute_and_log_success(self, mock_audit_log, mock_run):
        from utils.commands import PrivilegedCommand
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pkexec", "dnf", "install", "-y", "vim"],
            returncode=0, stdout="Done", stderr=""
        )
        mock_audit_log.return_value = {}

        cmd_tuple = ("pkexec", ["dnf", "install",
                     "-y", "vim"], "Installing vim...")
        result = PrivilegedCommand.execute_and_log(cmd_tuple, timeout=60)

        self.assertEqual(result.returncode, 0)
        mock_run.assert_called_once()
        mock_audit_log.assert_called_once()

    @patch("utils.audit.AuditLogger.log")
    def test_execute_and_log_dry_run(self, mock_audit_log):
        from utils.commands import PrivilegedCommand
        mock_audit_log.return_value = {}

        cmd_tuple = ("pkexec", ["dnf", "install",
                     "-y", "vim"], "Installing vim...")
        result = PrivilegedCommand.execute_and_log(cmd_tuple, dry_run=True)

        self.assertEqual(result.returncode, -1)
        mock_audit_log.assert_called_once()
        call_kwargs = mock_audit_log.call_args[1]
        self.assertTrue(call_kwargs["dry_run"])

    @patch("subprocess.run")
    @patch("utils.audit.AuditLogger.log")
    def test_execute_and_log_timeout_raises(self, mock_audit_log, mock_run):
        from utils.commands import PrivilegedCommand
        from utils.errors import CommandTimeoutError
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["ls"], timeout=5)
        mock_audit_log.return_value = {}

        cmd_tuple = ("pkexec", ["dnf", "install", "vim"], "Installing...")
        with self.assertRaises(CommandTimeoutError):
            PrivilegedCommand.execute_and_log(cmd_tuple, timeout=5)

        mock_audit_log.assert_called_once()

    def test_derive_action_name_pkexec(self):
        from utils.commands import PrivilegedCommand
        name = PrivilegedCommand._derive_action_name(
            "pkexec", ["dnf", "install"])
        self.assertEqual(name, "dnf.install")

    def test_derive_action_name_simple(self):
        from utils.commands import PrivilegedCommand
        name = PrivilegedCommand._derive_action_name("flatpak", ["install"])
        self.assertEqual(name, "flatpak.install")

    def test_derive_action_name_no_args(self):
        from utils.commands import PrivilegedCommand
        name = PrivilegedCommand._derive_action_name("ls", [])
        self.assertEqual(name, "ls")


class TestErrorClasses(unittest.TestCase):
    """Test v35.0 error classes."""

    def test_command_timeout_error(self):
        from utils.errors import CommandTimeoutError
        err = CommandTimeoutError(cmd="test cmd", timeout=30)
        self.assertEqual(err.code, "COMMAND_TIMEOUT")
        self.assertTrue(err.recoverable)
        self.assertIn("30", str(err))

    def test_validation_error(self):
        from utils.errors import ValidationError
        err = ValidationError(param="action", detail="Invalid choice")
        self.assertEqual(err.code, "VALIDATION_ERROR")
        self.assertTrue(err.recoverable)
        self.assertIn("action", str(err))


if __name__ == "__main__":
    unittest.main()
