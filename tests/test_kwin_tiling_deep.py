"""
Tests for utils/kwin_tiling.py — KWin tiling manager.

Covers:
- KWinManager.is_kde, is_wayland
- get_kwriteconfig, get_kreadconfig
- enable_quick_tiling
- set_keybinding
- apply_tiling_preset (vim, arrows, unknown)
- reconfigure_kwin (qdbus + dbus-send fallback)
- add_window_rule
- get_window_list
- install_tiling_script
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.kwin_tiling import KWinManager, Result


class TestKWinIsKDE(unittest.TestCase):

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_is_kde_true(self):
        self.assertTrue(KWinManager.is_kde())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "plasma"})
    def test_is_kde_plasma(self):
        self.assertTrue(KWinManager.is_kde())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_is_kde_false(self):
        self.assertFalse(KWinManager.is_kde())

    @patch.dict(os.environ, {}, clear=True)
    def test_is_kde_not_set(self):
        os.environ.pop("XDG_CURRENT_DESKTOP", None)
        self.assertFalse(KWinManager.is_kde())


class TestKWinIsWayland(unittest.TestCase):

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"})
    def test_wayland(self):
        self.assertTrue(KWinManager.is_wayland())

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"})
    def test_x11(self):
        self.assertFalse(KWinManager.is_wayland())


class TestGetKwriteconfig(unittest.TestCase):

    @patch("shutil.which", side_effect=lambda c: "/usr/bin/kwriteconfig6" if c == "kwriteconfig6" else None)
    def test_finds_kwriteconfig6(self, mock_which):
        self.assertEqual(KWinManager.get_kwriteconfig(), "kwriteconfig6")

    @patch("shutil.which", side_effect=lambda c: "/usr/bin/kwriteconfig5" if c == "kwriteconfig5" else None)
    def test_finds_kwriteconfig5(self, mock_which):
        self.assertEqual(KWinManager.get_kwriteconfig(), "kwriteconfig5")

    @patch("shutil.which", return_value=None)
    def test_not_found(self, mock_which):
        self.assertIsNone(KWinManager.get_kwriteconfig())


class TestGetKreadconfig(unittest.TestCase):

    @patch("shutil.which", side_effect=lambda c: "/usr/bin/kreadconfig6" if c == "kreadconfig6" else None)
    def test_finds_kreadconfig6(self, mock_which):
        self.assertEqual(KWinManager.get_kreadconfig(), "kreadconfig6")

    @patch("shutil.which", return_value=None)
    def test_not_found(self, mock_which):
        self.assertIsNone(KWinManager.get_kreadconfig())


class TestEnableQuickTiling(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_no_kwriteconfig(self, mock_which):
        r = KWinManager.enable_quick_tiling()
        self.assertFalse(r.success)
        self.assertIn("not found", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    def test_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = KWinManager.enable_quick_tiling()
        self.assertTrue(r.success)
        self.assertIn("Quick tiling enabled", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    def test_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="err")
        r = KWinManager.enable_quick_tiling()
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    @patch("subprocess.run", side_effect=OSError("boom"))
    def test_exception(self, mock_run, mock_which):
        r = KWinManager.enable_quick_tiling()
        self.assertFalse(r.success)
        self.assertIn("Error", r.message)


class TestSetKeybinding(unittest.TestCase):

    def test_unknown_action(self):
        r = KWinManager.set_keybinding("Meta+X", "nonexistent")
        self.assertFalse(r.success)
        self.assertIn("Unknown action", r.message)

    @patch("shutil.which", return_value=None)
    def test_no_kwriteconfig(self, mock_which):
        r = KWinManager.set_keybinding("Meta+H", "left")
        self.assertFalse(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    def test_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = KWinManager.set_keybinding("Meta+H", "left")
        self.assertTrue(r.success)
        self.assertIn("Bound", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    def test_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="err")
        r = KWinManager.set_keybinding("Meta+H", "left")
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run, mock_which):
        r = KWinManager.set_keybinding("Meta+H", "left")
        self.assertFalse(r.success)


class TestApplyTilingPreset(unittest.TestCase):

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    def test_vim_preset(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = KWinManager.apply_tiling_preset("vim")
        self.assertTrue(r.success)
        self.assertIn("vim", r.message)
        self.assertIn("bindings", r.data)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    def test_arrows_preset(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = KWinManager.apply_tiling_preset("arrows")
        self.assertTrue(r.success)

    def test_unknown_preset(self):
        r = KWinManager.apply_tiling_preset("invalid")
        self.assertFalse(r.success)
        self.assertIn("Unknown preset", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/kwriteconfig6")
    def test_preset_partial_failure(self, mock_which, mock_run):
        # First call succeeds, second fails
        mock_run.side_effect = [
            MagicMock(returncode=0),  # first binding
            MagicMock(returncode=1, stderr="err"),  # second binding fails
        ] + [MagicMock(returncode=0)] * 20
        r = KWinManager.apply_tiling_preset("vim")
        # Some bindings succeeded, some failed
        # Result depends on which binding fails


class TestReconfigureKwin(unittest.TestCase):

    @patch("subprocess.run")
    def test_qdbus_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = KWinManager.reconfigure_kwin()
        self.assertTrue(r.success)

    @patch("subprocess.run")
    def test_qdbus_fails_dbus_send_succeeds(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # qdbus fails
            MagicMock(returncode=0),  # dbus-send succeeds
        ]
        r = KWinManager.reconfigure_kwin()
        self.assertTrue(r.success)

    @patch("subprocess.run")
    def test_both_fail(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        r = KWinManager.reconfigure_kwin()
        self.assertFalse(r.success)

    @patch("subprocess.run", side_effect=OSError("no dbus"))
    def test_exception(self, mock_run):
        r = KWinManager.reconfigure_kwin()
        self.assertFalse(r.success)


class TestAddWindowRule(unittest.TestCase):

    @patch("subprocess.run")
    @patch("shutil.which", side_effect=lambda c: "/usr/bin/" + c if "kwrite" in c or "kread" in c else None)
    def test_add_rule_basic(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="0")
        r = KWinManager.add_window_rule("firefox")
        self.assertTrue(r.success)
        self.assertIn("firefox", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", side_effect=lambda c: "/usr/bin/" + c if "kwrite" in c or "kread" in c else None)
    def test_add_rule_with_workspace(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="2")
        r = KWinManager.add_window_rule("code", workspace=2)
        self.assertTrue(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", side_effect=lambda c: "/usr/bin/" + c if "kwrite" in c or "kread" in c else None)
    def test_add_rule_maximized(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="0")
        r = KWinManager.add_window_rule("steam", maximized=True)
        self.assertTrue(r.success)

    @patch("shutil.which", return_value=None)
    def test_no_kwriteconfig(self, mock_which):
        r = KWinManager.add_window_rule("app")
        self.assertFalse(r.success)

    @patch("shutil.which", side_effect=lambda c: "/usr/bin/kwriteconfig6" if "kwrite" in c else None)
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run, mock_which):
        r = KWinManager.add_window_rule("app")
        self.assertFalse(r.success)


class TestGetWindowList(unittest.TestCase):

    @patch("subprocess.run")
    def test_returns_windows(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Window1\nWindow2\n")
        result = KWinManager.get_window_list()
        self.assertEqual(len(result), 2)

    @patch("subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        result = KWinManager.get_window_list()
        self.assertEqual(result, [])

    @patch("subprocess.run", side_effect=OSError("no qdbus"))
    def test_exception(self, mock_run):
        result = KWinManager.get_window_list()
        self.assertEqual(result, [])


class TestInstallTilingScript(unittest.TestCase):

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.mkdir")
    def test_install(self, mock_mkdir, mock_write):
        r = KWinManager.install_tiling_script()
        self.assertTrue(r.success)
        self.assertIn("path", r.data)
        # Two files: main.js and metadata.json
        self.assertEqual(mock_write.call_count, 2)


if __name__ == '__main__':
    unittest.main()
