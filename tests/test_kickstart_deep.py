"""
Tests for utils/kickstart.py — Kickstart file generator.

Covers:
- KickstartGenerator._get_keyboard_layout
- KickstartGenerator._get_system_lang
- KickstartGenerator._get_timezone
- KickstartGenerator._get_user_packages
- KickstartGenerator._get_flatpak_apps
- KickstartGenerator.generate_kickstart
- KickstartGenerator.save_kickstart
- KickstartGenerator.validate_kickstart
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.kickstart import KickstartGenerator, Result


class TestGetKeyboardLayout(unittest.TestCase):

    @patch("subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="   System Locale: LANG=sv_SE.UTF-8\n   X11 Layout: se\n"
        )
        layout = KickstartGenerator._get_keyboard_layout()
        self.assertEqual(layout, "se")

    @patch("subprocess.run")
    def test_no_layout_line(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="nothing here\n")
        layout = KickstartGenerator._get_keyboard_layout()
        self.assertEqual(layout, "us")

    @patch("subprocess.run")
    def test_command_fails(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        layout = KickstartGenerator._get_keyboard_layout()
        self.assertEqual(layout, "us")

    @patch("subprocess.run", side_effect=Exception("no localectl"))
    def test_exception(self, mock_run):
        layout = KickstartGenerator._get_keyboard_layout()
        self.assertEqual(layout, "us")

    @patch("subprocess.run")
    def test_empty_layout(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="   X11 Layout: \n"
        )
        layout = KickstartGenerator._get_keyboard_layout()
        self.assertEqual(layout, "us")


class TestGetSystemLang(unittest.TestCase):

    @patch.dict(os.environ, {"LANG": "sv_SE.UTF-8"})
    def test_returns_lang(self):
        self.assertEqual(KickstartGenerator._get_system_lang(), "sv_SE.UTF-8")

    @patch.dict(os.environ, {}, clear=True)
    def test_default(self):
        os.environ.pop("LANG", None)
        result = KickstartGenerator._get_system_lang()
        self.assertEqual(result, "en_US.UTF-8")


class TestGetTimezone(unittest.TestCase):

    @patch("subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Europe/Stockholm\n")
        tz = KickstartGenerator._get_timezone()
        self.assertEqual(tz, "Europe/Stockholm")

    @patch("subprocess.run")
    def test_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")
        tz = KickstartGenerator._get_timezone()
        self.assertEqual(tz, "UTC")

    @patch("subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        tz = KickstartGenerator._get_timezone()
        self.assertEqual(tz, "UTC")

    @patch("subprocess.run", side_effect=Exception("no timedatectl"))
    def test_exception(self, mock_run):
        tz = KickstartGenerator._get_timezone()
        self.assertEqual(tz, "UTC")


class TestGetUserPackages(unittest.TestCase):

    @patch("subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="vim\ngit\nhtop\n"
        )
        pkgs = KickstartGenerator._get_user_packages()
        self.assertEqual(pkgs, ["vim", "git", "htop"])

    @patch("subprocess.run")
    def test_filters_excluded(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="vim\nkernel-core\nglibc\nsystemd-libs\nbash-completion\ncoreutils\nfedora-release\ngit\n"
        )
        pkgs = KickstartGenerator._get_user_packages()
        self.assertIn("vim", pkgs)
        self.assertIn("git", pkgs)
        self.assertNotIn("kernel-core", pkgs)
        self.assertNotIn("glibc", pkgs)

    @patch("subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        pkgs = KickstartGenerator._get_user_packages()
        self.assertEqual(pkgs, [])

    @patch("subprocess.run", side_effect=Exception("no dnf"))
    def test_exception(self, mock_run):
        pkgs = KickstartGenerator._get_user_packages()
        self.assertEqual(pkgs, [])


class TestGetFlatpakApps(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_no_flatpak(self, mock_which):
        apps = KickstartGenerator._get_flatpak_apps()
        self.assertEqual(apps, [])

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/flatpak")
    def test_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="org.mozilla.firefox\norg.gimp.GIMP\n"
        )
        apps = KickstartGenerator._get_flatpak_apps()
        self.assertEqual(apps, ["org.mozilla.firefox", "org.gimp.GIMP"])

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/flatpak")
    def test_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        apps = KickstartGenerator._get_flatpak_apps()
        self.assertEqual(apps, [])

    @patch("shutil.which", return_value="/usr/bin/flatpak")
    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_exception(self, mock_run, mock_which):
        apps = KickstartGenerator._get_flatpak_apps()
        self.assertEqual(apps, [])


class TestGenerateKickstart(unittest.TestCase):

    @patch.object(KickstartGenerator, "_get_flatpak_apps", return_value=["org.test.App"])
    @patch.object(KickstartGenerator, "_get_user_packages", return_value=["vim", "git"])
    @patch.object(KickstartGenerator, "_get_timezone", return_value="UTC")
    @patch.object(KickstartGenerator, "_get_system_lang", return_value="en_US.UTF-8")
    @patch.object(KickstartGenerator, "_get_keyboard_layout", return_value="us")
    def test_full_generation(self, m_kb, m_lang, m_tz, m_pkg, m_fp):
        content = KickstartGenerator.generate_kickstart()
        self.assertIn("vim", content)
        self.assertIn("git", content)
        self.assertIn("flatpak install", content)
        self.assertIn("org.test.App", content)
        self.assertIn("keyboard --xlayouts='us'", content)

    @patch.object(KickstartGenerator, "_get_flatpak_apps", return_value=[])
    @patch.object(KickstartGenerator, "_get_user_packages", return_value=[])
    @patch.object(KickstartGenerator, "_get_timezone", return_value="UTC")
    @patch.object(KickstartGenerator, "_get_system_lang", return_value="en_US.UTF-8")
    @patch.object(KickstartGenerator, "_get_keyboard_layout", return_value="us")
    def test_no_packages_no_flatpaks(self, m_kb, m_lang, m_tz, m_pkg, m_fp):
        content = KickstartGenerator.generate_kickstart(
            include_packages=False, include_flatpaks=False
        )
        self.assertNotIn("vim", content)
        self.assertNotIn("flatpak install", content)

    @patch.object(KickstartGenerator, "_get_flatpak_apps", return_value=[])
    @patch.object(KickstartGenerator, "_get_user_packages", return_value=[])
    @patch.object(KickstartGenerator, "_get_timezone", return_value="UTC")
    @patch.object(KickstartGenerator, "_get_system_lang", return_value="en_US.UTF-8")
    @patch.object(KickstartGenerator, "_get_keyboard_layout", return_value="us")
    def test_custom_post(self, m_kb, m_lang, m_tz, m_pkg, m_fp):
        content = KickstartGenerator.generate_kickstart(custom_post="echo hello")
        self.assertIn("echo hello", content)


class TestSaveKickstart(unittest.TestCase):

    @patch.object(KickstartGenerator, "generate_kickstart", return_value="# kickstart content")
    @patch("builtins.open", unittest.mock.mock_open())
    def test_save_default_path(self, mock_gen):
        r = KickstartGenerator.save_kickstart()
        self.assertTrue(r.success)
        self.assertIn("path", r.data)

    @patch.object(KickstartGenerator, "generate_kickstart", return_value="# content")
    @patch("builtins.open", unittest.mock.mock_open())
    def test_save_custom_path(self, mock_gen):
        r = KickstartGenerator.save_kickstart(path="/tmp/test.ks")
        self.assertTrue(r.success)

    @patch.object(KickstartGenerator, "generate_kickstart", return_value="# content")
    @patch("builtins.open", side_effect=PermissionError("denied"))
    def test_save_failure(self, mock_open, mock_gen):
        r = KickstartGenerator.save_kickstart()
        self.assertFalse(r.success)


class TestValidateKickstart(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_no_ksvalidator(self, mock_which):
        r = KickstartGenerator.validate_kickstart(Path("/tmp/test.ks"))
        self.assertTrue(r.success)
        self.assertIn("unable to validate", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/ksvalidator")
    def test_valid(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = KickstartGenerator.validate_kickstart(Path("/tmp/test.ks"))
        self.assertTrue(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/ksvalidator")
    def test_invalid(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="errors found")
        r = KickstartGenerator.validate_kickstart(Path("/tmp/test.ks"))
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/ksvalidator")
    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_exception(self, mock_run, mock_which):
        r = KickstartGenerator.validate_kickstart(Path("/tmp/test.ks"))
        self.assertFalse(r.success)


if __name__ == '__main__':
    unittest.main()
