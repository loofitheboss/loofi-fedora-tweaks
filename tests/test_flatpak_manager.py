"""
Tests for utils/flatpak_manager.py — Flatpak Manager.
Part of v37.0.0 "Pinnacle".

Covers: get_flatpak_sizes, get_flatpak_permissions, find_orphan_runtimes,
cleanup_unused, get_total_size, _parse_size, is_available.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.flatpak_manager import (
    FlatpakManager, FlatpakSizeEntry,
)


class TestFlatpakManagerAvailability(unittest.TestCase):
    """Tests for FlatpakManager.is_available()."""

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    def test_flatpak_available(self, mock_which):
        self.assertTrue(FlatpakManager.is_available())

    @patch("utils.flatpak_manager.shutil.which", return_value=None)
    def test_flatpak_not_available(self, mock_which):
        self.assertFalse(FlatpakManager.is_available())


class TestFlatpakSizes(unittest.TestCase):
    """Tests for FlatpakManager.get_flatpak_sizes()."""

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    @patch("utils.flatpak_manager.subprocess.run")
    def test_get_sizes(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Firefox\torg.mozilla.firefox\t500 MB\torg.freedesktop.Platform\torg.mozilla.firefox/x86_64/stable\n"
                "GIMP\torg.gimp.GIMP\t1.2 GB\torg.gnome.Platform\torg.gimp.GIMP/x86_64/stable\n"
                "Calculator\torg.gnome.Calculator\t10 MB\torg.gnome.Platform\torg.gnome.Calculator/x86_64/stable\n"
            ),
        )
        result = FlatpakManager.get_flatpak_sizes()
        self.assertEqual(len(result), 3)
        # Should be sorted by size descending
        self.assertEqual(result[0].name, "GIMP")
        self.assertGreater(result[0].size_bytes, result[1].size_bytes)

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    @patch("utils.flatpak_manager.subprocess.run")
    def test_get_sizes_empty(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = FlatpakManager.get_flatpak_sizes()
        self.assertEqual(len(result), 0)

    @patch("utils.flatpak_manager.shutil.which", return_value=None)
    def test_get_sizes_no_flatpak(self, mock_which):
        result = FlatpakManager.get_flatpak_sizes()
        self.assertEqual(len(result), 0)

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    @patch("utils.flatpak_manager.subprocess.run")
    def test_get_sizes_timeout(self, mock_run, mock_which):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="flatpak", timeout=30)
        result = FlatpakManager.get_flatpak_sizes()
        self.assertEqual(len(result), 0)


class TestParseSize(unittest.TestCase):
    """Tests for FlatpakManager._parse_size()."""

    def test_parse_gb(self):
        self.assertAlmostEqual(FlatpakManager._parse_size("1.2 GB"), 1.2 * 1024 ** 3, delta=1024)

    def test_parse_mb(self):
        self.assertAlmostEqual(FlatpakManager._parse_size("500 MB"), 500 * 1024 ** 2, delta=1024)

    def test_parse_kb(self):
        self.assertAlmostEqual(FlatpakManager._parse_size("100 kB"), 100 * 1024, delta=1024)

    def test_parse_empty(self):
        self.assertEqual(FlatpakManager._parse_size(""), 0)

    def test_parse_invalid(self):
        self.assertEqual(FlatpakManager._parse_size("unknown"), 0)


class TestFlatpakPermissions(unittest.TestCase):
    """Tests for FlatpakManager.get_flatpak_permissions()."""

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    @patch("utils.flatpak_manager.subprocess.run")
    def test_get_permissions(self, mock_run, mock_which):
        mock_run.side_effect = [
            # flatpak info --show-permissions
            MagicMock(
                returncode=0,
                stdout=(
                    "[Context]\n"
                    "shared=network;ipc;\n"
                    "sockets=x11;wayland;pulseaudio;\n"
                    "filesystems=home:ro;/tmp;\n"
                ),
            ),
            # flatpak info (for name)
            MagicMock(returncode=0, stdout="Name: Firefox\n"),
        ]
        result = FlatpakManager.get_flatpak_permissions("org.mozilla.firefox")
        self.assertEqual(result.app_id, "org.mozilla.firefox")
        self.assertEqual(result.name, "Firefox")
        self.assertGreater(len(result.permissions), 0)

        # Check specific permissions
        categories = {p.category for p in result.permissions}
        self.assertIn("context", categories)

    @patch("utils.flatpak_manager.shutil.which", return_value=None)
    def test_get_permissions_no_flatpak(self, mock_which):
        result = FlatpakManager.get_flatpak_permissions("org.test")
        self.assertEqual(len(result.permissions), 0)

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    @patch("utils.flatpak_manager.subprocess.run")
    def test_get_permissions_timeout(self, mock_run, mock_which):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="flatpak", timeout=15)
        result = FlatpakManager.get_flatpak_permissions("org.test")
        self.assertEqual(len(result.permissions), 0)


class TestOrphanDetection(unittest.TestCase):
    """Tests for FlatpakManager.find_orphan_runtimes()."""

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    @patch("utils.flatpak_manager.subprocess.run")
    def test_find_orphans(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "org.freedesktop.Platform/x86_64/22.08\n"
                "org.gnome.Platform/x86_64/44\n"
            ),
        )
        result = FlatpakManager.find_orphan_runtimes()
        self.assertEqual(len(result), 2)

    @patch("utils.flatpak_manager.shutil.which", return_value="/usr/bin/flatpak")
    @patch("utils.flatpak_manager.subprocess.run")
    def test_find_no_orphans(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Nothing unused to uninstall\n",
        )
        result = FlatpakManager.find_orphan_runtimes()
        self.assertEqual(len(result), 0)

    @patch("utils.flatpak_manager.shutil.which", return_value=None)
    def test_find_orphans_no_flatpak(self, mock_which):
        result = FlatpakManager.find_orphan_runtimes()
        self.assertEqual(len(result), 0)


class TestCleanup(unittest.TestCase):
    """Tests for FlatpakManager.cleanup_unused()."""

    def test_cleanup_command(self):
        binary, args, desc = FlatpakManager.cleanup_unused()
        self.assertEqual(binary, "flatpak")
        self.assertIn("uninstall", args)
        self.assertIn("--unused", args)


class TestTotalSize(unittest.TestCase):
    """Tests for FlatpakManager.get_total_size()."""

    @patch("utils.flatpak_manager.FlatpakManager.get_flatpak_sizes")
    def test_total_size_gb(self, mock_sizes):
        mock_sizes.return_value = [
            FlatpakSizeEntry(name="A", app_id="a", size_bytes=1024 ** 3),
            FlatpakSizeEntry(name="B", app_id="b", size_bytes=1024 ** 3),
        ]
        result = FlatpakManager.get_total_size()
        self.assertIn("GB", result)

    @patch("utils.flatpak_manager.FlatpakManager.get_flatpak_sizes")
    def test_total_size_mb(self, mock_sizes):
        mock_sizes.return_value = [
            FlatpakSizeEntry(name="A", app_id="a", size_bytes=500 * 1024 ** 2),
        ]
        result = FlatpakManager.get_total_size()
        self.assertIn("MB", result)

    @patch("utils.flatpak_manager.FlatpakManager.get_flatpak_sizes")
    def test_total_size_empty(self, mock_sizes):
        mock_sizes.return_value = []
        result = FlatpakManager.get_total_size()
        self.assertEqual(result, "0 B")


if __name__ == "__main__":
    unittest.main()
