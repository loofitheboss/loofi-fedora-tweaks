"""
Plugin marketplace API for GitHub-based plugin index.
Part of v26.0 Phase 1 (T7).
"""
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default marketplace configuration
DEFAULT_REPO_OWNER = "loofitheboss"
DEFAULT_REPO_NAME = "loofi-plugins"
DEFAULT_BRANCH = "main"


@dataclass
class PluginMetadata:
    """Plugin metadata from marketplace index."""
    id: str
    name: str
    description: str
    version: str
    author: str
    category: str
    icon: str
    download_url: str
    checksum_sha256: str
    featured: bool
    tags: List[str]
    requires: List[str]  # Plugin dependencies
    homepage: Optional[str] = None
    license: Optional[str] = None
    min_loofi_version: Optional[str] = None


@dataclass
class MarketplaceResult:
    """Result of marketplace API operation."""
    success: bool
    data: Optional[List[PluginMetadata]] = None
    error: Optional[str] = None


class PluginMarketplace:
    """GitHub-based plugin marketplace API."""

    def __init__(
        self,
        repo_owner: str = DEFAULT_REPO_OWNER,
        repo_name: str = DEFAULT_REPO_NAME,
        branch: str = DEFAULT_BRANCH
    ):
        """
        Initialize marketplace API.

        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            branch: Git branch to fetch from
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.base_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}"
        self._cache: Optional[List[PluginMetadata]] = None

    def _fetch_json(self, url: str, timeout: int = 10) -> Optional[Dict]:
        """
        Fetch JSON data from URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON dict or None on failure
        """
        try:
            logger.debug("Fetching %s", url)

            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Loofi-Fedora-Tweaks'}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                return json.loads(data.decode('utf-8'))

        except urllib.error.HTTPError as exc:
            logger.error("HTTP error fetching %s: %s", url, exc)
            return None
        except urllib.error.URLError as exc:
            logger.error("URL error fetching %s: %s", url, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.error("JSON decode error: %s", exc)
            return None
        except Exception as exc:
            logger.error("Unexpected error fetching %s: %s", url, exc)
            return None

    def _parse_plugin_entry(self, entry: Dict) -> Optional[PluginMetadata]:
        """
        Parse plugin entry from index JSON.

        Args:
            entry: Dictionary with plugin metadata

        Returns:
            PluginMetadata or None if invalid
        """
        try:
            # Required fields
            required = ["id", "name", "description", "version", "author", "category",
                        "download_url", "checksum_sha256"]

            for field in required:
                if field not in entry:
                    logger.warning("Missing required field '%s' in plugin entry", field)
                    return None

            return PluginMetadata(
                id=entry["id"],
                name=entry["name"],
                description=entry["description"],
                version=entry["version"],
                author=entry["author"],
                category=entry["category"],
                icon=entry.get("icon", "🔌"),
                download_url=entry["download_url"],
                checksum_sha256=entry["checksum_sha256"],
                featured=entry.get("featured", False),
                tags=entry.get("tags", []),
                requires=entry.get("requires", []),
                homepage=entry.get("homepage"),
                license=entry.get("license"),
                min_loofi_version=entry.get("min_loofi_version")
            )

        except Exception as exc:
            logger.error("Failed to parse plugin entry: %s", exc)
            return None

    def fetch_index(self, force_refresh: bool = False) -> MarketplaceResult:
        """
        Fetch complete plugin index from marketplace.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            MarketplaceResult with list of all available plugins
        """
        # Return cached data if available
        if not force_refresh and self._cache is not None:
            logger.debug("Returning cached plugin index (%d plugins)", len(self._cache))
            return MarketplaceResult(success=True, data=self._cache)

        try:
            url = f"{self.base_url}/plugins.json"
            logger.info("Fetching plugin index from %s", url)

            data = self._fetch_json(url)

            if not data:
                return MarketplaceResult(
                    success=False,
                    error="Failed to fetch plugin index (network error or invalid JSON)"
                )

            if "plugins" not in data:
                logger.error("Invalid index format: missing 'plugins' key")
                return MarketplaceResult(
                    success=False,
                    error="Invalid index format"
                )

            plugins = []
            for entry in data["plugins"]:
                plugin = self._parse_plugin_entry(entry)
                if plugin:
                    plugins.append(plugin)

            logger.info("Fetched %d plugins from marketplace", len(plugins))

            # Cache the result
            self._cache = plugins

            return MarketplaceResult(success=True, data=plugins)

        except Exception as exc:
            logger.error("Failed to fetch plugin index: %s", exc)
            return MarketplaceResult(
                success=False,
                error=f"Failed to fetch index: {exc}"
            )

    def search(self, query: str = "", category: Optional[str] = None) -> MarketplaceResult:
        """
        Search plugins by name, description, or tags.

        Args:
            query: Search query string (case-insensitive)
            category: Optional category filter

        Returns:
            MarketplaceResult with filtered plugin list
        """
        # Fetch full index first
        index_result = self.fetch_index()

        if not index_result.success or not index_result.data:
            return index_result
        query_lower = query.lower() if query else ""
        results = []

        for plugin in index_result.data:
            # Category filter
            if category and plugin.category.lower() != category.lower():
                continue

            # Search in name, description, tags (if query provided)
            if not query or (
                query_lower in plugin.name.lower()
                or query_lower in plugin.description.lower()
                or any(query_lower in tag.lower() for tag in plugin.tags)
            ):
                results.append(plugin)

        logger.info("Search '%s' found %d results", query, len(results))

        return MarketplaceResult(success=True, data=results)

    def get_plugin(self, plugin_id: str) -> MarketplaceResult:
        """
        Get detailed information for a specific plugin.

        Args:
            plugin_id: Plugin ID to lookup

        Returns:
            MarketplaceResult with single plugin or error
        """
        index_result = self.fetch_index()

        if not index_result.success:
            return MarketplaceResult(
                success=False,
                error="Failed to fetch plugin index"
            )

        if index_result.data is None:
            return MarketplaceResult(
                success=False,
                error="Failed to fetch plugin index"
            )

        for plugin in index_result.data:
            if plugin.id == plugin_id:
                logger.debug("Found plugin info for %s", plugin_id)
                return MarketplaceResult(success=True, data=[plugin])

        logger.warning("Plugin not found: %s", plugin_id)
        return MarketplaceResult(
            success=False,
            error=f"Plugin '{plugin_id}' not found in marketplace"
        )

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginMetadata]:
        """
        Get detailed information for a specific plugin (legacy method).

        Args:
            plugin_id: Plugin ID to lookup

        Returns:
            PluginMetadata or None if not found
        """
        result = self.get_plugin(plugin_id)
        if result.success and result.data:
            return result.data[0]
        return None

    def download_plugin(self, plugin_id: str, destination: Path, version: Optional[str] = None) -> MarketplaceResult:
        """
        Download plugin archive from marketplace.

        Args:
            plugin_id: Plugin ID to download
            destination: Path where archive will be saved
            version: Optional specific version (defaults to latest)

        Returns:
            MarketplaceResult with success status
        """
        try:
            # Get plugin info
            plugin = self.get_plugin_info(plugin_id)

            if not plugin:
                return MarketplaceResult(
                    success=False,
                    error=f"Plugin not found: {plugin_id}"
                )

            # Version check (if specific version requested)
            if version and plugin.version != version:
                logger.warning("Requested version %s, but marketplace has %s", version, plugin.version)
                # Could implement version-specific downloads later

            logger.info("Downloading %s v%s from %s", plugin_id, plugin.version, plugin.download_url)

            # Download archive
            req = urllib.request.Request(
                plugin.download_url,
                headers={'User-Agent': 'Loofi-Fedora-Tweaks'}
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with open(destination, 'wb') as f:
                    f.write(response.read())

            logger.info("Downloaded %s to %s", plugin_id, destination)

            # Return plugin metadata for checksum verification
            return MarketplaceResult(success=True, data=[plugin])

        except urllib.error.HTTPError as exc:
            logger.error("HTTP error downloading %s: %s", plugin_id, exc)
            return MarketplaceResult(
                success=False,
                error=f"Download failed: HTTP {exc.code}"
            )
        except urllib.error.URLError as exc:
            logger.error("URL error downloading %s: %s", plugin_id, exc)
            return MarketplaceResult(
                success=False,
                error=f"Network error: {exc.reason}"
            )
        except OSError as exc:
            logger.error("Failed to write %s: %s", destination, exc)
            return MarketplaceResult(
                success=False,
                error=f"Failed to save archive: {exc}"
            )
        except Exception as exc:
            logger.error("Unexpected error downloading %s: %s", plugin_id, exc)
            return MarketplaceResult(
                success=False,
                error=f"Download error: {exc}"
            )

    def get_featured(self) -> MarketplaceResult:
        """
        Get list of featured plugins.

        Returns:
            MarketplaceResult with featured plugins
        """
        index_result = self.fetch_index()

        if not index_result.success or not index_result.data:
            return index_result

        featured = [p for p in index_result.data if p.featured]

        logger.info("Found %d featured plugins", len(featured))

        return MarketplaceResult(success=True, data=featured)

    def get_categories(self) -> List[str]:
        """
        Get list of all available plugin categories.

        Returns:
            List of category names
        """
        index_result = self.fetch_index()

        if not index_result.success or not index_result.data:
            return []

        categories = sorted(set(p.category for p in index_result.data))

        logger.debug("Found %d categories", len(categories))

        return categories
