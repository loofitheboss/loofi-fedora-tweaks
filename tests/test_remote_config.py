"""Tests for utils/remote_config.py — AppConfigFetcher."""
import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.remote_config import AppConfigFetcher


class TestAppConfigFetcherInit(unittest.TestCase):
    """Tests for AppConfigFetcher initialization."""

    @patch('utils.remote_config.QThread.__init__')
    def test_default_no_force(self, mock_init):
        mock_init.return_value = None
        fetcher = AppConfigFetcher()
        self.assertFalse(fetcher.force_refresh)

    @patch('utils.remote_config.QThread.__init__')
    def test_force_refresh(self, mock_init):
        mock_init.return_value = None
        fetcher = AppConfigFetcher(force_refresh=True)
        self.assertTrue(fetcher.force_refresh)


class TestAppConfigFetcherClassAttrs(unittest.TestCase):
    """Tests for class-level constants."""

    def test_remote_url(self):
        self.assertIn("github", AppConfigFetcher.REMOTE_URL)
        self.assertTrue(AppConfigFetcher.REMOTE_URL.startswith("https://"))

    def test_cache_dir(self):
        self.assertIn("loofi-fedora-tweaks", AppConfigFetcher.CACHE_DIR)

    def test_cache_file(self):
        self.assertTrue(AppConfigFetcher.CACHE_FILE.endswith("apps.json"))

    def test_local_fallback(self):
        self.assertIn("config", AppConfigFetcher.LOCAL_FALLBACK)


class TestAppConfigFetcherRunRemote(unittest.TestCase):
    """Tests for run() — remote fetch path."""

    @patch('utils.remote_config.QThread.__init__')
    def setUp(self, mock_init):
        mock_init.return_value = None
        self.fetcher = AppConfigFetcher(force_refresh=True)
        self.fetcher.config_ready = MagicMock()
        self.fetcher.config_error = MagicMock()

    @patch.object(AppConfigFetcher, '_save_cache')
    @patch('utils.remote_config.urllib.request.urlopen')
    def test_remote_success(self, mock_urlopen, mock_save):
        test_data = [{"name": "firefox", "pkg": "firefox"}]
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps(test_data).encode()
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = response

        self.fetcher.run()

        self.fetcher.config_ready.emit.assert_called_once_with(test_data)
        mock_save.assert_called_once_with(test_data)
        self.fetcher.config_error.emit.assert_not_called()


class TestAppConfigFetcherRunCache(unittest.TestCase):
    """Tests for run() — cache fallback path."""

    @patch('utils.remote_config.QThread.__init__')
    def setUp(self, mock_init):
        mock_init.return_value = None
        self.fetcher = AppConfigFetcher(force_refresh=False)
        self.fetcher.config_ready = MagicMock()
        self.fetcher.config_error = MagicMock()

    @patch('builtins.open', new_callable=mock_open, read_data='[{"name":"vim"}]')
    @patch('utils.remote_config.os.path.exists')
    def test_cache_hit(self, mock_exists, mock_file):
        mock_exists.side_effect = lambda p: p == self.fetcher.CACHE_FILE

        self.fetcher.run()

        self.fetcher.config_ready.emit.assert_called_once()
        emitted = self.fetcher.config_ready.emit.call_args[0][0]
        self.assertEqual(emitted[0]["name"], "vim")


class TestAppConfigFetcherRunFallback(unittest.TestCase):
    """Tests for run() — local fallback path."""

    @patch('utils.remote_config.QThread.__init__')
    def setUp(self, mock_init):
        mock_init.return_value = None
        self.fetcher = AppConfigFetcher(force_refresh=False)
        self.fetcher.config_ready = MagicMock()
        self.fetcher.config_error = MagicMock()

    @patch('builtins.open', new_callable=mock_open, read_data='[{"name":"nano"}]')
    @patch('utils.remote_config.os.path.exists')
    def test_local_fallback(self, mock_exists, mock_file):
        def exists_side_effect(path):
            if path == self.fetcher.CACHE_FILE:
                return False
            if path == self.fetcher.LOCAL_FALLBACK:
                return True
            return False
        mock_exists.side_effect = exists_side_effect

        self.fetcher.run()

        self.fetcher.config_ready.emit.assert_called_once()

    @patch('utils.remote_config.os.path.exists', return_value=False)
    def test_no_source_emits_error(self, mock_exists):
        self.fetcher.run()
        self.fetcher.config_error.emit.assert_called_once()


class TestAppConfigFetcherSaveCache(unittest.TestCase):
    """Tests for _save_cache."""

    @patch('utils.remote_config.QThread.__init__')
    def setUp(self, mock_init):
        mock_init.return_value = None
        self.fetcher = AppConfigFetcher()
        self.fetcher.config_ready = MagicMock()
        self.fetcher.config_error = MagicMock()

    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.remote_config.os.makedirs')
    def test_save_creates_dir_and_writes(self, mock_makedirs, mock_file):
        data = [{"name": "test"}]
        self.fetcher._save_cache(data)
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()

    @patch('builtins.open', side_effect=OSError("permission denied"))
    @patch('utils.remote_config.os.makedirs')
    def test_save_handles_error(self, mock_makedirs, mock_file):
        self.fetcher._save_cache([{"x": 1}])


if __name__ == "__main__":
    unittest.main()
