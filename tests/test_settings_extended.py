"""
Extended tests for utils/settings.py - SettingsManager.
Covers edge cases beyond the basic test_settings.py:
  - concurrent access safety
  - type coercion robustness
  - partial/missing keys in saved JSON
  - atomic save (tmp-file rename)
  - set() idempotency
  - large value storage
"""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

# Add source path to sys.path
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
# TestPartialFile - only some keys present on disk
# ---------------------------------------------------------------------------

class TestPartialFile(unittest.TestCase):
    """When the JSON file contains only a subset of keys, missing ones
    should revert to their defaults."""

    def test_partial_keys_filled_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(tmpdir, initial={"theme": "light"})
            # Explicitly stored key
            self.assertEqual(mgr.get("theme"), "light")
            # Keys not in file should be default
            self.assertTrue(mgr.get("show_notifications"))
            self.assertFalse(mgr.get("start_minimized"))
            self.assertEqual(mgr.get("log_level"), "INFO")

    def test_empty_json_object_uses_all_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(tmpdir, initial={})
            self.assertEqual(mgr.get("theme"), "dark")
            self.assertEqual(set(mgr.all().keys()), KNOWN_KEYS)


# ---------------------------------------------------------------------------
# TestSetIdempotency - setting same value twice
# ---------------------------------------------------------------------------

class TestSetIdempotency(unittest.TestCase):
    """Setting the same key to the same value multiple times is safe."""

    def test_set_same_value_twice(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(tmpdir)
            mgr.set("theme", "light")
            mgr.set("theme", "light")
            self.assertEqual(mgr.get("theme"), "light")

    def test_overwrite_reverts_to_original(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(tmpdir)
            mgr.set("theme", "light")
            mgr.set("theme", "dark")
            self.assertEqual(mgr.get("theme"), "dark")


# ---------------------------------------------------------------------------
# TestTypeMismatch - stored type differs from default type
# ---------------------------------------------------------------------------

class TestTypeMismatch(unittest.TestCase):
    """If the JSON file contains a wrong type for a key, the manager
    should still load without crashing (it stores whatever JSON provides)."""

    def test_string_where_bool_expected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(
                tmpdir, initial={"show_notifications": "yes"}
            )
            # The manager doesn't enforce types -- it trusts the JSON
            self.assertEqual(mgr.get("show_notifications"), "yes")

    def test_int_where_string_expected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(tmpdir, initial={"theme": 42})
            self.assertEqual(mgr.get("theme"), 42)


# ---------------------------------------------------------------------------
# TestAtomicSave - tmp file rename
# ---------------------------------------------------------------------------

class TestAtomicSave(unittest.TestCase):
    """save() should write to a .tmp file then rename,
    so no partial writes corrupt settings."""

    def test_no_tmp_file_left_after_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            mgr = SettingsManager(settings_path=path)
            mgr.save()
            tmp_path = path.with_suffix(".tmp")
            self.assertFalse(
                tmp_path.exists(),
                ".tmp file should be renamed away after save",
            )

    def test_file_content_is_complete_after_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            mgr = SettingsManager(settings_path=path)
            mgr.set("theme", "light")
            mgr.save()
            raw = json.loads(path.read_text())
            self.assertEqual(raw["theme"], "light")


# ---------------------------------------------------------------------------
# TestLargeValues - storing large strings
# ---------------------------------------------------------------------------

class TestLargeValues(unittest.TestCase):
    """SettingsManager can handle reasonably large values."""

    def test_large_string_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            mgr = SettingsManager(settings_path=path)
            big = "x" * 10_000
            mgr.set("log_level", big)
            mgr.save()

            mgr2 = SettingsManager(settings_path=path)
            self.assertEqual(mgr2.get("log_level"), big)


# ---------------------------------------------------------------------------
# TestConcurrentAccess - basic thread safety
# ---------------------------------------------------------------------------

class TestConcurrentAccess(unittest.TestCase):
    """Multiple threads setting values should not crash."""

    def test_concurrent_set_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(tmpdir)
            errors = []

            def worker(value):
                try:
                    for _ in range(50):
                        mgr.set("theme", value)
                        mgr.get("theme")
                except Exception as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=worker, args=(f"theme-{i}",))
                for i in range(4)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [], f"Threads raised: {errors}")

    def test_concurrent_save_does_not_corrupt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            mgr = SettingsManager(settings_path=path)
            errors = []

            def saver():
                try:
                    for _ in range(20):
                        mgr.save()
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=saver) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            # File must still be valid JSON
            raw = json.loads(path.read_text())
            self.assertIsInstance(raw, dict)


# ---------------------------------------------------------------------------
# TestResetPersistence - deeper reset checks
# ---------------------------------------------------------------------------

class TestResetPersistence(unittest.TestCase):
    """reset() must restore all keys, not just the ones that were changed."""

    def test_reset_overwrites_all_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _make_manager(tmpdir)
            # Change several settings
            mgr.set("theme", "light")
            mgr.set("log_level", "DEBUG")
            mgr.set("start_minimized", True)
            mgr.reset()

            defaults = AppSettings()
            self.assertEqual(mgr.get("theme"), defaults.theme)
            self.assertEqual(mgr.get("log_level"), defaults.log_level)
            self.assertEqual(mgr.get("start_minimized"), defaults.start_minimized)

    def test_reset_then_save_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            mgr = SettingsManager(settings_path=path)
            mgr.set("theme", "solar")
            mgr.reset()
            # reset already saves; reload from disk
            mgr2 = SettingsManager(settings_path=path)
            self.assertEqual(mgr2.get("theme"), "dark")


if __name__ == '__main__':
    unittest.main()
