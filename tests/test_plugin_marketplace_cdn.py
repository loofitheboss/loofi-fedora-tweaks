"""Tests for CDN-first plugin marketplace behavior and fallback paths."""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_marketplace import PluginMarketplace


def _signed_index(plugin_id: str = "cdn-plugin") -> dict:
    return {
        "version": "1.0",
        "signature": {
            "algorithm": "ed25519",
            "key_id": "test-key",
            "signature": "deadbeef"
        },
        "plugins": [{
            "id": plugin_id,
            "name": "CDN Plugin",
            "description": "Loaded from CDN",
            "version": "1.0.0",
            "author": "Test",
            "category": "Utility",
            "download_url": "https://example.com/plugin.tar.gz",
            "checksum_sha256": "a" * 64
        }]
    }


def _fallback_index(plugin_id: str = "fallback-plugin") -> dict:
    data = _signed_index(plugin_id)
    data.pop("signature", None)
    return data


class TestPluginMarketplaceCdnProvider:
    """CDN provider tests: cache, timeout, malformed index, and fallback."""

    @patch.object(PluginMarketplace, "_fetch_json")
    def test_cdn_cache_hit_skips_network(self, mock_fetch_json):
        mp = PluginMarketplace()
        mp.cdn_client._cached_index = _signed_index("cached-plugin")

        result = mp.fetch_index()

        assert result.success is True
        assert result.data is not None
        assert result.data[0].id == "cached-plugin"
        mock_fetch_json.assert_not_called()

    @patch.object(PluginMarketplace, "_fetch_json")
    def test_cdn_cache_miss_fetches_from_cdn(self, mock_fetch_json):
        mock_fetch_json.return_value = _signed_index("cdn-miss")
        mp = PluginMarketplace()

        result = mp.fetch_index(force_refresh=True)

        assert result.success is True
        assert result.data is not None
        assert result.data[0].id == "cdn-miss"
        assert mock_fetch_json.call_count == 1

    @patch.object(PluginMarketplace, "_fetch_json")
    def test_cdn_timeout_falls_back_to_github(self, mock_fetch_json):
        def _side_effect(url: str):
            if "raw.githubusercontent.com" in url:
                return _fallback_index("fallback-timeout")
            return None

        mock_fetch_json.side_effect = _side_effect
        mp = PluginMarketplace()

        result = mp.fetch_index(force_refresh=True)

        assert result.success is True
        assert result.data is not None
        assert result.data[0].id == "fallback-timeout"

    @patch.object(PluginMarketplace, "_fetch_json")
    def test_malformed_cdn_index_falls_back_to_github(self, mock_fetch_json):
        malformed_cdn = {"signature": {"algorithm": "ed25519"}, "plugins": "invalid"}

        def _side_effect(url: str):
            if "raw.githubusercontent.com" in url:
                return _fallback_index("fallback-malformed")
            return malformed_cdn

        mock_fetch_json.side_effect = _side_effect
        mp = PluginMarketplace()

        result = mp.fetch_index(force_refresh=True)

        assert result.success is True
        assert result.data is not None
        assert result.data[0].id == "fallback-malformed"

    @patch.object(PluginMarketplace, "_fetch_json")
    def test_fallback_failure_returns_error(self, mock_fetch_json):
        mock_fetch_json.return_value = None
        mp = PluginMarketplace()

        result = mp.fetch_index(force_refresh=True)

        assert result.success is False
        assert result.data is None
        assert result.error is not None

    @patch.object(PluginMarketplace, "_fetch_json")
    def test_offline_uses_existing_cache(self, mock_fetch_json):
        mock_fetch_json.return_value = None
        mp = PluginMarketplace()
        mp._cache = [mp._parse_plugin_entry(_signed_index("cached-offline")["plugins"][0])]

        result = mp.fetch_index(force_refresh=True)

        assert result.success is True
        assert result.offline is True
        assert result.source == "cache"
