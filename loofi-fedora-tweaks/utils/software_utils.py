"""
Software utility helpers.

Extracted from ui/software_tab.py in v34.0 to enforce
the 'no subprocess in UI' architectural rule.
"""

import shlex
import subprocess


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
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return False
