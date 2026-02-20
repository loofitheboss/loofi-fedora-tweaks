"""Tests for utils/presets.py — PresetManager."""
import sys
import os
import subprocess
import unittest
from unittest.mock import patch, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.presets import PresetManager


class TestPresetManagerInit(unittest.TestCase):
    """Tests for PresetManager initialization."""

    @patch('utils.presets.os.makedirs')
    def test_creates_presets_directory(self, mock_makedirs):
        pm = PresetManager()
        mock_makedirs.assert_called_once_with(pm.PRESETS_DIR, exist_ok=True)


class TestSanitizeName(unittest.TestCase):
    """Tests for _sanitize_name path traversal prevention."""

    def test_normal_name(self):
        self.assertEqual(PresetManager._sanitize_name("my_preset"), "my_preset")

    def test_path_traversal(self):
        result = PresetManager._sanitize_name("../../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_empty_name(self):
        self.assertEqual(PresetManager._sanitize_name(""), "unnamed_preset")

    def test_dots_only(self):
        result = PresetManager._sanitize_name("..")
        self.assertEqual(result, "unnamed_preset")

    def test_slashes_stripped(self):
        result = PresetManager._sanitize_name("a/b\\c")
        self.assertNotIn("/", result)
        self.assertNotIn("\\", result)


class TestListPresets(unittest.TestCase):
    """Tests for list_presets."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('utils.presets.os.listdir')
    @patch('utils.presets.os.path.exists', return_value=True)
    def test_returns_preset_names(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["dark.json", "light.json", "readme.txt"]
        result = self.pm.list_presets()
        self.assertEqual(result, ["dark", "light"])

    @patch('utils.presets.os.path.exists', return_value=False)
    def test_returns_empty_when_dir_missing(self, mock_exists):
        result = self.pm.list_presets()
        self.assertEqual(result, [])

    @patch('utils.presets.os.listdir')
    @patch('utils.presets.os.path.exists', return_value=True)
    def test_no_json_files(self, mock_exists, mock_listdir):
        mock_listdir.return_value = ["readme.txt"]
        result = self.pm.list_presets()
        self.assertEqual(result, [])


class TestSavePreset(unittest.TestCase):
    """Tests for save_preset."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('builtins.open', new_callable=mock_open)
    @patch.object(PresetManager, '_get_power_profile', return_value='balanced')
    @patch.object(PresetManager, '_get_battery_limit', return_value=100)
    @patch.object(PresetManager, '_get_gsettings', return_value='Adwaita')
    def test_save_writes_json(self, mock_gs, mock_bat, mock_power, mock_file):
        result = self.pm.save_preset("test_preset")
        self.assertTrue(result)
        mock_file.assert_called_once()
        handle = mock_file()
        written = handle.write.call_args_list
        self.assertTrue(len(written) > 0)


class TestLoadPreset(unittest.TestCase):
    """Tests for load_preset."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('utils.presets.os.path.exists', return_value=False)
    def test_returns_false_when_missing(self, mock_exists):
        result = self.pm.load_preset("nonexistent")
        self.assertFalse(result)

    @patch.object(PresetManager, '_set_gsettings')
    @patch('builtins.open', new_callable=mock_open, read_data='{"name":"t","theme":"Adwaita"}')
    @patch('utils.presets.os.path.exists', return_value=True)
    def test_loads_and_applies(self, mock_exists, mock_file, mock_set_gs):
        result = self.pm.load_preset("test")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["theme"], "Adwaita")
        mock_set_gs.assert_called()


class TestDeletePreset(unittest.TestCase):
    """Tests for delete_preset."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('utils.presets.os.remove')
    @patch('utils.presets.os.path.exists', return_value=True)
    def test_deletes_existing(self, mock_exists, mock_remove):
        result = self.pm.delete_preset("old_preset")
        self.assertTrue(result)
        mock_remove.assert_called_once()

    @patch('utils.presets.os.path.exists', return_value=False)
    def test_returns_false_when_missing(self, mock_exists):
        result = self.pm.delete_preset("nonexistent")
        self.assertFalse(result)


class TestSavePresetData(unittest.TestCase):
    """Tests for save_preset_data (community presets)."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('builtins.open', new_callable=mock_open)
    def test_save_community_preset(self, mock_file):
        data = {"theme": "Nordic", "icon_theme": "Papirus"}
        result = self.pm.save_preset_data("community", data)
        self.assertTrue(result)

    @patch('builtins.open', side_effect=OSError("disk full"))
    def test_save_failure(self, mock_file):
        result = self.pm.save_preset_data("fail", {"theme": "X"})
        self.assertFalse(result)


class TestGetGsettings(unittest.TestCase):
    """Tests for _get_gsettings helper."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('utils.presets.subprocess.check_output', return_value="'Adwaita'\n")
    @patch('utils.presets.shutil.which', return_value="/usr/bin/gsettings")
    def test_returns_value(self, mock_which, mock_check):
        result = self.pm._get_gsettings("org.gnome.desktop.interface", "gtk-theme")
        self.assertEqual(result, "Adwaita")

    @patch('utils.presets.shutil.which', return_value=None)
    def test_returns_none_when_missing(self, mock_which):
        result = self.pm._get_gsettings("org.gnome.desktop.interface", "gtk-theme")
        self.assertIsNone(result)

    @patch('utils.presets.subprocess.check_output', side_effect=subprocess.CalledProcessError(1, "gsettings"))
    @patch('utils.presets.shutil.which', return_value="/usr/bin/gsettings")
    def test_returns_none_on_error(self, mock_which, mock_check):
        result = self.pm._get_gsettings("org.gnome.desktop.interface", "bad-key")
        self.assertIsNone(result)


class TestGetPowerProfile(unittest.TestCase):
    """Tests for _get_power_profile helper."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('utils.presets.subprocess.check_output', return_value="performance\n")
    @patch('utils.presets.shutil.which', return_value="/usr/bin/powerprofilesctl")
    def test_returns_profile(self, mock_which, mock_check):
        result = self.pm._get_power_profile()
        self.assertEqual(result, "performance")

    @patch('utils.presets.shutil.which', return_value=None)
    def test_returns_balanced_when_missing(self, mock_which):
        result = self.pm._get_power_profile()
        self.assertEqual(result, "balanced")


class TestGetBatteryLimit(unittest.TestCase):
    """Tests for _get_battery_limit helper."""

    @patch('utils.presets.os.makedirs')
    def setUp(self, mock_makedirs):
        self.pm = PresetManager()

    @patch('builtins.open', new_callable=mock_open, read_data="80")
    def test_reads_limit(self, mock_file):
        result = self.pm._get_battery_limit()
        self.assertEqual(result, 80)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_returns_100_when_missing(self, mock_file):
        result = self.pm._get_battery_limit()
        self.assertEqual(result, 100)


if __name__ == "__main__":
    unittest.main()
