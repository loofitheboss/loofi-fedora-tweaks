"""Tests for services.hardware.hardware.HardwareManager."""

import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from services.hardware.hardware import HardwareManager
from services.hardware.disk import DiskManager


class TestCpuGovernors(unittest.TestCase):
    """CPU governor tests."""

    @patch('builtins.open', new_callable=mock_open, read_data='powersave performance\n')
    def test_get_available_governors_success(self, _mock_file):
        governors = HardwareManager.get_available_governors()
        self.assertEqual(governors, ['powersave', 'performance'])

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_available_governors_fallback(self, _mock_file):
        governors = HardwareManager.get_available_governors()
        self.assertEqual(governors, ['powersave', 'performance'])

    @patch('builtins.open', side_effect=PermissionError)
    def test_get_available_governors_permission_denied(self, _mock_file):
        governors = HardwareManager.get_available_governors()
        self.assertEqual(governors, [])

    @patch('builtins.open', new_callable=mock_open, read_data='schedutil\n')
    def test_get_current_governor_success(self, _mock_file):
        self.assertEqual(HardwareManager.get_current_governor(), 'schedutil')

    @patch('builtins.open', side_effect=OSError('boom'))
    def test_get_current_governor_oserror(self, _mock_file):
        self.assertEqual(HardwareManager.get_current_governor(), 'unknown')

    @patch('services.hardware.hardware.HardwareManager.get_available_governors', return_value=['powersave'])
    def test_set_governor_rejects_unavailable(self, _mock_governors):
        self.assertFalse(HardwareManager.set_governor('performance'))

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.get_available_governors', return_value=['performance'])
    def test_set_governor_success(self, _mock_governors, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(HardwareManager.set_governor('performance'))

    @patch('services.hardware.hardware.subprocess.run', side_effect=OSError('boom'))
    @patch('services.hardware.hardware.HardwareManager.get_available_governors', return_value=['performance'])
    def test_set_governor_exception(self, _mock_governors, _mock_run):
        self.assertFalse(HardwareManager.set_governor('performance'))

    @patch('builtins.open')
    def test_get_cpu_frequency_success(self, mock_file):
        handles = [
            mock_open(read_data='3500000\n').return_value,
            mock_open(read_data='4200000\n').return_value,
        ]
        mock_file.side_effect = handles
        result = HardwareManager.get_cpu_frequency()
        self.assertEqual(result, {'current': 3500, 'max': 4200})

    @patch('builtins.open', side_effect=ValueError('bad int'))
    def test_get_cpu_frequency_bad_data(self, _mock_file):
        self.assertEqual(HardwareManager.get_cpu_frequency(), {'current': 0, 'max': 0})


class TestGpuControls(unittest.TestCase):
    """GPU detection and control tests."""

    @patch('services.hardware.hardware.glob.glob', return_value=['/sys/class/drm/card1/device/vendor_intel'])
    @patch('services.hardware.hardware.shutil.which', return_value='/usr/bin/nvidia-smi')
    @patch('services.hardware.hardware.os.path.exists', return_value=False)
    def test_is_hybrid_gpu_true_with_intel(self, _mock_exists, _mock_which, _mock_glob):
        self.assertTrue(HardwareManager.is_hybrid_gpu())

    @patch('services.hardware.hardware.glob.glob', return_value=[])
    @patch('services.hardware.hardware.shutil.which', return_value=None)
    @patch('services.hardware.hardware.os.path.exists', return_value=False)
    def test_is_hybrid_gpu_false(self, _mock_exists, _mock_which, _mock_glob):
        self.assertFalse(HardwareManager.is_hybrid_gpu())

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.shutil.which')
    def test_get_gpu_mode_envycontrol_integrated(self, mock_which, mock_run):
        mock_which.side_effect = lambda name: '/usr/bin/envycontrol' if name == 'envycontrol' else None
        mock_run.return_value = MagicMock(stdout='integrated\n')
        self.assertEqual(HardwareManager.get_gpu_mode(), 'integrated')

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.shutil.which')
    def test_get_gpu_mode_supergfx_fallback(self, mock_which, mock_run):
        def which_side_effect(name):
            if name == 'envycontrol':
                return None
            if name == 'supergfxctl':
                return '/usr/bin/supergfxctl'
            return None

        mock_which.side_effect = which_side_effect
        mock_run.return_value = MagicMock(stdout='Hybrid\n')
        self.assertEqual(HardwareManager.get_gpu_mode(), 'hybrid')

    @patch('services.hardware.hardware.shutil.which', return_value=None)
    def test_get_gpu_mode_unknown(self, _mock_which):
        self.assertEqual(HardwareManager.get_gpu_mode(), 'unknown')

    def test_set_gpu_mode_invalid(self):
        success, message = HardwareManager.set_gpu_mode('invalid')
        self.assertFalse(success)
        self.assertIn('Invalid mode', message)

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.shutil.which')
    def test_set_gpu_mode_envycontrol_success(self, mock_which, mock_run):
        mock_which.side_effect = lambda name: '/usr/bin/envycontrol' if name == 'envycontrol' else None
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        success, _message = HardwareManager.set_gpu_mode('hybrid')
        self.assertTrue(success)

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.shutil.which')
    def test_set_gpu_mode_supergfx_failure(self, mock_which, mock_run):
        def which_side_effect(name):
            if name == 'envycontrol':
                return None
            if name == 'supergfxctl':
                return '/usr/bin/supergfxctl'
            return None

        mock_which.side_effect = which_side_effect
        mock_run.return_value = MagicMock(returncode=1, stderr='failed')
        success, message = HardwareManager.set_gpu_mode('nvidia')
        self.assertFalse(success)
        self.assertEqual(message, 'failed')

    @patch('services.hardware.hardware.shutil.which', return_value=None)
    def test_set_gpu_mode_no_tool(self, _mock_which):
        success, message = HardwareManager.set_gpu_mode('integrated')
        self.assertFalse(success)
        self.assertIn('No GPU switching tool found', message)

    @patch('services.hardware.hardware.shutil.which')
    def test_get_available_gpu_tools(self, mock_which):
        mock_which.side_effect = lambda name: f'/usr/bin/{name}' if name in ('envycontrol', 'supergfxctl') else None
        self.assertEqual(HardwareManager.get_available_gpu_tools(), ['envycontrol', 'supergfxctl'])


class TestFanAndPowerProfiles(unittest.TestCase):
    """Fan and power profile tests."""

    @patch('services.hardware.hardware.shutil.which', return_value='/usr/bin/nbfc')
    def test_nbfc_available(self, _mock_which):
        self.assertTrue(HardwareManager.is_nbfc_available())

    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=False)
    def test_get_nbfc_profiles_unavailable(self, _mock_available):
        self.assertEqual(HardwareManager.get_nbfc_profiles(), [])

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=True)
    def test_get_nbfc_profiles_success(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='HP\nLenovo\n')
        self.assertEqual(HardwareManager.get_nbfc_profiles(), ['HP', 'Lenovo'])

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=True)
    def test_get_current_nbfc_config(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(stdout='Selected Config: HP EliteBook\n')
        self.assertEqual(HardwareManager.get_current_nbfc_config(), 'HP EliteBook')

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=True)
    def test_set_nbfc_profile_success(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(HardwareManager.set_nbfc_profile('HP'))

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=True)
    def test_set_fan_speed_manual_clamped(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(HardwareManager.set_fan_speed(150))
        called_cmd = mock_run.call_args[0][0]
        self.assertIn('100', called_cmd)

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=True)
    def test_set_fan_speed_auto_mode(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(HardwareManager.set_fan_speed(-1))

    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=False)
    def test_get_fan_status_unavailable(self, _mock_available):
        self.assertEqual(HardwareManager.get_fan_status(), {'speed': -1, 'temperature': -1, 'mode': 'unknown'})

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_nbfc_available', return_value=True)
    def test_get_fan_status_parses_values(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(stdout='Current Speed: 45%\nTemperature: 67°C\n')
        status = HardwareManager.get_fan_status()
        self.assertEqual(status['speed'], 45.0)
        self.assertEqual(status['temperature'], 67.0)

    @patch('services.hardware.hardware.shutil.which', return_value='/usr/bin/powerprofilesctl')
    def test_power_profiles_available(self, _mock_which):
        self.assertTrue(HardwareManager.is_power_profiles_available())

    @patch('services.hardware.hardware.HardwareManager.is_power_profiles_available', return_value=False)
    def test_get_power_profile_unavailable(self, _mock_available):
        self.assertEqual(HardwareManager.get_power_profile(), 'unknown')

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_power_profiles_available', return_value=True)
    def test_set_power_profile_valid_success(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(HardwareManager.set_power_profile('balanced'))

    @patch('services.hardware.hardware.HardwareManager.is_power_profiles_available', return_value=True)
    def test_set_power_profile_invalid(self, _mock_available):
        self.assertFalse(HardwareManager.set_power_profile('turbo'))

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.HardwareManager.is_power_profiles_available', return_value=True)
    def test_get_available_power_profiles_parse(self, _mock_available, mock_run):
        mock_run.return_value = MagicMock(stdout='* balanced:\nperformance:\npower-saver:\n')
        profiles = HardwareManager.get_available_power_profiles()
        self.assertIn('performance', profiles)


class TestAiCapabilities(unittest.TestCase):
    """AI acceleration detection tests."""

    @patch('services.hardware.hardware.subprocess.run')
    @patch('services.hardware.hardware.os.path.exists')
    @patch('services.hardware.hardware.glob.glob')
    @patch('services.hardware.hardware.shutil.which')
    def test_get_ai_capabilities_detects_all(self, mock_which, mock_glob, mock_exists, mock_run):
        def which_side_effect(name):
            return f'/usr/bin/{name}' if name in ('nvidia-smi', 'rocminfo') else None

        def exists_side_effect(path):
            return path in ('/sys/class/misc/intel_vpu', '/sys/class/amdxdna')

        mock_which.side_effect = which_side_effect
        mock_glob.return_value = ['/dev/accel/accel0']
        mock_exists.side_effect = exists_side_effect
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout='GPU 0: RTX\n'),
            MagicMock(returncode=0, stdout='Agent 0\n'),
            MagicMock(returncode=0, stdout='intel_vpu amdxdna\n'),
        ]

        caps = HardwareManager.get_ai_capabilities()
        self.assertTrue(caps['cuda'])
        self.assertTrue(caps['rocm'])
        self.assertTrue(caps['npu_intel'])
        self.assertTrue(caps['npu_amd'])

    @patch('services.hardware.hardware.subprocess.run', side_effect=OSError('boom'))
    @patch('services.hardware.hardware.os.path.exists', return_value=False)
    @patch('services.hardware.hardware.glob.glob', return_value=[])
    @patch('services.hardware.hardware.shutil.which', return_value=None)
    def test_get_ai_capabilities_failures(self, _mock_which, _mock_glob, _mock_exists, _mock_run):
        caps = HardwareManager.get_ai_capabilities()
        self.assertFalse(caps['cuda'])
        self.assertFalse(caps['rocm'])

    @patch('services.hardware.hardware.HardwareManager.get_ai_capabilities')
    def test_get_ai_summary_none(self, mock_caps):
        mock_caps.return_value = {
            'cuda': False,
            'rocm': False,
            'npu_intel': False,
            'npu_amd': False,
            'details': {},
        }
        summary = HardwareManager.get_ai_summary()
        self.assertIn('No AI hardware acceleration', summary)


class TestDiskManagerTimeouts(unittest.TestCase):
    """DiskManager timeout enforcement tests."""

    @patch('services.hardware.disk.subprocess.run')
    def test_get_all_mount_points_uses_timeout(self, mock_run):
        """get_all_mount_points should enforce timeout on df command."""
        mock_run.return_value = MagicMock(returncode=0, stdout="target size used avail pcent source\n")

        DiskManager.get_all_mount_points()

        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_run.call_args.kwargs.get('timeout'), 10)

    @patch('services.hardware.hardware.HardwareManager.get_ai_capabilities')
    def test_get_ai_summary_with_cuda(self, mock_caps):
        mock_caps.return_value = {
            'cuda': True,
            'rocm': False,
            'npu_intel': False,
            'npu_amd': False,
            'details': {'nvidia_gpu': 'GPU 0: RTX 4060'},
        }
        summary = HardwareManager.get_ai_summary()
        self.assertIn('CUDA', summary)


if __name__ == '__main__':
    unittest.main()
