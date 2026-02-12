"""Tests for opt-in plugin analytics behavior (Task T12)."""
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_analytics import PluginAnalytics
from utils.settings import SettingsManager


class _FakeResponse:
    """Small context-manager stub used to emulate urllib responses."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestPluginAnalytics(unittest.TestCase):
    """Coverage for opt-in defaults, suppression, persistence, and retries."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.settings_path = Path(self.temp_dir) / "settings.json"
        self.settings = SettingsManager(settings_path=self.settings_path)
        self.analytics = PluginAnalytics(settings_manager=self.settings, batch_size=2, timeout=1)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("utils.plugin_analytics.urllib.request.urlopen")
    def test_default_off_policy_suppresses_events(self, mock_urlopen):
        """Analytics should be disabled by default and ignore tracked events."""
        self.assertFalse(self.analytics.is_enabled())
        self.assertFalse(self.analytics.track_event("plugin", "installed", "demo"))
        self.assertEqual(self.analytics.queue_size(), 0)
        mock_urlopen.assert_not_called()

    @patch("utils.plugin_analytics.uuid.uuid4")
    def test_consent_toggle_persists_and_creates_anonymous_id(self, mock_uuid4):
        """set_enabled(True/False) should persist consent state across reload."""
        mock_uuid4.return_value.hex = "abc123anon"

        self.analytics.set_enabled(True)
        self.assertTrue(self.settings.get("plugin_analytics_enabled"))
        self.assertEqual(self.settings.get("plugin_analytics_anonymous_id"), "abc123anon")

        reloaded = SettingsManager(settings_path=self.settings_path)
        self.assertTrue(reloaded.get("plugin_analytics_enabled"))
        self.assertEqual(reloaded.get("plugin_analytics_anonymous_id"), "abc123anon")

        self.analytics.set_enabled(False)
        reloaded_after_disable = SettingsManager(settings_path=self.settings_path)
        self.assertFalse(reloaded_after_disable.get("plugin_analytics_enabled"))

    @patch("utils.plugin_analytics.urllib.request.urlopen")
    def test_flush_returns_false_when_disabled(self, mock_urlopen):
        """flush() is a no-op and returns False when analytics is disabled."""
        self.assertFalse(self.analytics.flush())
        mock_urlopen.assert_not_called()

    @patch("utils.plugin_analytics.urllib.request.urlopen")
    @patch("utils.plugin_analytics.uuid.uuid4")
    def test_send_retry_logic_requeues_on_failure_then_succeeds(self, mock_uuid4, mock_urlopen):
        """Failed send keeps queue and retries successfully on next flush."""
        mock_uuid4.return_value.hex = "retryanon"
        self.analytics.set_enabled(True)

        self.assertTrue(self.analytics.track_event("plugin", "install_started", "p1"))
        self.assertEqual(self.analytics.queue_size(), 1)

        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        self.assertFalse(self.analytics.track_event("plugin", "install_completed", "p1"))
        self.assertEqual(self.analytics.queue_size(), 2)

        mock_urlopen.side_effect = None
        mock_urlopen.return_value = _FakeResponse()
        self.assertTrue(self.analytics.flush())
        self.assertEqual(self.analytics.queue_size(), 0)


if __name__ == "__main__":
    unittest.main()
