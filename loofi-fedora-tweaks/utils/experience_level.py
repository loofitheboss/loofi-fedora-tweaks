"""
Experience Level Manager — v47.0 UX Improvement.

Provides a three-tier experience level system (Beginner, Intermediate, Advanced)
that controls which tabs are visible in the sidebar. Beginners see ~12 essential
tabs, Intermediate adds development and customization tabs, and Advanced shows
all 28 tabs.
"""

from enum import Enum
from typing import List

from utils.log import get_logger
from utils.settings import SettingsManager

logger = get_logger(__name__)

# Settings key for experience level persistence
_SETTINGS_KEY = "experience_level"


class ExperienceLevel(Enum):
    """User experience level controlling sidebar tab visibility."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# Tab IDs visible at each experience level (cumulative).
# BEGINNER tabs are always visible; INTERMEDIATE adds more; ADVANCED shows all.
_BEGINNER_TABS: List[str] = [
    "dashboard",
    "system-info",
    "software",
    "hardware",
    "network",
    "security",
    "backup",
    "settings",
    "storage",
    "performance",
    "desktop",
    "maintenance",
]

_INTERMEDIATE_TABS: List[str] = _BEGINNER_TABS + [
    "development",
    "extensions",
    "gaming",
    "profiles",
    "virtualization",
    "snapshot",
    "monitor",
    "diagnostics",
]


class ExperienceLevelManager:
    """Manages user experience level and tab visibility filtering."""

    @staticmethod
    def get_level() -> ExperienceLevel:
        """Get the current experience level from settings.

        Returns:
            Current ExperienceLevel, defaults to BEGINNER if unset.
        """
        mgr = SettingsManager.instance()
        raw = mgr.get(_SETTINGS_KEY, ExperienceLevel.BEGINNER.value)
        try:
            return ExperienceLevel(raw)
        except ValueError:
            logger.debug("Unknown experience level '%s', defaulting to BEGINNER", raw)
            return ExperienceLevel.BEGINNER

    @staticmethod
    def set_level(level: ExperienceLevel) -> None:
        """Persist the experience level to settings.

        Args:
            level: The experience level to set.
        """
        mgr = SettingsManager.instance()
        mgr.set(_SETTINGS_KEY, level.value)
        mgr.save()
        logger.info("Experience level set to %s", level.value)

    @staticmethod
    def get_visible_tabs(level: ExperienceLevel) -> List[str]:
        """Return the list of tab IDs visible at the given experience level.

        Args:
            level: The experience level.

        Returns:
            List of tab ID strings that should be visible.
            For ADVANCED, returns an empty list (meaning show all tabs).
        """
        if level == ExperienceLevel.BEGINNER:
            return list(_BEGINNER_TABS)
        elif level == ExperienceLevel.INTERMEDIATE:
            return list(_INTERMEDIATE_TABS)
        # ADVANCED: empty list signals "show everything"
        return []

    @staticmethod
    def is_tab_visible(tab_id: str, level: ExperienceLevel, favorites: "List[str] | None" = None) -> bool:
        """Check if a specific tab should be visible at the given level.

        Favorited tabs are always visible regardless of experience level.

        Args:
            tab_id: The plugin/tab ID to check.
            level: The current experience level.
            favorites: Optional list of favorited tab IDs (always visible).

        Returns:
            True if the tab should be shown.
        """
        if favorites and tab_id in favorites:
            return True
        if level == ExperienceLevel.ADVANCED:
            return True
        visible = ExperienceLevelManager.get_visible_tabs(level)
        return tab_id in visible

    @staticmethod
    def get_all_declared_tab_ids() -> set:
        """Return all tab IDs declared in any experience level list.

        Returns:
            Set of tab ID strings from all level lists. INTERMEDIATE is the
            superset of BEGINNER, so this returns the INTERMEDIATE set.
        """
        return set(_INTERMEDIATE_TABS)

    @staticmethod
    def get_default_for_profile(profile_name: str) -> ExperienceLevel:
        """Suggest an experience level based on the wizard's use-case profile.

        Args:
            profile_name: One of "gaming", "development", "daily", "server", "minimal".

        Returns:
            Suggested ExperienceLevel for the profile.
        """
        mapping = {
            "server": ExperienceLevel.ADVANCED,
            "development": ExperienceLevel.INTERMEDIATE,
            "gaming": ExperienceLevel.INTERMEDIATE,
            "daily": ExperienceLevel.BEGINNER,
            "minimal": ExperienceLevel.BEGINNER,
        }
        return mapping.get(profile_name.lower(), ExperienceLevel.BEGINNER)
