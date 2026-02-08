"""
Virtualization Plugin - First-party plugin for VM management.
Part of the Plugin Architecture Refactor for v12.0 "Sovereign Update".

Provides VM management, GPU passthrough checks, and disposable VMs
as an optional loadable plugin so users who don't need virtualization
features don't pay the import cost.
"""

import logging

from utils.plugin_base import LoofiPlugin, PluginInfo

logger = logging.getLogger("loofi.plugins.virtualization")


class VirtualizationPlugin(LoofiPlugin):
    """Virtualization plugin providing VM management and VFIO support."""

    @property
    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="Virtualization",
            version="1.0.0",
            author="Loofi Team",
            description="VM management, GPU passthrough, and disposable VMs",
            icon="\U0001f5a5\ufe0f",
        )

    def create_widget(self):
        """Lazily import and return the VirtualizationTab widget.

        Uses __import__ to avoid importing PyQt6 at module load time,
        keeping the plugin lightweight when loaded only for CLI commands.
        """
        mod = __import__(
            "ui.advanced_tab",
            fromlist=["AdvancedTab"],
        )
        return mod.AdvancedTab()

    def get_cli_commands(self) -> dict:
        """Return CLI commands provided by this plugin."""
        return {
            "vm-list": self._cmd_vm_list,
            "vm-status": self._cmd_vm_status,
            "vfio-check": self._cmd_vfio_check,
        }

    def on_load(self) -> None:
        """Called when the plugin is loaded."""
        logger.info("Virtualization plugin loaded")

    def on_unload(self) -> None:
        """Called when the plugin is unloaded. Perform cleanup."""
        logger.info("Virtualization plugin unloaded")

    # ---- CLI command implementations ----

    @staticmethod
    def _cmd_vm_list() -> str:
        """List virtual machines."""
        from utils.virtualization import VirtualizationManager
        status = VirtualizationManager.get_full_status()
        if not status.libvirt_available:
            return "libvirt is not installed. Install with: sudo dnf install libvirt"
        return "VM listing requires libvirt (use 'virsh list --all')"

    @staticmethod
    def _cmd_vm_status() -> str:
        """Show virtualization readiness."""
        from utils.virtualization import VirtualizationManager
        status = VirtualizationManager.get_full_status()
        lines = [
            f"KVM supported: {status.kvm_supported}",
            f"KVM module loaded: {status.kvm_module_loaded}",
            f"CPU vendor: {status.vendor}",
            f"CPU extension: {status.cpu_extension}",
            f"IOMMU enabled: {status.iommu_enabled}",
            f"IOMMU groups: {len(status.iommu_groups)}",
            f"libvirt available: {status.libvirt_available}",
            f"QEMU available: {status.qemu_available}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _cmd_vfio_check() -> str:
        """Check VFIO passthrough prerequisites."""
        from utils.virtualization import VirtualizationManager
        status = VirtualizationManager.get_full_status()
        checks = []
        checks.append(
            f"[{'OK' if status.kvm_supported else 'FAIL'}] "
            f"CPU virtualization extensions ({status.cpu_extension or 'none'})"
        )
        checks.append(
            f"[{'OK' if status.iommu_enabled else 'FAIL'}] "
            "IOMMU enabled"
        )
        checks.append(
            f"[{'OK' if status.qemu_available else 'FAIL'}] "
            "QEMU installed"
        )
        checks.append(
            f"[{'OK' if status.libvirt_available else 'FAIL'}] "
            "libvirt installed"
        )
        return "\n".join(checks)
