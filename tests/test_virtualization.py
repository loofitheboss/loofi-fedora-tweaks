"""
Tests for utils/virtualization.py — Pre-v11.5 virtualization detection.
Covers: CPU extensions, KVM module, IOMMU groups, VFIO helpers, tool checks.
"""
import unittest
from unittest.mock import patch, mock_open
import sys
import os

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.virtualization import (
    VirtualizationManager, VirtStatus, IOMMUGroup, IOMMUDevice,
)


# ---------------------------------------------------------------------------
# TestCPUExtensions — vmx / svm detection
# ---------------------------------------------------------------------------

class TestCPUExtensions(unittest.TestCase):
    """Tests for CPU virtualization extension detection."""

    @patch("builtins.open", mock_open(read_data="flags\t\t: fpu vme de pse vmx sse sse2\nmodel name\t: Intel Core"))
    def test_intel_vmx_detected(self):
        supported, vendor, ext = VirtualizationManager.check_cpu_virt_extensions()
        self.assertTrue(supported)
        self.assertEqual(vendor, "Intel")
        self.assertEqual(ext, "vmx")

    @patch("builtins.open", mock_open(read_data="flags\t\t: fpu vme de pse svm sse sse2\nmodel name\t: AMD Ryzen"))
    def test_amd_svm_detected(self):
        supported, vendor, ext = VirtualizationManager.check_cpu_virt_extensions()
        self.assertTrue(supported)
        self.assertEqual(vendor, "AMD")
        self.assertEqual(ext, "svm")

    @patch("builtins.open", mock_open(read_data="flags\t\t: fpu vme de pse sse sse2\n"))
    def test_no_virt_extensions(self):
        supported, vendor, ext = VirtualizationManager.check_cpu_virt_extensions()
        self.assertFalse(supported)
        self.assertEqual(vendor, "unknown")
        self.assertEqual(ext, "")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_cpuinfo_not_found(self, mock_file):
        supported, vendor, ext = VirtualizationManager.check_cpu_virt_extensions()
        self.assertFalse(supported)
        self.assertEqual(vendor, "unknown")

    @patch("builtins.open", side_effect=PermissionError)
    def test_cpuinfo_permission_denied(self, mock_file):
        supported, vendor, ext = VirtualizationManager.check_cpu_virt_extensions()
        self.assertFalse(supported)


# ---------------------------------------------------------------------------
# TestKVMModule — kernel module checks
# ---------------------------------------------------------------------------

class TestKVMModule(unittest.TestCase):
    """Tests for KVM kernel module detection."""

    @patch("builtins.open", mock_open(read_data="kvm_intel 348160 0\nkvm 1036288 1 kvm_intel\n"))
    def test_kvm_intel_loaded(self):
        self.assertTrue(VirtualizationManager.is_kvm_module_loaded())

    @patch("builtins.open", mock_open(read_data="kvm_amd 131072 0\nkvm 1036288 1 kvm_amd\n"))
    def test_kvm_amd_loaded(self):
        self.assertTrue(VirtualizationManager.is_kvm_module_loaded())

    @patch("builtins.open", mock_open(read_data="nvidia 57344000 0\nsnd_hda_intel 65536 0\n"))
    def test_kvm_not_loaded(self):
        self.assertFalse(VirtualizationManager.is_kvm_module_loaded())

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_proc_modules_missing(self, mock_file):
        self.assertFalse(VirtualizationManager.is_kvm_module_loaded())

    @patch("os.path.exists", return_value=True)
    def test_kvm_device_accessible(self, mock_exists):
        self.assertTrue(VirtualizationManager.is_kvm_device_accessible())

    @patch("os.path.exists", return_value=False)
    def test_kvm_device_not_accessible(self, mock_exists):
        self.assertFalse(VirtualizationManager.is_kvm_device_accessible())


# ---------------------------------------------------------------------------
# TestIOMMU — IOMMU group enumeration
# ---------------------------------------------------------------------------

class TestIOMMU(unittest.TestCase):
    """Tests for IOMMU detection and group enumeration."""

    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=["0", "1", "2"])
    def test_iommu_enabled(self, mock_listdir, mock_isdir):
        self.assertTrue(VirtualizationManager.is_iommu_enabled())

    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=[])
    def test_iommu_no_groups(self, mock_listdir, mock_isdir):
        self.assertFalse(VirtualizationManager.is_iommu_enabled())

    @patch("os.path.isdir", return_value=False)
    def test_iommu_sysfs_missing(self, mock_isdir):
        self.assertFalse(VirtualizationManager.is_iommu_enabled())

    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", side_effect=PermissionError)
    def test_iommu_permission_denied(self, mock_listdir, mock_isdir):
        self.assertFalse(VirtualizationManager.is_iommu_enabled())


# ---------------------------------------------------------------------------
# TestIOMMUGroups — detailed group parsing
# ---------------------------------------------------------------------------

class TestIOMMUGroups(unittest.TestCase):
    """Tests for IOMMU group and device enumeration."""

    @patch("utils.virtualization.VirtualizationManager._get_lspci_description", return_value="NVIDIA GA106")
    @patch("os.readlink", return_value="/sys/bus/pci/drivers/nvidia")
    @patch("os.path.islink", return_value=True)
    @patch("utils.virtualization.VirtualizationManager._read_sysfs")
    @patch("os.listdir")
    @patch("os.path.isdir")
    def test_get_iommu_groups_single(self, mock_isdir, mock_listdir, mock_sysfs, mock_islink, mock_readlink, mock_lspci):
        # Simulate: iommu_groups dir exists, has group "1", which has device "0000:01:00.0"
        def isdir_side(path):
            if path == "/sys/kernel/iommu_groups":
                return True
            if path == "/sys/kernel/iommu_groups/1/devices":
                return True
            return False

        mock_isdir.side_effect = isdir_side
        mock_listdir.side_effect = lambda path: {
            "/sys/kernel/iommu_groups": ["1"],
            "/sys/kernel/iommu_groups/1/devices": ["0000:01:00.0"],
        }.get(path, [])

        def sysfs_side(path):
            if "vendor" in path:
                return "0x10de"
            if "device" in path:
                return "0x2503"
            return ""

        mock_sysfs.side_effect = sysfs_side

        groups = VirtualizationManager.get_iommu_groups()
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].group_id, 1)
        self.assertEqual(len(groups[0].devices), 1)
        self.assertEqual(groups[0].devices[0].slot, "0000:01:00.0")
        self.assertEqual(groups[0].devices[0].vendor_id, "10de")
        self.assertEqual(groups[0].devices[0].device_id, "2503")
        self.assertEqual(groups[0].devices[0].driver, "nvidia")

    @patch("os.path.isdir", return_value=False)
    def test_get_iommu_groups_no_sysfs(self, mock_isdir):
        groups = VirtualizationManager.get_iommu_groups()
        self.assertEqual(groups, [])


# ---------------------------------------------------------------------------
# TestVFIOHelpers — GPU passthrough utilities
# ---------------------------------------------------------------------------

class TestVFIOHelpers(unittest.TestCase):
    """Tests for VFIO passthrough helper methods."""

    def test_generate_vfio_ids_single(self):
        dev = IOMMUDevice(slot="0000:01:00.0", description="GPU", vendor_id="10de", device_id="2503", driver="nvidia")
        result = VirtualizationManager.generate_vfio_ids([dev])
        self.assertEqual(result, "vfio-pci.ids=10de:2503")

    def test_generate_vfio_ids_multiple(self):
        devs = [
            IOMMUDevice(slot="0000:01:00.0", description="GPU", vendor_id="10de", device_id="2503", driver="nvidia"),
            IOMMUDevice(slot="0000:01:00.1", description="Audio", vendor_id="10de", device_id="228e", driver="snd_hda_intel"),
        ]
        result = VirtualizationManager.generate_vfio_ids(devs)
        self.assertEqual(result, "vfio-pci.ids=10de:2503,10de:228e")

    def test_generate_vfio_ids_deduplication(self):
        devs = [
            IOMMUDevice(slot="0000:01:00.0", description="GPU", vendor_id="10de", device_id="2503", driver=""),
            IOMMUDevice(slot="0000:02:00.0", description="GPU", vendor_id="10de", device_id="2503", driver=""),
        ]
        result = VirtualizationManager.generate_vfio_ids(devs)
        self.assertEqual(result, "vfio-pci.ids=10de:2503")

    def test_generate_vfio_ids_empty(self):
        result = VirtualizationManager.generate_vfio_ids([])
        self.assertEqual(result, "")

    @patch("builtins.open", mock_open(read_data="BOOT_IMAGE=/vmlinuz root=UUID=... intel_iommu=on iommu=pt"))
    def test_check_iommu_cmdline_intel(self):
        result = VirtualizationManager.check_iommu_in_cmdline()
        self.assertTrue(result["intel_iommu"])
        self.assertFalse(result["amd_iommu"])
        self.assertTrue(result["iommu_pt"])

    @patch("builtins.open", mock_open(read_data="BOOT_IMAGE=/vmlinuz root=UUID=... amd_iommu=on iommu=pt"))
    def test_check_iommu_cmdline_amd(self):
        result = VirtualizationManager.check_iommu_in_cmdline()
        self.assertFalse(result["intel_iommu"])
        self.assertTrue(result["amd_iommu"])
        self.assertTrue(result["iommu_pt"])

    @patch("builtins.open", mock_open(read_data="BOOT_IMAGE=/vmlinuz root=UUID=... quiet splash"))
    def test_check_iommu_cmdline_none(self):
        result = VirtualizationManager.check_iommu_in_cmdline()
        self.assertFalse(result["intel_iommu"])
        self.assertFalse(result["amd_iommu"])
        self.assertFalse(result["iommu_pt"])


# ---------------------------------------------------------------------------
# TestTooling — virt tool availability
# ---------------------------------------------------------------------------

class TestTooling(unittest.TestCase):
    """Tests for virtualization tool detection."""

    @patch("shutil.which")
    def test_all_tools_present(self, mock_which):
        mock_which.return_value = "/usr/bin/dummy"
        tools = VirtualizationManager.check_virt_tools()
        self.assertTrue(tools["libvirtd"])
        self.assertTrue(tools["virsh"])
        self.assertTrue(tools["virt-install"])
        self.assertTrue(tools["qemu-system-x86_64"])
        self.assertTrue(tools["swtpm"])

    @patch("shutil.which", return_value=None)
    def test_no_tools_present(self, mock_which):
        tools = VirtualizationManager.check_virt_tools()
        for tool_name, available in tools.items():
            self.assertFalse(available, f"{tool_name} should be missing")

    @patch("shutil.which", return_value=None)
    def test_missing_packages(self, mock_which):
        missing = VirtualizationManager.get_missing_packages()
        self.assertIn("qemu-kvm", missing)
        self.assertIn("libvirt-daemon-config-network", missing)
        self.assertIn("virt-install", missing)
        self.assertIn("swtpm", missing)

    @patch("shutil.which")
    def test_no_missing_packages_when_all_installed(self, mock_which):
        mock_which.return_value = "/usr/bin/dummy"
        missing = VirtualizationManager.get_missing_packages()
        self.assertEqual(missing, [])


# ---------------------------------------------------------------------------
# TestFullStatus — combined report
# ---------------------------------------------------------------------------

class TestFullStatus(unittest.TestCase):
    """Tests for the combined virtualization status report."""

    @patch("utils.virtualization.VirtualizationManager.get_iommu_groups", return_value=[])
    @patch("utils.virtualization.VirtualizationManager.is_iommu_enabled", return_value=False)
    @patch("utils.virtualization.VirtualizationManager.is_kvm_module_loaded", return_value=True)
    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions", return_value=(True, "Intel", "vmx"))
    @patch("shutil.which", return_value=None)
    def test_full_status_basic(self, mock_which, mock_cpu, mock_kvm, mock_iommu, mock_groups):
        status = VirtualizationManager.get_full_status()
        self.assertIsInstance(status, VirtStatus)
        self.assertTrue(status.kvm_supported)
        self.assertTrue(status.kvm_module_loaded)
        self.assertFalse(status.iommu_enabled)
        self.assertEqual(status.vendor, "Intel")
        self.assertEqual(status.cpu_extension, "vmx")
        self.assertEqual(status.iommu_groups, [])

    @patch("utils.virtualization.VirtualizationManager.get_iommu_groups")
    @patch("utils.virtualization.VirtualizationManager.is_iommu_enabled", return_value=True)
    @patch("utils.virtualization.VirtualizationManager.is_kvm_module_loaded", return_value=True)
    @patch("utils.virtualization.VirtualizationManager.check_cpu_virt_extensions", return_value=(True, "AMD", "svm"))
    @patch("shutil.which")
    def test_full_status_all_ready(self, mock_which, mock_cpu, mock_kvm, mock_iommu, mock_groups):
        mock_which.return_value = "/usr/bin/dummy"
        mock_groups.return_value = [IOMMUGroup(group_id=0), IOMMUGroup(group_id=1)]

        status = VirtualizationManager.get_full_status()
        self.assertTrue(status.kvm_supported)
        self.assertTrue(status.iommu_enabled)
        self.assertEqual(len(status.iommu_groups), 2)
        self.assertEqual(status.vendor, "AMD")
        self.assertTrue(status.libvirt_available)
        self.assertTrue(status.qemu_available)
        self.assertTrue(status.swtpm_available)


# ---------------------------------------------------------------------------
# TestSummary — human-readable output
# ---------------------------------------------------------------------------

class TestSummary(unittest.TestCase):
    """Tests for the summary text output."""

    @patch("utils.virtualization.VirtualizationManager.get_full_status")
    def test_summary_all_enabled(self, mock_status):
        mock_status.return_value = VirtStatus(
            kvm_supported=True,
            kvm_module_loaded=True,
            iommu_enabled=True,
            iommu_groups=[IOMMUGroup(0), IOMMUGroup(1), IOMMUGroup(2)],
            vendor="Intel",
            cpu_extension="vmx",
            libvirt_available=True,
            qemu_available=True,
            swtpm_available=True,
        )
        summary = VirtualizationManager.get_summary()
        self.assertIn("Intel", summary)
        self.assertIn("vmx", summary)
        self.assertIn("Module loaded", summary)
        self.assertIn("3 groups", summary)
        self.assertIn("QEMU: Installed", summary)
        self.assertIn("Libvirt: Available", summary)
        self.assertIn("swtpm: Available", summary)

    @patch("utils.virtualization.VirtualizationManager.get_full_status")
    def test_summary_nothing_available(self, mock_status):
        mock_status.return_value = VirtStatus()
        summary = VirtualizationManager.get_summary()
        self.assertIn("No hardware virtualization", summary)
        self.assertIn("NOT loaded", summary)
        self.assertIn("Disabled", summary)
        self.assertIn("Not installed", summary)


if __name__ == "__main__":
    unittest.main()
