"""Tests for core profile schema and storage layer (v24.0)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from core.profiles.models import ProfileBundle, ProfileRecord
from core.profiles.storage import ProfileStore


class TestProfileRecord(unittest.TestCase):
    """Tests for ProfileRecord validation and normalization."""

    def test_profile_record_normalizes_key(self):
        record = ProfileRecord(key="My Profile", name="My Profile", settings={"governor": "performance"})
        self.assertEqual(record.key, "my_profile")

    def test_profile_record_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            ProfileRecord(key="k", name="", settings={})

    def test_from_legacy_dict(self):
        data = {"name": "Legacy", "description": "legacy", "settings": {"swappiness": 20}}
        record = ProfileRecord.from_dict(data, default_key="legacy")
        self.assertEqual(record.key, "legacy")
        self.assertEqual(record.name, "Legacy")
        self.assertEqual(record.settings["swappiness"], 20)


class TestProfileStore(unittest.TestCase):
    """Tests for ProfileStore CRUD and import/export."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.builtins = {
            "gaming": {
                "name": "Gaming",
                "description": "builtin",
                "icon": "x",
                "settings": {"governor": "performance"},
            }
        }
        self.store = ProfileStore(self.tmp.name, self.builtins)

    def test_list_profiles_includes_builtin(self):
        profiles = self.store.list_profiles()
        self.assertEqual(len(profiles), 1)
        self.assertTrue(profiles[0].builtin)

    def test_save_and_get_custom_profile(self):
        record = ProfileRecord(key="dev", name="Dev", settings={"governor": "schedutil"})
        ok, _msg, path = self.store.save_custom_profile(record)
        self.assertTrue(ok)
        self.assertTrue(os.path.isfile(path))

        loaded = self.store.get_profile("dev")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Dev")

    def test_legacy_file_is_loaded(self):
        path = os.path.join(self.tmp.name, "legacy.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"name": "Legacy", "description": "old", "settings": {"x": 1}}, fh)

        loaded = self.store.get_profile("legacy")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Legacy")
        self.assertEqual(loaded.settings["x"], 1)

    def test_import_profile_duplicate_requires_overwrite(self):
        payload = {
            "profile": {
                "key": "my_custom",
                "name": "Custom",
                "settings": {"swappiness": 10},
            }
        }
        ok, _msg, _data = self.store.import_profile_data(payload, overwrite=False)
        self.assertTrue(ok)

        ok2, msg2, _data2 = self.store.import_profile_data(payload, overwrite=False)
        self.assertFalse(ok2)
        self.assertIn("already exists", msg2)

        ok3, _msg3, _data3 = self.store.import_profile_data(payload, overwrite=True)
        self.assertTrue(ok3)

    def test_bundle_import_mixed_results(self):
        # Existing profile to trigger duplicate error without overwrite
        self.store.import_profile_data({"profile": {"key": "dup", "name": "Dup", "settings": {}}})

        bundle = {
            "schema_version": 1,
            "profiles": [
                {"key": "dup", "name": "Dup", "settings": {}},
                {"key": "new_one", "name": "New One", "settings": {"governor": "powersave"}},
                {"key": "gaming", "name": "Builtin Clash", "settings": {}},
            ],
        }
        ok, msg, data = self.store.import_bundle_data(bundle, overwrite=False)

        self.assertFalse(ok)
        self.assertIn("errors", data)
        self.assertIn("new_one", data["imported"])
        self.assertIn("gaming", data["skipped"])
        self.assertEqual(msg, "Bundle imported with errors.")

    def test_export_bundle(self):
        self.store.import_profile_data({"profile": {"key": "one", "name": "One", "settings": {}}})
        ok, _msg, payload = self.store.export_bundle_data(include_builtins=False)
        self.assertTrue(ok)
        self.assertEqual(payload["kind"], "profile_bundle")
        self.assertEqual(len(payload["profiles"]), 1)


class TestProfileBundle(unittest.TestCase):
    """Tests for ProfileBundle serialization."""

    def test_bundle_roundtrip(self):
        bundle = ProfileBundle(
            profiles=[
                ProfileRecord(key="a", name="A", settings={}),
                ProfileRecord(key="b", name="B", settings={"x": 1}),
            ]
        )
        data = bundle.to_dict()
        restored = ProfileBundle.from_dict(data)
        self.assertEqual(len(restored.profiles), 2)
        self.assertEqual(restored.profiles[1].settings["x"], 1)


if __name__ == '__main__':
    unittest.main()
