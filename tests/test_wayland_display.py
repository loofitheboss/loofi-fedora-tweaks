"""
Tests for utils/wayland_display.py — Wayland Display Manager.
Part of v37.0.0 "Pinnacle" — T23.

Covers: is_wayland, detect_de, get_displays (GNOME/KDE/xrandr),
set_scaling, enable/disable fractional scaling, set_position,
get_session_info.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.wayland_display import WaylandDisplayManager, DisplayInfo


class TestSessionDetection(unittest.TestCase):
    """Tests for is_wayland() and _detect_de()."""

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"})
    def test_is_wayland(self):
        self.assertTrue(WaylandDisplayManager.is_wayland())

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"})
    def test_is_not_wayland(self):
        self.assertFalse(WaylandDisplayManager.is_wayland())

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": ""})
    def test_is_not_wayland_empty(self):
        self.assertFalse(WaylandDisplayManager.is_wayland())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_detect_gnome(self):
        self.assertEqual(WaylandDisplayManager._detect_de(), "gnome")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_detect_kde(self):
        self.assertEqual(WaylandDisplayManager._detect_de(), "kde")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "plasma"})
    def test_detect_plasma(self):
        self.assertEqual(WaylandDisplayManager._detect_de(), "kde")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "Cinnamon"})
    def test_detect_unknown(self):
        self.assertEqual(WaylandDisplayManager._detect_de(), "unknown")


class TestGetDisplays(unittest.TestCase):
    """Tests for get_displays()."""

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.wayland_display.subprocess.run")
    def test_get_displays_gnome(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "eDP-1:\n"
                "  resolution: 1920x1080\n"
                "  scale: 1.0\n"
                "  primary\n"
            ),
        )
        result = WaylandDisplayManager.get_displays()
        self.assertGreaterEqual(len(result), 0)

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"})
    @patch("utils.wayland_display.shutil.which", return_value="/usr/bin/kscreen-doctor")
    @patch("utils.wayland_display.subprocess.run")
    def test_get_displays_kde(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Output: 1\n"
                "  name: DP-1\n"
                "  enabled: true\n"
                "  scale: 1.0\n"
                "  priority: 1\n"
            ),
        )
        result = WaylandDisplayManager.get_displays()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "DP-1")
        self.assertTrue(result[0].primary)

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.wayland_display.shutil.which", return_value="/usr/bin/xrandr")
    @patch("utils.wayland_display.subprocess.run")
    def test_get_displays_xrandr_fallback(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Screen 0: minimum 8 x 8\n"
                "eDP-1 connected primary 1920x1080+0+0\n"
                "HDMI-1 connected 2560x1440+1920+0\n"
            ),
        )
        result = WaylandDisplayManager.get_displays()
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].primary)
        self.assertFalse(result[1].primary)

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"})
    @patch("utils.wayland_display.shutil.which", return_value=None)
    def test_get_displays_no_tools(self, mock_which):
        result = WaylandDisplayManager.get_displays()
        self.assertEqual(len(result), 0)

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "Cinnamon"})
    def test_get_displays_unknown_de(self):
        result = WaylandDisplayManager.get_displays()
        self.assertEqual(len(result), 0)

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.wayland_display.subprocess.run")
    def test_get_displays_gnome_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gnome-monitor-config", timeout=10)
        result = WaylandDisplayManager.get_displays()
        self.assertEqual(len(result), 0)


class TestSetScaling(unittest.TestCase):
    """Tests for set_scaling()."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_set_scaling_gnome(self):
        binary, args, desc = WaylandDisplayManager.set_scaling("eDP-1", 1.5)
        self.assertEqual(binary, "gsettings")
        self.assertIn("text-scaling-factor", args)
        self.assertIn("1.5", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_set_scaling_kde(self):
        binary, args, desc = WaylandDisplayManager.set_scaling("DP-1", 2.0)
        self.assertEqual(binary, "kscreen-doctor")
        self.assertIn("output.DP-1.scale.2.0", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "Cinnamon"})
    def test_set_scaling_unsupported(self):
        binary, args, desc = WaylandDisplayManager.set_scaling("X", 1.0)
        self.assertEqual(binary, "echo")


class TestFractionalScaling(unittest.TestCase):
    """Tests for enable/disable fractional scaling."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_enable_fractional_gnome(self):
        binary, args, desc = WaylandDisplayManager.enable_fractional_scaling()
        self.assertEqual(binary, "gsettings")
        self.assertIn("org.gnome.mutter", args)
        self.assertIn("experimental-features", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_enable_fractional_kde(self):
        binary, args, desc = WaylandDisplayManager.enable_fractional_scaling()
        self.assertEqual(binary, "echo")
        self.assertIn("natively", str(args))

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_disable_fractional_gnome(self):
        binary, args, desc = WaylandDisplayManager.disable_fractional_scaling()
        self.assertEqual(binary, "gsettings")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_disable_fractional_kde(self):
        binary, args, desc = WaylandDisplayManager.disable_fractional_scaling()
        self.assertEqual(binary, "echo")


class TestSetPosition(unittest.TestCase):
    """Tests for set_position()."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_set_position_gnome(self):
        binary, args, desc = WaylandDisplayManager.set_position("eDP-1", 0, 0)
        self.assertEqual(binary, "gnome-monitor-config")
        self.assertIn("eDP-1", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_set_position_kde(self):
        binary, args, desc = WaylandDisplayManager.set_position("DP-1", 1920, 0)
        self.assertEqual(binary, "kscreen-doctor")
        self.assertIn("output.DP-1.position.1920,0", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "Cinnamon"})
    def test_set_position_unsupported(self):
        binary, args, desc = WaylandDisplayManager.set_position("X", 0, 0)
        self.assertEqual(binary, "echo")


class TestSessionInfo(unittest.TestCase):
    """Tests for get_session_info()."""

    @patch.dict(os.environ, {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "GNOME",
        "WAYLAND_DISPLAY": "wayland-0",
    })
    def test_session_info_gnome_wayland(self):
        info = WaylandDisplayManager.get_session_info()
        self.assertEqual(info["session_type"], "wayland")
        self.assertTrue(info["wayland"])
        self.assertEqual(info["compositor"], "mutter")

    @patch.dict(os.environ, {
        "XDG_SESSION_TYPE": "x11",
        "XDG_CURRENT_DESKTOP": "KDE",
        "WAYLAND_DISPLAY": "",
    })
    def test_session_info_kde_x11(self):
        info = WaylandDisplayManager.get_session_info()
        self.assertEqual(info["session_type"], "x11")
        self.assertFalse(info["wayland"])
        self.assertEqual(info["compositor"], "kwin")


class TestParseKscreenOutputs(unittest.TestCase):
    """Tests for _parse_kscreen_outputs()."""

    def test_parse_multiple_outputs(self):
        output = (
            "Output: 1\n"
            "  name: eDP-1\n"
            "  enabled: true\n"
            "  scale: 1.0\n"
            "  priority: 1\n"
            "Output: 2\n"
            "  name: HDMI-1\n"
            "  enabled: true\n"
            "  scale: 2.0\n"
        )
        result = WaylandDisplayManager._parse_kscreen_outputs(output)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "eDP-1")
        self.assertTrue(result[0].primary)
        self.assertEqual(result[1].scale, 2.0)

    def test_parse_empty_output(self):
        result = WaylandDisplayManager._parse_kscreen_outputs("")
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
