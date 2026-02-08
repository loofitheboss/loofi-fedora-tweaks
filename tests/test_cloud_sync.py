"""
Tests for CloudSyncManager - Cloud sync and community presets.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import urllib.error

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.cloud_sync import CloudSyncManager


class TestCloudSyncDirectories(unittest.TestCase):
    """Tests for directory management."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = CloudSyncManager.CONFIG_DIR
        self.original_cache_dir = CloudSyncManager.CACHE_DIR
        self.original_token_file = CloudSyncManager.TOKEN_FILE
        self.original_gist_id_file = CloudSyncManager.GIST_ID_FILE

        # Override paths
        CloudSyncManager.CONFIG_DIR = Path(self.temp_dir) / "config"
        CloudSyncManager.CACHE_DIR = CloudSyncManager.CONFIG_DIR / "cache"
        CloudSyncManager.TOKEN_FILE = CloudSyncManager.CONFIG_DIR / ".gist_token"
        CloudSyncManager.GIST_ID_FILE = CloudSyncManager.CONFIG_DIR / ".gist_id"

    def tearDown(self):
        """Restore original paths and clean up."""
        CloudSyncManager.CONFIG_DIR = self.original_config_dir
        CloudSyncManager.CACHE_DIR = self.original_cache_dir
        CloudSyncManager.TOKEN_FILE = self.original_token_file
        CloudSyncManager.GIST_ID_FILE = self.original_gist_id_file

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_dirs_creates_config_dir(self):
        """ensure_dirs creates the config directory."""
        self.assertFalse(CloudSyncManager.CONFIG_DIR.exists())
        CloudSyncManager.ensure_dirs()
        self.assertTrue(CloudSyncManager.CONFIG_DIR.exists())

    def test_ensure_dirs_creates_cache_dir(self):
        """ensure_dirs creates the cache directory."""
        self.assertFalse(CloudSyncManager.CACHE_DIR.exists())
        CloudSyncManager.ensure_dirs()
        self.assertTrue(CloudSyncManager.CACHE_DIR.exists())


class TestGistTokenManagement(unittest.TestCase):
    """Tests for Gist token storage."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = CloudSyncManager.CONFIG_DIR
        self.original_cache_dir = CloudSyncManager.CACHE_DIR
        self.original_token_file = CloudSyncManager.TOKEN_FILE
        self.original_gist_id_file = CloudSyncManager.GIST_ID_FILE

        CloudSyncManager.CONFIG_DIR = Path(self.temp_dir) / "config"
        CloudSyncManager.CACHE_DIR = CloudSyncManager.CONFIG_DIR / "cache"
        CloudSyncManager.TOKEN_FILE = CloudSyncManager.CONFIG_DIR / ".gist_token"
        CloudSyncManager.GIST_ID_FILE = CloudSyncManager.CONFIG_DIR / ".gist_id"

    def tearDown(self):
        """Restore original paths and clean up."""
        CloudSyncManager.CONFIG_DIR = self.original_config_dir
        CloudSyncManager.CACHE_DIR = self.original_cache_dir
        CloudSyncManager.TOKEN_FILE = self.original_token_file
        CloudSyncManager.GIST_ID_FILE = self.original_gist_id_file

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_gist_token_returns_none_when_missing(self):
        """get_gist_token returns None when no token file exists."""
        result = CloudSyncManager.get_gist_token()
        self.assertIsNone(result)

    def test_save_and_get_gist_token(self):
        """save_gist_token stores token and get_gist_token retrieves it."""
        token = "ghp_test_token_12345"
        result = CloudSyncManager.save_gist_token(token)
        self.assertTrue(result)

        retrieved = CloudSyncManager.get_gist_token()
        self.assertEqual(retrieved, token)

    def test_save_gist_token_sets_permissions(self):
        """save_gist_token sets restrictive file permissions."""
        CloudSyncManager.save_gist_token("test_token")
        mode = oct(CloudSyncManager.TOKEN_FILE.stat().st_mode)[-3:]
        self.assertEqual(mode, "600")

    def test_clear_gist_token(self):
        """clear_gist_token removes token and gist ID files."""
        CloudSyncManager.save_gist_token("test_token")
        CloudSyncManager.save_gist_id("abc123")

        result = CloudSyncManager.clear_gist_token()
        self.assertTrue(result)
        self.assertFalse(CloudSyncManager.TOKEN_FILE.exists())
        self.assertFalse(CloudSyncManager.GIST_ID_FILE.exists())


class TestGistIdManagement(unittest.TestCase):
    """Tests for Gist ID storage."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = CloudSyncManager.CONFIG_DIR
        self.original_cache_dir = CloudSyncManager.CACHE_DIR
        self.original_token_file = CloudSyncManager.TOKEN_FILE
        self.original_gist_id_file = CloudSyncManager.GIST_ID_FILE

        CloudSyncManager.CONFIG_DIR = Path(self.temp_dir) / "config"
        CloudSyncManager.CACHE_DIR = CloudSyncManager.CONFIG_DIR / "cache"
        CloudSyncManager.TOKEN_FILE = CloudSyncManager.CONFIG_DIR / ".gist_token"
        CloudSyncManager.GIST_ID_FILE = CloudSyncManager.CONFIG_DIR / ".gist_id"

    def tearDown(self):
        """Restore original paths and clean up."""
        CloudSyncManager.CONFIG_DIR = self.original_config_dir
        CloudSyncManager.CACHE_DIR = self.original_cache_dir
        CloudSyncManager.TOKEN_FILE = self.original_token_file
        CloudSyncManager.GIST_ID_FILE = self.original_gist_id_file

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_gist_id_returns_none_when_missing(self):
        """get_gist_id returns None when no gist ID file exists."""
        result = CloudSyncManager.get_gist_id()
        self.assertIsNone(result)

    def test_save_and_get_gist_id(self):
        """save_gist_id stores ID and get_gist_id retrieves it."""
        gist_id = "abc123def456"
        result = CloudSyncManager.save_gist_id(gist_id)
        self.assertTrue(result)

        retrieved = CloudSyncManager.get_gist_id()
        self.assertEqual(retrieved, gist_id)


class TestSyncToGist(unittest.TestCase):
    """Tests for syncing configuration to Gist."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = CloudSyncManager.CONFIG_DIR
        self.original_cache_dir = CloudSyncManager.CACHE_DIR
        self.original_token_file = CloudSyncManager.TOKEN_FILE
        self.original_gist_id_file = CloudSyncManager.GIST_ID_FILE

        CloudSyncManager.CONFIG_DIR = Path(self.temp_dir) / "config"
        CloudSyncManager.CACHE_DIR = CloudSyncManager.CONFIG_DIR / "cache"
        CloudSyncManager.TOKEN_FILE = CloudSyncManager.CONFIG_DIR / ".gist_token"
        CloudSyncManager.GIST_ID_FILE = CloudSyncManager.CONFIG_DIR / ".gist_id"

    def tearDown(self):
        """Restore original paths and clean up."""
        CloudSyncManager.CONFIG_DIR = self.original_config_dir
        CloudSyncManager.CACHE_DIR = self.original_cache_dir
        CloudSyncManager.TOKEN_FILE = self.original_token_file
        CloudSyncManager.GIST_ID_FILE = self.original_gist_id_file

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sync_to_gist_fails_without_token(self):
        """sync_to_gist fails when no token is configured."""
        config = {"test": "data"}
        success, message = CloudSyncManager.sync_to_gist(config)
        self.assertFalse(success)
        self.assertIn("token", message.lower())

    @patch('urllib.request.urlopen')
    def test_sync_to_gist_creates_new_gist(self, mock_urlopen):
        """sync_to_gist creates a new gist when no gist_id exists."""
        CloudSyncManager.save_gist_token("test_token")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"id": "new_gist_123"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        config = {"test": "data"}
        success, message = CloudSyncManager.sync_to_gist(config)

        self.assertTrue(success)
        self.assertIn("new_gist_123", message)

    @patch('urllib.request.urlopen')
    def test_sync_to_gist_updates_existing_gist(self, mock_urlopen):
        """sync_to_gist updates existing gist when gist_id exists."""
        CloudSyncManager.save_gist_token("test_token")
        CloudSyncManager.save_gist_id("existing_gist_456")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"id": "existing_gist_456"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        config = {"test": "data"}
        success, message = CloudSyncManager.sync_to_gist(config)

        self.assertTrue(success)

    @patch('urllib.request.urlopen')
    def test_sync_to_gist_handles_401_error(self, mock_urlopen):
        """sync_to_gist handles invalid token error."""
        CloudSyncManager.save_gist_token("invalid_token")

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs={}, fp=None
        )

        config = {"test": "data"}
        success, message = CloudSyncManager.sync_to_gist(config)

        self.assertFalse(success)
        self.assertIn("Invalid", message)


class TestSyncFromGist(unittest.TestCase):
    """Tests for downloading configuration from Gist."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = CloudSyncManager.CONFIG_DIR
        self.original_cache_dir = CloudSyncManager.CACHE_DIR
        self.original_token_file = CloudSyncManager.TOKEN_FILE
        self.original_gist_id_file = CloudSyncManager.GIST_ID_FILE

        CloudSyncManager.CONFIG_DIR = Path(self.temp_dir) / "config"
        CloudSyncManager.CACHE_DIR = CloudSyncManager.CONFIG_DIR / "cache"
        CloudSyncManager.TOKEN_FILE = CloudSyncManager.CONFIG_DIR / ".gist_token"
        CloudSyncManager.GIST_ID_FILE = CloudSyncManager.CONFIG_DIR / ".gist_id"

    def tearDown(self):
        """Restore original paths and clean up."""
        CloudSyncManager.CONFIG_DIR = self.original_config_dir
        CloudSyncManager.CACHE_DIR = self.original_cache_dir
        CloudSyncManager.TOKEN_FILE = self.original_token_file
        CloudSyncManager.GIST_ID_FILE = self.original_gist_id_file

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sync_from_gist_fails_without_gist_id(self):
        """sync_from_gist fails when no gist ID is provided or stored."""
        success, message = CloudSyncManager.sync_from_gist()
        self.assertFalse(success)
        self.assertIn("Gist ID", message)

    @patch('urllib.request.urlopen')
    def test_sync_from_gist_fetches_config(self, mock_urlopen):
        """sync_from_gist successfully fetches configuration."""
        config_content = {"key": "value", "setting": True}
        gist_data = {
            "files": {
                "loofi-fedora-tweaks-config.json": {
                    "content": json.dumps(config_content)
                }
            }
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(gist_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        success, result = CloudSyncManager.sync_from_gist("test_gist_id")

        self.assertTrue(success)
        self.assertEqual(result, config_content)

    @patch('urllib.request.urlopen')
    def test_sync_from_gist_handles_missing_config_file(self, mock_urlopen):
        """sync_from_gist fails when gist doesn't contain config file."""
        gist_data = {"files": {"other_file.txt": {"content": "text"}}}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(gist_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        success, message = CloudSyncManager.sync_from_gist("test_gist_id")

        self.assertFalse(success)
        self.assertIn("valid config", message.lower())

    @patch('urllib.request.urlopen')
    def test_sync_from_gist_handles_404_error(self, mock_urlopen):
        """sync_from_gist handles gist not found error."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs={}, fp=None
        )

        success, message = CloudSyncManager.sync_from_gist("nonexistent_id")

        self.assertFalse(success)
        self.assertIn("not found", message.lower())


class TestCommunityPresets(unittest.TestCase):
    """Tests for community preset fetching."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = CloudSyncManager.CONFIG_DIR
        self.original_cache_dir = CloudSyncManager.CACHE_DIR
        self.original_token_file = CloudSyncManager.TOKEN_FILE
        self.original_gist_id_file = CloudSyncManager.GIST_ID_FILE

        CloudSyncManager.CONFIG_DIR = Path(self.temp_dir) / "config"
        CloudSyncManager.CACHE_DIR = CloudSyncManager.CONFIG_DIR / "cache"
        CloudSyncManager.TOKEN_FILE = CloudSyncManager.CONFIG_DIR / ".gist_token"
        CloudSyncManager.GIST_ID_FILE = CloudSyncManager.CONFIG_DIR / ".gist_id"

    def tearDown(self):
        """Restore original paths and clean up."""
        CloudSyncManager.CONFIG_DIR = self.original_config_dir
        CloudSyncManager.CACHE_DIR = self.original_cache_dir
        CloudSyncManager.TOKEN_FILE = self.original_token_file
        CloudSyncManager.GIST_ID_FILE = self.original_gist_id_file

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('urllib.request.urlopen')
    def test_fetch_community_presets_success(self, mock_urlopen):
        """fetch_community_presets returns list of presets."""
        presets = [
            {"id": "preset1", "name": "Gaming"},
            {"id": "preset2", "name": "Privacy"}
        ]

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(presets).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        success, result = CloudSyncManager.fetch_community_presets(use_cache=False)

        self.assertTrue(success)
        self.assertEqual(len(result), 2)

    @patch('urllib.request.urlopen')
    def test_fetch_community_presets_returns_empty_on_404(self, mock_urlopen):
        """fetch_community_presets returns empty list when repo doesn't exist."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs={}, fp=None
        )

        success, result = CloudSyncManager.fetch_community_presets(use_cache=False)

        self.assertTrue(success)
        self.assertEqual(result, [])


class TestDownloadPreset(unittest.TestCase):
    """Tests for preset downloading."""

    @patch('urllib.request.urlopen')
    def test_download_preset_success(self, mock_urlopen):
        """download_preset successfully downloads a preset."""
        preset_data = {"name": "Test Preset", "config": {}}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(preset_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        success, result = CloudSyncManager.download_preset("test_preset")

        self.assertTrue(success)
        self.assertEqual(result, preset_data)

    @patch('urllib.request.urlopen')
    def test_download_preset_not_found(self, mock_urlopen):
        """download_preset handles preset not found."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs={}, fp=None
        )

        success, message = CloudSyncManager.download_preset("nonexistent")

        self.assertFalse(success)
        self.assertIn("not found", message.lower())


class TestIsOnline(unittest.TestCase):
    """Tests for online check."""

    @patch('urllib.request.urlopen')
    def test_is_online_returns_true_when_connected(self, mock_urlopen):
        """is_online returns True when network is available."""
        mock_response = MagicMock()
        mock_urlopen.return_value = mock_response

        result = CloudSyncManager.is_online()
        self.assertTrue(result)

    @patch('urllib.request.urlopen')
    def test_is_online_returns_false_on_error(self, mock_urlopen):
        """is_online returns False when network is unavailable."""
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        result = CloudSyncManager.is_online()
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
