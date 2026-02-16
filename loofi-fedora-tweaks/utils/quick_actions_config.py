"""
Quick Actions Config — v31.0 Smart UX
Configurable quick actions grid for the Dashboard tab.
"""

import json
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.expanduser("~/.config/loofi-fedora-tweaks")
_ACTIONS_FILE = os.path.join(_CONFIG_DIR, "quick_actions.json")


class QuickActionsConfig:
    """Manages configurable quick actions for the Dashboard."""

    @staticmethod
    def default_actions() -> List[Dict[str, str]]:
        """
        Return the default quick actions.

        Returns:
            List of action dictionaries with id, label, icon, color, target_tab.
        """
        return [
            {
                "id": "clean_cache",
                "label": "Clean Cache",
                "icon": "🧹",
                "color": "#e8b84d",
                "target_tab": "Maintenance",
            },
            {
                "id": "update_all",
                "label": "Update All",
                "icon": "🔄",
                "color": "#39c5cf",
                "target_tab": "Maintenance",
            },
            {
                "id": "power_profile",
                "label": "Power Profile",
                "icon": "🔋",
                "color": "#3dd68c",
                "target_tab": "Hardware",
            },
            {
                "id": "gaming_mode",
                "label": "Gaming Mode",
                "icon": "🎮",
                "color": "#e8556d",
                "target_tab": "Gaming",
            },
        ]

    @classmethod
    def get_actions(cls) -> List[Dict[str, str]]:
        """
        Load configured quick actions from disk.
        Falls back to defaults if no config exists.

        Returns:
            List of action dictionaries.
        """
        try:
            if os.path.isfile(_ACTIONS_FILE):
                with open(_ACTIONS_FILE, "r") as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load quick actions config: %s", e)
        return cls.default_actions()

    @classmethod
    def set_actions(cls, actions: List[Dict[str, str]]) -> None:
        """
        Save quick actions configuration to disk.

        Args:
            actions: List of action dictionaries to save.
        """
        try:
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            with open(_ACTIONS_FILE, "w") as f:
                json.dump(actions, f, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to save quick actions config: %s", e)

    @classmethod
    def reset_to_defaults(cls) -> List[Dict[str, str]]:
        """
        Reset quick actions to defaults and save.

        Returns:
            The default actions list.
        """
        defaults = cls.default_actions()
        cls.set_actions(defaults)
        return defaults

    @staticmethod
    def validate_action(action: dict) -> bool:
        """
        Validate that an action dict has all required fields.

        Args:
            action: Action dictionary to validate.

        Returns:
            True if valid, False otherwise.
        """
        required = {"id", "label", "icon", "color", "target_tab"}
        return required.issubset(action.keys())
