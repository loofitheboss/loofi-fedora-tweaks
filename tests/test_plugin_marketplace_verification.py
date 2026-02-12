"""Tests for publisher verification extraction in utils.plugin_marketplace."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_marketplace import PluginMarketplace


def _plugin_with_verification() -> dict:
    """Create a valid plugin entry with nested verification payload."""
    return {
        "id": "verified-plugin",
        "name": "Verified Plugin",
        "description": "Plugin with publisher verification",
        "version": "1.0.0",
        "author": "Trusted Author",
        "category": "Utility",
        "download_url": "https://example.com/verified-plugin.tar.gz",
        "checksum_sha256": "a" * 64,
        "publisher_verification": {
            "verified": True,
            "publisher_id": "publisher-123",
            "badge": "verified",
            "signature": "a1b2c3d4e5f6a7b8c9d0",
            "trust_chain": ["root-ca", "marketplace-ca", "publisher-123"],
        },
    }


class TestPluginMarketplacePublisherVerification:
    """Coverage for publisher verification parsing states."""

    def test_parse_plugin_entry_keeps_verified_state_for_valid_signed_metadata(self):
        """Valid signed verification marks publisher as trusted."""
        marketplace = PluginMarketplace()
        entry = _plugin_with_verification()

        metadata = marketplace._parse_plugin_entry(entry)

        assert metadata is not None
        assert metadata.verified_publisher is True
        assert metadata.publisher_id == "publisher-123"
        assert metadata.publisher_badge == "verified"

    def test_parse_plugin_entry_rejects_invalid_signature_metadata(self):
        """Invalid signature metadata downgrades trusted state."""
        marketplace = PluginMarketplace()
        entry = _plugin_with_verification()
        entry["publisher_verification"]["signature"] = "short"

        metadata = marketplace._parse_plugin_entry(entry)

        assert metadata is not None
        assert metadata.verified_publisher is False
        assert metadata.publisher_id == "publisher-123"

    def test_parse_plugin_entry_rejects_missing_trust_chain_metadata(self):
        """Missing trust chain downgrades trusted state."""
        marketplace = PluginMarketplace()
        entry = _plugin_with_verification()
        entry["publisher_verification"]["trust_chain"] = []

        metadata = marketplace._parse_plugin_entry(entry)

        assert metadata is not None
        assert metadata.verified_publisher is False
        assert metadata.publisher_id == "publisher-123"

    def test_parse_plugin_entry_unsigned_publisher_path(self):
        """Unsigned publishers remain unverified and parse cleanly."""
        marketplace = PluginMarketplace()
        entry = _plugin_with_verification()
        entry["publisher_verification"] = {
            "verified": False,
            "publisher_id": "publisher-123",
            "badge": "community",
        }

        metadata = marketplace._parse_plugin_entry(entry)

        assert metadata is not None
        assert metadata.verified_publisher is False
        assert metadata.publisher_id == "publisher-123"
        assert metadata.publisher_badge == "community"
