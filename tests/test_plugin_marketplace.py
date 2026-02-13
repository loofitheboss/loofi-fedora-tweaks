"""Tests for utils.plugin_marketplace — PluginMarketplace GitHub API."""
from utils.plugin_marketplace import (
    DEFAULT_BRANCH,
    DEFAULT_REPO_NAME,
    DEFAULT_REPO_OWNER,
    ERR_MARKETPLACE_OFFLINE,
    MarketplaceResult,
    PluginMarketplace,
    PluginMetadata,
)
import json
import os
import sys
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), "..", "loofi-fedora-tweaks"))


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

    def test_parse_supports_nested_rating_and_verification_fields(self):
        """_parse_plugin_entry() supports v27 nested ratings/verification schema."""
        mp = PluginMarketplace()
        entry = _make_plugin_entry("nested-schema")
        entry["ratings"] = {
            "average": "4.7",
            "count": "22",
            "review_count": "19"
        }
        entry["publisher_verification"] = {
            "verified": True,
            "publisher_id": "publisher-123",
            "badge": "verified"
        }

        metadata = mp._parse_plugin_entry(entry)

        assert metadata is not None
        assert metadata.rating_average == 4.7
        assert metadata.rating_count == 22
        assert metadata.review_count == 19
        assert metadata.verified_publisher is True
        assert metadata.publisher_id == "publisher-123"
        assert metadata.publisher_badge == "verified"

    def test_parse_keeps_legacy_flat_rating_and_verification_fields(self):
        """_parse_plugin_entry() remains compatible with legacy flat fields."""
        mp = PluginMarketplace()
        entry = _make_plugin_entry("legacy-schema")
        entry["rating_average"] = 4.1
        entry["rating_count"] = 11
        entry["review_count"] = 9
        entry["verified_publisher"] = True
        entry["publisher_id"] = "legacy-publisher"
        entry["publisher_badge"] = "trusted"

        metadata = mp._parse_plugin_entry(entry)

        assert metadata is not None
        assert metadata.rating_average == 4.1
        assert metadata.rating_count == 11
        assert metadata.review_count == 9
        assert metadata.verified_publisher is True
        assert metadata.publisher_id == "legacy-publisher"
        assert metadata.publisher_badge == "trusted"


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

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_index_prefers_cdn_before_fallback(self, mock_fetch):
        """fetch_index() uses CDN response when available."""
        cdn_index = _make_index_json([_make_plugin_entry("cdn-first")])
        cdn_index["signature"] = {
            "algorithm": "ed25519",
            "key_id": "key-1",
            "signature": "abc123"
        }
        mock_fetch.return_value = cdn_index

        mp = PluginMarketplace()
        result = mp.fetch_index(force_refresh=True)

        assert result.success is True
        assert result.data is not None
        assert result.data[0].id == "cdn-first"
        assert "cdn.loofi.software" in mock_fetch.call_args[0][0]

    @patch.object(PluginMarketplace, '_fetch_json', return_value=None)
    @patch('utils.plugin_marketplace.PluginCdnClient.fetch_index', return_value=None)
    def test_fetch_index_offline_cache_hit_sets_source_cache(self, mock_cdn_fetch, mock_fetch_json):
        mp = PluginMarketplace()
        mp._cache = [
            PluginMetadata(
                id="cached-plugin",
                name="Cached Plugin",
                description="Cached",
                version="1.0.0",
                author="Test",
                category="Utility",
                icon="🔌",
                download_url="https://example.invalid/cached.tar.gz",
                checksum_sha256="a" * 64,
                featured=False,
                tags=[],
                requires=[],
            )
        ]

        result = mp.fetch_index(force_refresh=True)

        assert result.success is True
        assert result.offline is True
        assert result.source == "cache"
        assert result.data is not None
        assert result.data[0].id == "cached-plugin"

    @patch.object(PluginMarketplace, '_fetch_json', return_value=None)
    @patch('utils.plugin_marketplace.PluginCdnClient.fetch_index', return_value=None)
    def test_fetch_index_offline_cache_miss_sets_deterministic_error(self, mock_cdn_fetch, mock_fetch_json):
        mp = PluginMarketplace()
        mp._cache = None

        result = mp.fetch_index(force_refresh=True)

        assert result.success is False
        assert result.offline is True
        assert result.source == "network"
        assert result.error == ERR_MARKETPLACE_OFFLINE


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
        mock_fetch_index.return_value = MarketplaceResult(
            success=True, data=plugins)

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
        mock_fetch_index.return_value = MarketplaceResult(
            success=True, data=plugins)

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
        mock_fetch_index.return_value = MarketplaceResult(
            success=True, data=plugins)

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
        mock_fetch_index.return_value = MarketplaceResult(
            success=True, data=plugins)

        mp = PluginMarketplace()
        result = mp.get_plugin("target-plugin")

        assert result.success is True
        assert result.data[0].id == "target-plugin"

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_get_plugin_returns_error_if_not_found(self, mock_fetch_index):
        """get_plugin() returns error when ID not found."""
        mock_fetch_index.return_value = MarketplaceResult(
            success=True, data=[])

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
        mock_response.read.return_value = json.dumps(
            index_data).encode('utf-8')
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


class TestPluginMarketplaceAdditionalCoverage:
    """Additional branch coverage for review/rating/download paths."""

    def test_plugin_metadata_post_init_backfills_fields(self):
        metadata = PluginMetadata(
            id="",
            name="My Plugin",
            description="desc",
            version="1.0.0",
            author="A",
            category="Utility",
            download_url="https://example.invalid/plugin.tar.gz",
            checksum_sha256="a" * 64,
            tags=None,
            requires=None,
        )

        assert metadata.id == "my-plugin"
        assert metadata.tags == []
        assert metadata.requires == []

    @patch('urllib.request.urlopen')
    def test_post_json_empty_body_returns_empty_dict(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        mp = PluginMarketplace()
        result = mp._post_json("https://example.invalid/post", {"k": "v"})

        assert result == {}

    @patch('urllib.request.urlopen')
    def test_post_json_json_decode_error_returns_none(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"{not-valid-json"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        mp = PluginMarketplace()
        result = mp._post_json("https://example.invalid/post", {"k": "v"})

        assert result is None

    def test_map_http_error_statuses(self):
        status_to_expected = {
            400: "Invalid request payload",
            401: "Authentication required for marketplace reviews",
            403: "Marketplace review operation is not allowed",
            404: "Plugin or review endpoint not found",
            409: "Review conflict detected",
            422: "Review validation failed",
            500: "Marketplace service unavailable",
            418: "HTTP 418",
        }

        for status, expected in status_to_expected.items():
            exc = urllib.error.HTTPError(
                "https://example.invalid", status, "err", {}, None)
            assert PluginMarketplace._map_http_error(exc) == expected

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_reviews_success_parses_entries(self, mock_fetch):
        mock_fetch.return_value = {
            "reviews": [
                {
                    "plugin_id": "p1",
                    "reviewer": "alice",
                    "rating": "5",
                    "title": "Great",
                    "comment": "Works",
                    "created_at": "2026-01-01",
                },
                "skip-me",
            ]
        }

        mp = PluginMarketplace()
        result = mp.fetch_reviews("p1")

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].rating == 5

    def test_fetch_reviews_validation_errors(self):
        mp = PluginMarketplace()

        assert mp.fetch_reviews("").error == "Plugin ID is required"
        assert mp.fetch_reviews(
            "p1", limit=0).error == "Limit must be between 1 and 100"
        assert mp.fetch_reviews("p1", offset=-1).error == "Offset must be >= 0"

    @patch.object(PluginMarketplace, '_fetch_json', side_effect=urllib.error.URLError("offline"))
    def test_fetch_reviews_network_error(self, mock_fetch):
        mp = PluginMarketplace()
        result = mp.fetch_reviews("p1")
        assert result.success is False
        assert "Network error" in result.error

    @patch.object(PluginMarketplace, '_post_json')
    def test_submit_review_success_and_validation(self, mock_post):
        mock_post.return_value = {"ok": True}
        mp = PluginMarketplace()

        success = mp.submit_review(
            "plugin-x", "  reviewer  ", 4, title="  Good  ", comment="  Nice  ")
        assert success.success is True
        assert success.data["ok"] is True

        invalid = mp.submit_review("", "reviewer", 4)
        assert invalid.success is False
        assert invalid.error == "Plugin ID is required"

        too_long_title = mp.submit_review(
            "plugin-x", "reviewer", 4, title="x" * 121)
        assert too_long_title.success is False
        assert "title is too long" in too_long_title.error

        too_long_comment = mp.submit_review(
            "plugin-x", "reviewer", 4, comment="x" * 5001)
        assert too_long_comment.success is False
        assert "comment is too long" in too_long_comment.error

    @patch.object(PluginMarketplace, '_post_json', side_effect=urllib.error.HTTPError("u", 409, "c", {}, None))
    def test_submit_review_http_error_is_mapped(self, mock_post):
        mp = PluginMarketplace()
        result = mp.submit_review("plugin-x", "reviewer", 4)
        assert result.success is False
        assert result.error == "Review conflict detected"

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_get_rating_aggregate_success_and_invalid(self, mock_fetch):
        mp = PluginMarketplace()

        mock_fetch.return_value = {
            "aggregate": {
                "average_rating": "4.5",
                "rating_count": "10",
                "review_count": "8",
                "breakdown": {"5": "6", "4": "2"},
            }
        }
        ok = mp.get_rating_aggregate("plugin-x")
        assert ok.success is True
        assert ok.data.average_rating == 4.5
        assert ok.data.breakdown[5] == 6

        mock_fetch.return_value = {"aggregate": "invalid"}
        bad = mp.get_rating_aggregate("plugin-x")
        assert bad.success is False
        assert "Invalid aggregate" in bad.error

    @patch.object(PluginMarketplace, '_fetch_json', side_effect=urllib.error.URLError("offline"))
    def test_get_rating_aggregate_network_error(self, mock_fetch):
        mp = PluginMarketplace()
        result = mp.get_rating_aggregate("plugin-x")
        assert result.success is False
        assert "Network error" in result.error

    @patch('utils.plugin_marketplace.IntegrityVerifier.verify_publisher_metadata')
    def test_extract_publisher_fields_signed_verification_failure(self, mock_verify):
        mock_verify.return_value = Mock(
            success=False, signature_valid=False, error="invalid")
        entry = {
            "id": "plugin-x",
            "publisher_verification": {
                "verified": True,
                "publisher_id": "pub-1",
                "badge": "verified",
                "signature": "sig",
                "trust_chain": ["root"],
            }
        }

        verified, publisher_id, publisher_badge = PluginMarketplace._extract_publisher_fields(
            entry)
        assert verified is False
        assert publisher_id == "pub-1"
        assert publisher_badge == "verified"

    @patch.object(PluginMarketplace, 'get_plugin_info', return_value=None)
    def test_download_plugin_not_found(self, mock_get_plugin):
        mp = PluginMarketplace()
        with TemporaryDirectory() as temp_dir:
            result = mp.download_plugin(
                "missing", Path(temp_dir) / "artifact.zip")
        assert result.success is False
        assert "not found" in result.error.lower()

    @patch.object(PluginMarketplace, 'get_plugin_info')
    @patch('urllib.request.urlopen')
    def test_download_plugin_success(self, mock_urlopen, mock_get_plugin):
        plugin = PluginMetadata(
            id="plugin-x",
            name="Plugin X",
            description="Desc",
            version="1.0.0",
            author="A",
            category="Utility",
            download_url="https://example.invalid/plugin.zip",
            checksum_sha256="a" * 64,
        )
        mock_get_plugin.return_value = plugin

        mock_response = MagicMock()
        mock_response.read.return_value = b"zip-bytes"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        mp = PluginMarketplace()
        with TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "plugin.zip"
            result = mp.download_plugin(
                "plugin-x", destination, version="2.0.0")

            assert result.success is True
            assert destination.exists()

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_get_featured_and_categories_branches(self, mock_fetch_index):
        mp = PluginMarketplace()

        mock_fetch_index.return_value = MarketplaceResult(
            success=False, error="boom")
        featured_fail = mp.get_featured()
        categories_fail = mp.get_categories()
        assert featured_fail.success is False
        assert categories_fail == []

        mock_fetch_index.return_value = MarketplaceResult(success=True, data=[
            PluginMetadata(
                id="p1", name="P1", description="D1", version="1.0", author="A", category="Utility",
                icon="", download_url="u", checksum_sha256="h", featured=True, tags=[], requires=[]
            ),
            PluginMetadata(
                id="p2", name="P2", description="D2", version="1.0", author="A", category="Security",
                icon="", download_url="u", checksum_sha256="h", featured=False, tags=[], requires=[]
            ),
        ])

        featured_ok = mp.get_featured()
        categories_ok = mp.get_categories()
        assert featured_ok.success is True
        assert len(featured_ok.data) == 1
        assert categories_ok == ["Security", "Utility"]
