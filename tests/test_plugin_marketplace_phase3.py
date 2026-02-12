"""Tests for v27.0 Phase 3 marketplace UI enhancements (Task T10)."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QListWidgetItem

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_marketplace import (
    MarketplaceRatingAggregate,
    MarketplaceResult,
    MarketplaceReview,
    PluginMetadata,
)


def _make_plugin_metadata() -> PluginMetadata:
    """Create marketplace plugin metadata with v27 rating/badge fields."""
    return PluginMetadata(
        id="test-plugin",
        name="Test Plugin",
        description="Plugin metadata",
        version="1.0.0",
        author="Test Author",
        category="System",
        download_url="https://example.com/test-plugin.loofi-plugin",
        checksum_sha256="a" * 64,
        rating_average=4.7,
        rating_count=15,
        review_count=11,
        verified_publisher=True,
        publisher_id="publisher.acme",
        publisher_badge="verified",
    )


def _make_preset() -> SimpleNamespace:
    """Create preset-like object expected by CommunityTab UI rendering."""
    return SimpleNamespace(
        id="test-plugin",
        plugin_id="test-plugin",
        name="Test Plugin",
        author="Preset Author",
        category="System",
        description="Preset description for testing marketplace row rendering.",
        stars=5,
        download_count=99,
        tags=["fedora", "performance"],
    )


class TestCommunityTabMarketplacePhase3(unittest.TestCase):
    """UI tests for badge/rating rendering and review interactions."""

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.refresh_patch = patch("ui.community_tab.CommunityTab.refresh_marketplace")
        self.refresh_marketplace_mock = self.refresh_patch.start()

        self.plugin_marketplace_patch = patch("ui.community_tab.PluginMarketplace")
        self.plugin_installer_patch = patch("ui.community_tab.PluginInstaller")
        self.plugin_loader_patch = patch("ui.community_tab.PluginLoader")
        self.preset_marketplace_patch = patch("ui.community_tab.PresetMarketplace")
        self.config_manager_patch = patch("ui.community_tab.ConfigManager")
        self.cloud_sync_patch = patch("ui.community_tab.CloudSyncManager")
        self.preset_manager_patch = patch("ui.community_tab.PresetManager")
        self.drift_detector_patch = patch("ui.community_tab.DriftDetector")

        self.mock_plugin_marketplace_cls = self.plugin_marketplace_patch.start()
        self.mock_plugin_installer_cls = self.plugin_installer_patch.start()
        self.mock_plugin_loader_cls = self.plugin_loader_patch.start()
        self.mock_preset_marketplace_cls = self.preset_marketplace_patch.start()
        self.mock_config_manager_cls = self.config_manager_patch.start()
        self.mock_cloud_sync_cls = self.cloud_sync_patch.start()
        self.mock_preset_manager_cls = self.preset_manager_patch.start()
        self.mock_drift_detector_cls = self.drift_detector_patch.start()

        self.mock_plugin_marketplace = Mock()
        self.mock_plugin_marketplace.search.return_value = MarketplaceResult(success=True, data=[])
        self.mock_plugin_marketplace.fetch_reviews.return_value = MarketplaceResult(success=True, data=[])
        self.mock_plugin_marketplace.get_rating_aggregate.return_value = MarketplaceResult(success=True, data=None)
        self.mock_plugin_marketplace.submit_review.return_value = MarketplaceResult(success=True, data={"id": "rev-1"})
        self.mock_plugin_marketplace_cls.return_value = self.mock_plugin_marketplace

        self.mock_plugin_loader = Mock()
        self.mock_plugin_loader.list_plugins.return_value = []
        self.mock_plugin_loader_cls.return_value = self.mock_plugin_loader

        self.mock_cloud_sync_cls.get_gist_token.return_value = ""
        self.mock_cloud_sync_cls.get_gist_id.return_value = ""

        from ui.community_tab import CommunityTab
        self.tab = CommunityTab()

    def tearDown(self):
        self.drift_detector_patch.stop()
        self.preset_manager_patch.stop()
        self.cloud_sync_patch.stop()
        self.config_manager_patch.stop()
        self.preset_marketplace_patch.stop()
        self.plugin_loader_patch.stop()
        self.plugin_installer_patch.stop()
        self.plugin_marketplace_patch.stop()
        self.refresh_patch.stop()

    def _select_test_preset(self):
        preset = _make_preset()
        plugin_meta = _make_plugin_metadata()
        self.tab.marketplace_plugin_metadata = {"test-plugin": plugin_meta}

        item = QListWidgetItem("test")
        item.setData(Qt.ItemDataRole.UserRole, preset)
        self.tab.on_marketplace_preset_selected(item)
        return preset, plugin_meta

    def test_list_row_renders_verified_badge_and_rating_summary(self):
        """Marketplace list rows include badge/rating summary text."""
        preset = _make_preset()
        self.tab.current_presets = [preset]
        self.tab.marketplace_plugin_metadata = {"test-plugin": _make_plugin_metadata()}

        self.tab.populate_marketplace_preset_list()

        row_text = self.tab.marketplace_preset_list.item(0).text()
        self.assertIn("Verified", row_text)
        self.assertIn("4.7/5", row_text)

    def test_detail_view_renders_rating_and_verification(self):
        """Detail panel shows verification + rating aggregate + fetched reviews."""
        self.mock_plugin_marketplace.get_rating_aggregate.return_value = MarketplaceResult(
            success=True,
            data=MarketplaceRatingAggregate(
                plugin_id="test-plugin",
                average_rating=4.8,
                rating_count=20,
                review_count=14,
                breakdown={5: 12, 4: 8},
            ),
        )
        self.mock_plugin_marketplace.fetch_reviews.return_value = MarketplaceResult(
            success=True,
            data=[
                MarketplaceReview(
                    plugin_id="test-plugin",
                    reviewer="Alice",
                    rating=5,
                    title="Great",
                    comment="Works as expected",
                    created_at="2026-02-12T01:00:00Z",
                )
            ],
        )

        self._select_test_preset()

        self.assertIn("Verified Publisher", self.tab.detail_verification.text())
        self.assertIn("4.8/5", self.tab.detail_rating_summary.text())
        self.assertIn("Alice", self.tab.reviews_text.toPlainText())
        self.assertTrue(self.tab.submit_review_btn.isEnabled())

    def test_submit_review_success_path(self):
        """Successful review submit sends payload and shows success feedback."""
        self._select_test_preset()
        self.tab.review_reviewer_input.setText("Alice")
        self.tab.review_rating_combo.setCurrentIndex(0)
        self.tab.review_title_input.setText("Great")
        self.tab.review_comment_input.setPlainText("Solid preset")

        self.tab.submit_marketplace_review()

        self.mock_plugin_marketplace.submit_review.assert_called_once_with(
            plugin_id="test-plugin",
            reviewer="Alice",
            rating=5,
            title="Great",
            comment="Solid preset",
        )
        self.assertIn("submitted successfully", self.tab.review_feedback_label.text().lower())

    def test_submit_review_validation_feedback_for_missing_reviewer(self):
        """Missing reviewer blocks submit and renders validation feedback."""
        self._select_test_preset()
        self.tab.review_reviewer_input.setText("")
        self.tab.review_rating_combo.setCurrentIndex(0)

        self.tab.submit_marketplace_review()

        self.mock_plugin_marketplace.submit_review.assert_not_called()
        self.assertIn("required", self.tab.review_feedback_label.text().lower())

    def test_review_error_states_render_with_backend_failures(self):
        """Aggregate/review backend failures are rendered in UI feedback text."""
        self.mock_plugin_marketplace.get_rating_aggregate.return_value = MarketplaceResult(
            success=False,
            error="Marketplace service unavailable",
        )
        self.mock_plugin_marketplace.fetch_reviews.return_value = MarketplaceResult(
            success=False,
            error="Network error: timeout",
        )

        self._select_test_preset()
        self.assertIn("Ratings unavailable", self.tab.reviews_summary_label.text())
        self.assertIn("Unable to load reviews", self.tab.reviews_text.toPlainText())
