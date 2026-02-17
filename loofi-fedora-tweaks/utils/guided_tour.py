"""
Guided Tour Manager — v47.0 UX Improvement.

Manages a first-run guided tour that highlights key UI elements
after the onboarding wizard completes. The tour shows a spotlight
overlay on important features like the sidebar, health score,
command palette, quick actions, and settings.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from utils.log import get_logger

logger = get_logger(__name__)

_CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
_TOUR_SENTINEL = _CONFIG_DIR / "tour_complete"


@dataclass
class TourStep:
    """A single step in the guided tour."""
    widget_name: str
    title: str
    description: str
    position: str  # "left", "right", "above", "below"


# Default tour steps highlighting key features
_DEFAULT_STEPS: List[TourStep] = [
    TourStep(
        widget_name="sidebar",
        title="Sidebar Navigation",
        description="Browse all available tools organized by category. "
                    "Use the search bar at the top to find features quickly.",
        position="right",
    ),
    TourStep(
        widget_name="healthScoreGauge",
        title="System Health Score",
        description="Your system's overall health at a glance. "
                    "Click the score to see a detailed breakdown with fix suggestions.",
        position="below",
    ),
    TourStep(
        widget_name="quickActionsGrid",
        title="Quick Actions",
        description="One-click access to common tasks like system updates, "
                    "cleanup, and configuration. Customize which actions appear here.",
        position="below",
    ),
    TourStep(
        widget_name="commandPalette",
        title="Command Palette (Ctrl+K)",
        description="Search and run any feature instantly. Press Ctrl+K "
                    "from anywhere to open. You can navigate tabs or run actions directly.",
        position="below",
    ),
    TourStep(
        widget_name="settingsTab",
        title="Settings & Preferences",
        description="Customize your experience level, theme, behavior, "
                    "and advanced options. You can always change your experience level here.",
        position="left",
    ),
]


class GuidedTourManager:
    """Manages guided tour state and step definitions."""

    @staticmethod
    def needs_tour() -> bool:
        """Check whether the guided tour should be shown.

        Returns:
            True if the tour has not been completed yet.
        """
        return not _TOUR_SENTINEL.exists()

    @staticmethod
    def mark_tour_complete() -> None:
        """Mark the guided tour as completed so it won't show again."""
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            _TOUR_SENTINEL.touch()
            logger.info("Guided tour marked as complete")
        except OSError as e:
            logger.debug("Failed to mark tour complete: %s", e)

    @staticmethod
    def reset_tour() -> None:
        """Reset the tour so it will show again on next launch."""
        try:
            if _TOUR_SENTINEL.exists():
                _TOUR_SENTINEL.unlink()
                logger.info("Guided tour reset — will show on next launch")
        except OSError as e:
            logger.debug("Failed to reset tour: %s", e)

    @staticmethod
    def get_tour_steps() -> List[TourStep]:
        """Return the ordered list of tour steps.

        Returns:
            List of TourStep objects defining the tour sequence.
        """
        return list(_DEFAULT_STEPS)

    @staticmethod
    def get_step_count() -> int:
        """Return the total number of tour steps.

        Returns:
            Number of steps in the tour.
        """
        return len(_DEFAULT_STEPS)
