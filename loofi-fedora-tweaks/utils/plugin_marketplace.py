"""
Plugin marketplace API for GitHub-based plugin index.
Part of v26.0 Phase 1 (T7).
"""
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.plugins.integrity import IntegrityVerifier
from utils.plugin_cdn_client import PluginCdnClient

logger = logging.getLogger(__name__)

# Default marketplace configuration
DEFAULT_REPO_OWNER = "loofitheboss"
DEFAULT_REPO_NAME = "loofi-plugins"
DEFAULT_BRANCH = "main"
DEFAULT_MARKETPLACE_API_BASE = "https://api.loofi.software/marketplace/v1"


@dataclass(frozen=True)
class CdnIndexSignature:
    """Signature contract for CDN marketplace index verification."""
    algorithm: str = "ed25519"
    key_id: str = ""
    signature: str = ""


@dataclass(frozen=True)
class CdnMarketplaceIndex:
    """Signed CDN index schema contract (v27)."""
    version: str = "1.0"
    generated_at: str = ""
    plugins: List[Dict[str, Any]] = field(default_factory=list)
    signature: Optional[CdnIndexSignature] = None


@dataclass(frozen=True)
class MarketplacePublisherVerification:
    """Publisher trust/verification contract from marketplace provider."""
    verified: bool = False
    publisher_id: str = ""
    badge: str = ""
    signature: str = ""
    trust_chain: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class MarketplaceReview:
    """Review payload contract for read/write review integration."""
    plugin_id: str
    reviewer: str
    rating: int
    title: str = ""
    comment: str = ""
    created_at: str = ""
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class MarketplaceRatingAggregate:
    """Aggregate ratings payload contract for plugin listings/details."""
    plugin_id: str
    average_rating: float = 0.0
    rating_count: int = 0
    review_count: int = 0
    breakdown: Dict[int, int] = field(default_factory=dict)


@dataclass
class PluginMetadata:
    """Plugin metadata from marketplace index."""
    id: str = ""
    name: str = ""
    description: str = ""
    version: str = "0.0.0"
    author: str = ""
    category: str = "General"
    icon: str = "🔌"
    download_url: str = ""
    checksum_sha256: str = ""
    featured: bool = False
    tags: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)  # Plugin dependencies
    homepage: Optional[str] = None
    license: Optional[str] = None
    min_loofi_version: Optional[str] = None
    rating_average: Optional[float] = None
    rating_count: int = 0
    review_count: int = 0
    verified_publisher: bool = False
    publisher_id: Optional[str] = None
    publisher_badge: Optional[str] = None

    def __post_init__(self):
        """Backwards compatibility for call sites that provide only a subset of fields."""
        if not self.id and self.name:
            self.id = self.name.strip().lower().replace(" ", "-")
        if self.tags is None:
            self.tags = []
        if self.requires is None:
            self.requires = []


@dataclass
class MarketplaceResult:
    """Result of marketplace API operation."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class PluginMarketplace:
    """CDN-first plugin marketplace API with GitHub fallback."""

    def __init__(
        self,
        repo_owner: str = DEFAULT_REPO_OWNER,
        repo_name: str = DEFAULT_REPO_NAME,
        branch: str = DEFAULT_BRANCH,
        api_base_url: str = DEFAULT_MARKETPLACE_API_BASE,
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
        self.api_base_url = api_base_url.rstrip("/")
        self.base_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}"
        self.cdn_client = PluginCdnClient()
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

    def _post_json(self, url: str, payload: Dict[str, Any], timeout: int = 15) -> Optional[Dict]:
        """Send JSON POST request and return parsed response."""
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "User-Agent": "Loofi-Fedora-Tweaks",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                if not body:
                    return {}
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            logger.error("HTTP error posting to %s: %s", url, exc)
            raise
        except urllib.error.URLError as exc:
            logger.error("URL error posting to %s: %s", url, exc)
            raise
        except json.JSONDecodeError as exc:
            logger.error("JSON decode error posting to %s: %s", url, exc)
            return None
        except Exception as exc:
            logger.error("Unexpected POST error %s: %s", url, exc)
            return None

    @staticmethod
    def _map_http_error(exc: urllib.error.HTTPError) -> str:
        """Map HTTP status to stable user-facing marketplace API errors."""
        if exc.code == 400:
            return "Invalid request payload"
        if exc.code == 401:
            return "Authentication required for marketplace reviews"
        if exc.code == 403:
            return "Marketplace review operation is not allowed"
        if exc.code == 404:
            return "Plugin or review endpoint not found"
        if exc.code == 409:
            return "Review conflict detected"
        if exc.code == 422:
            return "Review validation failed"
        if exc.code >= 500:
            return "Marketplace service unavailable"
        return f"HTTP {exc.code}"

    @staticmethod
    def _validate_plugin_id(plugin_id: str) -> Optional[str]:
        if not isinstance(plugin_id, str) or not plugin_id.strip():
            return "Plugin ID is required"
        return None

    @staticmethod
    def _validate_reviewer(reviewer: str) -> Optional[str]:
        if not isinstance(reviewer, str) or not reviewer.strip():
            return "Reviewer name is required"
        if len(reviewer.strip()) > 80:
            return "Reviewer name is too long (max 80 chars)"
        return None

    @staticmethod
    def _validate_rating(rating: int) -> Optional[str]:
        try:
            parsed = int(rating)
        except (TypeError, ValueError):
            return "Rating must be an integer from 1 to 5"
        if parsed < 1 or parsed > 5:
            return "Rating must be between 1 and 5"
        return None

    def fetch_reviews(self, plugin_id: str, limit: int = 20, offset: int = 0) -> MarketplaceResult:
        """Fetch reviews for one plugin with pagination support."""
        plugin_error = self._validate_plugin_id(plugin_id)
        if plugin_error:
            return MarketplaceResult(success=False, error=plugin_error)
        if limit < 1 or limit > 100:
            return MarketplaceResult(success=False, error="Limit must be between 1 and 100")
        if offset < 0:
            return MarketplaceResult(success=False, error="Offset must be >= 0")

        url = f"{self.api_base_url}/plugins/{plugin_id}/reviews?limit={limit}&offset={offset}"
        try:
            payload = self._fetch_json(url)
            if payload is None:
                return MarketplaceResult(success=False, error="Failed to fetch reviews")

            reviews_data = payload.get("reviews", [])
            if not isinstance(reviews_data, list):
                return MarketplaceResult(success=False, error="Invalid reviews response format")

            reviews: List[MarketplaceReview] = []
            for entry in reviews_data:
                if not isinstance(entry, dict):
                    continue
                reviews.append(
                    MarketplaceReview(
                        plugin_id=str(entry.get("plugin_id", plugin_id)),
                        reviewer=str(entry.get("reviewer", "")),
                        rating=self._coerce_int(entry.get("rating"), default=0),
                        title=str(entry.get("title", "")),
                        comment=str(entry.get("comment", "")),
                        created_at=str(entry.get("created_at", "")),
                        updated_at=str(entry.get("updated_at")) if entry.get("updated_at") else None,
                    )
                )

            return MarketplaceResult(success=True, data=reviews)
        except urllib.error.HTTPError as exc:
            return MarketplaceResult(success=False, error=self._map_http_error(exc))
        except urllib.error.URLError as exc:
            return MarketplaceResult(success=False, error=f"Network error: {exc.reason}")
        except Exception as exc:
            return MarketplaceResult(success=False, error=f"Failed to fetch reviews: {exc}")

    def submit_review(
        self,
        plugin_id: str,
        reviewer: str,
        rating: int,
        title: str = "",
        comment: str = "",
    ) -> MarketplaceResult:
        """Submit a marketplace review for one plugin."""
        for validation in (
            self._validate_plugin_id(plugin_id),
            self._validate_reviewer(reviewer),
            self._validate_rating(rating),
        ):
            if validation:
                return MarketplaceResult(success=False, error=validation)
        if len(title or "") > 120:
            return MarketplaceResult(success=False, error="Review title is too long (max 120 chars)")
        if len(comment or "") > 5000:
            return MarketplaceResult(success=False, error="Review comment is too long (max 5000 chars)")

        payload = {
            "plugin_id": plugin_id,
            "reviewer": reviewer.strip(),
            "rating": int(rating),
            "title": (title or "").strip(),
            "comment": (comment or "").strip(),
        }
        url = f"{self.api_base_url}/plugins/{plugin_id}/reviews"
        try:
            response = self._post_json(url, payload)
            if response is None:
                return MarketplaceResult(success=False, error="Failed to submit review")
            return MarketplaceResult(success=True, data=response)
        except urllib.error.HTTPError as exc:
            return MarketplaceResult(success=False, error=self._map_http_error(exc))
        except urllib.error.URLError as exc:
            return MarketplaceResult(success=False, error=f"Network error: {exc.reason}")
        except Exception as exc:
            return MarketplaceResult(success=False, error=f"Failed to submit review: {exc}")

    def get_rating_aggregate(self, plugin_id: str) -> MarketplaceResult:
        """Fetch rating aggregate for one plugin."""
        plugin_error = self._validate_plugin_id(plugin_id)
        if plugin_error:
            return MarketplaceResult(success=False, error=plugin_error)

        url = f"{self.api_base_url}/plugins/{plugin_id}/ratings"
        try:
            payload = self._fetch_json(url)
            if payload is None:
                return MarketplaceResult(success=False, error="Failed to fetch rating aggregate")

            data = payload.get("aggregate", payload)
            if not isinstance(data, dict):
                return MarketplaceResult(success=False, error="Invalid aggregate response format")

            breakdown_raw = data.get("breakdown", {})
            if not isinstance(breakdown_raw, dict):
                breakdown_raw = {}

            aggregate = MarketplaceRatingAggregate(
                plugin_id=plugin_id,
                average_rating=float(data.get("average_rating", data.get("average", 0.0))),
                rating_count=self._coerce_int(data.get("rating_count", data.get("count", 0))),
                review_count=self._coerce_int(data.get("review_count", data.get("reviews", 0))),
                breakdown={self._coerce_int(k): self._coerce_int(v) for k, v in breakdown_raw.items()},
            )
            return MarketplaceResult(success=True, data=aggregate)
        except urllib.error.HTTPError as exc:
            return MarketplaceResult(success=False, error=self._map_http_error(exc))
        except urllib.error.URLError as exc:
            return MarketplaceResult(success=False, error=f"Network error: {exc.reason}")
        except (TypeError, ValueError):
            return MarketplaceResult(success=False, error="Invalid aggregate response format")
        except Exception as exc:
            return MarketplaceResult(success=False, error=f"Failed to fetch rating aggregate: {exc}")

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

            for required_field in required:
                if required_field not in entry:
                    logger.warning("Missing required field '%s' in plugin entry", required_field)
                    return None

            rating_average, rating_count, review_count = self._extract_rating_fields(entry)
            verified_publisher, publisher_id, publisher_badge = self._extract_publisher_fields(entry)

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
                min_loofi_version=entry.get("min_loofi_version"),
                rating_average=rating_average,
                rating_count=rating_count,
                review_count=review_count,
                verified_publisher=verified_publisher,
                publisher_id=publisher_id,
                publisher_badge=publisher_badge
            )

        except Exception as exc:
            logger.error("Failed to parse plugin entry: %s", exc)
            return None

    @staticmethod
    def _extract_rating_fields(entry: Dict) -> tuple[Optional[float], int, int]:
        """Read rating/review fields from nested or legacy index schema."""
        ratings = entry.get("ratings", {})
        if not isinstance(ratings, dict):
            ratings = {}

        average_rating_raw = ratings.get("average", entry.get("rating_average"))
        average_rating = None
        if average_rating_raw is not None:
            try:
                average_rating = float(average_rating_raw)
            except (TypeError, ValueError):
                average_rating = None

        return (
            average_rating,
            PluginMarketplace._coerce_int(ratings.get("count", entry.get("rating_count", 0))),
            PluginMarketplace._coerce_int(
                ratings.get("review_count", ratings.get("reviews", entry.get("review_count", 0)))
            ),
        )

    @staticmethod
    def _extract_publisher_fields(entry: Dict) -> tuple[bool, Optional[str], Optional[str]]:
        """Read publisher verification fields from nested or legacy index schema."""
        verification = entry.get("publisher_verification", {})
        if not isinstance(verification, dict):
            verification = {}

        publisher_id_raw = verification.get("publisher_id", entry.get("publisher_id"))
        publisher_badge_raw = verification.get("badge", entry.get("publisher_badge"))
        publisher_id = str(publisher_id_raw) if publisher_id_raw else None
        publisher_badge = str(publisher_badge_raw) if publisher_badge_raw else None

        declared_verified = bool(verification.get("verified", entry.get("verified_publisher", False)))
        signed_markers_present = (
            "signature" in verification
            or "trust_chain" in verification
        )

        verified_state = declared_verified
        if signed_markers_present:
            verification_result = IntegrityVerifier.verify_publisher_metadata(
                verified=declared_verified,
                publisher_id=publisher_id or "",
                signature=str(verification.get("signature", "") or ""),
                trust_chain=verification.get("trust_chain", []),
            )
            verified_state = bool(verification_result.success and verification_result.signature_valid)
            if declared_verified and not verified_state:
                logger.warning(
                    "Publisher verification rejected for plugin '%s': %s",
                    entry.get("id", "<unknown>"),
                    verification_result.error or "invalid publisher verification metadata",
                )

        return (
            verified_state,
            publisher_id,
            publisher_badge,
        )

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

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
            data = self.cdn_client.fetch_index(
                repo_owner=self.repo_owner,
                repo_name=self.repo_name,
                branch=self.branch,
                fetch_json=self._fetch_json,
                force_refresh=force_refresh
            )

            if data:
                logger.info("Fetched plugin index from CDN")
            else:
                fallback_url = f"{self.base_url}/plugins.json"
                logger.warning("CDN unavailable or invalid index, falling back to %s", fallback_url)
                data = self._fetch_json(fallback_url)

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
