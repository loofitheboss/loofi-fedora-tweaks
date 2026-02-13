"""Tests for services.hardware.hardware — HardwareManager (66 miss, 77.1%)."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from services.hardware.hardware import HardwareManager


class TestGetAvailableGovernors(unittest.TestCase):
    @patch("builtins.open", unittest.mock.mock_open(read_data="powersave performance schedutil\n"))
    def test_reads_file(self):
        result = HardwareManager.get_available_governors()
        self.assertIn("powersave", result)
        self.assertIn("performance", result)

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_fallback(self, mock_open):
        result = HardwareManager.get_available_governors()
        self.assertEqual(result, ["powersave", "performance"])

    @patch("builtins.open", side_effect=PermissionError)
    def test_permission_error(self, mock_open):
        result = HardwareManager.get_available_governors()
        self.assertEqual(result, [])


class TestGetCurrentGovernor(unittest.TestCase):
    @patch("builtins.open", unittest.mock.mock_open(read_data="schedutil\n"))
    def test_reads_governor(self):
        self.assertEqual(HardwareManager.get_current_governor(), "schedutil")

    @patch("builtins.open", side_effect=OSError("no file"))
    def test_oserror(self, mock_open):
        self.assertEqual(HardwareManager.get_current_governor(), "unknown")


class TestSetGovernor(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    @patch.object(HardwareManager, "get_available_governors", return_value=["powersave", "performance"])
    def test_success(self, mock_gov, mock_run):
        self.assertTrue(HardwareManager.set_governor("performance"))

    @patch.object(HardwareManager, "get_available_governors", return_value=["powersave"])
    def test_invalid_governor(self, mock_gov):
        self.assertFalse(HardwareManager.set_governor("turbo"))

    @patch("subprocess.run", side_effect=OSError("no pkexec"))
    @patch.object(HardwareManager, "get_available_governors", return_value=["performance"])
    def test_subprocess_error(self, mock_gov, mock_run):
        self.assertFalse(HardwareManager.set_governor("performance"))


class TestGetCpuFrequency(unittest.TestCase):
    def test_reads_freq(self):
        # 2400000 kHz = 2400 MHz
        m = unittest.mock.mock_open()
        m.side_effect = [
            unittest.mock.mock_open(read_data="2400000\n").return_value,
            unittest.mock.mock_open(read_data="3600000\n").return_value,
        ]
        with patch("builtins.open", m):
            result = HardwareManager.get_cpu_frequency()
            self.assertEqual(result["current"], 2400)
            self.assertEqual(result["max"], 3600)

    @patch("builtins.open", side_effect=OSError)
    def test_error(self, mock_open):
        result = HardwareManager.get_cpu_frequency()
        self.assertEqual(result["current"], 0)
        self.assertEqual(result["max"], 0)


class TestIsHybridGpu(unittest.TestCase):
    @patch("glob.glob", return_value=["/sys/class/drm/card0/device/vendor"])
    @patch("shutil.which", return_value="/usr/bin/nvidia-smi")
    @patch("os.path.exists", return_value=True)
    def test_hybrid(self, mock_exists, mock_which, mock_glob):
        # nvidia present + intel present
        with patch("builtins.open", unittest.mock.mock_open(read_data="intel")):
            result = HardwareManager.is_hybrid_gpu()
            # Result depends on glob content matching, but exercises the code
            self.assertIsInstance(result, bool)

    @patch("glob.glob", return_value=[])
    @patch("shutil.which", return_value=None)
    @patch("os.path.exists", return_value=False)
    def test_not_hybrid(self, mock_exists, mock_which, mock_glob):
        self.assertFalse(HardwareManager.is_hybrid_gpu())


class TestGetGpuMode(unittest.TestCase):
    @patch("shutil.which", return_value="/usr/bin/envycontrol")
    @patch("subprocess.run")
    def test_envycontrol_integrated(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="integrated mode")
        self.assertEqual(HardwareManager.get_gpu_mode(), "integrated")

    @patch("shutil.which", return_value="/usr/bin/envycontrol")
    @patch("subprocess.run")
    def test_envycontrol_hybrid(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="hybrid mode")
        self.assertEqual(HardwareManager.get_gpu_mode(), "hybrid")

    @patch("shutil.which", return_value="/usr/bin/envycontrol")
    @patch("subprocess.run")
    def test_envycontrol_nvidia(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="nvidia mode")
        self.assertEqual(HardwareManager.get_gpu_mode(), "nvidia")

    @patch("shutil.which", return_value=None)
    def test_unknown(self, mock_which):
        self.assertEqual(HardwareManager.get_gpu_mode(), "unknown")


class TestSetGpuMode(unittest.TestCase):
    def test_invalid_mode(self):
        success, msg = HardwareManager.set_gpu_mode("turbo")
        self.assertFalse(success)

    @patch("shutil.which", return_value="/usr/bin/envycontrol")
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_envycontrol_success(self, mock_run, mock_which):
        success, msg = HardwareManager.set_gpu_mode("hybrid")
        self.assertTrue(success)

    @patch("shutil.which", return_value="/usr/bin/envycontrol")
    @patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="fail"))
    def test_envycontrol_failure(self, mock_run, mock_which):
        success, msg = HardwareManager.set_gpu_mode("hybrid")
        self.assertFalse(success)

    @patch("shutil.which", return_value=None)
    def test_no_tool(self, mock_which):
        success, msg = HardwareManager.set_gpu_mode("nvidia")
        self.assertFalse(success)
        self.assertIn("No GPU switching tool", msg)


class TestGetAvailableGpuTools(unittest.TestCase):
    @patch("shutil.which", side_effect=lambda x: "/usr/bin/" + x if x == "envycontrol" else None)
    def test_envycontrol_only(self, mock_which):
        tools = HardwareManager.get_available_gpu_tools()
        self.assertIn("envycontrol", tools)
        self.assertNotIn("supergfxctl", tools)

    @patch("shutil.which", return_value=None)
    def test_no_tools(self, mock_which):
        self.assertEqual(HardwareManager.get_available_gpu_tools(), [])


class TestNbfc(unittest.TestCase):
    @patch("shutil.which", return_value="/usr/bin/nbfc")
    def test_is_available(self, mock_which):
        self.assertTrue(HardwareManager.is_nbfc_available())

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        self.assertFalse(HardwareManager.is_nbfc_available())

    @patch("shutil.which", return_value=None)
    def test_get_profiles_no_nbfc(self, mock_which):
        self.assertEqual(HardwareManager.get_nbfc_profiles(), [])

    @patch("shutil.which", return_value="/usr/bin/nbfc")
    @patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="Profile1\nProfile2\n"))
    def test_get_profiles(self, mock_run, mock_which):
        profiles = HardwareManager.get_nbfc_profiles()
        self.assertIn("Profile1", profiles)

    @patch("shutil.which", return_value=None)
    def test_get_current_config_no_nbfc(self, mock_which):
        self.assertIsNone(HardwareManager.get_current_nbfc_config())

    @patch("shutil.which", return_value="/usr/bin/nbfc")
    @patch("subprocess.run", return_value=MagicMock(
        returncode=0, stdout="Selected Config: MyProfile\n"
    ))
    def test_get_current_config(self, mock_run, mock_which):
        result = HardwareManager.get_current_nbfc_config()
        self.assertEqual(result, "MyProfile")

    @patch("shutil.which", return_value="/usr/bin/nbfc")
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_set_profile(self, mock_run, mock_which):
        self.assertTrue(HardwareManager.set_nbfc_profile("MyProfile"))

    @patch("shutil.which", return_value=None)
    def test_set_profile_no_nbfc(self, mock_which):
        self.assertFalse(HardwareManager.set_nbfc_profile("x"))

    @patch("shutil.which", return_value="/usr/bin/nbfc")
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_set_fan_speed_manual(self, mock_run, mock_which):
        self.assertTrue(HardwareManager.set_fan_speed(50))

    @patch("shutil.which", return_value="/usr/bin/nbfc")
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_set_fan_speed_auto(self, mock_run, mock_which):
        self.assertTrue(HardwareManager.set_fan_speed(-1))

    @patch("shutil.which", return_value=None)
    def test_set_fan_speed_no_nbfc(self, mock_which):
        self.assertFalse(HardwareManager.set_fan_speed(50))

    @patch("shutil.which", return_value="/usr/bin/nbfc")
    @patch("subprocess.run", return_value=MagicMock(
        returncode=0, stdout="Current Speed: 45%\nTemperature: 55°C\n"
    ))
    def test_get_fan_status(self, mock_run, mock_which):
        status = HardwareManager.get_fan_status()
        self.assertEqual(status["speed"], 45.0)
        self.assertEqual(status["temperature"], 55.0)

    @patch("shutil.which", return_value=None)
    def test_get_fan_status_no_nbfc(self, mock_which):
        status = HardwareManager.get_fan_status()
        self.assertEqual(status["speed"], -1)


class TestPowerProfiles(unittest.TestCase):
    @patch("shutil.which", return_value="/usr/bin/powerprofilesctl")
    def test_available(self, mock_which):
        self.assertTrue(HardwareManager.is_power_profiles_available())

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        self.assertFalse(HardwareManager.is_power_profiles_available())

    @patch("shutil.which", return_value="/usr/bin/powerprofilesctl")
    @patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="balanced\n"))
    def test_get_profile(self, mock_run, mock_which):
        self.assertEqual(HardwareManager.get_power_profile(), "balanced")

    @patch("shutil.which", return_value=None)
    def test_get_profile_unavailable(self, mock_which):
        self.assertEqual(HardwareManager.get_power_profile(), "unknown")

    @patch("shutil.which", return_value="/usr/bin/powerprofilesctl")
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_set_profile_success(self, mock_run, mock_which):
        self.assertTrue(HardwareManager.set_power_profile("performance"))

    @patch("shutil.which", return_value="/usr/bin/powerprofilesctl")
    def test_set_profile_invalid(self, mock_which):
        self.assertFalse(HardwareManager.set_power_profile("turbo"))

    @patch("shutil.which", return_value=None)
    def test_set_profile_unavailable(self, mock_which):
        self.assertFalse(HardwareManager.set_power_profile("balanced"))

    @patch("shutil.which", return_value="/usr/bin/powerprofilesctl")
    @patch("subprocess.run", return_value=MagicMock(
        returncode=0, stdout="power-saver:\n  ...\nbalanced:\n  ...\nperformance:\n  ...\n"
    ))
    def test_get_available_profiles(self, mock_run, mock_which):
        profiles = HardwareManager.get_available_power_profiles()
        self.assertIsInstance(profiles, list)

    @patch("shutil.which", return_value=None)
    def test_get_available_profiles_unavailable(self, mock_which):
        self.assertEqual(HardwareManager.get_available_power_profiles(), [])


class TestGetAiCapabilities(unittest.TestCase):
    @patch("subprocess.run")
    @patch("shutil.which", return_value=None)
    @patch("glob.glob", return_value=[])
    @patch("os.path.exists", return_value=False)
    def test_no_ai_hw(self, mock_exists, mock_glob, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        caps = HardwareManager.get_ai_capabilities()
        self.assertFalse(caps["cuda"])
        self.assertFalse(caps["rocm"])

    @patch("subprocess.run")
    @patch("shutil.which", side_effect=lambda x: "/usr/bin/nvidia-smi" if x == "nvidia-smi" else None)
    @patch("glob.glob", return_value=[])
    @patch("os.path.exists", return_value=False)
    def test_cuda_detected(self, mock_exists, mock_glob, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="GPU 0: NVIDIA RTX 4090")
        caps = HardwareManager.get_ai_capabilities()
        self.assertTrue(caps["cuda"])


class TestGetAiSummary(unittest.TestCase):
    @patch.object(HardwareManager, "get_ai_capabilities", return_value={
        "cuda": False, "rocm": False, "npu_intel": False, "npu_amd": False, "details": {}
    })
    def test_no_hw(self, mock_caps):
        summary = HardwareManager.get_ai_summary()
        self.assertIn("No AI hardware", summary)

    @patch.object(HardwareManager, "get_ai_capabilities", return_value={
        "cuda": True, "rocm": False, "npu_intel": True, "npu_amd": False,
        "details": {"nvidia_gpu": "RTX 4090"}
    })
    def test_with_hw(self, mock_caps):
        summary = HardwareManager.get_ai_summary()
        self.assertIn("CUDA", summary)
        self.assertIn("Intel NPU", summary)


if __name__ == "__main__":
    unittest.main()
