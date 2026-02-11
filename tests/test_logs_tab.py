"""Source-level checks for LogsTab live panel wiring (v24.0)."""

import os
import unittest


class TestLogsTabSource(unittest.TestCase):
    """Ensure the live log panel and incremental polling hooks exist."""

    def test_logs_tab_contains_live_panel_features(self):
        path = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'logs_tab.py'
        )
        with open(path, 'r', encoding='utf-8') as fh:
            source = fh.read()

        self.assertIn("Live Log Panel", source)
        self.assertIn("def _toggle_live", source)
        self.assertIn("def _poll_live_logs", source)
        self.assertIn("get_logs_incremental", source)
        self.assertIn("Buffer rows:", source)

    def test_logs_tab_export_uses_entries_signature(self):
        path = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'logs_tab.py'
        )
        with open(path, 'r', encoding='utf-8') as fh:
            source = fh.read()

        self.assertIn("entries = SmartLogViewer.get_logs", source)
        self.assertIn("SmartLogViewer.export_logs(entries, path, format=fmt)", source)


if __name__ == '__main__':
    unittest.main()
