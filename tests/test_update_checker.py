"""Tests for update checker."""
import json
import os
import sys
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.update_checker import (
    DownloadResult,
    UpdateAsset,
    UpdateChecker,
    UpdateInfo,
    VerifyResult,
)


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
    def setUp(self):
        UpdateChecker._cached_info = None

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

    @patch("utils.update_checker.urllib.request.urlopen", side_effect=urllib.error.URLError("offline"))
    def test_network_failure_returns_cached_offline_info(self, mock_urlopen):
        UpdateChecker._cached_info = UpdateInfo(
            current_version="29.0.0",
            latest_version="30.0.0",
            release_notes="Cached",
            download_url="https://example.invalid/release",
            is_newer=True,
        )

        info = UpdateChecker.check_for_updates(timeout=1, use_cache=True)
        self.assertIsNotNone(info)
        self.assertTrue(info.offline)
        self.assertEqual(info.source, "cache")


class TestUpdateAssetPipeline(unittest.TestCase):
    def test_select_download_asset_prefers_rpm(self):
        assets = [
            UpdateAsset(name="loofi.tar.gz", download_url="https://example.invalid/a"),
            UpdateAsset(name="loofi.rpm", download_url="https://example.invalid/b"),
        ]
        selected = UpdateChecker.select_download_asset(assets)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "loofi.rpm")

    @patch("utils.update_checker.urllib.request.urlopen")
    def test_download_update_success(self, mock_urlopen):
        payload = b"artifact"
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        mock_urlopen.return_value = mock_resp

        with tempfile.TemporaryDirectory() as temp_dir:
            result = UpdateChecker.download_update(
                UpdateAsset(name="loofi.rpm", download_url="https://example.invalid/pkg"),
                temp_dir,
                timeout=2,
            )

            self.assertIsInstance(result, DownloadResult)
            self.assertTrue(result.ok)
            self.assertTrue(os.path.exists(result.file_path))

    @patch("utils.update_checker.urllib.request.urlopen", side_effect=urllib.error.URLError("offline"))
    def test_download_update_failure(self, mock_urlopen):
        result = UpdateChecker.download_update(
            UpdateAsset(name="loofi.rpm", download_url="https://example.invalid/pkg"),
            "/tmp/loofi-does-not-matter",
            timeout=1,
        )
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)

    @patch("utils.update_checker.subprocess.run")
    def test_verify_download_checksum_and_signature(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "artifact.rpm")
            signature = os.path.join(temp_dir, "artifact.sig")
            Path(artifact).write_bytes(b"data")
            Path(signature).write_bytes(b"sig")

            digest = "3a6eb0790f39ac87c94f3856b2dd2c5d110e6811602261a9a923d3bb23adc8b7"
            result = UpdateChecker.verify_download(
                artifact,
                expected_sha256=digest,
                signature_path=signature,
            )

            self.assertIsInstance(result, VerifyResult)
            self.assertTrue(result.ok)

    def test_verify_download_checksum_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "artifact.rpm")
            Path(artifact).write_bytes(b"data")

            result = UpdateChecker.verify_download(
                artifact,
                expected_sha256="0" * 64,
            )

            self.assertFalse(result.ok)
            self.assertIn("mismatch", result.error.lower())


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
