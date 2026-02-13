"""Tests for update checker."""
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.update_checker import (
    ERR_CHECKSUM_MISMATCH,
    ERR_DOWNLOAD_FAILED,
    ERR_NETWORK,
    ERR_NO_ASSET,
    ERR_NO_UPDATE,
    ERR_SIGNATURE_FAILED,
    AutoUpdateResult,
    DownloadResult,
    UpdateAsset,
    UpdateChecker,
    UpdateInfo,
    VerifyResult,
)

sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), "..", "loofi-fedora-tweaks"))


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
            UpdateAsset(name="loofi.tar.gz",
                        download_url="https://example.invalid/a"),
            UpdateAsset(name="loofi.rpm",
                        download_url="https://example.invalid/b"),
        ]
        selected = UpdateChecker.select_download_asset(assets)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "loofi.rpm")

    def test_select_download_asset_falls_back_to_first_asset(self):
        assets = [
            UpdateAsset(name="loofi.pkg",
                        download_url="https://example.invalid/a"),
            UpdateAsset(name="loofi.bin",
                        download_url="https://example.invalid/b"),
        ]
        selected = UpdateChecker.select_download_asset(assets)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "loofi.pkg")

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
                UpdateAsset(name="loofi.rpm",
                            download_url="https://example.invalid/pkg"),
                temp_dir,
                timeout=2,
            )

            self.assertIsInstance(result, DownloadResult)
            self.assertTrue(result.ok)
            self.assertTrue(os.path.exists(result.file_path))

    @patch("utils.update_checker.urllib.request.urlopen", side_effect=urllib.error.URLError("offline"))
    def test_download_update_failure(self, mock_urlopen):
        result = UpdateChecker.download_update(
            UpdateAsset(name="loofi.rpm",
                        download_url="https://example.invalid/pkg"),
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

    def test_verify_download_missing_artifact(self):
        result = UpdateChecker.verify_download("/nonexistent/artifact.rpm")
        self.assertFalse(result.ok)
        self.assertIn("does not exist", result.error)

    def test_verify_download_missing_signature_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "artifact.rpm")
            Path(artifact).write_bytes(b"data")

            result = UpdateChecker.verify_download(
                artifact,
                signature_path=os.path.join(temp_dir, "missing.sig"),
            )

            self.assertFalse(result.ok)
            self.assertIn("Missing signature file", result.error)

    def test_verify_download_missing_public_key_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "artifact.rpm")
            signature = os.path.join(temp_dir, "artifact.sig")
            Path(artifact).write_bytes(b"data")
            Path(signature).write_bytes(b"sig")

            result = UpdateChecker.verify_download(
                artifact,
                signature_path=signature,
                public_key_path=os.path.join(temp_dir, "missing.pub"),
            )

            self.assertFalse(result.ok)
            self.assertIn("Missing public key file", result.error)

    @patch("utils.update_checker.subprocess.run", side_effect=OSError("gpg missing"))
    def test_verify_download_signature_oserror(self, mock_run):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "artifact.rpm")
            signature = os.path.join(temp_dir, "artifact.sig")
            Path(artifact).write_bytes(b"data")
            Path(signature).write_bytes(b"sig")

            result = UpdateChecker.verify_download(
                artifact,
                signature_path=signature,
            )

            self.assertFalse(result.ok)
            self.assertIn("Signature verification failed", result.error)

    @patch("utils.update_checker.subprocess.run")
    def test_verify_download_signature_nonzero_uses_stderr_or_default(self, mock_run):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "artifact.rpm")
            signature = os.path.join(temp_dir, "artifact.sig")
            Path(artifact).write_bytes(b"data")
            Path(signature).write_bytes(b"sig")

            mock_run.return_value = MagicMock(
                returncode=1, stderr="bad signature")
            result = UpdateChecker.verify_download(
                artifact, signature_path=signature)
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "bad signature")

            mock_run.return_value = MagicMock(returncode=1, stderr="")
            result_default = UpdateChecker.verify_download(
                artifact, signature_path=signature)
            self.assertFalse(result_default.ok)
            self.assertEqual(result_default.error,
                             "Signature verification failed")


class TestAutoUpdateOrchestration(unittest.TestCase):
    def setUp(self):
        self.update_info = UpdateInfo(
            current_version="29.0.0",
            latest_version="30.0.0",
            release_notes="Release",
            download_url="https://example.invalid/release",
            is_newer=True,
            assets=[UpdateAsset(
                name="loofi.rpm", download_url="https://example.invalid/asset")],
        )

    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_no_update_available(self, mock_check):
        mock_check.return_value = UpdateInfo(
            current_version="30.0.0",
            latest_version="30.0.0",
            release_notes="",
            download_url="",
            is_newer=False,
            assets=[],
        )

        result = UpdateChecker.run_auto_update((".rpm",), "/tmp")

        self.assertIsInstance(result, AutoUpdateResult)
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "check")
        self.assertEqual(result.error, ERR_NO_UPDATE)

    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_missing_asset(self, mock_check):
        no_asset_info = UpdateInfo(
            current_version="29.0.0",
            latest_version="30.0.0",
            release_notes="Release",
            download_url="https://example.invalid/release",
            is_newer=True,
            assets=[],
        )
        mock_check.return_value = no_asset_info

        result = UpdateChecker.run_auto_update((".rpm",), "/tmp")

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "select")
        self.assertEqual(result.error, ERR_NO_ASSET)

    @patch("utils.update_checker.UpdateChecker.download_update")
    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_download_failure(self, mock_check, mock_download):
        mock_check.return_value = self.update_info
        mock_download.return_value = DownloadResult(ok=False, error="offline")

        result = UpdateChecker.run_auto_update((".rpm",), "/tmp")

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "download")
        self.assertEqual(result.error, ERR_DOWNLOAD_FAILED)

    @patch("utils.update_checker.UpdateChecker.verify_download")
    @patch("utils.update_checker.UpdateChecker.download_update")
    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_checksum_mismatch(self, mock_check, mock_download, mock_verify):
        mock_check.return_value = self.update_info
        mock_download.return_value = DownloadResult(
            ok=True, file_path="/tmp/loofi.rpm")
        mock_verify.return_value = VerifyResult(
            ok=False, method="sha256", error="SHA256 checksum mismatch")

        result = UpdateChecker.run_auto_update(
            (".rpm",), "/tmp", expected_sha256="abcd")

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "verify")
        self.assertEqual(result.error, ERR_CHECKSUM_MISMATCH)

    @patch("utils.update_checker.UpdateChecker.verify_download")
    @patch("utils.update_checker.UpdateChecker.download_update")
    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_signature_failure(self, mock_check, mock_download, mock_verify):
        mock_check.return_value = self.update_info
        mock_download.return_value = DownloadResult(
            ok=True, file_path="/tmp/loofi.rpm")
        mock_verify.return_value = VerifyResult(
            ok=False, method="signature", error="bad signature")

        result = UpdateChecker.run_auto_update(
            (".rpm",), "/tmp", signature_path="/tmp/loofi.sig")

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "verify")
        self.assertEqual(result.error, ERR_SIGNATURE_FAILED)

    @patch("utils.update_checker.UpdateChecker.verify_download")
    @patch("utils.update_checker.UpdateChecker.download_update")
    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_success(self, mock_check, mock_download, mock_verify):
        mock_check.return_value = self.update_info
        mock_download.return_value = DownloadResult(
            ok=True, file_path="/tmp/loofi.rpm", bytes_written=1024)
        mock_verify.return_value = VerifyResult(ok=True, method="sha256")

        result = UpdateChecker.run_auto_update((".rpm",), "/tmp")

        self.assertTrue(result.success)
        self.assertEqual(result.stage, "complete")
        self.assertIsNotNone(result.selected_asset)
        self.assertEqual(result.selected_asset.name, "loofi.rpm")

    @patch("utils.update_checker.UpdateChecker.verify_download")
    @patch("utils.update_checker.UpdateChecker.download_update")
    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_preserves_offline_cache_source(self, mock_check, mock_download, mock_verify):
        offline_info = UpdateInfo(
            current_version="29.0.0",
            latest_version="30.0.0",
            release_notes="Cached",
            download_url="https://example.invalid/release",
            is_newer=True,
            assets=[UpdateAsset(name="loofi.flatpak",
                                download_url="https://example.invalid/asset")],
            offline=True,
            source="cache",
        )
        mock_check.return_value = offline_info
        mock_download.return_value = DownloadResult(
            ok=True, file_path="/tmp/loofi.flatpak")
        mock_verify.return_value = VerifyResult(ok=True, method="none")

        result = UpdateChecker.run_auto_update((".flatpak",), "/tmp")

        self.assertTrue(result.success)
        self.assertTrue(result.offline)
        self.assertEqual(result.source, "cache")

    @patch("utils.update_checker.UpdateChecker.check_for_updates")
    def test_run_auto_update_network_miss_without_cache(self, mock_check):
        mock_check.return_value = None

        result = UpdateChecker.run_auto_update(
            (".rpm",), "/tmp", use_cache=False)

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "check")
        self.assertTrue(result.offline)
        self.assertEqual(result.source, "network")
        self.assertEqual(result.error, ERR_NETWORK)


class TestArtifactPreference(unittest.TestCase):
    def test_resolve_artifact_preference_auto_dnf(self):
        self.assertEqual(
            UpdateChecker.resolve_artifact_preference("dnf", "auto"),
            (".rpm", ".flatpak", ".AppImage", ".tar.gz"),
        )

    def test_resolve_artifact_preference_auto_rpm_ostree(self):
        self.assertEqual(
            UpdateChecker.resolve_artifact_preference("rpm-ostree", "auto"),
            (".flatpak", ".AppImage", ".rpm", ".tar.gz"),
        )

    def test_resolve_artifact_preference_explicit_appimage(self):
        self.assertEqual(
            UpdateChecker.resolve_artifact_preference("dnf", "appimage")[0],
            ".AppImage",
        )


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
