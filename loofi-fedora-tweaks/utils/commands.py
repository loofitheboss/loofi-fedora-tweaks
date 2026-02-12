"""
Centralized command builder for privileged operations.
Part of v11.0 "Aurora Update".

Replaces inconsistent pkexec command construction across multiple files.
Ensures all privileged commands use argument arrays (never shell strings)
to prevent command injection.
"""

from typing import List, Tuple

from utils.system import SystemManager

CommandTuple = Tuple[str, List[str], str]


class PrivilegedCommand:
    """Safe builder for pkexec-wrapped system commands."""

    @staticmethod
    def dnf(action: str, *packages: str, flags: list | None = None) -> CommandTuple:
        """Build a DNF command tuple (cmd, args, description).

        On Atomic systems, automatically uses rpm-ostree instead.
        """
        pm = SystemManager.get_package_manager()
        flag_list = flags or []

        if pm == "rpm-ostree":
            if action == "install":
                return ("pkexec", ["rpm-ostree", "install"] + list(packages), f"Installing {', '.join(packages)} via rpm-ostree...")
            elif action == "remove":
                return ("pkexec", ["rpm-ostree", "uninstall"] + list(packages), f"Removing {', '.join(packages)} via rpm-ostree...")
            elif action == "update":
                return ("pkexec", ["rpm-ostree", "upgrade"], "Upgrading system via rpm-ostree...")
            elif action == "clean":
                return ("pkexec", ["rpm-ostree", "cleanup", "--base"], "Cleaning rpm-ostree base...")
            else:
                return ("pkexec", ["rpm-ostree", action] + list(packages), f"rpm-ostree {action}...")
        else:
            args = ["dnf", action, "-y"] + flag_list + list(packages)
            desc_map = {
                "install": f"Installing {', '.join(packages)}...",
                "remove": f"Removing {', '.join(packages)}...",
                "update": "Updating system packages...",
                "clean": "Cleaning DNF cache...",
                "autoremove": "Removing unused packages...",
            }
            desc = desc_map.get(action, f"DNF {action}...")
            return ("pkexec", args, desc)

    @staticmethod
    def systemctl(action: str, service: str, user: bool = False) -> CommandTuple:
        """Build a systemctl command tuple."""
        if user:
            return ("systemctl", ["--user", action, service], f"{action.title()} user service {service}...")
        return ("pkexec", ["systemctl", action, service], f"{action.title()} system service {service}...")

    @staticmethod
    def sysctl(key: str, value: str) -> CommandTuple:
        """Build a sysctl set command tuple."""
        return ("pkexec", ["sysctl", "-w", f"{key}={value}"], f"Setting {key} = {value}...")

    @staticmethod
    def write_file(path: str, content: str) -> CommandTuple:
        """Write content to a file via pkexec tee."""
        return ("pkexec", ["tee", path], f"Writing to {path}...")

    @staticmethod
    def flatpak(action: str, *args: str) -> CommandTuple:
        """Build a flatpak command tuple."""
        return ("flatpak", [action] + list(args), f"Flatpak {action}...")

    @staticmethod
    def fwupd(action: str = "update") -> CommandTuple:
        """Build a fwupdmgr command tuple."""
        return ("pkexec", ["fwupdmgr", action, "-y"], f"Firmware {action}...")

    @staticmethod
    def journal_vacuum(time: str = "2weeks") -> CommandTuple:
        """Build a journal vacuum command tuple."""
        return ("pkexec", ["journalctl", f"--vacuum-time={time}"], f"Vacuuming journal ({time})...")

    @staticmethod
    def fstrim() -> CommandTuple:
        """Build an SSD trim command tuple."""
        return ("pkexec", ["fstrim", "-av"], "Trimming SSD volumes...")

    @staticmethod
    def rpm_rebuild() -> CommandTuple:
        """Build an RPM database rebuild command tuple."""
        return ("pkexec", ["rpm", "--rebuilddb"], "Rebuilding RPM database...")
