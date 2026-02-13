"""Deep tests for utils/plugin_marketplace.py — validation, fetch, reviews, search."""

import os
import sys
import json
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.plugin_marketplace import (
    PluginMarketplace, PluginMetadata, MarketplaceResult,
    MarketplaceReview, MarketplaceRatingAggregate,
    CdnIndexSignature, CdnMarketplaceIndex,
    MarketplacePublisherVerification,
)


class TestPluginMetadata(unittest.TestCase):
    def test_defaults(self):
        m = PluginMetadata()
        self.assertEqual(m.id, "")
        self.assertEqual(m.category, "General")
        self.assertFalse(m.featured)
        self.assertEqual(m.tags, [])

    def test_post_init_id_from_name(self):
        m = PluginMetadata(name="My Cool Plugin")
        self.assertEqual(m.id, "my-cool-plugin")

    def test_post_init_none_tags(self):
        m = PluginMetadata(id="x", tags=None)
        self.assertEqual(m.tags, [])

    def test_post_init_none_requires(self):
        m = PluginMetadata(id="x", requires=None)
        self.assertEqual(m.requires, [])


class TestMarketplaceResult(unittest.TestCase):
    def test_success(self):
        r = MarketplaceResult(success=True, data=[1, 2])
        self.assertTrue(r.success)
        self.assertEqual(r.data, [1, 2])

    def test_failure(self):
        r = MarketplaceResult(success=False, error="oops")
        self.assertFalse(r.success)
        self.assertEqual(r.error, "oops")

    def test_offline(self):
        r = MarketplaceResult(success=False, offline=True)
        self.assertTrue(r.offline)


class TestDataclasses(unittest.TestCase):
    def test_cdn_index_signature(self):
        s = CdnIndexSignature()
        self.assertEqual(s.algorithm, "ed25519")

    def test_cdn_marketplace_index(self):
        idx = CdnMarketplaceIndex()
        self.assertEqual(idx.version, "1.0")
        self.assertEqual(idx.plugins, [])

    def test_publisher_verification(self):
        pv = MarketplacePublisherVerification()
        self.assertFalse(pv.verified)

    def test_marketplace_review(self):
        r = MarketplaceReview(plugin_id="x", reviewer="me", rating=5)
        self.assertEqual(r.title, "")

    def test_rating_aggregate(self):
        ra = MarketplaceRatingAggregate(plugin_id="x")
        self.assertEqual(ra.average_rating, 0.0)
        self.assertEqual(ra.review_count, 0)


class TestMapHttpError(unittest.TestCase):
    def _make_err(self, code):
        return urllib.error.HTTPError("http://x", code, "msg", {}, None)

    def test_400(self):
        self.assertIn("Invalid", PluginMarketplace._map_http_error(self._make_err(400)))

    def test_401(self):
        self.assertIn("Authentication", PluginMarketplace._map_http_error(self._make_err(401)))

    def test_403(self):
        self.assertIn("not allowed", PluginMarketplace._map_http_error(self._make_err(403)))

    def test_404(self):
        self.assertIn("not found", PluginMarketplace._map_http_error(self._make_err(404)))

    def test_409(self):
        self.assertIn("conflict", PluginMarketplace._map_http_error(self._make_err(409)))

    def test_422(self):
        self.assertIn("validation", PluginMarketplace._map_http_error(self._make_err(422)))

    def test_500(self):
        self.assertIn("unavailable", PluginMarketplace._map_http_error(self._make_err(500)))

    def test_other(self):
        self.assertIn("418", PluginMarketplace._map_http_error(self._make_err(418)))


class TestValidators(unittest.TestCase):
    def test_validate_plugin_id_empty(self):
        self.assertIsNotNone(PluginMarketplace._validate_plugin_id(""))

    def test_validate_plugin_id_none(self):
        self.assertIsNotNone(PluginMarketplace._validate_plugin_id(None))

    def test_validate_plugin_id_valid(self):
        self.assertIsNone(PluginMarketplace._validate_plugin_id("my-plugin"))

    def test_validate_reviewer_empty(self):
        self.assertIsNotNone(PluginMarketplace._validate_reviewer(""))

    def test_validate_reviewer_too_long(self):
        self.assertIsNotNone(PluginMarketplace._validate_reviewer("x" * 81))

    def test_validate_reviewer_valid(self):
        self.assertIsNone(PluginMarketplace._validate_reviewer("johndoe"))

    def test_validate_rating_too_low(self):
        self.assertIsNotNone(PluginMarketplace._validate_rating(0))

    def test_validate_rating_too_high(self):
        self.assertIsNotNone(PluginMarketplace._validate_rating(6))

    def test_validate_rating_valid(self):
        self.assertIsNone(PluginMarketplace._validate_rating(3))

    def test_validate_rating_non_int(self):
        self.assertIsNotNone(PluginMarketplace._validate_rating("bad"))


class TestFetchJson(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_urlopen.return_value = mock_resp
        mp = PluginMarketplace()
        result = mp._fetch_json("http://example.com/data.json")
        self.assertEqual(result, {"ok": True})

    @patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("x", 404, "nf", {}, None))
    def test_http_error(self, _):
        mp = PluginMarketplace()
        self.assertIsNone(mp._fetch_json("http://bad.example.com"))

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout"))
    def test_url_error(self, _):
        mp = PluginMarketplace()
        self.assertIsNone(mp._fetch_json("http://timeout.example.com"))

    @patch("urllib.request.urlopen")
    def test_json_decode_error(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b"not json"
        mock_urlopen.return_value = mock_resp
        mp = PluginMarketplace()
        self.assertIsNone(mp._fetch_json("http://example.com"))


class TestFetchReviews(unittest.TestCase):
    def test_invalid_plugin_id(self):
        mp = PluginMarketplace()
        r = mp.fetch_reviews("")
        self.assertFalse(r.success)

    def test_invalid_limit(self):
        mp = PluginMarketplace()
        r = mp.fetch_reviews("test", limit=0)
        self.assertFalse(r.success)


class TestSubmitReview(unittest.TestCase):
    def test_invalid_plugin_id(self):
        mp = PluginMarketplace()
        r = mp.submit_review("", reviewer="me", rating=5)
        self.assertFalse(r.success)

    def test_invalid_reviewer(self):
        mp = PluginMarketplace()
        r = mp.submit_review("plugin", reviewer="", rating=5)
        self.assertFalse(r.success)

    def test_invalid_rating(self):
        mp = PluginMarketplace()
        r = mp.submit_review("plugin", reviewer="me", rating=0)
        self.assertFalse(r.success)


class TestGetRatingAggregate(unittest.TestCase):
    def test_invalid_plugin_id(self):
        mp = PluginMarketplace()
        r = mp.get_rating_aggregate("")
        self.assertFalse(r.success)


class TestSearch(unittest.TestCase):
    @patch.object(PluginMarketplace, 'fetch_index')
    def test_empty_index(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(success=True, data=[])
        mp = PluginMarketplace()
        r = mp.search("test")
        self.assertTrue(r.success)
        self.assertEqual(r.data, [])

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_search_match(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(
            success=True,
            data=[PluginMetadata(id="test", name="Test Plugin", description="Hello")]
        )
        mp = PluginMarketplace()
        r = mp.search("test")
        self.assertTrue(r.success)
        self.assertEqual(len(r.data), 1)

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_search_with_category(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(
            success=True,
            data=[
                PluginMetadata(id="a", name="A", description="", category="Dev"),
                PluginMetadata(id="b", name="B", description="", category="Gaming"),
            ]
        )
        mp = PluginMarketplace()
        r = mp.search("", category="Dev")
        self.assertTrue(r.success)
        self.assertEqual(len(r.data), 1)

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_fetch_fails(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(success=False, error="fail")
        mp = PluginMarketplace()
        r = mp.search("test")
        self.assertFalse(r.success)


class TestGetPlugin(unittest.TestCase):
    @patch.object(PluginMarketplace, 'fetch_index')
    def test_found(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(
            success=True,
            data=[PluginMetadata(id="my-plugin", name="My Plugin", description="")]
        )
        mp = PluginMarketplace()
        r = mp.get_plugin("my-plugin")
        self.assertTrue(r.success)
        self.assertEqual(r.data[0].id, "my-plugin")

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(success=True, data=[])
        mp = PluginMarketplace()
        r = mp.get_plugin("nonexistent")
        self.assertFalse(r.success)


class TestGetPluginInfo(unittest.TestCase):
    @patch.object(PluginMarketplace, 'get_plugin')
    def test_found(self, mock_get):
        mock_get.return_value = MarketplaceResult(
            success=True, data=[PluginMetadata(id="x", name="X")]
        )
        mp = PluginMarketplace()
        info = mp.get_plugin_info("x")
        self.assertIsNotNone(info)

    @patch.object(PluginMarketplace, 'get_plugin')
    def test_not_found(self, mock_get):
        mock_get.return_value = MarketplaceResult(success=False, error="nope")
        mp = PluginMarketplace()
        info = mp.get_plugin_info("bad")
        self.assertIsNone(info)


class TestGetFeatured(unittest.TestCase):
    @patch.object(PluginMarketplace, 'fetch_index')
    def test_returns_featured(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(
            success=True,
            data=[
                PluginMetadata(id="a", name="A", featured=True),
                PluginMetadata(id="b", name="B", featured=False),
            ]
        )
        mp = PluginMarketplace()
        r = mp.get_featured()
        self.assertTrue(r.success)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0].id, "a")


class TestGetCategories(unittest.TestCase):
    @patch.object(PluginMarketplace, 'fetch_index')
    def test_returns_unique_categories(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(
            success=True,
            data=[
                PluginMetadata(id="a", name="A", category="Dev"),
                PluginMetadata(id="b", name="B", category="Gaming"),
                PluginMetadata(id="c", name="C", category="Dev"),
            ]
        )
        mp = PluginMarketplace()
        cats = mp.get_categories()
        self.assertIn("Dev", cats)
        self.assertIn("Gaming", cats)
        self.assertEqual(len(set(cats)), len(cats))

    @patch.object(PluginMarketplace, 'fetch_index')
    def test_fetch_fail_returns_empty(self, mock_fetch):
        mock_fetch.return_value = MarketplaceResult(success=False, error="fail")
        mp = PluginMarketplace()
        self.assertEqual(mp.get_categories(), [])


class TestCoerceInt(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(PluginMarketplace._coerce_int("42"), 42)

    def test_invalid(self):
        self.assertEqual(PluginMarketplace._coerce_int("bad", 0), 0)

    def test_none(self):
        self.assertEqual(PluginMarketplace._coerce_int(None, 5), 5)


if __name__ == "__main__":
    unittest.main()
