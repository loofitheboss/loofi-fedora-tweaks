"""
Tests for PresetMarketplace - Community preset sharing via GitHub.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error
from datetime import datetime

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.marketplace import PresetMarketplace, CommunityPreset, MarketplaceResult


class TestCommunityPresetDataclass(unittest.TestCase):
    """Tests for CommunityPreset dataclass."""

    def test_from_dict_creates_preset(self):
        """from_dict creates a CommunityPreset from dictionary."""
        data = {
            "id": "test-preset",
            "name": "Test Preset",
            "author": "TestUser",
            "description": "A test preset",
            "category": "gaming",
            "download_count": 100,
            "stars": 50,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-15",
            "download_url": "https://example.com/preset.json",
            "tags": ["gaming", "performance"]
        }
        preset = CommunityPreset.from_dict(data)

        self.assertEqual(preset.id, "test-preset")
        self.assertEqual(preset.name, "Test Preset")
        self.assertEqual(preset.author, "TestUser")
        self.assertEqual(preset.category, "gaming")
        self.assertEqual(preset.download_count, 100)
        self.assertEqual(preset.stars, 50)
        self.assertEqual(len(preset.tags), 2)

    def test_from_dict_with_missing_fields(self):
        """from_dict handles missing fields with defaults."""
        data = {"id": "minimal"}
        preset = CommunityPreset.from_dict(data)

        self.assertEqual(preset.id, "minimal")
        self.assertEqual(preset.name, "Unknown")
        self.assertEqual(preset.author, "Anonymous")
        self.assertEqual(preset.category, "general")
        self.assertEqual(preset.download_count, 0)
        self.assertEqual(preset.tags, [])


class TestMarketplaceResult(unittest.TestCase):
    """Tests for MarketplaceResult dataclass."""

    def test_result_success(self):
        """MarketplaceResult stores success state."""
        result = MarketplaceResult(True, "Success message", {"key": "value"})
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Success message")
        self.assertEqual(result.data, {"key": "value"})

    def test_result_failure(self):
        """MarketplaceResult stores failure state."""
        result = MarketplaceResult(False, "Error message")
        self.assertFalse(result.success)
        self.assertIsNone(result.data)


class TestPresetMarketplaceInit(unittest.TestCase):
    """Tests for PresetMarketplace initialization."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_dir = PresetMarketplace.CACHE_DIR
        self.original_index_cache = PresetMarketplace.INDEX_CACHE

        PresetMarketplace.CACHE_DIR = Path(self.temp_dir) / "marketplace"
        PresetMarketplace.INDEX_CACHE = PresetMarketplace.CACHE_DIR / "index.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        PresetMarketplace.CACHE_DIR = self.original_cache_dir
        PresetMarketplace.INDEX_CACHE = self.original_index_cache

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_cache_directory(self):
        """__init__ creates the cache directory."""
        self.assertFalse(PresetMarketplace.CACHE_DIR.exists())
        market = PresetMarketplace()
        self.assertTrue(PresetMarketplace.CACHE_DIR.exists())


class TestFetchIndex(unittest.TestCase):
    """Tests for fetch_index method."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_dir = PresetMarketplace.CACHE_DIR
        self.original_index_cache = PresetMarketplace.INDEX_CACHE

        PresetMarketplace.CACHE_DIR = Path(self.temp_dir) / "marketplace"
        PresetMarketplace.INDEX_CACHE = PresetMarketplace.CACHE_DIR / "index.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        PresetMarketplace.CACHE_DIR = self.original_cache_dir
        PresetMarketplace.INDEX_CACHE = self.original_index_cache

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('urllib.request.urlopen')
    def test_fetch_index_success(self, mock_urlopen):
        """fetch_index fetches presets from GitHub."""
        presets_data = {
            "presets": [
                {"id": "preset1", "name": "Preset 1"},
                {"id": "preset2", "name": "Preset 2"}
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(presets_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        market = PresetMarketplace()
        result = market.fetch_index(force_refresh=True)

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)

    @patch('urllib.request.urlopen')
    def test_fetch_index_caches_result(self, mock_urlopen):
        """fetch_index caches the fetched index."""
        presets_data = {"presets": [{"id": "test"}]}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(presets_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        market = PresetMarketplace()
        market.fetch_index(force_refresh=True)

        self.assertTrue(PresetMarketplace.INDEX_CACHE.exists())

    @patch('urllib.request.urlopen')
    def test_fetch_index_returns_empty_on_404(self, mock_urlopen):
        """fetch_index returns empty list when marketplace doesn't exist."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs={}, fp=None
        )

        market = PresetMarketplace()
        result = market.fetch_index(force_refresh=True)

        self.assertTrue(result.success)
        self.assertEqual(result.data, [])

    @patch('urllib.request.urlopen')
    def test_fetch_index_handles_http_error(self, mock_urlopen):
        """fetch_index handles HTTP errors."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=500, msg="Server Error", hdrs={}, fp=None
        )

        market = PresetMarketplace()
        result = market.fetch_index(force_refresh=True)

        self.assertFalse(result.success)
        self.assertIn("500", result.message)

    @patch('urllib.request.urlopen')
    def test_fetch_index_handles_url_error(self, mock_urlopen):
        """fetch_index handles URL/network errors."""
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        market = PresetMarketplace()
        result = market.fetch_index(force_refresh=True)

        self.assertFalse(result.success)
        self.assertIn("Network", result.message)


class TestDownloadPreset(unittest.TestCase):
    """Tests for download_preset method."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_dir = PresetMarketplace.CACHE_DIR
        self.original_index_cache = PresetMarketplace.INDEX_CACHE

        PresetMarketplace.CACHE_DIR = Path(self.temp_dir) / "marketplace"
        PresetMarketplace.INDEX_CACHE = PresetMarketplace.CACHE_DIR / "index.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        PresetMarketplace.CACHE_DIR = self.original_cache_dir
        PresetMarketplace.INDEX_CACHE = self.original_index_cache

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('urllib.request.urlopen')
    def test_download_preset_success(self, mock_urlopen):
        """download_preset downloads and saves preset."""
        preset_content = {"config": {"key": "value"}}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(preset_content).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        preset = CommunityPreset(
            id="test-preset",
            name="Test Preset",
            author="Test",
            description="Test",
            category="general",
            download_count=0,
            stars=0,
            created_at="",
            updated_at="",
            download_url="https://example.com/preset.json",
            tags=[]
        )

        market = PresetMarketplace()
        result = market.download_preset(preset)

        self.assertTrue(result.success)
        self.assertIn("Downloaded", result.message)
        self.assertEqual(result.data["data"], preset_content)

    @patch('urllib.request.urlopen')
    def test_download_preset_handles_error(self, mock_urlopen):
        """download_preset handles download errors."""
        mock_urlopen.side_effect = Exception("Download failed")

        preset = CommunityPreset.from_dict({
            "id": "test",
            "download_url": "https://example.com/preset.json"
        })

        market = PresetMarketplace()
        result = market.download_preset(preset)

        self.assertFalse(result.success)
        self.assertIn("failed", result.message.lower())


class TestSearchPresets(unittest.TestCase):
    """Tests for search_presets method."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_dir = PresetMarketplace.CACHE_DIR
        self.original_index_cache = PresetMarketplace.INDEX_CACHE

        PresetMarketplace.CACHE_DIR = Path(self.temp_dir) / "marketplace"
        PresetMarketplace.INDEX_CACHE = PresetMarketplace.CACHE_DIR / "index.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        PresetMarketplace.CACHE_DIR = self.original_cache_dir
        PresetMarketplace.INDEX_CACHE = self.original_index_cache

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.object(PresetMarketplace, 'fetch_index')
    def test_search_by_query(self, mock_fetch):
        """search_presets filters by query string."""
        presets = [
            CommunityPreset.from_dict({"id": "gaming", "name": "Gaming Preset", "description": "For gamers", "tags": []}),
            CommunityPreset.from_dict({"id": "privacy", "name": "Privacy Preset", "description": "For privacy", "tags": []}),
        ]
        mock_fetch.return_value = MarketplaceResult(True, "OK", presets)

        market = PresetMarketplace()
        result = market.search_presets(query="gaming")

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].id, "gaming")

    @patch.object(PresetMarketplace, 'fetch_index')
    def test_search_by_category(self, mock_fetch):
        """search_presets filters by category."""
        presets = [
            CommunityPreset.from_dict({"id": "p1", "name": "P1", "category": "gaming", "tags": []}),
            CommunityPreset.from_dict({"id": "p2", "name": "P2", "category": "privacy", "tags": []}),
        ]
        mock_fetch.return_value = MarketplaceResult(True, "OK", presets)

        market = PresetMarketplace()
        result = market.search_presets(category="privacy")

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].id, "p2")

    @patch.object(PresetMarketplace, 'fetch_index')
    def test_search_by_tag(self, mock_fetch):
        """search_presets filters by tags."""
        presets = [
            CommunityPreset.from_dict({"id": "p1", "name": "P1", "tags": ["performance", "fps"]}),
            CommunityPreset.from_dict({"id": "p2", "name": "P2", "tags": ["minimal"]}),
        ]
        mock_fetch.return_value = MarketplaceResult(True, "OK", presets)

        market = PresetMarketplace()
        result = market.search_presets(query="fps")

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].id, "p1")

    @patch.object(PresetMarketplace, 'fetch_index')
    def test_search_handles_fetch_error(self, mock_fetch):
        """search_presets propagates fetch errors."""
        mock_fetch.return_value = MarketplaceResult(False, "Network error")

        market = PresetMarketplace()
        result = market.search_presets(query="test")

        self.assertFalse(result.success)


class TestGetCategories(unittest.TestCase):
    """Tests for get_categories method."""

    def test_get_categories_returns_list(self):
        """get_categories returns a list of category strings."""
        market = PresetMarketplace()
        categories = market.get_categories()

        self.assertIsInstance(categories, list)
        self.assertIn("gaming", categories)
        self.assertIn("privacy", categories)
        self.assertIn("performance", categories)
        self.assertIn("minimal", categories)


class TestGetFeatured(unittest.TestCase):
    """Tests for get_featured method."""

    @patch.object(PresetMarketplace, 'fetch_index')
    def test_get_featured_sorts_by_popularity(self, mock_fetch):
        """get_featured returns presets sorted by popularity."""
        presets = [
            CommunityPreset.from_dict({"id": "p1", "stars": 10, "download_count": 10}),
            CommunityPreset.from_dict({"id": "p2", "stars": 100, "download_count": 100}),
            CommunityPreset.from_dict({"id": "p3", "stars": 50, "download_count": 50}),
        ]
        mock_fetch.return_value = MarketplaceResult(True, "OK", presets)

        market = PresetMarketplace()
        result = market.get_featured()

        self.assertTrue(result.success)
        self.assertEqual(result.data[0].id, "p2")  # Most popular first
        self.assertEqual(result.data[1].id, "p3")

    @patch.object(PresetMarketplace, 'fetch_index')
    def test_get_featured_limits_to_10(self, mock_fetch):
        """get_featured returns at most 10 presets."""
        presets = [CommunityPreset.from_dict({"id": f"p{i}"}) for i in range(20)]
        mock_fetch.return_value = MarketplaceResult(True, "OK", presets)

        market = PresetMarketplace()
        result = market.get_featured()

        self.assertTrue(result.success)
        self.assertLessEqual(len(result.data), 10)


class TestCacheValidity(unittest.TestCase):
    """Tests for cache validity checking."""

    def setUp(self):
        """Set up temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_dir = PresetMarketplace.CACHE_DIR
        self.original_index_cache = PresetMarketplace.INDEX_CACHE

        PresetMarketplace.CACHE_DIR = Path(self.temp_dir) / "marketplace"
        PresetMarketplace.INDEX_CACHE = PresetMarketplace.CACHE_DIR / "index.json"

    def tearDown(self):
        """Restore original paths and clean up."""
        PresetMarketplace.CACHE_DIR = self.original_cache_dir
        PresetMarketplace.INDEX_CACHE = self.original_index_cache

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_not_valid_when_missing(self):
        """_is_cache_valid returns False when cache doesn't exist."""
        market = PresetMarketplace()
        self.assertFalse(market._is_cache_valid())

    def test_cache_valid_when_recent(self):
        """_is_cache_valid returns True when cache is fresh."""
        market = PresetMarketplace()

        # Create a fresh cache file
        with open(PresetMarketplace.INDEX_CACHE, "w") as f:
            json.dump({"presets": []}, f)

        self.assertTrue(market._is_cache_valid())


if __name__ == '__main__':
    unittest.main()
