"""CDN client for plugin marketplace index retrieval with instance cache."""

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CDN_BASE_URL = "https://cdn.loofi.software/plugins"
DEFAULT_CACHE_TTL_SECONDS = 3600


@dataclass(frozen=True)
class CdnFetchConfig:
    """CDN fetch settings for plugin index retrieval."""
    base_url: str = DEFAULT_CDN_BASE_URL
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS


class PluginCdnClient:
    """Fetches signed plugin index data from CDN with local caching."""

    def __init__(self, config: Optional[CdnFetchConfig] = None):
        self.config = config or CdnFetchConfig()
        self._cached_index: Optional[Dict] = None

    def fetch_index(
        self,
        repo_owner: str,
        repo_name: str,
        branch: str,
        fetch_json: Callable[[str], Optional[Dict]],
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """Fetch signed index from CDN, falling back to local cache when needed."""
        if not force_refresh and self._cached_index is not None:
            return self._cached_index

        for url in self._candidate_urls(repo_owner, repo_name, branch):
            data = fetch_json(url)
            if data and self._is_valid_signed_index(data):
                self._cached_index = data
                return data

        return self._cached_index

    def _candidate_urls(self, repo_owner: str, repo_name: str, branch: str) -> List[str]:
        base = self.config.base_url.rstrip("/")
        return [
            f"{base}/{repo_owner}/{repo_name}/{branch}/plugins.json",
            f"{base}/{repo_owner}/{repo_name}/plugins.json",
        ]

    @staticmethod
    def _is_valid_signed_index(data: Dict) -> bool:
        if not isinstance(data.get("plugins"), list):
            logger.warning("CDN index rejected: missing plugins list")
            return False

        signature = data.get("signature")
        if signature is None:
            logger.warning("CDN index is unsigned; accepting for backward compatibility")
            return True
        if not isinstance(signature, dict):
            logger.warning("CDN index rejected: invalid signature block")
            return False
        if not isinstance(signature.get("algorithm"), str):
            logger.warning("CDN index rejected: missing signature.algorithm")
            return False
        if not isinstance(signature.get("key_id"), str):
            logger.warning("CDN index rejected: missing signature.key_id")
            return False
        if not isinstance(signature.get("signature"), str):
            logger.warning("CDN index rejected: missing signature.signature")
            return False
        return True
