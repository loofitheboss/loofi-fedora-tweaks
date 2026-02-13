"""
Tests for I18nManager — v31.0 Smart UX
"""
import unittest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.i18n import I18nManager


class TestI18nManager(unittest.TestCase):
    """Tests for I18nManager."""

    def test_default_locale(self):
        """Default locale is 'en'."""
        I18nManager._current_locale = "en"
        self.assertEqual(I18nManager.get_locale(), "en")

    def test_translations_dir_is_string(self):
        """translations_dir returns a string path."""
        result = I18nManager.translations_dir()
        self.assertIsInstance(result, str)
        self.assertIn("translations", result)

    @patch('os.path.isdir', return_value=False)
    def test_available_locales_no_dir(self, mock_isdir):
        """Returns ['en'] if translations dir doesn't exist."""
        locales = I18nManager.available_locales()
        self.assertEqual(locales, ["en"])

    @patch('os.listdir', return_value=["en.qm", "sv.qm", "README.md"])
    @patch('os.path.isdir', return_value=True)
    def test_available_locales_with_files(self, mock_isdir, mock_listdir):
        """Returns locale codes from .qm files."""
        locales = I18nManager.available_locales()
        self.assertIn("en", locales)
        self.assertIn("sv", locales)
        self.assertNotIn("README", locales)

    @patch('os.listdir', return_value=["sv.qm"])
    @patch('os.path.isdir', return_value=True)
    def test_available_locales_adds_en_if_missing(self, mock_isdir, mock_listdir):
        """English is always included even without en.qm."""
        locales = I18nManager.available_locales()
        self.assertIn("en", locales)
        self.assertEqual(locales[0], "en")

    def test_set_locale_english(self):
        """Setting locale to 'en' always succeeds."""
        app = MagicMock()
        I18nManager._translator = MagicMock()
        result = I18nManager.set_locale(app, "en")
        self.assertTrue(result)
        self.assertEqual(I18nManager.get_locale(), "en")
        app.removeTranslator.assert_called_once()

    @patch('os.path.isfile', return_value=False)
    def test_set_locale_missing_file(self, mock_isfile):
        """Setting locale to missing file returns False."""
        app = MagicMock()
        I18nManager._translator = None
        result = I18nManager.set_locale(app, "fr")
        self.assertFalse(result)

    @patch('os.path.isfile', return_value=True)
    @patch('os.path.expanduser', return_value="/tmp/test_settings.json")
    def test_get_preferred_locale_default(self, mock_expand, mock_isfile):
        """Returns 'en' when no settings file exists."""
        mock_isfile.return_value = False
        locale = I18nManager.get_preferred_locale()
        self.assertEqual(locale, "en")

    def test_get_preferred_locale_from_file(self):
        """Reads locale from settings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"locale": "sv"}, f)
            temp_path = f.name
        try:
            with patch('os.path.expanduser', return_value=temp_path):
                with patch('os.path.isfile', return_value=True):
                    with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps({"locale": "sv"}))):
                        locale = I18nManager.get_preferred_locale()
                        self.assertEqual(locale, "sv")
        finally:
            os.unlink(temp_path)

    @patch('builtins.open', side_effect=Exception("IO error"))
    @patch('os.path.isfile', return_value=True)
    @patch('os.path.expanduser', return_value="/tmp/settings.json")
    def test_get_preferred_locale_error(self, mock_expand, mock_isfile, mock_open):
        """Returns 'en' on file read error."""
        locale = I18nManager.get_preferred_locale()
        self.assertEqual(locale, "en")

    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.path.isfile', return_value=False)
    @patch('os.makedirs')
    @patch('os.path.expanduser', return_value="/tmp/config/settings.json")
    def test_save_preferred_locale(self, mock_expand, mock_makedirs, mock_isfile, mock_open):
        """Saves locale preference to settings file."""
        I18nManager.save_preferred_locale("sv")
        mock_open.assert_called()

    @patch('builtins.open', side_effect=Exception("IO error"))
    @patch('os.path.isfile', return_value=False)
    @patch('os.makedirs')
    @patch('os.path.expanduser', return_value="/tmp/config/settings.json")
    def test_save_preferred_locale_error(self, mock_expand, mock_makedirs, mock_isfile, mock_open):
        """Save locale handles errors gracefully."""
        # Should not raise
        I18nManager.save_preferred_locale("sv")


if __name__ == '__main__':
    unittest.main()
