import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add source path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.presets import PresetManager
from utils.remote_config import AppConfigFetcher


class TestPresetManager(unittest.TestCase):
    @patch('shutil.which')
    @patch('subprocess.check_output')
    def test_get_power_profile_success(self, mock_sub, mock_which):
        mock_which.return_value = '/usr/bin/powerprofilesctl'
        mock_sub.return_value = 'performance\n'
        
        manager = PresetManager()
        profile = manager._get_power_profile()
        self.assertEqual(profile, 'performance')

    @patch('shutil.which')
    def test_get_power_profile_missing_tool(self, mock_which):
        mock_which.return_value = None
        manager = PresetManager()
        profile = manager._get_power_profile()
        self.assertEqual(profile, 'balanced')

    @patch('builtins.open', new_callable=mock_open, read_data='80')
    def test_get_battery_limit_success(self, mock_file):
        manager = PresetManager()
        limit = manager._get_battery_limit()
        self.assertEqual(limit, 80)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_battery_limit_missing_file(self, mock_file):
        manager = PresetManager()
        limit = manager._get_battery_limit()
        self.assertEqual(limit, 100)


class TestAppConfigFetcher(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_fetch_success(self, mock_urlopen):
        # Mock successful JSON response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'[{"name": "Test App"}]'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        fetcher = AppConfigFetcher(force_refresh=True)
        
        # Connect signal to capture result
        results = []
        fetcher.config_ready.connect(lambda data: results.append(data))
        
        fetcher.run()
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0]['name'], "Test App")

if __name__ == '__main__':
    unittest.main()
