"""
i18n Manager — v31.0 Smart UX
Qt Linguist translation workflow for internationalization.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)

# Translation directory relative to package root
_TRANSLATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "resources", "translations"
)


class I18nManager:
    """Manages application internationalization via Qt Linguist workflow."""

    _current_locale: str = "en"
    _translator = None

    @staticmethod
    def translations_dir() -> str:
        """Return the path to the translations directory."""
        return _TRANSLATIONS_DIR

    @staticmethod
    def available_locales() -> List[str]:
        """
        Scan the translations directory for available locales.

        Returns:
            List of locale codes (e.g., ['en', 'sv']).
        """
        locales = []
        tr_dir = _TRANSLATIONS_DIR
        if not os.path.isdir(tr_dir):
            return ["en"]
        for fname in sorted(os.listdir(tr_dir)):
            if fname.endswith(".qm"):
                locale = fname.rsplit(".", 1)[0]
                locales.append(locale)
        if "en" not in locales:
            locales.insert(0, "en")
        return locales

    @classmethod
    def get_locale(cls) -> str:
        """Return the current locale code."""
        return cls._current_locale

    @classmethod
    def set_locale(cls, app, locale: str) -> bool:
        """
        Install a QTranslator for the given locale on the QApplication.

        Args:
            app: QApplication instance.
            locale: Locale code (e.g., 'sv').

        Returns:
            True if translator was loaded successfully, False otherwise.
        """
        try:
            from PyQt6.QtCore import QTranslator
        except ImportError:
            logger.warning("PyQt6 not available — cannot set locale")
            return False

        # Remove previous translator
        if cls._translator is not None:
            app.removeTranslator(cls._translator)
            cls._translator = None

        # English is the source language — no translation file needed
        if locale == "en":
            cls._current_locale = "en"
            return True

        qm_path = os.path.join(_TRANSLATIONS_DIR, f"{locale}.qm")
        if not os.path.isfile(qm_path):
            logger.warning("Translation file not found: %s", qm_path)
            return False

        translator = QTranslator()
        if translator.load(qm_path):
            app.installTranslator(translator)
            cls._translator = translator
            cls._current_locale = locale
            logger.info("Locale set to: %s", locale)
            return True
        else:
            logger.warning("Failed to load translation: %s", qm_path)
            return False

    @staticmethod
    def get_preferred_locale() -> str:
        """
        Read preferred locale from user settings.

        Returns:
            Locale code string, defaults to 'en'.
        """
        try:
            import json

            config_path = os.path.expanduser(
                "~/.config/loofi-fedora-tweaks/settings.json"
            )
            if os.path.isfile(config_path):
                with open(config_path, "r") as f:
                    settings = json.load(f)
                return str(settings.get("locale", "en"))
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to read preferred locale from settings: %s", e)
        return "en"

    @staticmethod
    def save_preferred_locale(locale: str) -> None:
        """
        Save preferred locale to user settings.

        Args:
            locale: Locale code to save.
        """
        try:
            import json

            config_dir = os.path.expanduser("~/.config/loofi-fedora-tweaks")
            config_path = os.path.join(config_dir, "settings.json")

            settings = {}
            if os.path.isfile(config_path):
                with open(config_path, "r") as f:
                    settings = json.load(f)

            settings["locale"] = locale
            os.makedirs(config_dir, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(settings, f, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to save locale preference: %s", e)
