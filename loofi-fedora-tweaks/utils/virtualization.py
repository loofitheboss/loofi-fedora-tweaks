"""
Virtualization support detection and IOMMU analysis.
Pre-v11.5 "Hypervisor Update" groundwork.

Checks CPU virtualization extensions (VT-x / AMD-V), KVM module status,
IOMMU groups, and libvirt availability. Used by the upcoming VM Quick-Create
wizard and VFIO Passthrough Assistant.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class IOMMUGroup:
    """Represents a single IOMMU group with its PCI devices."""
    group_id: int
    devices: list = field(default_factory=list)


@dataclass
class IOMMUDevice:
    """A PCI device within an IOMMU group."""
    slot: str           # e.g. "0000:01:00.0"
    description: str    # e.g. "NVIDIA Corporation GA106 [GeForce RTX 3060]"
    vendor_id: str      # e.g. "10de"
    device_id: str      # e.g. "2503"
    driver: str         # e.g. "nvidia", "vfio-pci", ""


@dataclass
class VirtStatus:
    """Full virtualization capability report."""
    kvm_supported: bool = False
    kvm_module_loaded: bool = False
    iommu_enabled: bool = False
    iommu_groups: list = field(default_factory=list)
    vendor: str = "unknown"
    cpu_extension: str = ""       # "vmx" or "svm"
    libvirt_available: bool = False
    qemu_available: bool = False
    swtpm_available: bool = False  # TPM 2.0 emulator (needed for Win11)
    virt_install_available: bool = False


class VirtualizationManager:
    """Detects virtualization capabilities: KVM, IOMMU, VFIO readiness."""

    # ==================== CPU & KVM CHECKS ====================

    @classmethod
    def check_cpu_virt_extensions(cls) -> tuple:
        """Check CPU for hardware virtualization extensions.

        Returns:
            (supported: bool, vendor: str, extension: str)
            vendor is 'Intel' or 'AMD', extension is 'vmx' or 'svm'.
        """
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()
        except (FileNotFoundError, PermissionError):
            return (False, "unknown", "")

        if "vmx" in cpuinfo:
            return (True, "Intel", "vmx")
        elif "svm" in cpuinfo:
            return (True, "AMD", "svm")

        return (False, "unknown", "")

    @classmethod
    def is_kvm_module_loaded(cls) -> bool:
        """Check if the KVM kernel module is loaded."""
        try:
            with open("/proc/modules", "r") as f:
                modules = f.read()
            return "kvm_intel" in modules or "kvm_amd" in modules or "kvm " in modules
        except (FileNotFoundError, PermissionError):
            return False

    @classmethod
    def is_kvm_device_accessible(cls) -> bool:
        """Check if /dev/kvm exists and is accessible."""
        return os.path.exists("/dev/kvm")

    # ==================== IOMMU CHECKS ====================

    @classmethod
    def is_iommu_enabled(cls) -> bool:
        """Check if IOMMU is enabled by looking for populated groups in sysfs."""
        iommu_base = "/sys/kernel/iommu_groups"
        if not os.path.isdir(iommu_base):
            return False
        try:
            entries = os.listdir(iommu_base)
            return len(entries) > 0
        except PermissionError:
            return False

    @classmethod
    def get_iommu_groups(cls) -> list:
        """Enumerate all IOMMU groups and their PCI devices.

        Returns:
            List of IOMMUGroup objects, each containing IOMMUDevice entries.
        """
        iommu_base = "/sys/kernel/iommu_groups"
        if not os.path.isdir(iommu_base):
            return []

        groups = []
        try:
            group_dirs = sorted(os.listdir(iommu_base), key=lambda x: int(x) if x.isdigit() else 0)
        except PermissionError:
            return []

        for group_name in group_dirs:
            if not group_name.isdigit():
                continue

            group_id = int(group_name)
            devices_dir = os.path.join(iommu_base, group_name, "devices")
            if not os.path.isdir(devices_dir):
                continue

            group = IOMMUGroup(group_id=group_id)
            try:
                device_slots = os.listdir(devices_dir)
            except PermissionError:
                groups.append(group)
                continue

            for slot in sorted(device_slots):
                device = cls._read_pci_device(slot)
                group.devices.append(device)

            groups.append(group)

        return groups

    @classmethod
    def _read_pci_device(cls, slot: str) -> IOMMUDevice:
        """Read PCI device info from sysfs for a given slot."""
        base = f"/sys/bus/pci/devices/{slot}"
        vendor_id = cls._read_sysfs(os.path.join(base, "vendor")).replace("0x", "")
        device_id = cls._read_sysfs(os.path.join(base, "device")).replace("0x", "")

        # Current driver (if bound)
        driver_link = os.path.join(base, "driver")
        driver = ""
        if os.path.islink(driver_link):
            driver = os.path.basename(os.readlink(driver_link))

        # Human-readable description via lspci (if available)
        description = cls._get_lspci_description(slot)

        return IOMMUDevice(
            slot=slot,
            description=description,
            vendor_id=vendor_id,
            device_id=device_id,
            driver=driver,
        )

    @classmethod
    def _get_lspci_description(cls, slot: str) -> str:
        """Get human-readable device description from lspci."""
        if not shutil.which("lspci"):
            return ""
        try:
            result = subprocess.run(
                ["lspci", "-s", slot],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # lspci output: "01:00.0 VGA compatible controller: NVIDIA ..."
                parts = result.stdout.strip().split(": ", 1)
                return parts[1] if len(parts) > 1 else result.stdout.strip()
        except (subprocess.TimeoutExpired, Exception):
            pass
        return ""

    @staticmethod
    def _read_sysfs(path: str) -> str:
        """Read a single sysfs file, returning empty string on failure."""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError):
            return ""

    # ==================== GPU PASSTHROUGH HELPERS ====================

    @classmethod
    def find_gpu_devices(cls) -> list:
        """Find all GPU devices across IOMMU groups.

        Returns list of (IOMMUGroup, IOMMUDevice) tuples for VGA/3D devices.
        Useful for the VFIO Assistant to identify passthrough candidates.
        """
        gpu_results = []
        for group in cls.get_iommu_groups():
            for device in group.devices:
                desc_lower = device.description.lower()
                if any(kw in desc_lower for kw in ("vga", "3d controller", "display")):
                    gpu_results.append((group, device))
        return gpu_results

    @classmethod
    def generate_vfio_ids(cls, devices: list) -> str:
        """Generate the vfio-pci.ids= kernel parameter for given devices.

        Args:
            devices: List of IOMMUDevice objects to isolate.

        Returns:
            Kernel parameter string, e.g. "vfio-pci.ids=10de:2503,10de:228e"
        """
        ids = []
        for dev in devices:
            if dev.vendor_id and dev.device_id:
                pair = f"{dev.vendor_id}:{dev.device_id}"
                if pair not in ids:
                    ids.append(pair)
        if not ids:
            return ""
        return f"vfio-pci.ids={','.join(ids)}"

    @classmethod
    def get_current_kernel_cmdline(cls) -> str:
        """Read the current kernel command line."""
        try:
            with open("/proc/cmdline", "r") as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError):
            return ""

    @classmethod
    def check_iommu_in_cmdline(cls) -> dict:
        """Check if IOMMU is enabled in the kernel command line.

        Returns dict with 'intel_iommu', 'amd_iommu', and 'iommu_pt' booleans.
        """
        cmdline = cls.get_current_kernel_cmdline()
        return {
            "intel_iommu": "intel_iommu=on" in cmdline,
            "amd_iommu": "amd_iommu=on" in cmdline,
            "iommu_pt": "iommu=pt" in cmdline,
        }

    # ==================== TOOLING CHECKS ====================

    @classmethod
    def check_virt_tools(cls) -> dict:
        """Check availability of virtualization management tools.

        Returns dict mapping tool names to booleans.
        """
        tools = {
            "libvirtd": shutil.which("libvirtd") is not None,
            "virsh": shutil.which("virsh") is not None,
            "virt-install": shutil.which("virt-install") is not None,
            "virt-manager": shutil.which("virt-manager") is not None,
            "qemu-system-x86_64": shutil.which("qemu-system-x86_64") is not None,
            "swtpm": shutil.which("swtpm") is not None,
        }
        return tools

    @classmethod
    def get_missing_packages(cls) -> list:
        """Return package names that should be installed for full VM support.

        Only returns packages whose corresponding tools are missing.
        """
        tool_to_package = {
            "libvirtd": "libvirt-daemon-config-network",
            "virsh": "libvirt-client",
            "virt-install": "virt-install",
            "qemu-system-x86_64": "qemu-kvm",
            "swtpm": "swtpm",
        }
        missing = []
        tools = cls.check_virt_tools()
        for tool, pkg in tool_to_package.items():
            if not tools.get(tool, False):
                missing.append(pkg)
        return missing

    # ==================== FULL STATUS REPORT ====================

    @classmethod
    def get_full_status(cls) -> VirtStatus:
        """Run all virtualization checks and return a full status report.

        This is the primary entry point for the UI and CLI.
        """
        cpu_ok, vendor, ext = cls.check_cpu_virt_extensions()
        tools = cls.check_virt_tools()
        iommu_enabled = cls.is_iommu_enabled()

        status = VirtStatus(
            kvm_supported=cpu_ok,
            kvm_module_loaded=cls.is_kvm_module_loaded(),
            iommu_enabled=iommu_enabled,
            iommu_groups=cls.get_iommu_groups() if iommu_enabled else [],
            vendor=vendor,
            cpu_extension=ext,
            libvirt_available=tools.get("libvirtd", False) or tools.get("virsh", False),
            qemu_available=tools.get("qemu-system-x86_64", False),
            swtpm_available=tools.get("swtpm", False),
            virt_install_available=tools.get("virt-install", False),
        )
        return status

    @classmethod
    def get_summary(cls) -> str:
        """Get a human-readable summary of virtualization readiness."""
        status = cls.get_full_status()
        parts = []

        if status.kvm_supported:
            parts.append(f"CPU: {status.vendor} ({status.cpu_extension})")
        else:
            parts.append("CPU: No hardware virtualization detected")

        if status.kvm_module_loaded:
            parts.append("KVM: Module loaded")
        else:
            parts.append("KVM: Module NOT loaded")

        if status.iommu_enabled:
            count = len(status.iommu_groups)
            parts.append(f"IOMMU: Enabled ({count} groups)")
        else:
            parts.append("IOMMU: Disabled")

        if status.qemu_available:
            parts.append("QEMU: Installed")
        else:
            parts.append("QEMU: Not installed")

        if status.libvirt_available:
            parts.append("Libvirt: Available")
        else:
            parts.append("Libvirt: Not available")

        if status.swtpm_available:
            parts.append("swtpm: Available (Win11 TPM ready)")
        else:
            parts.append("swtpm: Not installed")

        return " | ".join(parts)
