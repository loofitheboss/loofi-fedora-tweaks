"""Tests for v37.0 CLI subcommands — updates, extension, flatpak-manage, boot, display, backup."""

import argparse
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

import cli.main as cli_main


class TestCmdUpdates(unittest.TestCase):
    """Tests for cmd_updates CLI handler."""

    def setUp(self):
        cli_main._json_output = False
        cli_main._dry_run = False

    @patch('utils.update_manager.UpdateManager.check_updates')
    def test_check_no_updates(self, mock_check):
        mock_check.return_value = []
        args = argparse.Namespace(action="check")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 0)
        mock_check.assert_called_once()

    @patch('utils.update_manager.UpdateManager.check_updates')
    def test_check_with_updates(self, mock_check):
        entry = MagicMock()
        entry.name = "kernel"
        entry.old_version = "6.10"
        entry.new_version = "6.11"
        entry.source = "dnf"
        mock_check.return_value = [entry]
        args = argparse.Namespace(action="check")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 0)

    @patch('utils.update_manager.UpdateManager.check_updates')
    def test_check_json_output(self, mock_check):
        cli_main._json_output = True
        mock_check.return_value = []
        args = argparse.Namespace(action="check")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 0)

    @patch('utils.update_manager.UpdateManager.preview_conflicts')
    def test_conflicts(self, mock_conflicts):
        mock_conflicts.return_value = []
        args = argparse.Namespace(action="conflicts")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.update_manager.UpdateManager.get_schedule_commands')
    @patch('utils.update_manager.UpdateManager.schedule_update')
    def test_schedule(self, mock_schedule, mock_cmds, mock_run):
        mock_schedule.return_value = MagicMock()
        mock_cmds.return_value = [("systemctl", ["enable", "timer"], "Enable")]
        mock_run.return_value = True
        args = argparse.Namespace(action="schedule", time="03:00")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.update_manager.UpdateManager.rollback_last')
    def test_rollback(self, mock_rollback, mock_run):
        mock_rollback.return_value = ("pkexec", ["dnf", "history", "undo"], "Rollback")
        mock_run.return_value = True
        args = argparse.Namespace(action="rollback")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 0)

    @patch('utils.update_manager.UpdateManager.get_update_history')
    def test_history(self, mock_history):
        mock_history.return_value = []
        args = argparse.Namespace(action="history")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 0)

    def test_unknown_action(self):
        args = argparse.Namespace(action="nonexistent")
        code = cli_main.cmd_updates(args)
        self.assertEqual(code, 1)


class TestCmdExtension(unittest.TestCase):
    """Tests for cmd_extension CLI handler."""

    def setUp(self):
        cli_main._json_output = False
        cli_main._dry_run = False

    @patch('utils.extension_manager.ExtensionManager.list_installed')
    def test_list(self, mock_list):
        entry = MagicMock()
        entry.uuid = "test@gnome.org"
        entry.name = "Test"
        entry.enabled = True
        entry.desktop = "GNOME"
        mock_list.return_value = [entry]
        args = argparse.Namespace(action="list")
        code = cli_main.cmd_extension(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.extension_manager.ExtensionManager.install')
    def test_install(self, mock_install, mock_run):
        mock_install.return_value = ("gnome-extensions", ["install", "uuid"], "Install")
        mock_run.return_value = True
        args = argparse.Namespace(action="install", uuid="test@gnome.org")
        code = cli_main.cmd_extension(args)
        self.assertEqual(code, 0)

    def test_install_no_uuid(self):
        args = argparse.Namespace(action="install", uuid=None)
        code = cli_main.cmd_extension(args)
        self.assertEqual(code, 1)

    @patch('cli.main.run_operation')
    @patch('utils.extension_manager.ExtensionManager.enable')
    def test_enable(self, mock_enable, mock_run):
        mock_enable.return_value = ("gnome-extensions", ["enable", "uuid"], "Enable")
        mock_run.return_value = True
        args = argparse.Namespace(action="enable", uuid="test@gnome.org")
        code = cli_main.cmd_extension(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.extension_manager.ExtensionManager.disable')
    def test_disable(self, mock_disable, mock_run):
        mock_disable.return_value = ("gnome-extensions", ["disable", "uuid"], "Disable")
        mock_run.return_value = True
        args = argparse.Namespace(action="disable", uuid="test@gnome.org")
        code = cli_main.cmd_extension(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.extension_manager.ExtensionManager.remove')
    def test_remove(self, mock_remove, mock_run):
        mock_remove.return_value = ("gnome-extensions", ["uninstall", "uuid"], "Remove")
        mock_run.return_value = True
        args = argparse.Namespace(action="remove", uuid="test@gnome.org")
        code = cli_main.cmd_extension(args)
        self.assertEqual(code, 0)


class TestCmdFlatpakManage(unittest.TestCase):
    """Tests for cmd_flatpak_manage CLI handler."""

    def setUp(self):
        cli_main._json_output = False
        cli_main._dry_run = False

    @patch('utils.flatpak_manager.FlatpakManager.get_total_size')
    @patch('utils.flatpak_manager.FlatpakManager.get_flatpak_sizes')
    def test_sizes(self, mock_sizes, mock_total):
        entry = MagicMock()
        entry.app_id = "org.example.App"
        entry.size_str = "100 MB"
        mock_sizes.return_value = [entry]
        mock_total.return_value = "100 MB"
        args = argparse.Namespace(action="sizes")
        code = cli_main.cmd_flatpak_manage(args)
        self.assertEqual(code, 0)

    @patch('utils.flatpak_manager.FlatpakManager.get_all_permissions')
    def test_permissions(self, mock_perms):
        mock_perms.return_value = []
        args = argparse.Namespace(action="permissions")
        code = cli_main.cmd_flatpak_manage(args)
        self.assertEqual(code, 0)

    @patch('utils.flatpak_manager.FlatpakManager.find_orphan_runtimes')
    def test_orphans(self, mock_orphans):
        mock_orphans.return_value = ["org.old.Runtime"]
        args = argparse.Namespace(action="orphans")
        code = cli_main.cmd_flatpak_manage(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.flatpak_manager.FlatpakManager.cleanup_unused')
    def test_cleanup(self, mock_cleanup, mock_run):
        mock_cleanup.return_value = ("flatpak", ["uninstall", "--unused"], "Cleanup")
        mock_run.return_value = True
        args = argparse.Namespace(action="cleanup")
        code = cli_main.cmd_flatpak_manage(args)
        self.assertEqual(code, 0)


class TestCmdBoot(unittest.TestCase):
    """Tests for cmd_boot CLI handler."""

    def setUp(self):
        cli_main._json_output = False
        cli_main._dry_run = False

    @patch('utils.boot_config.BootConfigManager.get_grub_config')
    def test_config(self, mock_config):
        cfg = MagicMock()
        cfg.default_entry = "0"
        cfg.timeout = 5
        cfg.theme = None
        cfg.cmdline_linux = "quiet"
        mock_config.return_value = cfg
        args = argparse.Namespace(action="config")
        code = cli_main.cmd_boot(args)
        self.assertEqual(code, 0)

    @patch('utils.boot_config.BootConfigManager.list_kernels')
    def test_kernels(self, mock_kernels):
        k = MagicMock()
        k.title = "Fedora Linux (6.11.0)"
        k.version = "6.11.0"
        k.is_default = True
        mock_kernels.return_value = [k]
        args = argparse.Namespace(action="kernels")
        code = cli_main.cmd_boot(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.boot_config.BootConfigManager.set_timeout')
    def test_timeout(self, mock_set, mock_run):
        mock_set.return_value = ("pkexec", ["sed", "-i", "..."], "Set timeout")
        mock_run.return_value = True
        args = argparse.Namespace(action="timeout", seconds=10)
        code = cli_main.cmd_boot(args)
        self.assertEqual(code, 0)

    def test_timeout_no_seconds(self):
        args = argparse.Namespace(action="timeout", seconds=None)
        code = cli_main.cmd_boot(args)
        self.assertEqual(code, 1)

    @patch('cli.main.run_operation')
    @patch('utils.boot_config.BootConfigManager.apply_grub_changes')
    def test_apply(self, mock_apply, mock_run):
        mock_apply.return_value = ("pkexec", ["grub2-mkconfig"], "Apply")
        mock_run.return_value = True
        args = argparse.Namespace(action="apply")
        code = cli_main.cmd_boot(args)
        self.assertEqual(code, 0)


class TestCmdDisplay(unittest.TestCase):
    """Tests for cmd_display CLI handler."""

    def setUp(self):
        cli_main._json_output = False
        cli_main._dry_run = False

    @patch('utils.wayland_display.WaylandDisplayManager.get_displays')
    def test_list(self, mock_displays):
        d = MagicMock()
        d.name = "eDP-1"
        d.resolution = "1920x1080"
        d.scale = 1.0
        d.refresh_rate = 60.0
        d.primary = True
        mock_displays.return_value = [d]
        args = argparse.Namespace(action="list")
        code = cli_main.cmd_display(args)
        self.assertEqual(code, 0)

    @patch('utils.wayland_display.WaylandDisplayManager.get_session_info')
    def test_session(self, mock_session):
        mock_session.return_value = {"type": "wayland", "desktop": "GNOME"}
        args = argparse.Namespace(action="session")
        code = cli_main.cmd_display(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.wayland_display.WaylandDisplayManager.enable_fractional_scaling')
    def test_fractional_on(self, mock_enable, mock_run):
        mock_enable.return_value = ("gsettings", ["set", "..."], "Enable")
        mock_run.return_value = True
        args = argparse.Namespace(action="fractional-on")
        code = cli_main.cmd_display(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.wayland_display.WaylandDisplayManager.disable_fractional_scaling')
    def test_fractional_off(self, mock_disable, mock_run):
        mock_disable.return_value = ("gsettings", ["set", "..."], "Disable")
        mock_run.return_value = True
        args = argparse.Namespace(action="fractional-off")
        code = cli_main.cmd_display(args)
        self.assertEqual(code, 0)


class TestCmdBackup(unittest.TestCase):
    """Tests for cmd_backup CLI handler."""

    def setUp(self):
        cli_main._json_output = False
        cli_main._dry_run = False

    @patch('utils.backup_wizard.BackupWizard.get_available_tools')
    @patch('utils.backup_wizard.BackupWizard.detect_backup_tool')
    def test_detect(self, mock_detect, mock_available):
        mock_detect.return_value = "timeshift"
        mock_available.return_value = ["timeshift"]
        args = argparse.Namespace(action="detect")
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.backup_wizard.BackupWizard.create_snapshot')
    def test_create(self, mock_create, mock_run):
        mock_create.return_value = ("pkexec", ["timeshift", "--create"], "Create")
        mock_run.return_value = True
        args = argparse.Namespace(action="create", description="test", tool=None)
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 0)

    @patch('utils.backup_wizard.BackupWizard.list_snapshots')
    def test_list_empty(self, mock_list):
        mock_list.return_value = []
        args = argparse.Namespace(action="list", tool=None)
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 0)

    @patch('utils.backup_wizard.BackupWizard.list_snapshots')
    def test_list_with_snapshots(self, mock_list):
        s = MagicMock()
        s.id = "1"
        s.date = "2025-01-01"
        s.description = "test"
        s.tool = "timeshift"
        mock_list.return_value = [s]
        args = argparse.Namespace(action="list", tool=None)
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 0)

    @patch('cli.main.run_operation')
    @patch('utils.backup_wizard.BackupWizard.restore_snapshot')
    def test_restore(self, mock_restore, mock_run):
        mock_restore.return_value = ("pkexec", ["timeshift", "--restore"], "Restore")
        mock_run.return_value = True
        args = argparse.Namespace(action="restore", snapshot_id="1", tool=None)
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 0)

    def test_restore_no_id(self):
        args = argparse.Namespace(action="restore", snapshot_id=None, tool=None)
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 1)

    @patch('cli.main.run_operation')
    @patch('utils.backup_wizard.BackupWizard.delete_snapshot')
    def test_delete(self, mock_delete, mock_run):
        mock_delete.return_value = ("pkexec", ["timeshift", "--delete"], "Delete")
        mock_run.return_value = True
        args = argparse.Namespace(action="delete", snapshot_id="1", tool=None)
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 0)

    def test_delete_no_id(self):
        args = argparse.Namespace(action="delete", snapshot_id=None, tool=None)
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 1)

    @patch('utils.backup_wizard.BackupWizard.get_backup_status')
    def test_status(self, mock_status):
        mock_status.return_value = {"tool": "timeshift", "snapshots": 3}
        args = argparse.Namespace(action="status")
        code = cli_main.cmd_backup(args)
        self.assertEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
