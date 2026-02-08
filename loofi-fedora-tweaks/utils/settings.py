"""
Settings Manager - Persistent application settings with JSON storage.
Part of v13.5 "UX Polish" update.

Provides a singleton SettingsManager that persists user preferences
to ~/.config/loofi-fedora-tweaks/settings.json. Includes typed
defaults via AppSettings dataclass and safe read/write with
automatic recovery from corrupt files.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


@dataclass
class AppSettings:
    """Default application settings with typed fields."""

    # Appearance
    theme: str = "dark"
    follow_system_theme: bool = False

    # Behavior
    start_minimized: bool = False
    show_notifications: bool = True
    confirm_dangerous_actions: bool = True
    restore_last_tab: bool = False
    last_tab_index: int = 0

    # Advanced
    log_level: str = "INFO"
    check_updates_on_start: bool = True

    # Version tracking
    last_seen_version: str = "0.0.0"


# Canonical set of known setting keys (derived from the dataclass).
_DEFAULTS = AppSettings()
KNOWN_KEYS = set(asdict(_DEFAULTS).keys())


class SettingsManager:
    """
    Singleton settings manager with JSON persistence.

    Usage::

        from utils.settings import SettingsManager

        mgr = SettingsManager.instance()
        theme = mgr.get("theme")       # -> "dark"
        mgr.set("theme", "light")
        mgr.save()
    """

    _instance: Optional["SettingsManager"] = None
    _lock = threading.Lock()

    def __init__(self, settings_path: Optional[Path] = None):
        """
        Initialise with an optional custom path (useful for testing).
        Prefer ``SettingsManager.instance()`` for production use.
        """
        self._path = settings_path or SETTINGS_FILE
        self._settings: dict = asdict(AppSettings())
        self._load()

    # ---- Singleton accessor ------------------------------------------------

    @classmethod
    def instance(cls) -> "SettingsManager":
        """Return the global singleton, creating it on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def _reset_instance(cls):
        """Reset singleton (for testing only)."""
        with cls._lock:
            cls._instance = None

    # ---- Public API --------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """
        Return the value for *key*.

        If *key* is unknown **and** no explicit *default* is given,
        ``KeyError`` is raised so callers notice typos early.
        """
        if key in self._settings:
            return self._settings[key]
        if default is not None:
            return default
        if key not in KNOWN_KEYS:
            raise KeyError(f"Unknown setting: {key!r}")
        return asdict(AppSettings()).get(key)

    def set(self, key: str, value: Any) -> None:
        """
        Set *key* to *value*.

        Only keys present in ``KNOWN_KEYS`` are accepted; unknown keys
        raise ``KeyError``.  The change is held in memory until
        :meth:`save` is called.
        """
        if key not in KNOWN_KEYS:
            raise KeyError(f"Unknown setting: {key!r}")
        self._settings[key] = value

    def reset(self) -> None:
        """Restore every setting to its default value and persist."""
        self._settings = asdict(AppSettings())
        self.save()

    def all(self) -> dict:
        """Return a shallow copy of the current settings dict."""
        return dict(self._settings)

    # ---- Persistence -------------------------------------------------------

    def save(self) -> None:
        """Write current settings to disk as pretty-printed JSON."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(self._settings, indent=2) + "\n")
            tmp_path.replace(self._path)
            logger.debug("Settings saved to %s", self._path)
        except OSError as exc:
            logger.warning("Failed to save settings: %s", exc)

    def _load(self) -> None:
        """Load settings from disk, falling back to defaults on error."""
        if not self._path.exists():
            logger.debug("No settings file found; using defaults.")
            return

        try:
            raw = json.loads(self._path.read_text())
            if not isinstance(raw, dict):
                raise ValueError("Settings file root is not a JSON object")
            # Merge only known keys, ignore stale/unknown keys silently
            defaults = asdict(AppSettings())
            for key in defaults:
                if key in raw:
                    defaults[key] = raw[key]
            self._settings = defaults
            logger.debug("Settings loaded from %s", self._path)
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning(
                "Corrupt settings file (%s); reverting to defaults.", exc
            )
            self._settings = asdict(AppSettings())
