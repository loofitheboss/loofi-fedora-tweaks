"""
Risk Registry — Classifies privileged actions by risk level.
Part of v36.0 "Horizon" (base) and v37.0 "Pinnacle" (extensions).

Provides a RiskLevel enum, RiskEntry dataclass, and RiskRegistry
singleton that maps action IDs to risk classifications.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class RiskLevel(Enum):
    """Risk classification for privileged actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class RiskEntry:
    """Immutable risk classification for a single action."""
    level: RiskLevel
    description: str
    revert_command: Optional[str] = None
    revert_description: Optional[str] = None


class RiskRegistry:
    """Singleton registry mapping action IDs to risk entries."""

    _instance: Optional["RiskRegistry"] = None
    _registry: Dict[str, RiskEntry] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._registry = cls._build_registry()
        return cls._instance

    @classmethod
    def _build_registry(cls) -> Dict[str, RiskEntry]:
        """Build the default risk registry with all known actions."""
        return {
            # === v36.0 Horizon — Core actions ===

            "dnf_install": RiskEntry(
                level=RiskLevel.LOW,
                description="Install packages via DNF",
                revert_command="pkexec dnf remove -y <package>",
                revert_description="Remove the installed package",
            ),
            "dnf_remove": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Remove packages via DNF",
                revert_command="pkexec dnf install -y <package>",
                revert_description="Reinstall the removed package",
            ),
            "dnf_update": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Update all system packages",
                revert_command=None,
                revert_description="Restore from snapshot if available",
            ),
            "dnf_clean": RiskEntry(
                level=RiskLevel.LOW,
                description="Clean DNF cache",
            ),
            "systemctl_enable": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Enable a systemd service",
                revert_command="pkexec systemctl disable <service>",
                revert_description="Disable the service",
            ),
            "systemctl_disable": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Disable a systemd service",
                revert_command="pkexec systemctl enable <service>",
                revert_description="Re-enable the service",
            ),
            "systemctl_restart": RiskEntry(
                level=RiskLevel.LOW,
                description="Restart a systemd service",
            ),
            "firewall_add_rule": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Add a firewall rule",
                revert_command="pkexec firewall-cmd --remove-<type>=<value> --permanent",
                revert_description="Remove the added firewall rule",
            ),
            "firewall_remove_rule": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Remove a firewall rule",
                revert_command="pkexec firewall-cmd --add-<type>=<value> --permanent",
                revert_description="Re-add the removed rule",
            ),
            "kernel_parameter_set": RiskEntry(
                level=RiskLevel.HIGH,
                description="Modify kernel boot parameters",
                revert_command="pkexec grubby --update-kernel=DEFAULT --remove-args=<param>",
                revert_description="Remove the kernel parameter and regenerate GRUB",
            ),

            # === v37.0 Pinnacle — New actions ===

            # Smart Updates
            "update_rollback": RiskEntry(
                level=RiskLevel.HIGH,
                description="Rollback the last system update",
                revert_command=None,
                revert_description="Re-run the update to restore previous state",
            ),
            "update_schedule": RiskEntry(
                level=RiskLevel.LOW,
                description="Schedule an automatic update",
                revert_command="systemctl --user disable loofi-update.timer",
                revert_description="Cancel the scheduled update timer",
            ),

            # Extension Management
            "extension_install": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Install a desktop extension",
                revert_command="gnome-extensions uninstall <uuid>",
                revert_description="Uninstall the extension",
            ),
            "extension_remove": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Remove a desktop extension",
                revert_command="gnome-extensions install <uuid>",
                revert_description="Reinstall the extension",
            ),
            "extension_enable": RiskEntry(
                level=RiskLevel.LOW,
                description="Enable a desktop extension",
                revert_command="gnome-extensions disable <uuid>",
                revert_description="Disable the extension",
            ),
            "extension_disable": RiskEntry(
                level=RiskLevel.LOW,
                description="Disable a desktop extension",
                revert_command="gnome-extensions enable <uuid>",
                revert_description="Re-enable the extension",
            ),

            # Flatpak Management
            "flatpak_cleanup": RiskEntry(
                level=RiskLevel.LOW,
                description="Remove unused Flatpak runtimes",
            ),

            # Boot Configuration
            "grub_set_timeout": RiskEntry(
                level=RiskLevel.HIGH,
                description="Change GRUB boot timeout",
                revert_command="pkexec sed -i 's/GRUB_TIMEOUT=.*/GRUB_TIMEOUT=5/' /etc/default/grub",
                revert_description="Reset GRUB timeout to default (5 seconds)",
            ),
            "grub_set_default_kernel": RiskEntry(
                level=RiskLevel.HIGH,
                description="Change default boot kernel",
                revert_command="pkexec grubby --set-default-index=0",
                revert_description="Reset to first kernel as default",
            ),
            "grub_set_theme": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Change GRUB visual theme",
                revert_command="pkexec sed -i '/GRUB_THEME/d' /etc/default/grub",
                revert_description="Remove custom GRUB theme",
            ),
            "grub_apply": RiskEntry(
                level=RiskLevel.HIGH,
                description="Regenerate GRUB configuration",
                revert_command=None,
                revert_description="Restore from snapshot if GRUB becomes unbootable",
            ),
            "grub_set_cmdline": RiskEntry(
                level=RiskLevel.HIGH,
                description="Modify kernel command line parameters",
                revert_command=None,
                revert_description="Remove parameter and regenerate GRUB",
            ),

            # Snapshot / Backup
            "snapshot_create": RiskEntry(
                level=RiskLevel.LOW,
                description="Create a system snapshot",
            ),
            "snapshot_restore": RiskEntry(
                level=RiskLevel.HIGH,
                description="Restore system from a snapshot",
                revert_command=None,
                revert_description="Create a new snapshot before restoring to preserve current state",
            ),
            "snapshot_delete": RiskEntry(
                level=RiskLevel.MEDIUM,
                description="Delete a system snapshot",
                revert_command=None,
                revert_description="Snapshot deletion is irreversible",
            ),

            # Display Configuration
            "display_scaling": RiskEntry(
                level=RiskLevel.LOW,
                description="Change display scaling factor",
                revert_command="gsettings set org.gnome.desktop.interface text-scaling-factor 1.0",
                revert_description="Reset to 100% scaling",
            ),
            "display_fractional": RiskEntry(
                level=RiskLevel.LOW,
                description="Toggle fractional scaling",
            ),
        }

    @staticmethod
    def get_risk(action_id: str) -> Optional[RiskEntry]:
        """Get risk entry for an action ID, or None if unregistered."""
        registry = RiskRegistry()
        return registry._registry.get(action_id)

    @staticmethod
    def get_revert_instructions(action_id: str) -> Optional[str]:
        """Get human-readable revert instructions for an action."""
        entry = RiskRegistry.get_risk(action_id)
        if entry and entry.revert_description:
            return entry.revert_description
        return None

    @staticmethod
    def get_all_actions() -> Dict[str, RiskEntry]:
        """Return all registered actions."""
        registry = RiskRegistry()
        return dict(registry._registry)

    @staticmethod
    def get_actions_by_level(level: RiskLevel) -> Dict[str, RiskEntry]:
        """Return all actions matching the given risk level."""
        registry = RiskRegistry()
        return {k: v for k, v in registry._registry.items() if v.level == level}
