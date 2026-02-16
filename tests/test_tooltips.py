"""
Tests for ui/tooltips.py - Tooltip string constants.
Verifies that every expected tooltip constant exists, is a non-empty string,
and that no accidental duplicates crept in.
"""

import os
import sys
import unittest

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from ui import tooltips


# All constants that must be present, grouped by section.
EXPECTED_CONSTANTS = {
    # Main Window
    "MAIN_APPLY",
    "MAIN_REVERT",
    "MAIN_REFRESH",
    # Boot
    "BOOT_TIMEOUT",
    "BOOT_DEFAULT_ENTRY",
    "BOOT_QUIET",
    "BOOT_PLYMOUTH",
    # Hardware
    "HW_CPU_GOVERNOR",
    "HW_GPU_PROFILE",
    "HW_FAN_MODE",
    "HW_BACKLIGHT",
    # Performance
    "PERF_SWAPPINESS",
    "PERF_THP",
    "PERF_ZRAM",
    "PERF_SCHEDULER",
    # Diagnostics
    "DIAG_JOURNAL",
    "DIAG_COREDUMPS",
    "DIAG_DISK_HEALTH",
    "DIAG_NETWORK",
    # Mesh / Teleport
    "MESH_DISCOVERY",
    "MESH_PAIR",
    "TELEPORT_SEND",
    "TELEPORT_RECEIVE",
    # Settings Dialog
    "SETTINGS_THEME",
    "SETTINGS_LANGUAGE",
    "SETTINGS_AUTOSTART",
    "SETTINGS_NOTIFICATIONS",
    # Dashboard
    "DASH_HEALTH_SCORE",
    "DASH_QUICK_ACTIONS",
    "DASH_FOCUS_MODE",
    "DASH_SYSTEM_OVERVIEW",
    # Software
    "SW_SEARCH",
    "SW_INSTALL",
    "SW_BATCH_INSTALL",
    "SW_BATCH_REMOVE",
    "SW_RPM_FUSION",
    "SW_CODECS",
    "SW_FLATHUB",
    # Maintenance
    "MAINT_CLEANUP",
    "MAINT_JOURNAL",
    "MAINT_FLATPAK_CLEANUP",
    "MAINT_ORPHANS",
    # Desktop
    "DESK_THEME",
    "DESK_FONTS",
    "DESK_EXTENSIONS",
    "DESK_WALLPAPER",
    # Development
    "DEV_TOOLBOX",
    "DEV_VSCODE",
    "DEV_LANGUAGES",
    "DEV_CONTAINERS",
}


class TestTooltipConstantsExist(unittest.TestCase):
    """Every expected tooltip constant must be defined in the module."""

    def test_all_expected_constants_present(self):
        for name in EXPECTED_CONSTANTS:
            with self.subTest(name=name):
                self.assertTrue(
                    hasattr(tooltips, name),
                    f"Missing tooltip constant: {name}",
                )


class TestTooltipValues(unittest.TestCase):
    """Each constant must be a non-empty string."""

    def test_all_values_are_nonempty_strings(self):
        for name in EXPECTED_CONSTANTS:
            with self.subTest(name=name):
                value = getattr(tooltips, name)
                self.assertIsInstance(value, str, f"{name} should be a str")
                self.assertTrue(len(value) > 0, f"{name} should not be empty")

    def test_values_are_reasonably_short(self):
        """Tooltips should be concise -- under 120 chars."""
        for name in EXPECTED_CONSTANTS:
            with self.subTest(name=name):
                value = getattr(tooltips, name)
                self.assertLessEqual(
                    len(value), 120,
                    f"{name} tooltip is too long ({len(value)} chars)",
                )


class TestNoDuplicates(unittest.TestCase):
    """No two tooltip constants should share the exact same string."""

    def test_no_duplicate_values(self):
        seen = {}
        for name in EXPECTED_CONSTANTS:
            value = getattr(tooltips, name)
            if value in seen:
                self.fail(
                    f"Duplicate tooltip value between {seen[value]} and {name}: "
                    f"{value!r}"
                )
            seen[value] = name


class TestModuleHasNoUnexpectedPublicNames(unittest.TestCase):
    """Guard against stray exports sneaking in."""

    def test_only_expected_public_names(self):
        public_names = {
            n for n in dir(tooltips)
            if not n.startswith("_")
        }
        unexpected = public_names - EXPECTED_CONSTANTS
        self.assertEqual(
            unexpected, set(),
            f"Unexpected public names in tooltips module: {unexpected}",
        )


if __name__ == '__main__':
    unittest.main()
