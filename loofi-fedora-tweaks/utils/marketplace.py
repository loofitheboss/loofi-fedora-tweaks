"""
Preset Marketplace - Community preset sharing via GitHub.
Browse, download, and share system presets with the community.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Any
from datetime import datetime
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


@dataclass
class CommunityPreset:
    """A preset from the community marketplace."""
    id: str
    name: str
    author: str
    description: str
    category: str  # gaming, privacy, performance, minimal, etc.
    download_count: int
    stars: int
    created_at: str
    updated_at: str
    download_url: str
    tags: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> "CommunityPreset":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unknown"),
            author=data.get("author", "Anonymous"),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            download_count=data.get("download_count", 0),
            stars=data.get("stars", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            download_url=data.get("download_url", ""),
            tags=data.get("tags", [])
        )


@dataclass
class MarketplaceResult:
    """Result of a marketplace operation."""
    success: bool
    message: str
    data: Any = None


class PresetMarketplace:
    """
    Community preset marketplace powered by GitHub.

    Uses a dedicated GitHub repo to store community presets:
    - Presets stored as JSON files
    - Index file for browsing
    - Stars/downloads tracked via GitHub API
    """

    # GitHub-based preset repository
    REPO_OWNER = "loofitheboss"
    REPO_NAME = "loofi-presets"
    BRANCH = "main"

    BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}"
    API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

    # Local cache
    CACHE_DIR = Path.home() / ".local/share/loofi-fedora-tweaks/marketplace"
    INDEX_CACHE = CACHE_DIR / "index.json"
    CACHE_TTL = 3600  # 1 hour

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _resolve_writable_presets_dir() -> Path:
        """Resolve a writable presets directory with sandbox-safe fallback."""
        primary = Path.home() / ".local/share/loofi-fedora-tweaks/presets"
        try:
            primary.mkdir(parents=True, exist_ok=True)
            probe = primary / ".write_test"
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            probe.unlink(missing_ok=True)
            return primary
        except OSError as e:
            logger.debug("Primary presets dir unavailable, using /tmp fallback: %s", e)
            fallback = Path("/tmp/loofi-fedora-tweaks/presets")
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def fetch_index(self, force_refresh: bool = False) -> MarketplaceResult:
        """
        Fetch the preset index from the marketplace.

        Args:
            force_refresh: If True, bypass cache.

        Returns:
            MarketplaceResult with list of CommunityPreset.
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            try:
                with open(self.INDEX_CACHE, "r") as f:
                    data = json.load(f)
                presets = [CommunityPreset.from_dict(p) for p in data.get("presets", [])]
                return MarketplaceResult(True, "Loaded from cache", presets)
            except (OSError, json.JSONDecodeError) as e:
                logger.debug("Failed to read marketplace cache: %s", e)

        # Fetch from GitHub
        try:
            url = f"{self.BASE_URL}/index.json"
            req = urllib.request.Request(url, headers={"User-Agent": "LoofiTweaks/7.0"})

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            # Cache the result
            with open(self.INDEX_CACHE, "w") as f:
                json.dump(data, f)

            presets = [CommunityPreset.from_dict(p) for p in data.get("presets", [])]
            return MarketplaceResult(True, f"Fetched {len(presets)} presets", presets)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Repository or index doesn't exist yet
                return MarketplaceResult(True, "Marketplace is empty", [])
            return MarketplaceResult(False, f"HTTP Error: {e.code}")
        except urllib.error.URLError as e:
            return MarketplaceResult(False, f"Network error: {e.reason}")
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            return MarketplaceResult(False, f"Error: {str(e)}")

    def download_preset(self, preset: CommunityPreset) -> MarketplaceResult:
        """
        Download a preset from the marketplace.

        Args:
            preset: The CommunityPreset to download.

        Returns:
            MarketplaceResult with the preset data.
        """
        try:
            req = urllib.request.Request(
                preset.download_url,
                headers={"User-Agent": "LoofiTweaks/7.0"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            # Save to local presets directory (fallback when HOME is not writable)
            presets_dir = self._resolve_writable_presets_dir()

            # Use preset ID as filename
            preset_file = presets_dir / f"{preset.id}.json"
            with open(preset_file, "w") as f:
                json.dump(data, f, indent=2)

            return MarketplaceResult(
                True,
                f"Downloaded: {preset.name}",
                {"path": str(preset_file), "data": data}
            )

        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            return MarketplaceResult(False, f"Download failed: {str(e)}")

    def search_presets(self, query: str = "", category: str = "") -> MarketplaceResult:
        """
        Search presets by name, description, or category.

        Args:
            query: Search query string.
            category: Filter by category.

        Returns:
            MarketplaceResult with filtered presets.
        """
        result = self.fetch_index()
        if not result.success:
            return result

        presets = result.data or []

        if category:
            presets = [p for p in presets if p.category.lower() == category.lower()]

        if query:
            query_lower = query.lower()
            presets = [
                p for p in presets
                if query_lower in p.name.lower()
                or query_lower in p.description.lower()
                or any(query_lower in tag.lower() for tag in p.tags)
            ]

        return MarketplaceResult(True, f"Found {len(presets)} presets", presets)

    def get_categories(self) -> List[str]:
        """Get list of available preset categories."""
        return [
            "gaming",
            "privacy",
            "performance",
            "minimal",
            "developer",
            "multimedia",
            "server",
            "general"
        ]

    def _is_cache_valid(self) -> bool:
        """Check if the index cache is still valid."""
        if not self.INDEX_CACHE.exists():
            return False

        mtime = self.INDEX_CACHE.stat().st_mtime
        age = datetime.now().timestamp() - mtime
        return age < self.CACHE_TTL

    def get_featured(self) -> MarketplaceResult:
        """Get featured/popular presets."""
        result = self.fetch_index()
        if not result.success:
            return result

        presets = result.data or []
        # Sort by stars + downloads
        presets.sort(key=lambda p: p.stars + p.download_count, reverse=True)

        return MarketplaceResult(True, "Featured presets", presets[:10])
