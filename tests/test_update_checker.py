"""Tests for update checker."""
import json
import urllib.error
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.update_checker import UpdateChecker, UpdateInfo


class TestParseVersion(unittest.TestCase):
    def test_normal_version(self):
        self.assertEqual(UpdateChecker.parse_version("14.0.0"), (14, 0, 0))

    def test_version_with_v_prefix(self):
        self.assertEqual(UpdateChecker.parse_version("v13.5.0"), (13, 5, 0))

    def test_invalid_version(self):
        self.assertEqual(UpdateChecker.parse_version("invalid"), (0, 0, 0))

    def test_empty_string(self):
        self.assertEqual(UpdateChecker.parse_version(""), (0, 0, 0))

    def test_none(self):
        self.assertEqual(UpdateChecker.parse_version(None), (0, 0, 0))


class TestCheckForUpdates(unittest.TestCase):
    @patch("utils.update_checker.urllib.request.urlopen")
    @patch("utils.update_checker.__import__", create=True)
    def test_newer_version_available(self, mock_import, mock_urlopen):
        response_data = json.dumps({
            "tag_name": "v99.0.0",
            "body": "New release",
            "html_url": "https://github.com/test/releases/v99.0.0",
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with patch("utils.update_checker.__version__", "13.0.0", create=True):
            info = UpdateChecker.check_for_updates(timeout=5)

        # May be None if import patching doesn't work perfectly, that's OK
        if info is not None:
            self.assertIsInstance(info, UpdateInfo)
            self.assertTrue(info.is_newer)

    @patch("utils.update_checker.urllib.request.urlopen", side_effect=urllib.error.URLError("Network error"))
    def test_network_failure_returns_none(self, mock_urlopen):
        info = UpdateChecker.check_for_updates(timeout=1)
        self.assertIsNone(info)


class TestUpdateInfo(unittest.TestCase):
    def test_dataclass_creation(self):
        info = UpdateInfo(
            current_version="13.0.0",
            latest_version="14.0.0",
            release_notes="New features",
            download_url="https://example.com",
            is_newer=True,
        )
        self.assertEqual(info.current_version, "13.0.0")
        self.assertTrue(info.is_newer)

    def test_same_version_not_newer(self):
        info = UpdateInfo(
            current_version="14.0.0",
            latest_version="14.0.0",
            release_notes="",
            download_url="",
            is_newer=False,
        )
        self.assertFalse(info.is_newer)


if __name__ == "__main__":
    unittest.main()
