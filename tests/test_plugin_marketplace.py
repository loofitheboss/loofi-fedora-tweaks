"""Tests for utils.plugin_marketplace — PluginMarketplace GitHub API."""
import os
import sys
import json
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_marketplace import (
    PluginMarketplace,
    PluginMetadata,
    MarketplaceResult,
    DEFAULT_REPO_OWNER,
    DEFAULT_REPO_NAME,
    DEFAULT_BRANCH
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin_entry(plugin_id: str = "test-plugin") -> dict:
    """Create a valid plugin entry dict."""
    return {
        "id": plugin_id,
        "name": plugin_id.replace("-", " ").title(),
        "description": f"Description for {plugin_id}",
        "version": "1.0.0",
        "author": "Test Author",
        "category": "Utility",
        "icon": "🔌",
        "download_url": f"https://example.com/{plugin_id}.tar.gz",
        "checksum_sha256": "a" * 64,
        "featured": False,
        "tags": ["test"],
        "requires": []
    }


def _make_index_json(plugin_entries: list) -> dict:
    """Create marketplace index JSON."""
    return {
        "version": "1.0",
        "plugins": plugin_entries
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginMarketplaceInitialization:
    """Tests for PluginMarketplace construction."""

    def test_marketplace_uses_default_repo(self):
        """Marketplace uses default GitHub repo."""
        mp = PluginMarketplace()
        assert mp.repo_owner == DEFAULT_REPO_OWNER
        assert mp.repo_name == DEFAULT_REPO_NAME
        assert mp.branch == DEFAULT_BRANCH

    def test_marketplace_accepts_custom_repo(self):
        """Marketplace accepts custom repo settings."""
        mp = PluginMarketplace(
            repo_owner="custom-owner",
            repo_name="custom-repo",
            branch="develop"
        )
        assert mp.repo_owner == "custom-owner"
        assert mp.repo_name == "custom-repo"
        assert mp.branch == "develop"

    def test_marketplace_sets_base_url(self):
        """Marketplace constructs correct GitHub raw URL."""
        mp = PluginMarketplace()
        expected = f"https://raw.githubusercontent.com/{DEFAULT_REPO_OWNER}/{DEFAULT_REPO_NAME}/{DEFAULT_BRANCH}"
        assert mp.base_url == expected

    def test_marketplace_initializes_empty_cache(self):
        """Marketplace starts with no cached data."""
        mp = PluginMarketplace()
        assert mp._cache is None


class TestPluginMarketplaceFetchJson:
    """Tests for _fetch_json() internal method."""

    @patch('urllib.request.urlopen')
    def test_fetch_json_returns_parsed_dict(self, mock_urlopen):
        """_fetch_json() parses valid JSON response."""
        test_data = {"key": "value"}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(test_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        mp = PluginMarketplace()
        result = mp._fetch_json("https://example.com/test.json")
        
        assert result == test_data

    @patch('urllib.request.urlopen')
    def test_fetch_json_handles_http_error(self, mock_urlopen):
        """_fetch_json() returns None on HTTP error."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 404, "Not Found", {}, None
        )
        
        mp = PluginMarketplace()
        result = mp._fetch_json("https://example.com/404.json")
        
        assert result is None

    @patch('urllib.request.urlopen')
    def test_fetch_json_handles_url_error(self, mock_urlopen):
        """_fetch_json() returns None on network error."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")
        
        mp = PluginMarketplace()
        result = mp._fetch_json("https://example.com/fail.json")
        
        assert result is None

    @patch('urllib.request.urlopen')
    def test_fetch_json_handles_malformed_json(self, mock_urlopen):
        """_fetch_json() returns None on JSON decode error."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{ invalid json }"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        mp = PluginMarketplace()
        result = mp._fetch_json("https://example.com/bad.json")
        
        assert result is None

    @patch('urllib.request.urlopen')
    def test_fetch_json_sets_user_agent(self, mock_urlopen):
        """_fetch_json() sets User-Agent header."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        mp = PluginMarketplace()
        mp._fetch_json("https://example.com/test.json")
        
        # Check that Request was called with headers containing User-Agent
        # urllib may canonicalize the header name
        call_args = mock_urlopen.call_args[0][0]
        # Check both cases since urllib may change the case
        assert hasattr(call_args, 'headers')
        # urllib canonicalizes header to 'User-agent'
        header_keys_lower = {k.lower() for k in call_args.headers}
        assert 'user-agent' in header_keys_lower


class TestPluginMarketplaceParseEntry:
    """Tests for _parse_plugin_entry() validation."""

    def test_parse_valid_entry(self):
        """_parse_plugin_entry() accepts valid entry."""
        mp = PluginMarketplace()
        entry = _make_plugin_entry("test-plugin")
        
        metadata = mp._parse_plugin_entry(entry)
        
        assert metadata is not None
        assert metadata.id == "test-plugin"
        assert metadata.name == "Test Plugin"

    def test_parse_rejects_missing_required_field(self):
        """_parse_plugin_entry() rejects entry missing required fields."""
        mp = PluginMarketplace()
        incomplete = {
            "id": "incomplete",
            "name": "Incomplete"
            # Missing description, version, author, etc.
        }
        
        metadata = mp._parse_plugin_entry(incomplete)
        
        assert metadata is None

    def test_parse_uses_default_icon(self):
        """_parse_plugin_entry() uses default icon if missing."""
        mp = PluginMarketplace()
        entry = _make_plugin_entry()
        del entry["icon"]
        
        metadata = mp._parse_plugin_entry(entry)
        
        assert metadata is not None
        assert metadata.icon == "🔌"

    def test_parse_handles_optional_fields(self):
        """_parse_plugin_entry() handles optional fields correctly."""
        mp = PluginMarketplace()
        entry = _make_plugin_entry()
        entry["homepage"] = "https://example.com"
        entry["license"] = "MIT"
        entry["min_loofi_version"] = "26.0.0"
        
        metadata = mp._parse_plugin_entry(entry)
        
        assert metadata.homepage == "https://example.com"
        assert metadata.license == "MIT"
        assert metadata.min_loofi_version == "26.0.0"

    def test_parse_defaults_featured_to_false(self):
        """_parse_plugin_entry() defaults featured to False."""
        mp = PluginMarketplace()
        entry = _make_plugin_entry()
        del entry["featured"]
        
        metadata = mp._parse_plugin_entry(entry)
        
        assert metadata.featured is False

    def test_parse_defaults_empty_arrays(self):
        """_parse_plugin_entry() defaults tags/requires to empty list."""
        mp = PluginMarketplace()
        entry = _make_plugin_entry()
        del entry["tags"]
        del entry["requires"]
        
        metadata = mp._parse_plugin_entry(entry)
        
        assert metadata.tags == []
        assert metadata.requires == []


class TestPluginMarketplaceFetchIndex:
    """Tests for fetch_index() marketplace API."""

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_index_returns_success_with_plugins(self, mock_fetch):
        """fetch_index() returns success result with plugin list."""
        index_data = _make_index_json([
            _make_plugin_entry("plugin-1"),
            _make_plugin_entry("plugin-2")
        ])
        mock_fetch.return_value = index_data
        
        mp = PluginMarketplace()
        result = mp.fetch_index()
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0].id == "plugin-1"

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_index_caches_results(self, mock_fetch):
        """fetch_index() caches results for subsequent calls."""
        index_data = _make_index_json([_make_plugin_entry()])
        mock_fetch.return_value = index_data
        
        mp = PluginMarketplace()
        
        # First call
        result1 = mp.fetch_index()
        assert mock_fetch.call_count == 1
        
        # Second call should use cache
        result2 = mp.fetch_index()
        assert mock_fetch.call_count == 1  # Not called again
        assert result1.data == result2.data

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_index_force_refresh_bypasses_cache(self, mock_fetch):
        """fetch_index(force_refresh=True) fetches fresh data."""
        index_data = _make_index_json([_make_plugin_entry()])
        mock_fetch.return_value = index_data
        
        mp = PluginMarketplace()
        
        # First call
        mp.fetch_index()
        assert mock_fetch.call_count == 1
        
        # Force refresh
        mp.fetch_index(force_refresh=True)
        assert mock_fetch.call_count == 2

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_index_returns_error_on_fetch_failure(self, mock_fetch):
        """fetch_index() returns error result on network failure."""
        mock_fetch.return_value = None
        
        mp = PluginMarketplace()
        result = mp.fetch_index()
        
        assert result.success is False
        assert result.error is not None
        assert result.data is None

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_index_skips_invalid_entries(self, mock_fetch):
        """fetch_index() skips entries with missing required fields."""
        index_data = _make_index_json([
            _make_plugin_entry("valid-plugin"),
            {"id": "invalid", "name": "Incomplete"},  # Invalid
            _make_plugin_entry("another-valid")
        ])
        mock_fetch.return_value = index_data
        
        mp = PluginMarketplace()
        result = mp.fetch_index()
        
        assert result.success is True
        assert len(result.data) == 2  # Only valid entries


class TestPluginMarketplaceSearch:
    """Tests for search() filtering."""

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_search_filters_by_query(self, mock_fetch_index):
        """search() filters plugins by name/description query."""
        plugins = [
            PluginMetadata(
                id="backup-tool", name="Backup Tool", description="Backup utility",
                version="1.0", author="A", category="Utility", icon="",
                download_url="", checksum_sha256="", featured=False,
                tags=[], requires=[]
            ),
            PluginMetadata(
                id="network-monitor", name="Network Monitor", description="Monitor network",
                version="1.0", author="A", category="Network", icon="",
                download_url="", checksum_sha256="", featured=False,
                tags=[], requires=[]
            )
        ]
        mock_fetch_index.return_value = MarketplaceResult(success=True, data=plugins)
        
        mp = PluginMarketplace()
        result = mp.search(query="backup")
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].id == "backup-tool"

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_search_filters_by_category(self, mock_fetch_index):
        """search() filters plugins by category."""
        plugins = [
            PluginMetadata(
                id="p1", name="P1", description="D1", version="1.0",
                author="A", category="Utility", icon="", download_url="",
                checksum_sha256="", featured=False, tags=[], requires=[]
            ),
            PluginMetadata(
                id="p2", name="P2", description="D2", version="1.0",
                author="A", category="Security", icon="", download_url="",
                checksum_sha256="", featured=False, tags=[], requires=[]
            )
        ]
        mock_fetch_index.return_value = MarketplaceResult(success=True, data=plugins)
        
        mp = PluginMarketplace()
        result = mp.search(category="Security")
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].id == "p2"

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_search_case_insensitive(self, mock_fetch_index):
        """search() is case-insensitive."""
        plugins = [
            PluginMetadata(
                id="test", name="Test Plugin", description="Description",
                version="1.0", author="A", category="Utility", icon="",
                download_url="", checksum_sha256="", featured=False,
                tags=[], requires=[]
            )
        ]
        mock_fetch_index.return_value = MarketplaceResult(success=True, data=plugins)
        
        mp = PluginMarketplace()
        result = mp.search(query="TEST")
        
        assert result.success is True
        assert len(result.data) == 1


class TestPluginMarketplaceGetPlugin:
    """Tests for get_plugin() by ID."""

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_get_plugin_finds_by_id(self, mock_fetch_index):
        """get_plugin() finds plugin by exact ID match."""
        plugins = [
            PluginMetadata(
                id="target-plugin", name="Target", description="D",
                version="1.0", author="A", category="Utility", icon="",
                download_url="", checksum_sha256="", featured=False,
                tags=[], requires=[]
            )
        ]
        mock_fetch_index.return_value = MarketplaceResult(success=True, data=plugins)
        
        mp = PluginMarketplace()
        result = mp.get_plugin("target-plugin")
        
        assert result.success is True
        assert result.data[0].id == "target-plugin"

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_get_plugin_returns_error_if_not_found(self, mock_fetch_index):
        """get_plugin() returns error when ID not found."""
        mock_fetch_index.return_value = MarketplaceResult(success=True, data=[])
        
        mp = PluginMarketplace()
        result = mp.get_plugin("nonexistent")
        
        assert result.success is False
        assert "not found" in result.error.lower()


class TestPluginMarketplaceIntegration:
    """Integration tests for marketplace workflow."""

    @patch('urllib.request.urlopen')
    def test_full_fetch_search_workflow(self, mock_urlopen):
        """Test complete fetch -> cache -> search workflow."""
        index_data = _make_index_json([
            _make_plugin_entry("plugin-alpha"),
            _make_plugin_entry("plugin-beta")
        ])
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(index_data).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        mp = PluginMarketplace()
        
        # Fetch index
        fetch_result = mp.fetch_index()
        assert fetch_result.success is True
        assert len(fetch_result.data) == 2
        
        # Search (uses cache)
        search_result = mp.search(query="alpha")
        assert search_result.success is True
        assert len(search_result.data) == 1
        assert search_result.data[0].id == "plugin-alpha"
