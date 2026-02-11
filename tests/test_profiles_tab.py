"""Source-level checks for ProfilesTab import/export wiring (v24.0)."""

import os
import unittest


class TestProfilesTabSource(unittest.TestCase):
    """Ensure v24 profile UI actions are present."""

    def test_profiles_tab_contains_import_export_controls(self):
        path = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'profiles_tab.py'
        )
        with open(path, 'r', encoding='utf-8') as fh:
            source = fh.read()

        self.assertIn("Export All", source)
        self.assertIn("Import Bundle", source)
        self.assertIn("def _export_profile", source)
        self.assertIn("def _export_all_profiles", source)
        self.assertIn("def _import_bundle", source)

    def test_profiles_tab_uses_profile_manager_import_export(self):
        path = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'profiles_tab.py'
        )
        with open(path, 'r', encoding='utf-8') as fh:
            source = fh.read()

        self.assertIn("ProfileManager.export_profile_json", source)
        self.assertIn("ProfileManager.export_bundle_json", source)
        self.assertIn("ProfileManager.import_bundle_json", source)
        self.assertIn("ProfileManager.import_profile_json", source)


if __name__ == '__main__':
    unittest.main()
