"""Additional CLI handler coverage for hardware/plugins/preset commands."""

import argparse
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from cli.main import cmd_hardware, cmd_plugins, cmd_preset


class TestHardwareCommand(unittest.TestCase):
    """Tests for cmd_hardware."""

    @patch('cli.main._print')
    @patch('utils.hardware_profiles.detect_hardware_profile')
    def test_cmd_hardware_text_output(self, mock_detect, mock_print):
        mock_detect.return_value = (
            'hp',
            {
                'label': 'HP EliteBook',
                'battery_limit': True,
                'nbfc': False,
                'fingerprint': True,
                'power_profiles': True,
                'thermal_management': 'intel_pstate',
            },
        )

        with patch('cli.main._json_output', False):
            rc = cmd_hardware(argparse.Namespace())

        self.assertEqual(rc, 0)
        self.assertTrue(mock_print.called)

    @patch('cli.main._output_json')
    @patch('utils.hardware_profiles.detect_hardware_profile')
    def test_cmd_hardware_json_output(self, mock_detect, mock_output_json):
        mock_detect.return_value = ('generic', {'label': 'Generic'})

        with patch('cli.main._json_output', True):
            rc = cmd_hardware(argparse.Namespace())

        self.assertEqual(rc, 0)
        mock_output_json.assert_called_once()


class TestPluginsCommand(unittest.TestCase):
    """Tests for cmd_plugins."""

    @patch('cli.main._print')
    @patch('cli.main.PluginLoader')
    def test_cmd_plugins_list_text(self, mock_loader_cls, mock_print):
        mock_loader = MagicMock()
        mock_loader.list_plugins.return_value = [
            {
                'name': 'demo',
                'enabled': True,
                'manifest': {'version': '1.2.3', 'description': 'Demo plugin'},
            }
        ]
        mock_loader_cls.return_value = mock_loader

        with patch('cli.main._json_output', False):
            rc = cmd_plugins(argparse.Namespace(action='list', name=None))

        self.assertEqual(rc, 0)
        self.assertTrue(mock_print.called)

    @patch('cli.main._output_json')
    @patch('cli.main.PluginLoader')
    def test_cmd_plugins_list_json(self, mock_loader_cls, mock_output_json):
        mock_loader = MagicMock()
        mock_loader.list_plugins.return_value = []
        mock_loader_cls.return_value = mock_loader

        with patch('cli.main._json_output', True):
            rc = cmd_plugins(argparse.Namespace(action='list', name=None))

        self.assertEqual(rc, 0)
        mock_output_json.assert_called_once_with({'plugins': []})

    @patch('cli.main._print')
    @patch('cli.main.PluginLoader')
    def test_cmd_plugins_enable_missing_name(self, mock_loader_cls, mock_print):
        mock_loader_cls.return_value = MagicMock()
        with patch('cli.main._json_output', False):
            rc = cmd_plugins(argparse.Namespace(action='enable', name=None))
        self.assertEqual(rc, 1)

    @patch('cli.main._output_json')
    @patch('cli.main.PluginLoader')
    def test_cmd_plugins_disable_json(self, mock_loader_cls, mock_output_json):
        mock_loader = MagicMock()
        mock_loader_cls.return_value = mock_loader

        with patch('cli.main._json_output', True):
            rc = cmd_plugins(argparse.Namespace(action='disable', name='demo'))

        self.assertEqual(rc, 0)
        mock_loader.set_enabled.assert_called_once_with('demo', False)
        mock_output_json.assert_called_once_with({'plugin': 'demo', 'enabled': False})

    @patch('cli.main.PluginLoader')
    def test_cmd_plugins_unknown_action(self, mock_loader_cls):
        mock_loader_cls.return_value = MagicMock()
        rc = cmd_plugins(argparse.Namespace(action='unknown', name=None))
        self.assertEqual(rc, 1)


class TestPresetCommand(unittest.TestCase):
    """Tests for cmd_preset."""

    @patch('cli.main._print')
    @patch('cli.main.PresetManager')
    def test_cmd_preset_list_text(self, mock_manager_cls, mock_print):
        manager = MagicMock()
        manager.list_presets.return_value = ['gaming', 'battery']
        mock_manager_cls.return_value = manager

        with patch('cli.main._json_output', False):
            rc = cmd_preset(argparse.Namespace(action='list', name=None, path=None))

        self.assertEqual(rc, 0)
        self.assertTrue(mock_print.called)

    @patch('cli.main._output_json')
    @patch('cli.main.PresetManager')
    def test_cmd_preset_apply_json_success(self, mock_manager_cls, mock_output_json):
        manager = MagicMock()
        manager.load_preset.return_value = {'cpu_governor': 'performance'}
        mock_manager_cls.return_value = manager

        with patch('cli.main._json_output', True):
            rc = cmd_preset(argparse.Namespace(action='apply', name='gaming', path=None))

        self.assertEqual(rc, 0)
        mock_output_json.assert_called_once()

    @patch('cli.main._output_json')
    @patch('cli.main.PresetManager')
    def test_cmd_preset_apply_json_not_found(self, mock_manager_cls, mock_output_json):
        manager = MagicMock()
        manager.load_preset.return_value = None
        mock_manager_cls.return_value = manager

        with patch('cli.main._json_output', True):
            rc = cmd_preset(argparse.Namespace(action='apply', name='missing', path=None))

        self.assertEqual(rc, 1)
        mock_output_json.assert_called_once()

    @patch('cli.main._print')
    @patch('cli.main.PresetManager')
    def test_cmd_preset_export_missing_args(self, mock_manager_cls, _mock_print):
        mock_manager_cls.return_value = MagicMock()
        rc = cmd_preset(argparse.Namespace(action='export', name=None, path=None))
        self.assertEqual(rc, 1)

    @patch('cli.main._print')
    @patch('cli.main.PresetManager')
    def test_cmd_preset_export_success(self, mock_manager_cls, _mock_print):
        manager = MagicMock()
        manager.load_preset.return_value = {'foo': 'bar'}
        mock_manager_cls.return_value = manager

        with tempfile.NamedTemporaryFile(delete=True) as tf:
            rc = cmd_preset(argparse.Namespace(action='export', name='gaming', path=tf.name))

        self.assertEqual(rc, 0)

    @patch('cli.main._print')
    @patch('cli.main.PresetManager')
    def test_cmd_preset_export_write_error(self, mock_manager_cls, _mock_print):
        manager = MagicMock()
        manager.load_preset.return_value = {'foo': 'bar'}
        mock_manager_cls.return_value = manager

        with patch('builtins.open', side_effect=OSError('nope')):
            rc = cmd_preset(argparse.Namespace(action='export', name='gaming', path='/tmp/x.json'))

        self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main()
