"""
Gaming utility helpers.

Extracted from ui/gaming_tab.py in v34.0 to enforce
the 'no subprocess in UI' architectural rule.
"""

import subprocess
from typing import Literal


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
                capture_output=True, text=True,
            )
            if "active" in result.stdout:
                return "active"

            res_rpm = subprocess.run(
                ["rpm", "-q", "gamemode"],
                capture_output=True,
            )
            if res_rpm.returncode == 0:
                return "installed"

            return "missing"
        except Exception:
            return "error"
