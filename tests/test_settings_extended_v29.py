"""
Tests for SettingsManager.reset_group feature — v29.0 "Usability & Polish".

Extended coverage for the reset_group method:
- Resets only specified keys
- Leaves other keys unchanged
- Persists to disk
- Handles edge cases (all keys, single key, overlapping calls)
"""

import json
import os
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.settings import SettingsManager, AppSettings, KNOWN_KEYS


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_manager(tmpdir: str, initial: dict = None) -> SettingsManager:
    """Create a SettingsManager backed by a file inside *tmpdir*."""
    path = Path(tmpdir) / "settings.json"
    if initial is not None:
        path.write_text(json.dumps(initial, indent=2))
    return SettingsManager(settings_path=path)


# ---------------------------------------------------------------------------
# TestResetGroupBasic
# ---------------------------------------------------------------------------

class TestResetGroupBasic(unittest.TestCase):
    """Basic reset_group functionality."""

    def _defaults(self):
        return asdict(AppSettings())

    def test_single_key_reset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = self._defaults()
            initial["theme"] = "light"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["theme"])
            self.assertEqual(mgr.get("theme"), "dark")

    def test_multiple_keys_reset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = self._defaults()
            initial["theme"] = "light"
            initial["follow_system_theme"] = True
            initial["log_level"] = "DEBUG"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["theme", "follow_system_theme"])
            self.assertEqual(mgr.get("theme"), "dark")
            self.assertFalse(mgr.get("follow_system_theme"))
            # log_level untouched
            self.assertEqual(mgr.get("log_level"), "DEBUG")

    def test_reset_all_known_keys(self):
        """Resetting all keys should restore full defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = self._defaults()
            initial["theme"] = "light"
            initial["log_level"] = "DEBUG"
            initial["show_notifications"] = False
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(list(KNOWN_KEYS))

            defaults = self._defaults()
            for key in KNOWN_KEYS:
                self.assertEqual(
                    mgr.get(key), defaults[key],
                    f"Key '{key}' not reset to default",
                )


class TestResetGroupPersistence(unittest.TestCase):
    """reset_group persists changes to disk."""

    def test_persisted_after_reset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            initial = asdict(AppSettings())
            initial["theme"] = "solarized"
            initial["start_minimized"] = True
            path.write_text(json.dumps(initial, indent=2))

            mgr = SettingsManager(settings_path=path)
            mgr.reset_group(["theme"])

            # Read separately from disk
            saved = json.loads(path.read_text())
            self.assertEqual(saved["theme"], "dark")
            self.assertTrue(saved["start_minimized"])

    def test_reload_after_reset_group(self):
        """A new SettingsManager reading the same file sees the reset values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            initial = asdict(AppSettings())
            initial["theme"] = "nord"
            path.write_text(json.dumps(initial, indent=2))

            mgr1 = SettingsManager(settings_path=path)
            mgr1.reset_group(["theme"])

            mgr2 = SettingsManager(settings_path=path)
            self.assertEqual(mgr2.get("theme"), "dark")


class TestResetGroupEdgeCases(unittest.TestCase):
    """Edge cases for reset_group."""

    def test_empty_list_is_noop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group([])
            self.assertEqual(mgr.get("theme"), "light")

    def test_unknown_key_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            mgr = _make_manager(tmpdir, initial)

            # Should not raise
            mgr.reset_group(["nonexistent_xyz", "theme"])
            self.assertEqual(mgr.get("theme"), "dark")

    def test_duplicate_keys_in_list(self):
        """Duplicate keys in the list should not cause issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["theme", "theme", "theme"])
            self.assertEqual(mgr.get("theme"), "dark")

    def test_reset_group_twice(self):
        """Calling reset_group twice should be idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            initial["log_level"] = "DEBUG"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["theme"])
            mgr.reset_group(["theme"])

            self.assertEqual(mgr.get("theme"), "dark")
            # Other keys still untouched
            self.assertEqual(mgr.get("log_level"), "DEBUG")

    def test_reset_boolean_setting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["confirm_dangerous_actions"] = False
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["confirm_dangerous_actions"])
            self.assertTrue(mgr.get("confirm_dangerous_actions"))

    def test_reset_string_setting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["log_level"] = "CRITICAL"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["log_level"])
            self.assertEqual(mgr.get("log_level"), "INFO")

    def test_reset_integer_setting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["last_tab_index"] = 42
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["last_tab_index"])
            self.assertEqual(mgr.get("last_tab_index"), 0)

    def test_reset_preserves_non_default_unreset_values(self):
        """Only keys in the group are reset; others keep custom values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            initial["log_level"] = "DEBUG"
            initial["show_notifications"] = False
            initial["start_minimized"] = True
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["theme", "show_notifications"])

            self.assertEqual(mgr.get("theme"), "dark")
            self.assertTrue(mgr.get("show_notifications"))
            # These should remain customised
            self.assertEqual(mgr.get("log_level"), "DEBUG")
            self.assertTrue(mgr.get("start_minimized"))


class TestResetGroupVsFullReset(unittest.TestCase):
    """Contrast reset_group with full reset()."""

    def test_reset_group_subset_differs_from_full_reset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            initial["log_level"] = "DEBUG"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset_group(["theme"])

            # theme is back to default
            self.assertEqual(mgr.get("theme"), "dark")
            # log_level is NOT reset (unlike full reset())
            self.assertEqual(mgr.get("log_level"), "DEBUG")

    def test_full_reset_resets_everything(self):
        """Full reset() should reset all keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            initial["log_level"] = "DEBUG"
            mgr = _make_manager(tmpdir, initial)

            mgr.reset()

            defaults = asdict(AppSettings())
            self.assertEqual(mgr.get("theme"), defaults["theme"])
            self.assertEqual(mgr.get("log_level"), defaults["log_level"])


if __name__ == '__main__':
    unittest.main()
