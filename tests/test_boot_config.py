"""
Tests for utils/boot_config.py — Boot Configuration Manager.
Part of v37.0.0 "Pinnacle".

Covers: get_grub_config, list_kernels, list_themes, set_timeout,
set_default_kernel, set_theme, apply_grub_changes, get_current_cmdline,
set_cmdline_param.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.boot_config import BootConfigManager, GrubConfig, KernelEntry


class TestGetGrubConfig(unittest.TestCase):
    """Tests for BootConfigManager.get_grub_config()."""

    @patch("builtins.open", mock_open(read_data=(
        'GRUB_TIMEOUT=5\n'
        'GRUB_DEFAULT="saved"\n'
        'GRUB_CMDLINE_LINUX="rhgb quiet"\n'
        'GRUB_THEME="/boot/grub2/themes/starfield/theme.txt"\n'
        '# This is a comment\n'
    )))
    @patch("utils.boot_config.os.path.exists", return_value=True)
    def test_parse_grub_config(self, mock_exists):
        config = BootConfigManager.get_grub_config()
        self.assertEqual(config.timeout, 5)
        self.assertEqual(config.default_entry, "saved")
        self.assertIn("rhgb", config.cmdline_linux)
        self.assertIn("starfield", config.theme)

    @patch("utils.boot_config.os.path.exists", return_value=False)
    def test_grub_config_not_found(self, mock_exists):
        config = BootConfigManager.get_grub_config()
        self.assertIsInstance(config, GrubConfig)
        self.assertEqual(config.timeout, 5)  # default

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    @patch("utils.boot_config.os.path.exists", return_value=True)
    def test_grub_config_read_error(self, mock_exists, mock_file):
        config = BootConfigManager.get_grub_config()
        self.assertIsInstance(config, GrubConfig)

    @patch("builtins.open", mock_open(read_data=(
        'GRUB_TIMEOUT=invalid\n'
        'GRUB_DEFAULT=0\n'
    )))
    @patch("utils.boot_config.os.path.exists", return_value=True)
    def test_invalid_timeout_value(self, mock_exists):
        """Invalid timeout value defaults to 5."""
        config = BootConfigManager.get_grub_config()
        self.assertEqual(config.timeout, 5)  # default, since "invalid" can't be parsed


class TestListKernels(unittest.TestCase):
    """Tests for BootConfigManager.list_kernels()."""

    @patch("utils.boot_config.shutil.which", return_value="/usr/sbin/grubby")
    @patch("utils.boot_config.subprocess.run")
    def test_list_kernels_success(self, mock_run, mock_which):
        mock_run.side_effect = [
            # grubby --info=ALL
            MagicMock(
                returncode=0,
                stdout=(
                    'index=0\n'
                    'kernel="/boot/vmlinuz-6.10.0-1.fc43.x86_64"\n'
                    'title="Fedora Linux (6.10.0-1.fc43.x86_64) 43"\n'
                    'initrd="/boot/initramfs-6.10.0-1.fc43.x86_64.img"\n'
                    'root="UUID=abc-123"\n'
                    'args="ro rhgb quiet"\n'
                    '\n'
                    'index=1\n'
                    'kernel="/boot/vmlinuz-6.9.0-1.fc43.x86_64"\n'
                    'title="Fedora Linux (6.9.0-1.fc43.x86_64) 43"\n'
                    'initrd="/boot/initramfs-6.9.0-1.fc43.x86_64.img"\n'
                    'root="UUID=abc-123"\n'
                    'args="ro rhgb quiet"\n'
                ),
            ),
            # grubby --default-kernel
            MagicMock(
                returncode=0,
                stdout="/boot/vmlinuz-6.10.0-1.fc43.x86_64\n",
            ),
        ]
        result = BootConfigManager.list_kernels()
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].default)
        self.assertFalse(result[1].default)
        self.assertIn("6.10", result[0].title)

    @patch("utils.boot_config.shutil.which", return_value=None)
    def test_list_kernels_no_grubby(self, mock_which):
        result = BootConfigManager.list_kernels()
        self.assertEqual(len(result), 0)

    @patch("utils.boot_config.shutil.which", return_value="/usr/sbin/grubby")
    @patch("utils.boot_config.subprocess.run")
    def test_list_kernels_timeout(self, mock_run, mock_which):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="grubby", timeout=15)
        result = BootConfigManager.list_kernels()
        self.assertEqual(len(result), 0)


class TestListThemes(unittest.TestCase):
    """Tests for BootConfigManager.list_themes()."""

    @patch("utils.boot_config.Path.exists", return_value=True)
    @patch("utils.boot_config.Path.iterdir")
    def test_list_themes(self, mock_iterdir, mock_exists):
        theme1 = MagicMock()
        theme1.is_dir.return_value = True
        theme1.name = "starfield"
        theme1_txt = MagicMock()
        theme1_txt.exists.return_value = True
        theme1.__truediv__ = MagicMock(return_value=theme1_txt)

        theme2 = MagicMock()
        theme2.is_dir.return_value = True
        theme2.name = "catppuccin"
        theme2_txt = MagicMock()
        theme2_txt.exists.return_value = True
        theme2.__truediv__ = MagicMock(return_value=theme2_txt)

        mock_iterdir.return_value = [theme1, theme2]
        result = BootConfigManager.list_themes()
        self.assertEqual(len(result), 2)
        self.assertIn("starfield", result)

    @patch("utils.boot_config.Path.exists", return_value=False)
    def test_no_theme_dir(self, mock_exists):
        result = BootConfigManager.list_themes()
        self.assertEqual(len(result), 0)


class TestSetCommands(unittest.TestCase):
    """Tests for set_timeout, set_default_kernel, set_theme."""

    def test_set_timeout(self):
        binary, args, desc = BootConfigManager.set_timeout(10)
        self.assertEqual(binary, "pkexec")
        self.assertIn("sed", args)
        self.assertIn("GRUB_TIMEOUT", str(args))

    def test_set_timeout_zero(self):
        binary, args, desc = BootConfigManager.set_timeout(0)
        self.assertEqual(binary, "pkexec")

    @patch("utils.boot_config.shutil.which", return_value="/usr/sbin/grubby")
    def test_set_default_kernel_with_grubby(self, mock_which):
        binary, args, desc = BootConfigManager.set_default_kernel(
            "/boot/vmlinuz-6.10.0"
        )
        self.assertEqual(binary, "pkexec")
        self.assertIn("grubby", args)
        self.assertIn("--set-default", args)

    @patch("utils.boot_config.shutil.which", return_value=None)
    def test_set_default_kernel_no_grubby(self, mock_which):
        binary, args, desc = BootConfigManager.set_default_kernel("0")
        self.assertEqual(binary, "pkexec")
        self.assertIn("sed", args)

    def test_set_theme_by_name(self):
        binary, args, desc = BootConfigManager.set_theme("starfield")
        self.assertEqual(binary, "pkexec")
        self.assertIn("GRUB_THEME", str(args))

    def test_set_theme_by_path(self):
        binary, args, desc = BootConfigManager.set_theme(
            "/boot/grub2/themes/custom/theme.txt"
        )
        self.assertEqual(binary, "pkexec")


class TestApplyGrubChanges(unittest.TestCase):
    """Tests for BootConfigManager.apply_grub_changes()."""

    @patch("utils.boot_config.os.path.exists", return_value=True)
    def test_apply_grub_changes(self, mock_exists):
        binary, args, desc = BootConfigManager.apply_grub_changes()
        self.assertEqual(binary, "pkexec")
        self.assertIn("grub2-mkconfig", args)
        self.assertIn("-o", args)


class TestCurrentCmdline(unittest.TestCase):
    """Tests for BootConfigManager.get_current_cmdline()."""

    @patch("builtins.open", mock_open(
        read_data="BOOT_IMAGE=/vmlinuz-6.10.0 root=UUID=abc ro rhgb quiet\n"
    ))
    def test_read_cmdline(self):
        result = BootConfigManager.get_current_cmdline()
        self.assertIn("BOOT_IMAGE", result)
        self.assertIn("rhgb", result)

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_read_cmdline_error(self, mock_file):
        result = BootConfigManager.get_current_cmdline()
        self.assertEqual(result, "")


class TestSetCmdlineParam(unittest.TestCase):
    """Tests for BootConfigManager.set_cmdline_param()."""

    @patch.object(BootConfigManager, "get_grub_config")
    def test_set_new_param(self, mock_config):
        mock_config.return_value = GrubConfig(cmdline_linux="ro rhgb quiet")
        binary, args, desc = BootConfigManager.set_cmdline_param("mitigations", "off")
        self.assertEqual(binary, "pkexec")
        self.assertIn("GRUB_CMDLINE_LINUX", str(args))

    @patch.object(BootConfigManager, "get_grub_config")
    def test_set_flag_param(self, mock_config):
        mock_config.return_value = GrubConfig(cmdline_linux="ro rhgb quiet")
        binary, args, desc = BootConfigManager.set_cmdline_param("debug")
        self.assertEqual(binary, "pkexec")

    @patch.object(BootConfigManager, "get_grub_config")
    def test_replace_existing_param(self, mock_config):
        mock_config.return_value = GrubConfig(
            cmdline_linux="ro rhgb quiet mitigations=auto"
        )
        binary, args, desc = BootConfigManager.set_cmdline_param("mitigations", "off")
        self.assertEqual(binary, "pkexec")


if __name__ == "__main__":
    unittest.main()
