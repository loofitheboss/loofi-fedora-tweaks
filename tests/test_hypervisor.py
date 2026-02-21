"""
Tests for v11.5 "Hypervisor Update" modules.
Covers: VMManager, VFIOAssistant, DisposableVMManager.
All subprocess / filesystem calls are mocked.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.vm_manager import VMManager, VMInfo, VM_FLAVORS
from utils.vfio import VFIOAssistant
from utils.disposable_vm import DisposableVMManager
from utils.virtualization import IOMMUGroup, IOMMUDevice


# ===================================================================
# VMManager — Flavour listing
# ===================================================================

class TestVMManagerFlavors(unittest.TestCase):
    """Tests for VM Quick-Create flavour presets."""

    def test_get_available_flavors_returns_dict(self):
        flavors = VMManager.get_available_flavors()
        self.assertIsInstance(flavors, dict)

    def test_all_expected_flavors_present(self):
        flavors = VMManager.get_available_flavors()
        for key in ("windows11", "fedora", "ubuntu", "kali", "arch"):
            self.assertIn(key, flavors)

    def test_windows11_needs_tpm(self):
        flavors = VMManager.get_available_flavors()
        self.assertTrue(flavors["windows11"]["needs_tpm"])

    def test_fedora_no_tpm(self):
        flavors = VMManager.get_available_flavors()
        self.assertFalse(flavors["fedora"]["needs_tpm"])

    def test_flavor_has_required_keys(self):
        required = {"label", "ram_mb", "vcpus", "disk_gb", "os_variant"}
        for key, flavor in VM_FLAVORS.items():
            for rk in required:
                self.assertIn(rk, flavor, f"Flavour '{key}' missing key '{rk}'")


# ===================================================================
# VMManager — Availability
# ===================================================================

class TestVMManagerAvailability(unittest.TestCase):
    """Tests for VMManager.is_available()."""

    @patch("shutil.which")
    def test_available_when_tools_present(self, mock_which):
        mock_which.return_value = "/usr/bin/dummy"
        self.assertTrue(VMManager.is_available())

    @patch("shutil.which", return_value=None)
    def test_unavailable_when_tools_missing(self, mock_which):
        self.assertFalse(VMManager.is_available())

    @patch("shutil.which")
    def test_unavailable_when_only_virsh(self, mock_which):
        def side(name):
            return "/usr/bin/virsh" if name == "virsh" else None
        mock_which.side_effect = side
        self.assertFalse(VMManager.is_available())


# ===================================================================
# VMManager — VM listing (virsh output parsing)
# ===================================================================

VIRSH_LIST_OUTPUT = """\
 Id   Name         State
-------------------------------
 1    fedora-vm    running
 -    win11-test   shut off
 -    arch-dev     shut off
"""

VIRSH_LIST_EMPTY = """\
 Id   Name   State
---------------------

"""


class TestVMManagerListVMs(unittest.TestCase):
    """Tests for VMManager.list_vms()."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_list_vms_parses_running_and_shutoff(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=VIRSH_LIST_OUTPUT)
        vms = VMManager.list_vms()
        self.assertEqual(len(vms), 3)
        self.assertEqual(vms[0].name, "fedora-vm")
        self.assertEqual(vms[0].state, "running")
        self.assertEqual(vms[1].name, "win11-test")
        self.assertEqual(vms[1].state, "shut off")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_list_vms_empty(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=VIRSH_LIST_EMPTY)
        vms = VMManager.list_vms()
        self.assertEqual(vms, [])

    @patch("shutil.which", return_value=None)
    def test_list_vms_no_virsh(self, mock_which):
        vms = VMManager.list_vms()
        self.assertEqual(vms, [])

    @patch("subprocess.run", side_effect=Exception("oops"))
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_list_vms_exception(self, mock_which, mock_run):
        vms = VMManager.list_vms()
        self.assertEqual(vms, [])


# ===================================================================
# VMManager — VM info (virsh dominfo parsing)
# ===================================================================

VIRSH_DOMINFO = """\
Name:           fedora-vm
UUID:           aabbccdd-1234-5678-abcd-ef0123456789
OS Type:        hvm
State:          running
CPU(s):         4
Max memory:     4194304 KiB
Used memory:    4194304 KiB
"""


class TestVMManagerGetVMInfo(unittest.TestCase):
    """Tests for VMManager.get_vm_info()."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_get_vm_info_parses_fields(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=VIRSH_DOMINFO)
        info = VMManager.get_vm_info("fedora-vm")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "fedora-vm")
        self.assertEqual(info.state, "running")
        self.assertEqual(info.uuid, "aabbccdd-1234-5678-abcd-ef0123456789")
        self.assertEqual(info.vcpus, 4)
        self.assertEqual(info.memory_mb, 4096)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_get_vm_info_not_found(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        info = VMManager.get_vm_info("ghost")
        self.assertIsNone(info)

    @patch("shutil.which", return_value=None)
    def test_get_vm_info_no_virsh(self, mock_which):
        info = VMManager.get_vm_info("anything")
        self.assertIsNone(info)


# ===================================================================
# VMManager — Create VM command building
# ===================================================================

class TestVMManagerCreateVM(unittest.TestCase):
    """Tests for VMManager.create_vm() command building."""

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.isdir", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/virt-install")
    def test_create_vm_success(self, mock_which, mock_isdir, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = VMManager.create_vm("test-vm", "fedora", "/tmp/fedora.iso")
        self.assertTrue(result.success)
        self.assertIn("test-vm", result.message)
        # Verify virt-install was called with correct args
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "virt-install")
        self.assertIn("--name", cmd)
        self.assertIn("test-vm", cmd)
        self.assertIn("--os-variant", cmd)

    def test_create_vm_invalid_name(self):
        result = VMManager.create_vm("bad name!", "fedora", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("Invalid", result.message)

    def test_create_vm_unknown_flavor(self):
        result = VMManager.create_vm("ok-name", "nonexistent", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("Unknown", result.message)

    @patch("os.path.isfile", return_value=False)
    @patch("shutil.which", return_value="/usr/bin/virt-install")
    def test_create_vm_missing_iso(self, mock_which, mock_isfile):
        result = VMManager.create_vm("ok-name", "fedora", "/nonexistent.iso")
        self.assertFalse(result.success)
        self.assertIn("ISO", result.message)

    @patch("os.path.isfile")
    @patch("os.path.isdir", return_value=True)
    @patch("shutil.which")
    def test_create_vm_windows_needs_swtpm(self, mock_which, mock_isdir, mock_isfile):
        mock_isfile.return_value = True
        # virsh & virt-install present, but swtpm missing
        def which_side(name):
            if name == "swtpm":
                return None
            return "/usr/bin/" + name
        mock_which.side_effect = which_side
        result = VMManager.create_vm("win-test", "windows11", "/tmp/win.iso")
        self.assertFalse(result.success)
        self.assertIn("swtpm", result.message)

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.isdir", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/dummy")
    def test_create_vm_windows_with_swtpm(self, mock_which, mock_isdir, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = VMManager.create_vm("win-test", "windows11", "/tmp/win.iso")
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--tpm", cmd)

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.isdir", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/dummy")
    def test_create_vm_with_overrides(self, mock_which, mock_isdir, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = VMManager.create_vm("test", "arch", "/tmp/a.iso", ram_mb=4096, vcpus=4)
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("4096", cmd)
        self.assertIn("4", cmd)

    @patch("subprocess.run", side_effect=OSError("kaboom"))
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.isdir", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/dummy")
    def test_create_vm_exception(self, mock_which, mock_isdir, mock_isfile, mock_run):
        result = VMManager.create_vm("exc-test", "fedora", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("Error", result.message)


# ===================================================================
# VMManager — Start / Stop / Delete
# ===================================================================

class TestVMManagerLifecycle(unittest.TestCase):
    """Tests for start, stop, force_stop, delete VM operations."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_start_vm_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Domain started", stderr="")
        result = VMManager.start_vm("my-vm")
        self.assertTrue(result.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_start_vm_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error: already running")
        result = VMManager.start_vm("my-vm")
        self.assertFalse(result.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_stop_vm_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = VMManager.stop_vm("my-vm")
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("shutdown", cmd)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_force_stop_vm_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = VMManager.force_stop_vm("my-vm")
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("destroy", cmd)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_delete_vm_without_storage(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = VMManager.delete_vm("my-vm", delete_storage=False)
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertNotIn("--remove-all-storage", cmd)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_delete_vm_with_storage(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = VMManager.delete_vm("my-vm", delete_storage=True)
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--remove-all-storage", cmd)

    @patch("shutil.which", return_value=None)
    def test_start_vm_no_virsh(self, mock_which):
        result = VMManager.start_vm("x")
        self.assertFalse(result.success)
        self.assertIn("virsh", result.message)

    @patch("shutil.which", return_value=None)
    def test_stop_vm_no_virsh(self, mock_which):
        result = VMManager.stop_vm("x")
        self.assertFalse(result.success)

    @patch("shutil.which", return_value=None)
    def test_delete_vm_no_virsh(self, mock_which):
        result = VMManager.delete_vm("x")
        self.assertFalse(result.success)


# ===================================================================
# VMManager — User group check
# ===================================================================

class TestVMManagerUserGroup(unittest.TestCase):
    """Tests for VMManager.check_user_in_libvirt_group()."""

    @patch("subprocess.run")
    def test_user_in_libvirt_group(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="wheel libvirt docker")
        self.assertTrue(VMManager.check_user_in_libvirt_group())

    @patch("subprocess.run")
    def test_user_not_in_libvirt_group(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="wheel docker")
        self.assertFalse(VMManager.check_user_in_libvirt_group())

    @patch("subprocess.run", side_effect=Exception("nope"))
    def test_user_group_check_exception(self, mock_run):
        self.assertFalse(VMManager.check_user_in_libvirt_group())


# ===================================================================
# VMManager — Storage pool
# ===================================================================

class TestVMManagerStoragePool(unittest.TestCase):
    """Tests for VMManager.get_default_storage_pool()."""

    @patch("os.path.isdir", return_value=True)
    def test_system_pool_exists(self, mock_isdir):
        pool = VMManager.get_default_storage_pool()
        self.assertEqual(pool, "/var/lib/libvirt/images")

    @patch("os.makedirs")
    @patch("os.path.isdir", return_value=False)
    def test_user_pool_fallback(self, mock_isdir, mock_makedirs):
        pool = VMManager.get_default_storage_pool()
        self.assertIn("loofi-vms", pool)


# ===================================================================
# VFIOAssistant — Prerequisites
# ===================================================================

class TestVFIOPrerequisites(unittest.TestCase):
    """Tests for VFIOAssistant.check_prerequisites()."""

    @patch("subprocess.run")
    @patch("utils.virtualization.VirtualizationManager.find_gpu_devices")
    @patch("utils.virtualization.VirtualizationManager.is_iommu_enabled", return_value=True)
    @patch("utils.virtualization.VirtualizationManager.is_kvm_module_loaded", return_value=True)
    def test_all_prerequisites_met(self, mock_kvm, mock_iommu, mock_gpus, mock_run):
        # Two GPUs
        mock_gpus.return_value = [
            (IOMMUGroup(1), IOMMUDevice("0000:00:02.0", "Intel iGPU", "8086", "3e92", "i915")),
            (IOMMUGroup(2), IOMMUDevice("0000:01:00.0", "NVIDIA RTX", "10de", "2503", "nvidia")),
        ]
        mock_run.return_value = MagicMock(returncode=0)  # modinfo vfio-pci
        prereqs = VFIOAssistant.check_prerequisites()
        self.assertTrue(prereqs["kvm_ok"])
        self.assertTrue(prereqs["iommu_ok"])
        self.assertTrue(prereqs["second_gpu"])
        self.assertTrue(prereqs["vfio_module"])

    @patch("subprocess.run")
    @patch("utils.virtualization.VirtualizationManager.find_gpu_devices", return_value=[])
    @patch("utils.virtualization.VirtualizationManager.is_iommu_enabled", return_value=False)
    @patch("utils.virtualization.VirtualizationManager.is_kvm_module_loaded", return_value=False)
    def test_no_prerequisites_met(self, mock_kvm, mock_iommu, mock_gpus, mock_run):
        mock_run.return_value = MagicMock(returncode=1)  # modinfo fails
        prereqs = VFIOAssistant.check_prerequisites()
        self.assertFalse(prereqs["kvm_ok"])
        self.assertFalse(prereqs["iommu_ok"])
        self.assertFalse(prereqs["second_gpu"])
        self.assertFalse(prereqs["vfio_module"])

    @patch("subprocess.run")
    @patch("utils.virtualization.VirtualizationManager.find_gpu_devices")
    @patch("utils.virtualization.VirtualizationManager.is_iommu_enabled", return_value=True)
    @patch("utils.virtualization.VirtualizationManager.is_kvm_module_loaded", return_value=True)
    def test_single_gpu_fails_second_gpu_check(self, mock_kvm, mock_iommu, mock_gpus, mock_run):
        mock_gpus.return_value = [
            (IOMMUGroup(1), IOMMUDevice("0000:00:02.0", "Intel iGPU", "8086", "3e92", "i915")),
        ]
        mock_run.return_value = MagicMock(returncode=0)
        prereqs = VFIOAssistant.check_prerequisites()
        self.assertFalse(prereqs["second_gpu"])


# ===================================================================
# VFIOAssistant — Candidate detection
# ===================================================================

class TestVFIOCandidates(unittest.TestCase):
    """Tests for VFIOAssistant.get_passthrough_candidates()."""

    @patch("utils.vfio.VFIOAssistant._get_primary_gpu_slot", return_value="0000:00:02.0")
    @patch("utils.virtualization.VirtualizationManager.find_gpu_devices")
    def test_filters_primary_gpu(self, mock_gpus, mock_primary):
        mock_gpus.return_value = [
            (IOMMUGroup(1), IOMMUDevice("0000:00:02.0", "Intel iGPU", "8086", "3e92", "i915")),
            (IOMMUGroup(2), IOMMUDevice("0000:01:00.0", "NVIDIA RTX", "10de", "2503", "nvidia")),
        ]
        candidates = VFIOAssistant.get_passthrough_candidates()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["slot"], "0000:01:00.0")

    @patch("utils.vfio.VFIOAssistant._get_primary_gpu_slot", return_value="0000:00:02.0")
    @patch("utils.virtualization.VirtualizationManager.find_gpu_devices", return_value=[])
    def test_no_gpus_returns_empty(self, mock_gpus, mock_primary):
        candidates = VFIOAssistant.get_passthrough_candidates()
        self.assertEqual(candidates, [])

    @patch("utils.vfio.VFIOAssistant._get_primary_gpu_slot", return_value="0000:00:02.0")
    @patch("utils.virtualization.VirtualizationManager.find_gpu_devices")
    def test_candidate_dict_keys(self, mock_gpus, mock_primary):
        mock_gpus.return_value = [
            (IOMMUGroup(2), IOMMUDevice("0000:01:00.0", "GPU", "10de", "2503", "nvidia")),
        ]
        candidates = VFIOAssistant.get_passthrough_candidates()
        self.assertEqual(len(candidates), 1)
        for key in ("slot", "description", "vendor_id", "device_id", "driver", "iommu_group"):
            self.assertIn(key, candidates[0])


# ===================================================================
# VFIOAssistant — Kernel arg generation
# ===================================================================

class TestVFIOKernelArgs(unittest.TestCase):
    """Tests for VFIOAssistant.generate_kernel_args()."""

    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions",
           return_value=(True, "Intel", "vmx"))
    def test_intel_kernel_args(self, mock_cpu):
        result = VFIOAssistant.generate_kernel_args(["10de:2503"])
        self.assertIn("intel_iommu=on", result)
        self.assertIn("iommu=pt", result)
        self.assertIn("vfio-pci.ids=10de:2503", result)

    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions",
           return_value=(True, "AMD", "svm"))
    def test_amd_kernel_args(self, mock_cpu):
        result = VFIOAssistant.generate_kernel_args(["10de:2503"])
        self.assertIn("amd_iommu=on", result)

    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions",
           return_value=(True, "Intel", "vmx"))
    def test_multiple_device_ids(self, mock_cpu):
        result = VFIOAssistant.generate_kernel_args(["10de:2503", "10de:228e"])
        self.assertIn("vfio-pci.ids=10de:2503,10de:228e", result)


# ===================================================================
# VFIOAssistant — Dracut / modprobe config generation
# ===================================================================

class TestVFIOConfigGeneration(unittest.TestCase):
    """Tests for dracut and modprobe config file generation."""

    def test_dracut_config_contains_vfio(self):
        content = VFIOAssistant.generate_dracut_config(["10de:2503"])
        self.assertIn("vfio", content)
        self.assertIn("add_drivers", content)

    def test_modprobe_config_contains_ids(self):
        content = VFIOAssistant.generate_modprobe_config(["10de:2503"])
        self.assertIn("10de:2503", content)
        self.assertIn("options vfio-pci", content)

    def test_modprobe_config_softdep_nvidia(self):
        content = VFIOAssistant.generate_modprobe_config(["10de:2503"])
        self.assertIn("softdep nvidia pre: vfio-pci", content)

    def test_modprobe_config_softdep_amdgpu(self):
        content = VFIOAssistant.generate_modprobe_config(["1002:7480"])
        self.assertIn("softdep amdgpu pre: vfio-pci", content)


# ===================================================================
# VFIOAssistant — GRUB cmdline parsing
# ===================================================================

class TestVFIOGrubCmdline(unittest.TestCase):
    """Tests for VFIOAssistant.get_current_grub_cmdline()."""

    @patch("builtins.open", mock_open(read_data='GRUB_CMDLINE_LINUX="quiet splash intel_iommu=on"\n'))
    def test_reads_grub_cmdline(self):
        result = VFIOAssistant.get_current_grub_cmdline()
        self.assertEqual(result, "quiet splash intel_iommu=on")

    @patch("builtins.open", mock_open(read_data='GRUB_TIMEOUT=5\n'))
    def test_no_cmdline_returns_empty(self):
        result = VFIOAssistant.get_current_grub_cmdline()
        self.assertEqual(result, "")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_grub_file_missing(self, mock_file):
        result = VFIOAssistant.get_current_grub_cmdline()
        self.assertEqual(result, "")


# ===================================================================
# VFIOAssistant — Step-by-step plan
# ===================================================================

class TestVFIOStepPlan(unittest.TestCase):
    """Tests for VFIOAssistant.get_step_by_step_plan()."""

    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions",
           return_value=(True, "Intel", "vmx"))
    def test_plan_has_six_steps(self, mock_cpu):
        gpu = {"vendor_id": "10de", "device_id": "2503"}
        steps = VFIOAssistant.get_step_by_step_plan(gpu)
        self.assertEqual(len(steps), 6)

    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions",
           return_value=(True, "Intel", "vmx"))
    def test_plan_step_keys(self, mock_cpu):
        gpu = {"vendor_id": "10de", "device_id": "2503"}
        steps = VFIOAssistant.get_step_by_step_plan(gpu)
        for step in steps:
            self.assertIn("step_number", step)
            self.assertIn("description", step)
            self.assertIn("command", step)
            self.assertIn("reversible", step)

    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions",
           return_value=(True, "Intel", "vmx"))
    def test_plan_mentions_grub(self, mock_cpu):
        gpu = {"vendor_id": "10de", "device_id": "2503"}
        steps = VFIOAssistant.get_step_by_step_plan(gpu)
        grub_steps = [s for s in steps if "GRUB" in s["description"] or "grub" in s["command"]]
        self.assertTrue(len(grub_steps) > 0)


# ===================================================================
# VFIOAssistant — Command builders
# ===================================================================

class TestVFIOCommandBuilders(unittest.TestCase):
    """Tests for PrivilegedCommand-pattern builders."""

    def test_grub_update_command(self):
        cmd, args, desc = VFIOAssistant.build_grub_update_command()
        self.assertEqual(cmd, "pkexec")
        self.assertIn("grub2-mkconfig", args)

    def test_dracut_rebuild_command(self):
        cmd, args, desc = VFIOAssistant.build_dracut_rebuild_command()
        self.assertEqual(cmd, "pkexec")
        self.assertIn("dracut", args)
        self.assertIn("--force", args)


# ===================================================================
# DisposableVMManager — Base image
# ===================================================================

class TestDisposableBaseImage(unittest.TestCase):
    """Tests for DisposableVMManager base image management."""

    @patch("os.path.isfile", return_value=True)
    @patch("os.makedirs")
    def test_base_image_available(self, mock_makedirs, mock_isfile):
        self.assertTrue(DisposableVMManager.is_base_image_available())

    @patch("os.path.isfile", return_value=False)
    @patch("os.makedirs")
    def test_base_image_not_available(self, mock_makedirs, mock_isfile):
        self.assertFalse(DisposableVMManager.is_base_image_available())

    @patch("os.makedirs")
    def test_base_image_path_contains_disposable(self, mock_makedirs):
        path = DisposableVMManager.get_base_image_path()
        self.assertIn("disposable", path)
        self.assertTrue(path.endswith(".qcow2"))

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("os.makedirs")
    @patch("shutil.which", return_value="/usr/bin/qemu-img")
    def test_create_base_image_success(self, mock_which, mock_makedirs, mock_isfile, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = DisposableVMManager.create_base_image("/tmp/test.iso", size_gb=20)
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "qemu-img")
        self.assertIn("20G", cmd)

    @patch("os.path.isfile", return_value=False)
    @patch("os.makedirs")
    @patch("shutil.which", return_value="/usr/bin/qemu-img")
    def test_create_base_image_missing_iso(self, mock_which, mock_makedirs, mock_isfile):
        result = DisposableVMManager.create_base_image("/nonexistent.iso")
        self.assertFalse(result.success)
        self.assertIn("ISO", result.message)

    @patch("os.makedirs")
    @patch("shutil.which", return_value=None)
    def test_create_base_image_no_qemu_img(self, mock_which, mock_makedirs):
        result = DisposableVMManager.create_base_image("/tmp/test.iso")
        self.assertFalse(result.success)
        self.assertIn("qemu-img", result.message)


# ===================================================================
# DisposableVMManager — Overlay creation
# ===================================================================

class TestDisposableOverlay(unittest.TestCase):
    """Tests for DisposableVMManager.create_snapshot_overlay()."""

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("shutil.which", return_value="/usr/bin/qemu-img")
    def test_overlay_creation_success(self, mock_which, mock_makedirs, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        path = DisposableVMManager.create_snapshot_overlay("/base.qcow2")
        self.assertTrue(path.endswith(".qcow2"))
        self.assertIn("disposable-", path)
        cmd = mock_run.call_args[0][0]
        self.assertIn("-b", cmd)
        self.assertIn("/base.qcow2", cmd)

    @patch("os.makedirs")
    @patch("shutil.which", return_value=None)
    def test_overlay_creation_no_qemu_img(self, mock_which, mock_makedirs):
        path = DisposableVMManager.create_snapshot_overlay("/base.qcow2")
        self.assertEqual(path, "")

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("shutil.which", return_value="/usr/bin/qemu-img")
    def test_overlay_creation_failure(self, mock_which, mock_makedirs, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
        path = DisposableVMManager.create_snapshot_overlay("/base.qcow2")
        self.assertEqual(path, "")


# ===================================================================
# DisposableVMManager — Cleanup
# ===================================================================

class TestDisposableCleanup(unittest.TestCase):
    """Tests for DisposableVMManager.cleanup_disposable()."""

    @patch("os.remove")
    @patch("os.path.isfile", return_value=True)
    def test_cleanup_success(self, mock_isfile, mock_remove):
        result = DisposableVMManager.cleanup_disposable("/tmp/overlay.qcow2")
        self.assertTrue(result.success)
        mock_remove.assert_called_once_with("/tmp/overlay.qcow2")

    @patch("os.path.isfile", return_value=False)
    def test_cleanup_file_not_found(self, mock_isfile):
        result = DisposableVMManager.cleanup_disposable("/tmp/ghost.qcow2")
        self.assertFalse(result.success)

    def test_cleanup_empty_path(self):
        result = DisposableVMManager.cleanup_disposable("")
        self.assertFalse(result.success)

    @patch("os.remove", side_effect=OSError("permission denied"))
    @patch("os.path.isfile", return_value=True)
    def test_cleanup_os_error(self, mock_isfile, mock_remove):
        result = DisposableVMManager.cleanup_disposable("/tmp/overlay.qcow2")
        self.assertFalse(result.success)
        self.assertIn("permission denied", result.message)


# ===================================================================
# DisposableVMManager — List active
# ===================================================================

class TestDisposableListActive(unittest.TestCase):
    """Tests for DisposableVMManager.list_active_disposables()."""

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_list_active_finds_disposables(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="fedora-vm\ndisposable-abc12345\ndisposable-def67890\n",
        )
        names = DisposableVMManager.list_active_disposables()
        self.assertEqual(len(names), 2)
        self.assertEqual(names[0], "disposable-abc12345")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/virsh")
    def test_list_active_no_disposables(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="fedora-vm\nwin11\n")
        names = DisposableVMManager.list_active_disposables()
        self.assertEqual(names, [])

    @patch("shutil.which", return_value=None)
    def test_list_active_no_virsh(self, mock_which):
        names = DisposableVMManager.list_active_disposables()
        self.assertEqual(names, [])


# ===================================================================
# VMManager — VM state helper
# ===================================================================

class TestVMManagerGetState(unittest.TestCase):
    """Tests for VMManager.get_vm_state()."""

    @patch("utils.vm_manager.VMManager.get_vm_info")
    def test_get_state_running(self, mock_info):
        mock_info.return_value = VMInfo(name="test", state="running")
        self.assertEqual(VMManager.get_vm_state("test"), "running")

    @patch("utils.vm_manager.VMManager.get_vm_info", return_value=None)
    def test_get_state_unknown(self, mock_info):
        self.assertEqual(VMManager.get_vm_state("ghost"), "unknown")


if __name__ == "__main__":
    unittest.main()
