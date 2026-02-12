"""Tests for review/rating operations in utils.plugin_marketplace."""
import os
import sys
import urllib.error
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_marketplace import (
    PluginMarketplace,
    MarketplaceReview,
    MarketplaceRatingAggregate,
)


class TestPluginMarketplaceFetchReviews:
    """Tests for fetch_reviews()."""

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_reviews_success(self, mock_fetch_json):
        """fetch_reviews returns parsed MarketplaceReview items."""
        mock_fetch_json.return_value = {
            "reviews": [
                {
                    "plugin_id": "test-plugin",
                    "reviewer": "Alice",
                    "rating": 5,
                    "title": "Great",
                    "comment": "Works well",
                    "created_at": "2026-01-01T12:00:00Z",
                }
            ]
        }

        marketplace = PluginMarketplace()
        result = marketplace.fetch_reviews("test-plugin", limit=10, offset=0)

        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 1
        assert isinstance(result.data[0], MarketplaceReview)
        assert result.data[0].reviewer == "Alice"
        assert result.data[0].rating == 5

    def test_fetch_reviews_validation_failures(self):
        """fetch_reviews validates plugin_id, limit, and offset."""
        marketplace = PluginMarketplace()

        missing_plugin = marketplace.fetch_reviews("")
        assert missing_plugin.success is False
        assert missing_plugin.error == "Plugin ID is required"

        bad_limit = marketplace.fetch_reviews("test-plugin", limit=0)
        assert bad_limit.success is False
        assert bad_limit.error == "Limit must be between 1 and 100"

        bad_offset = marketplace.fetch_reviews("test-plugin", offset=-1)
        assert bad_offset.success is False
        assert bad_offset.error == "Offset must be >= 0"

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_reviews_invalid_response_shape(self, mock_fetch_json):
        """fetch_reviews fails when response format is invalid."""
        mock_fetch_json.return_value = {"reviews": "not-a-list"}

        marketplace = PluginMarketplace()
        result = marketplace.fetch_reviews("test-plugin")

        assert result.success is False
        assert result.error == "Invalid reviews response format"

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_fetch_reviews_http_error_mapping(self, mock_fetch_json):
        """fetch_reviews maps HTTP errors to stable messages."""
        mock_fetch_json.side_effect = urllib.error.HTTPError(
            url="https://example.test",
            code=422,
            msg="Unprocessable Entity",
            hdrs=None,
            fp=None,
        )

        marketplace = PluginMarketplace()
        result = marketplace.fetch_reviews("test-plugin")

        assert result.success is False
        assert result.error == "Review validation failed"


class TestPluginMarketplaceSubmitReview:
    """Tests for submit_review()."""

    @patch.object(PluginMarketplace, '_post_json')
    def test_submit_review_success(self, mock_post_json):
        """submit_review returns success payload from API."""
        mock_post_json.return_value = {"id": "r-123", "status": "accepted"}

        marketplace = PluginMarketplace()
        result = marketplace.submit_review(
            plugin_id="test-plugin",
            reviewer="Alice",
            rating=5,
            title=" Nice ",
            comment=" Great plugin ",
        )

        assert result.success is True
        assert result.data == {"id": "r-123", "status": "accepted"}

    def test_submit_review_validation_failures(self):
        """submit_review validates required fields and limits."""
        marketplace = PluginMarketplace()

        missing_plugin = marketplace.submit_review("", "Alice", 5)
        assert missing_plugin.success is False
        assert missing_plugin.error == "Plugin ID is required"

        missing_reviewer = marketplace.submit_review("test-plugin", "", 5)
        assert missing_reviewer.success is False
        assert missing_reviewer.error == "Reviewer name is required"

        bad_rating = marketplace.submit_review("test-plugin", "Alice", 7)
        assert bad_rating.success is False
        assert bad_rating.error == "Rating must be between 1 and 5"

        long_title = marketplace.submit_review("test-plugin", "Alice", 5, title="x" * 121)
        assert long_title.success is False
        assert long_title.error == "Review title is too long (max 120 chars)"

        long_comment = marketplace.submit_review("test-plugin", "Alice", 5, comment="x" * 5001)
        assert long_comment.success is False
        assert long_comment.error == "Review comment is too long (max 5000 chars)"

    @patch.object(PluginMarketplace, '_post_json')
    def test_submit_review_http_error_mapping(self, mock_post_json):
        """submit_review maps HTTP status to marketplace errors."""
        mock_post_json.side_effect = urllib.error.HTTPError(
            url="https://example.test",
            code=409,
            msg="Conflict",
            hdrs=None,
            fp=None,
        )

        marketplace = PluginMarketplace()
        result = marketplace.submit_review("test-plugin", "Alice", 5)

        assert result.success is False
        assert result.error == "Review conflict detected"


class TestPluginMarketplaceRatingAggregate:
    """Tests for get_rating_aggregate()."""

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_get_rating_aggregate_success(self, mock_fetch_json):
        """get_rating_aggregate parses aggregate payload."""
        mock_fetch_json.return_value = {
            "aggregate": {
                "average_rating": 4.4,
                "rating_count": 12,
                "review_count": 9,
                "breakdown": {"5": 7, "4": 3, "3": 2},
            }
        }

        marketplace = PluginMarketplace()
        result = marketplace.get_rating_aggregate("test-plugin")

        assert result.success is True
        assert isinstance(result.data, MarketplaceRatingAggregate)
        assert result.data.plugin_id == "test-plugin"
        assert result.data.average_rating == 4.4
        assert result.data.rating_count == 12
        assert result.data.review_count == 9
        assert result.data.breakdown[5] == 7

    @patch.object(PluginMarketplace, '_fetch_json')
    def test_get_rating_aggregate_invalid_payload(self, mock_fetch_json):
        """get_rating_aggregate reports invalid response payloads."""
        mock_fetch_json.return_value = {"aggregate": "bad"}

        marketplace = PluginMarketplace()
        result = marketplace.get_rating_aggregate("test-plugin")

        assert result.success is False
        assert result.error == "Invalid aggregate response format"
