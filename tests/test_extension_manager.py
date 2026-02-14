"""
Tests for utils/extension_manager.py — Desktop Extension Manager.
Part of v37.0.0 "Pinnacle".

Covers: detect_desktop, list_installed (GNOME + KDE), install, remove,
enable, disable, is_supported, and search_available.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.extension_manager import (
    ExtensionManager, ExtensionEntry, DesktopEnvironment,
)


class TestDesktopDetection(unittest.TestCase):
    """Tests for ExtensionManager.detect_desktop()."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_detect_gnome(self):
        result = ExtensionManager.detect_desktop()
        self.assertEqual(result, DesktopEnvironment.GNOME)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_detect_kde(self):
        result = ExtensionManager.detect_desktop()
        self.assertEqual(result, DesktopEnvironment.KDE)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-Cinnamon"}, clear=False)
    @patch.dict(os.environ, {"DESKTOP_SESSION": ""}, clear=False)
    def test_detect_unknown(self):
        result = ExtensionManager.detect_desktop()
        self.assertEqual(result, DesktopEnvironment.UNKNOWN)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"})
    def test_detect_gnome_variant(self):
        result = ExtensionManager.detect_desktop()
        self.assertEqual(result, DesktopEnvironment.GNOME)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "plasma"})
    def test_detect_plasma(self):
        result = ExtensionManager.detect_desktop()
        self.assertEqual(result, DesktopEnvironment.KDE)


class TestIsSupported(unittest.TestCase):
    """Tests for ExtensionManager.is_supported()."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.extension_manager.shutil.which", return_value="/usr/bin/gnome-extensions")
    def test_gnome_supported(self, mock_which):
        self.assertTrue(ExtensionManager.is_supported())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.extension_manager.shutil.which", return_value=None)
    def test_gnome_not_supported(self, mock_which):
        self.assertFalse(ExtensionManager.is_supported())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    @patch("utils.extension_manager.shutil.which", return_value="/usr/bin/plasmapkg2")
    def test_kde_supported(self, mock_which):
        self.assertTrue(ExtensionManager.is_supported())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-Cinnamon"}, clear=False)
    @patch.dict(os.environ, {"DESKTOP_SESSION": ""}, clear=False)
    def test_unknown_not_supported(self):
        self.assertFalse(ExtensionManager.is_supported())


class TestListInstalled(unittest.TestCase):
    """Tests for ExtensionManager.list_installed()."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.extension_manager.shutil.which", return_value="/usr/bin/gnome-extensions")
    @patch("utils.extension_manager.subprocess.run")
    def test_list_gnome_extensions(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "dash-to-dock@micxgx.gmail.com\n"
                "  Name: Dash to Dock\n"
                "  Description: A dock for GNOME\n"
                "  State: ENABLED\n"
                "  Version: 80\n"
                "\n"
                "appindicator@rgcjonas.gmail.com\n"
                "  Name: AppIndicator\n"
                "  State: DISABLED\n"
                "\n"
            ),
        )
        result = ExtensionManager.list_installed()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].uuid, "dash-to-dock@micxgx.gmail.com")
        self.assertTrue(result[0].enabled)
        self.assertFalse(result[1].enabled)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    @patch("utils.extension_manager.shutil.which", return_value="/usr/bin/plasmapkg2")
    @patch("utils.extension_manager.subprocess.run")
    def test_list_kde_extensions(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Listing service types: Plasma/Applet in /usr/share\n"
                "org.kde.plasma.analogclock\n"
                "org.kde.plasma.battery\n"
            ),
        )
        result = ExtensionManager.list_installed()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].desktop, "kde")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.extension_manager.shutil.which", return_value=None)
    def test_list_gnome_no_tool(self, mock_which):
        """No gnome-extensions binary returns empty list."""
        result = ExtensionManager.list_installed()
        self.assertEqual(len(result), 0)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.extension_manager.shutil.which", return_value="/usr/bin/gnome-extensions")
    @patch("utils.extension_manager.subprocess.run")
    def test_list_gnome_timeout(self, mock_run, mock_which):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gnome-extensions", timeout=30)
        result = ExtensionManager.list_installed()
        self.assertEqual(len(result), 0)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-Cinnamon"}, clear=False)
    @patch.dict(os.environ, {"DESKTOP_SESSION": ""}, clear=False)
    def test_list_unknown_desktop(self):
        """Unknown desktop returns empty list."""
        result = ExtensionManager.list_installed()
        self.assertEqual(len(result), 0)


class TestInstallRemoveEnableDisable(unittest.TestCase):
    """Tests for install, remove, enable, disable commands."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_install_gnome(self):
        binary, args, desc = ExtensionManager.install("test@example.com")
        self.assertEqual(binary, "gnome-extensions")
        self.assertIn("install", args)
        self.assertIn("test@example.com", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_install_kde(self):
        binary, args, desc = ExtensionManager.install("org.kde.test")
        self.assertEqual(binary, "plasmapkg2")
        self.assertIn("--install", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_remove_gnome(self):
        binary, args, desc = ExtensionManager.remove("test@example.com")
        self.assertEqual(binary, "gnome-extensions")
        self.assertIn("uninstall", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_remove_kde(self):
        binary, args, desc = ExtensionManager.remove("org.kde.test")
        self.assertEqual(binary, "plasmapkg2")
        self.assertIn("--remove", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_enable_gnome(self):
        binary, args, desc = ExtensionManager.enable("test@example.com")
        self.assertEqual(binary, "gnome-extensions")
        self.assertIn("enable", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_disable_gnome(self):
        binary, args, desc = ExtensionManager.disable("test@example.com")
        self.assertEqual(binary, "gnome-extensions")
        self.assertIn("disable", args)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-Cinnamon"}, clear=False)
    @patch.dict(os.environ, {"DESKTOP_SESSION": ""}, clear=False)
    def test_install_unsupported(self):
        """Unsupported desktop returns echo fallback."""
        binary, args, desc = ExtensionManager.install("test")
        self.assertEqual(binary, "echo")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_enable_kde_noop(self):
        """KDE enable is a no-op echo."""
        binary, args, desc = ExtensionManager.enable("org.kde.test")
        self.assertEqual(binary, "echo")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_disable_kde_noop(self):
        """KDE disable is a no-op echo."""
        binary, args, desc = ExtensionManager.disable("org.kde.test")
        self.assertEqual(binary, "echo")


class TestSearchAvailable(unittest.TestCase):
    """Tests for ExtensionManager.search_available()."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_search_non_gnome(self):
        """Search on non-GNOME returns empty list."""
        result = ExtensionManager.search_available("test")
        self.assertEqual(len(result), 0)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("urllib.request.urlopen")
    def test_search_gnome_success(self, mock_urlopen):
        """GNOME extension search parses API response."""
        import json
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "extensions": [
                {"uuid": "test@example.com", "name": "Test Ext", "description": "A test", "creator": "Author", "pk": 123},
            ]
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = ExtensionManager.search_available("test")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].uuid, "test@example.com")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("urllib.request.urlopen")
    def test_search_gnome_network_error(self, mock_urlopen):
        """Network error returns empty list."""
        mock_urlopen.side_effect = Exception("Network error")
        result = ExtensionManager.search_available("test")
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
