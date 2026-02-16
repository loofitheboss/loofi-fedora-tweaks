"""
Gaming utility helpers.

Extracted from ui/gaming_tab.py in v34.0 to enforce
the 'no subprocess in UI' architectural rule.
"""

import logging
import subprocess
from typing import Literal

logger = logging.getLogger(__name__)


class GamingUtils:
    """Static helpers for gaming-related system checks."""

    @staticmethod
    def get_gamemode_status() -> Literal["active", "installed", "missing", "error"]:
        """Check GameMode installation and service status.

        Returns
        -------
        str
            One of:
            - ``"active"``    — gamemoded service is running
            - ``"installed"`` — package present but service inactive
            - ``"missing"``   — package not installed
            - ``"error"``     — detection failed
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "gamemoded"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if "active" in result.stdout:
                return "active"

            res_rpm = subprocess.run(
                ["rpm", "-q", "gamemode"],
                capture_output=True,
                timeout=600,
            )
            if res_rpm.returncode == 0:
                return "installed"

            return "missing"
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check GameMode status: %s", e)
            return "error"
