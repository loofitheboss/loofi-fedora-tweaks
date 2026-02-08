"""
App update checker - fetches latest release from GitHub API.
Part of v14.0 "Horizon Update".
"""
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

GITHUB_REPO = "loofitheboss/loofi-fedora-tweaks"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    release_notes: str
    download_url: str
    is_newer: bool


class UpdateChecker:
    """Check for application updates via GitHub releases API."""

    @staticmethod
    def parse_version(version_str: str) -> Tuple[int, ...]:
        """Parse a version string like '14.0.0' into a tuple of ints."""
        try:
            return tuple(int(p) for p in version_str.strip().lstrip("v").split("."))
        except (ValueError, AttributeError):
            return (0, 0, 0)

    @staticmethod
    def check_for_updates(timeout: int = 10) -> Optional[UpdateInfo]:
        """
        Check GitHub for the latest release.

        Returns UpdateInfo if check succeeds, None on failure.
        """
        from version import __version__

        try:
            req = urllib.request.Request(
                RELEASES_URL,
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "loofi-fedora-tweaks"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            latest_tag = data.get("tag_name", "")
            latest_version = latest_tag.lstrip("v")
            release_notes = data.get("body", "")
            html_url = data.get("html_url", "")

            current_tuple = UpdateChecker.parse_version(__version__)
            latest_tuple = UpdateChecker.parse_version(latest_version)

            return UpdateInfo(
                current_version=__version__,
                latest_version=latest_version,
                release_notes=release_notes,
                download_url=html_url,
                is_newer=latest_tuple > current_tuple,
            )

        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
                OSError, KeyError, ValueError) as exc:
            logger.debug("Update check failed: %s", exc)
            return None
