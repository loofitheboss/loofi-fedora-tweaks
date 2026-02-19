"""Tests for utils/vfio.py"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.vfio import VFIOAssistant


class TestVFIOPrerequisites(unittest.TestCase):
    """Tests for VFIOAssistant prerequisite checks."""

    @patch('utils.vfio.VFIOAssistant._is_vfio_module_available', return_value=True)
    @patch('utils.vfio.VirtualizationManager.find_gpu_devices', return_value=[1, 2])
    @patch('utils.vfio.VirtualizationManager.is_iommu_enabled', return_value=True)
    @patch('utils.vfio.VirtualizationManager.is_kvm_module_loaded', return_value=True)
    def test_check_prerequisites_all_met(self, mock_kvm, mock_iommu, mock_gpu, mock_vfio):
        result = VFIOAssistant.check_prerequisites()
        self.assertTrue(result["kvm_ok"])
        self.assertTrue(result["iommu_ok"])
        self.assertTrue(result["second_gpu"])
        self.assertTrue(result["vfio_module"])

    @patch('utils.vfio.VFIOAssistant._is_vfio_module_available', return_value=False)
    @patch('utils.vfio.VirtualizationManager.find_gpu_devices', return_value=[])
    @patch('utils.vfio.VirtualizationManager.is_iommu_enabled', return_value=False)
    @patch('utils.vfio.VirtualizationManager.is_kvm_module_loaded', return_value=False)
    def test_check_prerequisites_none_met(self, mock_kvm, mock_iommu, mock_gpu, mock_vfio):
        result = VFIOAssistant.check_prerequisites()
        self.assertFalse(result["kvm_ok"])
        self.assertFalse(result["iommu_ok"])
        self.assertFalse(result["second_gpu"])
        self.assertFalse(result["vfio_module"])

    @patch('utils.vfio.VFIOAssistant._is_vfio_module_available', return_value=True)
    @patch('utils.vfio.VirtualizationManager.find_gpu_devices', return_value=[1])
    @patch('utils.vfio.VirtualizationManager.is_iommu_enabled', return_value=True)
    @patch('utils.vfio.VirtualizationManager.is_kvm_module_loaded', return_value=True)
    def test_check_prerequisites_single_gpu(self, mock_kvm, mock_iommu, mock_gpu, mock_vfio):
        result = VFIOAssistant.check_prerequisites()
        self.assertFalse(result["second_gpu"])


class TestVFIOModuleAvailable(unittest.TestCase):
    """Tests for VFIO module availability check."""

    @patch('utils.vfio.subprocess.run')
    def test_vfio_module_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = VFIOAssistant._is_vfio_module_available()
        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('utils.vfio.subprocess.run')
    def test_vfio_module_not_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        result = VFIOAssistant._is_vfio_module_available()
        self.assertFalse(result)

    @patch('utils.vfio.subprocess.run')
    def test_vfio_module_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="modinfo", timeout=10)
        result = VFIOAssistant._is_vfio_module_available()
        self.assertFalse(result)

    @patch('utils.vfio.subprocess.run')
    def test_vfio_module_exception(self, mock_run):
        mock_run.side_effect = OSError("fail")
        result = VFIOAssistant._is_vfio_module_available()
        self.assertFalse(result)


class TestGetPassthroughCandidates(unittest.TestCase):
    """Tests for GPU passthrough candidate detection."""

    @patch('utils.vfio.VFIOAssistant._get_primary_gpu_slot', return_value="0000:00:02.0")
    @patch('utils.vfio.VirtualizationManager.find_gpu_devices')
    def test_get_candidates_filters_primary(self, mock_gpus, mock_primary):
        device1 = MagicMock()
        device1.slot = "0000:00:02.0"
        device2 = MagicMock()
        device2.slot = "0000:01:00.0"
        device2.description = "NVIDIA RTX"
        device2.vendor_id = "10de"
        device2.device_id = "2503"
        device2.driver = "nouveau"

        group1 = MagicMock()
        group1.group_id = "1"
        group2 = MagicMock()
        group2.group_id = "2"

        mock_gpus.return_value = [(group1, device1), (group2, device2)]

        result = VFIOAssistant.get_passthrough_candidates()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["slot"], "0000:01:00.0")
        self.assertEqual(result[0]["vendor_id"], "10de")
        self.assertEqual(result[0]["iommu_group"], "2")

    @patch('utils.vfio.VFIOAssistant._get_primary_gpu_slot', return_value="0000:00:02.0")
    @patch('utils.vfio.VirtualizationManager.find_gpu_devices', return_value=[])
    def test_get_candidates_no_gpus(self, mock_gpus, mock_primary):
        result = VFIOAssistant.get_passthrough_candidates()
        self.assertEqual(result, [])


class TestGetPrimaryGPUSlot(unittest.TestCase):
    """Tests for primary GPU slot detection."""

    @patch('utils.vfio.os.readlink', return_value="../../0000:00:02.0")
    @patch('utils.vfio.os.path.islink', return_value=True)
    @patch('builtins.open', mock_open(read_data="1\n"))
    @patch('utils.vfio.os.path.isfile', return_value=True)
    @patch('utils.vfio.os.listdir', return_value=["card0"])
    def test_get_primary_slot_found(self, mock_listdir, mock_isfile, mock_islink, mock_readlink):
        result = VFIOAssistant._get_primary_gpu_slot()
        self.assertEqual(result, "0000:00:02.0")

    @patch('utils.vfio.os.listdir')
    def test_get_primary_slot_no_drm(self, mock_listdir):
        mock_listdir.side_effect = FileNotFoundError
        result = VFIOAssistant._get_primary_gpu_slot()
        self.assertEqual(result, "")

    @patch('utils.vfio.os.path.isfile', return_value=False)
    @patch('utils.vfio.os.listdir', return_value=["card0"])
    def test_get_primary_slot_no_boot_vga(self, mock_listdir, mock_isfile):
        result = VFIOAssistant._get_primary_gpu_slot()
        self.assertEqual(result, "")


class TestConfigGeneration(unittest.TestCase):
    """Tests for VFIO config file generation."""

    @patch('utils.vfio.VirtualizationManager.check_cpu_virt_extensions', return_value=(True, "Intel", "VT-x"))
    def test_generate_kernel_args_intel(self, mock_cpu):
        result = VFIOAssistant.generate_kernel_args(["10de:2503"])
        self.assertIn("intel_iommu=on", result)
        self.assertIn("vfio-pci.ids=10de:2503", result)
        self.assertIn("iommu=pt", result)

    @patch('utils.vfio.VirtualizationManager.check_cpu_virt_extensions', return_value=(True, "AMD", "AMD-V"))
    def test_generate_kernel_args_amd(self, mock_cpu):
        result = VFIOAssistant.generate_kernel_args(["1002:7340"])
        self.assertIn("amd_iommu=on", result)
        self.assertIn("vfio-pci.ids=1002:7340", result)

    @patch('utils.vfio.VirtualizationManager.check_cpu_virt_extensions', return_value=(False, "Unknown", ""))
    def test_generate_kernel_args_unknown_vendor(self, mock_cpu):
        result = VFIOAssistant.generate_kernel_args(["10de:2503"])
        self.assertIn("iommu=on", result)

    @patch('utils.vfio.VirtualizationManager.check_cpu_virt_extensions', return_value=(True, "Intel", "VT-x"))
    def test_generate_kernel_args_multiple_ids(self, mock_cpu):
        result = VFIOAssistant.generate_kernel_args(["10de:2503", "10de:228e"])
        self.assertIn("vfio-pci.ids=10de:2503,10de:228e", result)

    def test_generate_dracut_config(self):
        result = VFIOAssistant.generate_dracut_config(["10de:2503"])
        self.assertIn("vfio", result)
        self.assertIn("vfio_pci", result)
        self.assertIn("add_drivers", result)

    def test_generate_modprobe_config(self):
        result = VFIOAssistant.generate_modprobe_config(["10de:2503"])
        self.assertIn("options vfio-pci ids=10de:2503", result)
        self.assertIn("softdep nvidia pre: vfio-pci", result)
        self.assertIn("softdep nouveau pre: vfio-pci", result)
        self.assertIn("softdep amdgpu pre: vfio-pci", result)

    def test_generate_modprobe_config_multiple_ids(self):
        result = VFIOAssistant.generate_modprobe_config(["10de:2503", "10de:228e"])
        self.assertIn("ids=10de:2503,10de:228e", result)


class TestGrubHelpers(unittest.TestCase):
    """Tests for GRUB configuration helpers."""

    def test_get_current_grub_cmdline_success(self):
        grub_content = 'GRUB_CMDLINE_LINUX="quiet splash"\n'
        with patch('builtins.open', mock_open(read_data=grub_content)):
            result = VFIOAssistant.get_current_grub_cmdline()
            self.assertEqual(result, "quiet splash")

    def test_get_current_grub_cmdline_file_not_found(self):
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = VFIOAssistant.get_current_grub_cmdline()
            self.assertEqual(result, "")

    def test_get_current_grub_cmdline_permission_error(self):
        with patch('builtins.open', side_effect=PermissionError):
            result = VFIOAssistant.get_current_grub_cmdline()
            self.assertEqual(result, "")

    def test_build_grub_update_command(self):
        cmd, args, desc = VFIOAssistant.build_grub_update_command()
        self.assertEqual(cmd, "pkexec")
        self.assertIn("grub2-mkconfig", args)
        self.assertIsInstance(desc, str)

    def test_build_dracut_rebuild_command(self):
        cmd, args, desc = VFIOAssistant.build_dracut_rebuild_command()
        self.assertEqual(cmd, "pkexec")
        self.assertIn("dracut", args)
        self.assertIn("--force", args)
        self.assertIsInstance(desc, str)


class TestStepByStepPlan(unittest.TestCase):
    """Tests for VFIO setup step-by-step plan generation."""

    @patch('utils.vfio.VirtualizationManager.check_cpu_virt_extensions', return_value=(True, "Intel", "VT-x"))
    def test_get_step_by_step_plan(self, mock_cpu):
        target_gpu = {
            "vendor_id": "10de",
            "device_id": "2503",
            "slot": "0000:01:00.0",
        }
        steps = VFIOAssistant.get_step_by_step_plan(target_gpu)
        self.assertEqual(len(steps), 6)
        self.assertEqual(steps[0]["step_number"], 1)
        self.assertEqual(steps[-1]["step_number"], 6)
        for step in steps:
            self.assertIn("description", step)
            self.assertIn("command", step)
            self.assertIn("reversible", step)
            self.assertTrue(step["reversible"])

    @patch('utils.vfio.VirtualizationManager.check_cpu_virt_extensions', return_value=(True, "AMD", "AMD-V"))
    def test_get_step_by_step_plan_amd(self, mock_cpu):
        target_gpu = {
            "vendor_id": "1002",
            "device_id": "7340",
            "slot": "0000:06:00.0",
        }
        steps = VFIOAssistant.get_step_by_step_plan(target_gpu)
        self.assertEqual(len(steps), 6)
        self.assertIn("amd_iommu=on", steps[0]["description"])


if __name__ == '__main__':
    unittest.main()
