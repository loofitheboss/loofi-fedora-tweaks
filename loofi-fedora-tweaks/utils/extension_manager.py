"""
Desktop Extension Manager — GNOME Shell and KDE Plasma extension management.
Part of v37.0.0 "Pinnacle".

Provides a unified interface to browse, install, enable/disable, and remove
desktop environment extensions across GNOME and KDE.
"""

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import List

from utils.commands import CommandTuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Dataclasses
# ---------------------------------------------------------------------------

class DesktopEnvironment(Enum):
    """Supported desktop environments."""
    GNOME = "gnome"
    KDE = "kde"
    UNKNOWN = "unknown"


@dataclass
class ExtensionEntry:
    """Represents a desktop extension."""
    uuid: str
    name: str
    description: str = ""
    version: str = ""
    author: str = ""
    enabled: bool = False
    homepage: str = ""
    desktop: str = ""  # "gnome" or "kde"


# ---------------------------------------------------------------------------
# ExtensionManager
# ---------------------------------------------------------------------------

class ExtensionManager:
    """Unified extension manager for GNOME Shell and KDE Plasma.

    All public methods are ``@staticmethod`` so the class can be used without
    instantiation, consistent with other ``utils/*`` managers.
    """

    # -----------------------------------------------------------------
    # Desktop environment detection
    # -----------------------------------------------------------------

    @staticmethod
    def detect_desktop() -> DesktopEnvironment:
        """Detect the current desktop environment.

        Checks ``$XDG_CURRENT_DESKTOP`` and falls back to session info.

        Returns:
            DesktopEnvironment enum value.
        """
        xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "gnome" in xdg:
            return DesktopEnvironment.GNOME
        if "kde" in xdg or "plasma" in xdg:
            return DesktopEnvironment.KDE

        # Fallback: check session type
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        if "gnome" in session:
            return DesktopEnvironment.GNOME
        if "plasma" in session or "kde" in session:
            return DesktopEnvironment.KDE

        return DesktopEnvironment.UNKNOWN

    @staticmethod
    def is_supported() -> bool:
        """Check if extension management is supported on this system."""
        de = ExtensionManager.detect_desktop()
        if de == DesktopEnvironment.GNOME:
            return shutil.which("gnome-extensions") is not None
        if de == DesktopEnvironment.KDE:
            return shutil.which("plasmapkg2") is not None
        return False

    # -----------------------------------------------------------------
    # List extensions
    # -----------------------------------------------------------------

    @staticmethod
    def list_installed() -> List[ExtensionEntry]:
        """List installed extensions for the current desktop.

        Returns:
            List of ExtensionEntry with enabled/disabled state.
        """
        de = ExtensionManager.detect_desktop()
        if de == DesktopEnvironment.GNOME:
            return ExtensionManager._list_gnome()
        if de == DesktopEnvironment.KDE:
            return ExtensionManager._list_kde()
        return []

    @staticmethod
    def _list_gnome() -> List[ExtensionEntry]:
        """List GNOME Shell extensions via gnome-extensions."""
        extensions: List[ExtensionEntry] = []
        if not shutil.which("gnome-extensions"):
            return extensions

        try:
            result = subprocess.run(
                ["gnome-extensions", "list", "--details"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                current: dict = {}
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        if current.get("uuid"):
                            extensions.append(ExtensionEntry(
                                uuid=current.get("uuid", ""),
                                name=current.get("name", current.get("uuid", "")),
                                description=current.get("description", ""),
                                version=current.get("version", ""),
                                enabled=current.get("state", "").lower() == "enabled",
                                desktop="gnome",
                            ))
                        current = {}
                        continue

                    if "@" in line and "." in line and not line.startswith(" "):
                        current = {"uuid": line}
                    elif ":" in line:
                        key, _, val = line.partition(":")
                        current[key.strip().lower()] = val.strip()

                # Don't forget last entry
                if current.get("uuid"):
                    extensions.append(ExtensionEntry(
                        uuid=current.get("uuid", ""),
                        name=current.get("name", current.get("uuid", "")),
                        description=current.get("description", ""),
                        version=current.get("version", ""),
                        enabled=current.get("state", "").lower() == "enabled",
                        desktop="gnome",
                    ))
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to list GNOME extensions: %s", e)
        return extensions

    @staticmethod
    def _list_kde() -> List[ExtensionEntry]:
        """List KDE Plasma widgets/extensions."""
        extensions: List[ExtensionEntry] = []
        if not shutil.which("plasmapkg2"):
            return extensions

        try:
            result = subprocess.run(
                ["plasmapkg2", "--list"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if not line or line.startswith("-") or line.startswith("Listing"):
                        continue
                    # plasmapkg2 --list outputs: "org.kde.plasma.widget.name"
                    uuid = line.strip()
                    name = uuid.rsplit(".", 1)[-1] if "." in uuid else uuid
                    extensions.append(ExtensionEntry(
                        uuid=uuid,
                        name=name,
                        enabled=True,  # KDE doesn't easily expose enabled state
                        desktop="kde",
                    ))
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to list KDE extensions: %s", e)
        return extensions

    # -----------------------------------------------------------------
    # Install / Remove / Enable / Disable
    # -----------------------------------------------------------------

    @staticmethod
    def install(uuid: str) -> CommandTuple:
        """Build command to install an extension.

        Args:
            uuid: Extension UUID (GNOME) or package ID (KDE).

        Returns:
            CommandTuple (binary, args, description).
        """
        de = ExtensionManager.detect_desktop()
        if de == DesktopEnvironment.GNOME:
            return ("gnome-extensions", ["install", uuid],
                    f"Installing GNOME extension {uuid}...")
        if de == DesktopEnvironment.KDE:
            return ("plasmapkg2", ["--install", uuid],
                    f"Installing KDE widget {uuid}...")
        return ("echo", ["Extension management not supported"],
                "No supported desktop environment detected")

    @staticmethod
    def remove(uuid: str) -> CommandTuple:
        """Build command to remove an extension.

        Args:
            uuid: Extension UUID.

        Returns:
            CommandTuple (binary, args, description).
        """
        de = ExtensionManager.detect_desktop()
        if de == DesktopEnvironment.GNOME:
            return ("gnome-extensions", ["uninstall", uuid],
                    f"Removing GNOME extension {uuid}...")
        if de == DesktopEnvironment.KDE:
            return ("plasmapkg2", ["--remove", uuid],
                    f"Removing KDE widget {uuid}...")
        return ("echo", ["Extension management not supported"],
                "No supported desktop environment detected")

    @staticmethod
    def enable(uuid: str) -> CommandTuple:
        """Build command to enable an extension.

        Args:
            uuid: Extension UUID.

        Returns:
            CommandTuple (binary, args, description).
        """
        de = ExtensionManager.detect_desktop()
        if de == DesktopEnvironment.GNOME:
            return ("gnome-extensions", ["enable", uuid],
                    f"Enabling GNOME extension {uuid}...")
        if de == DesktopEnvironment.KDE:
            # KDE doesn't have a simple enable/disable CLI
            return ("echo", [f"KDE widget {uuid} is always active"],
                    f"KDE widgets are always active: {uuid}")
        return ("echo", ["Extension management not supported"],
                "No supported desktop environment detected")

    @staticmethod
    def disable(uuid: str) -> CommandTuple:
        """Build command to disable an extension.

        Args:
            uuid: Extension UUID.

        Returns:
            CommandTuple (binary, args, description).
        """
        de = ExtensionManager.detect_desktop()
        if de == DesktopEnvironment.GNOME:
            return ("gnome-extensions", ["disable", uuid],
                    f"Disabling GNOME extension {uuid}...")
        if de == DesktopEnvironment.KDE:
            return ("echo", [f"KDE widget {uuid} cannot be disabled via CLI"],
                    f"KDE widgets cannot be individually disabled: {uuid}")
        return ("echo", ["Extension management not supported"],
                "No supported desktop environment detected")

    # -----------------------------------------------------------------
    # Search / Available (GNOME Extensions API)
    # -----------------------------------------------------------------

    @staticmethod
    def search_available(query: str, page: int = 1) -> List[ExtensionEntry]:
        """Search for available GNOME Shell extensions.

        Uses the GNOME Extensions website API. KDE store search is not
        implemented (requires web scraping).

        Args:
            query: Search query string.
            page: Page number for pagination.

        Returns:
            List of available extensions matching the query.
        """
        de = ExtensionManager.detect_desktop()
        if de != DesktopEnvironment.GNOME:
            logger.info("Extension search only supported on GNOME")
            return []

        extensions: List[ExtensionEntry] = []
        try:
            # Use gnome-extensions or direct API call via curl
            import urllib.request
            import urllib.parse
            url = (
                f"https://extensions.gnome.org/extension-query/"
                f"?search={urllib.parse.quote(query)}&page={page}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Loofi-Fedora-Tweaks/37.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                for ext in data.get("extensions", []):
                    extensions.append(ExtensionEntry(
                        uuid=ext.get("uuid", ""),
                        name=ext.get("name", ""),
                        description=ext.get("description", "")[:200],
                        author=ext.get("creator", ""),
                        homepage=f"https://extensions.gnome.org/extension/{ext.get('pk', '')}/",
                        desktop="gnome",
                    ))
        except Exception as e:
            logger.error("Failed to search GNOME extensions: %s", e)
        return extensions
