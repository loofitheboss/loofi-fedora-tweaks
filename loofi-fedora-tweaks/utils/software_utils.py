"""
Software utility helpers.

Extracted from ui/software_tab.py in v34.0 to enforce
the 'no subprocess in UI' architectural rule.
"""

import shlex
import subprocess

from utils.log import get_logger

logger = get_logger(__name__)


class SoftwareUtils:
    """Static helpers for software/package checks."""

    @staticmethod
    def is_check_command_satisfied(cmd: str) -> bool:
        """Run an arbitrary check command and return True if it succeeds.

        Parameters
        ----------
        cmd:
            Shell-style command string (split via :func:`shlex.split`).
            Typically comes from an app catalog ``check_cmd`` field,
            e.g. ``"rpm -q gimp"`` or ``"which flatpak"``.

        Returns
        -------
        bool
            True if the command exits with code 0, False otherwise.
        """
        try:
            subprocess.run(
                shlex.split(cmd),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return False

    @staticmethod
    def get_fedora_version() -> str:
        """Detect the current Fedora release version.

        Returns
        -------
        str
            The Fedora version string (e.g. '41'), or '41' as fallback.
        """
        try:
            result = subprocess.run(
                ["rpm", "-E", "%fedora"],
                capture_output=True, text=True, timeout=10
            )
            version = result.stdout.strip()
            if version and version != "%fedora":
                return version
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to detect Fedora version: %s", e)
        return "41"
