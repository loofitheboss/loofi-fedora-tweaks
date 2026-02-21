"""
Favorites Manager — v31.0 Smart UX
Persists favorite/pinned tabs to JSON config.
"""

import json
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.expanduser("~/.config/loofi-fedora-tweaks")
_FAVORITES_FILE = os.path.join(_CONFIG_DIR, "favorites.json")


class FavoritesManager:
    """Manages favorite/pinned tabs with JSON persistence."""

    @staticmethod
    def _load() -> List[str]:
        """Load favorites list from disk."""
        try:
            if os.path.isfile(_FAVORITES_FILE):
                with open(_FAVORITES_FILE, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load favorites: %s", e)
        return []

    @staticmethod
    def _save(favorites: List[str]) -> None:
        """Save favorites list to disk."""
        try:
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            with open(_FAVORITES_FILE, "w") as f:
                json.dump(favorites, f, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to save favorites: %s", e)

    @classmethod
    def get_favorites(cls) -> List[str]:
        """
        Get list of favorite tab IDs.

        Returns:
            List of tab ID strings.
        """
        return cls._load()

    @classmethod
    def add_favorite(cls, tab_id: str) -> None:
        """
        Add a tab to favorites.

        Args:
            tab_id: Plugin/tab ID to add.
        """
        favorites = cls._load()
        if tab_id not in favorites:
            favorites.append(tab_id)
            cls._save(favorites)

    @classmethod
    def remove_favorite(cls, tab_id: str) -> None:
        """
        Remove a tab from favorites.

        Args:
            tab_id: Plugin/tab ID to remove.
        """
        favorites = cls._load()
        if tab_id in favorites:
            favorites.remove(tab_id)
            cls._save(favorites)

    @classmethod
    def is_favorite(cls, tab_id: str) -> bool:
        """
        Check if a tab is in favorites.

        Args:
            tab_id: Plugin/tab ID to check.

        Returns:
            True if the tab is a favorite.
        """
        return tab_id in cls._load()

    @classmethod
    def toggle_favorite(cls, tab_id: str) -> bool:
        """
        Toggle a tab's favorite status.

        Args:
            tab_id: Plugin/tab ID to toggle.

        Returns:
            True if tab is now a favorite, False if removed.
        """
        favorites = cls._load()
        if tab_id in favorites:
            favorites.remove(tab_id)
            cls._save(favorites)
            return False
        else:
            favorites.append(tab_id)
            cls._save(favorites)
            return True
