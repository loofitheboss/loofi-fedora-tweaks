"""Tests for utils.plugin_cdn_client — PluginCdnClient CDN index retrieval."""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_cdn_client import (
    DEFAULT_CDN_BASE_URL,
    DEFAULT_CACHE_TTL_SECONDS,
    CdnFetchConfig,
    PluginCdnClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_signed_index() -> dict:
    """Return a valid signed plugin index."""
    return {
        "plugins": [{"id": "test-plugin", "name": "Test Plugin", "version": "1.0.0"}],
        "signature": {
            "algorithm": "sha256",
            "key_id": "key-001",
            "signature": "abc123deadbeef",
        },
    }


def _unsigned_index() -> dict:
    """Return a valid index without a signature (backward compatible)."""
    return {
        "plugins": [{"id": "unsigned-plugin", "name": "Unsigned", "version": "0.1.0"}],
    }


def _invalid_index_no_plugins() -> dict:
    """Return an index missing the plugins list."""
    return {"metadata": "something"}


# ---------------------------------------------------------------------------
# CdnFetchConfig
# ---------------------------------------------------------------------------


class TestCdnFetchConfig(unittest.TestCase):
    """Tests for CdnFetchConfig dataclass."""

    def test_defaults(self):
        cfg = CdnFetchConfig()
        self.assertEqual(cfg.base_url, DEFAULT_CDN_BASE_URL)
        self.assertEqual(cfg.cache_ttl_seconds, DEFAULT_CACHE_TTL_SECONDS)

    def test_custom_values(self):
        cfg = CdnFetchConfig(base_url="https://custom.cdn/p", cache_ttl_seconds=60)
        self.assertEqual(cfg.base_url, "https://custom.cdn/p")
        self.assertEqual(cfg.cache_ttl_seconds, 60)

    def test_frozen(self):
        cfg = CdnFetchConfig()
        with self.assertRaises(AttributeError):
            cfg.base_url = "https://other.cdn"


# ---------------------------------------------------------------------------
# PluginCdnClient — initialization
# ---------------------------------------------------------------------------


class TestPluginCdnClientInit(unittest.TestCase):
    """Tests for PluginCdnClient construction."""

    def test_default_config(self):
        client = PluginCdnClient()
        self.assertEqual(client.config.base_url, DEFAULT_CDN_BASE_URL)
        self.assertIsNone(client._cached_index)

    def test_custom_config(self):
        cfg = CdnFetchConfig(base_url="https://my.cdn/plugins", cache_ttl_seconds=120)
        client = PluginCdnClient(config=cfg)
        self.assertEqual(client.config.base_url, "https://my.cdn/plugins")


# ---------------------------------------------------------------------------
# PluginCdnClient._candidate_urls
# ---------------------------------------------------------------------------


class TestCandidateUrls(unittest.TestCase):
    """Tests for URL generation."""

    def test_generates_two_urls(self):
        client = PluginCdnClient()
        urls = client._candidate_urls("owner", "repo", "main")
        self.assertEqual(len(urls), 2)

    def test_branch_specific_url_first(self):
        client = PluginCdnClient()
        urls = client._candidate_urls("myorg", "myrepo", "develop")
        self.assertIn("/myorg/myrepo/develop/plugins.json", urls[0])

    def test_fallback_url_without_branch(self):
        client = PluginCdnClient()
        urls = client._candidate_urls("myorg", "myrepo", "develop")
        self.assertIn("/myorg/myrepo/plugins.json", urls[1])
        self.assertNotIn("develop", urls[1])

    def test_trailing_slash_stripped(self):
        cfg = CdnFetchConfig(base_url="https://cdn.example.com/plugins/")
        client = PluginCdnClient(config=cfg)
        urls = client._candidate_urls("o", "r", "b")
        for url in urls:
            self.assertNotIn("//o", url)


# ---------------------------------------------------------------------------
# PluginCdnClient._is_valid_signed_index
# ---------------------------------------------------------------------------


class TestIsValidSignedIndex(unittest.TestCase):
    """Tests for index validation logic."""

    def test_valid_signed_index(self):
        self.assertTrue(PluginCdnClient._is_valid_signed_index(_valid_signed_index()))

    def test_unsigned_index_accepted(self):
        self.assertTrue(PluginCdnClient._is_valid_signed_index(_unsigned_index()))

    def test_missing_plugins_list_rejected(self):
        self.assertFalse(
            PluginCdnClient._is_valid_signed_index(_invalid_index_no_plugins())
        )

    def test_plugins_not_a_list_rejected(self):
        self.assertFalse(
            PluginCdnClient._is_valid_signed_index({"plugins": "not-a-list"})
        )

    def test_signature_not_dict_rejected(self):
        data = _valid_signed_index()
        data["signature"] = "just-a-string"
        self.assertFalse(PluginCdnClient._is_valid_signed_index(data))

    def test_missing_algorithm_rejected(self):
        data = _valid_signed_index()
        del data["signature"]["algorithm"]
        self.assertFalse(PluginCdnClient._is_valid_signed_index(data))

    def test_missing_key_id_rejected(self):
        data = _valid_signed_index()
        del data["signature"]["key_id"]
        self.assertFalse(PluginCdnClient._is_valid_signed_index(data))

    def test_missing_signature_value_rejected(self):
        data = _valid_signed_index()
        del data["signature"]["signature"]
        self.assertFalse(PluginCdnClient._is_valid_signed_index(data))

    def test_algorithm_not_string_rejected(self):
        data = _valid_signed_index()
        data["signature"]["algorithm"] = 123
        self.assertFalse(PluginCdnClient._is_valid_signed_index(data))

    def test_key_id_not_string_rejected(self):
        data = _valid_signed_index()
        data["signature"]["key_id"] = 456
        self.assertFalse(PluginCdnClient._is_valid_signed_index(data))

    def test_signature_value_not_string_rejected(self):
        data = _valid_signed_index()
        data["signature"]["signature"] = 789
        self.assertFalse(PluginCdnClient._is_valid_signed_index(data))


# ---------------------------------------------------------------------------
# PluginCdnClient.fetch_index
# ---------------------------------------------------------------------------


class TestFetchIndex(unittest.TestCase):
    """Tests for the main fetch_index method."""

    def test_fetches_from_first_valid_url(self):
        client = PluginCdnClient()
        index = _valid_signed_index()
        fetch_fn = MagicMock(return_value=index)

        result = client.fetch_index("owner", "repo", "main", fetch_fn)

        self.assertEqual(result, index)
        fetch_fn.assert_called_once()

    def test_returns_cached_on_second_call(self):
        client = PluginCdnClient()
        index = _valid_signed_index()
        fetch_fn = MagicMock(return_value=index)

        client.fetch_index("owner", "repo", "main", fetch_fn)
        result = client.fetch_index("owner", "repo", "main", fetch_fn)

        self.assertEqual(result, index)
        # fetch_fn only called once — second call uses cache
        fetch_fn.assert_called_once()

    def test_force_refresh_bypasses_cache(self):
        client = PluginCdnClient()
        index = _valid_signed_index()
        fetch_fn = MagicMock(return_value=index)

        client.fetch_index("owner", "repo", "main", fetch_fn)
        client.fetch_index("owner", "repo", "main", fetch_fn, force_refresh=True)

        self.assertEqual(fetch_fn.call_count, 2)

    def test_falls_back_to_second_url(self):
        client = PluginCdnClient()
        index = _valid_signed_index()
        call_count = 0

        def fetch_fn(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First URL fails
            return index

        result = client.fetch_index("owner", "repo", "main", fetch_fn)
        self.assertEqual(result, index)
        self.assertEqual(call_count, 2)

    def test_returns_cached_when_all_urls_fail(self):
        client = PluginCdnClient()
        old_index = _valid_signed_index()
        client._cached_index = old_index

        fetch_fn = MagicMock(return_value=None)
        result = client.fetch_index(
            "owner", "repo", "main", fetch_fn, force_refresh=True
        )

        self.assertEqual(result, old_index)

    def test_returns_none_when_no_cache_and_all_fail(self):
        client = PluginCdnClient()
        fetch_fn = MagicMock(return_value=None)

        result = client.fetch_index("owner", "repo", "main", fetch_fn)
        self.assertIsNone(result)

    def test_skips_invalid_index(self):
        client = PluginCdnClient()
        invalid = _invalid_index_no_plugins()
        valid = _valid_signed_index()
        call_count = 0

        def fetch_fn(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return invalid  # Invalid index
            return valid

        result = client.fetch_index("owner", "repo", "main", fetch_fn)
        self.assertEqual(result, valid)

    def test_unsigned_index_accepted_and_cached(self):
        client = PluginCdnClient()
        unsigned = _unsigned_index()
        fetch_fn = MagicMock(return_value=unsigned)

        result = client.fetch_index("owner", "repo", "main", fetch_fn)
        self.assertEqual(result, unsigned)
        self.assertEqual(client._cached_index, unsigned)


if __name__ == "__main__":
    unittest.main()
