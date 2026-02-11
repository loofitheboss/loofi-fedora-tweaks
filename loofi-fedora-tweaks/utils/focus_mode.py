"""
Focus Mode - Distraction blocking and productivity features.
Blocks distracting domains, enables DND, and kills specified processes.
"""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class FocusModeProfile:
    """A Focus Mode profile configuration."""
    name: str
    blocked_domains: List[str]
    kill_processes: List[str]
    enable_dnd: bool = True
    custom_hosts_backup: str = ""


class FocusMode:
    """
    Focus Mode manager.
    Provides distraction blocking via hosts file, DND, and process control.
    """

    CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
    CONFIG_FILE = CONFIG_DIR / "focus_mode.json"
    HOSTS_FILE = Path("/etc/hosts")
    HOSTS_BACKUP = CONFIG_DIR / "hosts.backup"
    FOCUS_MARKER = "# LOOFI-FOCUS-MODE-START"
    FOCUS_MARKER_END = "# LOOFI-FOCUS-MODE-END"

    # Default blocked domains
    DEFAULT_BLOCKED = [
        "reddit.com", "www.reddit.com", "old.reddit.com",
        "twitter.com", "www.twitter.com", "x.com", "www.x.com",
        "facebook.com", "www.facebook.com",
        "instagram.com", "www.instagram.com",
        "tiktok.com", "www.tiktok.com",
        "youtube.com", "www.youtube.com",
        "twitch.tv", "www.twitch.tv",
        "discord.com", "www.discord.com",
    ]

    # Default processes to kill
    DEFAULT_KILL_PROCESSES = [
        "steam", "discord", "slack", "telegram-desktop"
    ]

    _active = False
    _active_profile: Optional[str] = None

    @classmethod
    def ensure_config(cls):
        """Ensure config directory and default profile exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if not cls.CONFIG_FILE.exists():
            default_config = {
                "active": False,
                "active_profile": None,
                "profiles": {
                    "default": {
                        "name": "Default Work Profile",
                        "blocked_domains": cls.DEFAULT_BLOCKED,
                        "kill_processes": cls.DEFAULT_KILL_PROCESSES,
                        "enable_dnd": True
                    }
                }
            }
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=2)

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Load focus mode configuration."""
        cls.ensure_config()
        try:
            with open(cls.CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"active": False, "profiles": {}}

    @classmethod
    def save_config(cls, config: Dict[str, Any]):
        """Save focus mode configuration."""
        cls.ensure_config()
        with open(cls.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    @classmethod
    def list_profiles(cls) -> List[str]:
        """
        Get list of available focus mode profiles.

        Returns:
            List of profile names
        """
        config = cls.load_config()
        return list(config.get("profiles", {}).keys())

    @classmethod
    def get_profile(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific profile by name.

        Returns:
            Profile dict or None
        """
        config = cls.load_config()
        return config.get("profiles", {}).get(name)

    @classmethod
    def save_profile(cls, name: str, profile: Dict[str, Any]) -> bool:
        """
        Save or update a focus mode profile.

        Returns:
            True on success
        """
        try:
            config = cls.load_config()
            if "profiles" not in config:
                config["profiles"] = {}
            config["profiles"][name] = profile
            cls.save_config(config)
            return True
        except Exception:
            return False

    @classmethod
    def delete_profile(cls, name: str) -> bool:
        """
        Delete a focus mode profile.

        Returns:
            True on success
        """
        try:
            config = cls.load_config()
            if name in config.get("profiles", {}):
                del config["profiles"][name]
                cls.save_config(config)
                return True
            return False
        except Exception:
            return False

    @classmethod
    def is_active(cls) -> bool:
        """
        Check if focus mode is currently active.

        Returns:
            True if active
        """
        config = cls.load_config()
        return config.get("active", False)

    @classmethod
    def get_active_profile(cls) -> Optional[str]:
        """
        Get the name of the currently active profile.

        Returns:
            Profile name or None
        """
        config = cls.load_config()
        if config.get("active"):
            return config.get("active_profile")
        return None

    # -------------------------------------------------------------------------
    # Activation / Deactivation
    # -------------------------------------------------------------------------

    @classmethod
    def enable(cls, profile_name: str = "default") -> Dict[str, Any]:
        """
        Enable focus mode with specified profile.

        Args:
            profile_name: Name of profile to activate

        Returns:
            Dict with 'success', 'message', and details
        """
        result = {
            "success": False,
            "message": "",
            "hosts_modified": False,
            "dnd_enabled": False,
            "processes_killed": []
        }

        profile = cls.get_profile(profile_name)
        if not profile:
            result["message"] = f"Profile '{profile_name}' not found"
            return result

        # Block domains via /etc/hosts
        if profile.get("blocked_domains"):
            hosts_result = cls._block_domains(profile["blocked_domains"])
            result["hosts_modified"] = hosts_result["success"]
            if not hosts_result["success"]:
                result["message"] = hosts_result["message"]
                return result

        # Enable Do Not Disturb
        if profile.get("enable_dnd", True):
            dnd_result = cls._enable_dnd()
            result["dnd_enabled"] = dnd_result["success"]

        # Kill distracting processes
        if profile.get("kill_processes"):
            killed = cls._kill_processes(profile["kill_processes"])
            result["processes_killed"] = killed

        # Update state
        config = cls.load_config()
        config["active"] = True
        config["active_profile"] = profile_name
        cls.save_config(config)

        result["success"] = True
        result["message"] = f"Focus mode enabled with profile '{profile_name}'"
        return result

    @classmethod
    def disable(cls) -> Dict[str, Any]:
        """
        Disable focus mode and restore normal state.

        Returns:
            Dict with 'success' and 'message'
        """
        result = {
            "success": False,
            "message": "",
            "hosts_restored": False,
            "dnd_disabled": False
        }

        # Restore hosts file
        restore_result = cls._restore_hosts()
        result["hosts_restored"] = restore_result["success"]

        # Disable DND
        dnd_result = cls._disable_dnd()
        result["dnd_disabled"] = dnd_result["success"]

        # Update state
        config = cls.load_config()
        config["active"] = False
        config["active_profile"] = None
        cls.save_config(config)

        result["success"] = True
        result["message"] = "Focus mode disabled"
        return result

    @classmethod
    def toggle(cls, profile_name: str = "default") -> Dict[str, Any]:
        """
        Toggle focus mode on/off.

        Returns:
            Result dict from enable() or disable()
        """
        if cls.is_active():
            return cls.disable()
        else:
            return cls.enable(profile_name)

    # -------------------------------------------------------------------------
    # Domain Blocking
    # -------------------------------------------------------------------------

    @classmethod
    def _block_domains(cls, domains: List[str]) -> Dict[str, Any]:
        """
        Add blocking entries to /etc/hosts.
        Requires pkexec for root access.

        Returns:
            Dict with 'success' and 'message'
        """
        try:
            # Create hosts entries
            entries = [cls.FOCUS_MARKER]
            for domain in domains:
                entries.append(f"127.0.0.1 {domain}")
            entries.append(cls.FOCUS_MARKER_END)
            entries_str = "\n".join(entries) + "\n"

            # Read current hosts file
            with open(cls.HOSTS_FILE, "r") as f:
                current_hosts = f.read()

            # Backup original hosts file (without our entries)
            clean_hosts = cls._remove_focus_entries(current_hosts)
            cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(cls.HOSTS_BACKUP, "w") as f:
                f.write(clean_hosts)

            # Add our entries
            new_hosts = clean_hosts.rstrip() + "\n\n" + entries_str

            # Write via pkexec
            result = subprocess.run(
                ["pkexec", "tee", str(cls.HOSTS_FILE)],
                input=new_hosts.encode(),
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0:
                return {"success": True, "message": f"Blocked {len(domains)} domains"}
            else:
                return {"success": False, "message": "Failed to modify hosts (pkexec denied?)"}

        except subprocess.TimeoutExpired:
            return {"success": False, "message": "pkexec timed out"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @classmethod
    def _restore_hosts(cls) -> Dict[str, Any]:
        """
        Remove focus mode entries from /etc/hosts.

        Returns:
            Dict with 'success' and 'message'
        """
        try:
            with open(cls.HOSTS_FILE, "r") as f:
                current_hosts = f.read()

            clean_hosts = cls._remove_focus_entries(current_hosts)

            result = subprocess.run(
                ["pkexec", "tee", str(cls.HOSTS_FILE)],
                input=clean_hosts.encode(),
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0:
                return {"success": True, "message": "Hosts file restored"}
            else:
                return {"success": False, "message": "Failed to restore hosts"}

        except Exception as e:
            return {"success": False, "message": str(e)}

    @classmethod
    def _remove_focus_entries(cls, hosts_content: str) -> str:
        """Remove focus mode entries from hosts content."""
        lines = hosts_content.splitlines()
        result = []
        in_focus_block = False

        for line in lines:
            if cls.FOCUS_MARKER in line:
                in_focus_block = True
                continue
            elif cls.FOCUS_MARKER_END in line:
                in_focus_block = False
                continue

            if not in_focus_block:
                result.append(line)

        return "\n".join(result)

    # -------------------------------------------------------------------------
    # Do Not Disturb
    # -------------------------------------------------------------------------

    @classmethod
    def _enable_dnd(cls) -> Dict[str, Any]:
        """
        Enable Do Not Disturb via desktop environment DBus.

        Returns:
            Dict with 'success' and 'message'
        """
        # Try KDE first
        kde_result = cls._kde_dnd(True)
        if kde_result["success"]:
            return kde_result

        # Try GNOME
        gnome_result = cls._gnome_dnd(True)
        if gnome_result["success"]:
            return gnome_result

        return {"success": False, "message": "Could not enable DND (unsupported desktop)"}

    @classmethod
    def _disable_dnd(cls) -> Dict[str, Any]:
        """
        Disable Do Not Disturb.

        Returns:
            Dict with 'success' and 'message'
        """
        kde_result = cls._kde_dnd(False)
        if kde_result["success"]:
            return kde_result

        gnome_result = cls._gnome_dnd(False)
        if gnome_result["success"]:
            return gnome_result

        return {"success": False, "message": "Could not disable DND"}

    @classmethod
    def _kde_dnd(cls, enable: bool) -> Dict[str, Any]:
        """Toggle KDE Do Not Disturb via dbus-send."""
        try:
            # KDE Plasma uses org.freedesktop.Notifications inhibit
            "Inhibit" if enable else "UnInhibit"

            if enable:
                result = subprocess.run([
                    "dbus-send", "--session", "--print-reply",
                    "--dest=org.freedesktop.Notifications",
                    "/org/freedesktop/Notifications",
                    "org.freedesktop.Notifications.Inhibit",
                    "string:loofi-focus-mode",
                    "string:Focus Mode Active",
                    "dict:string:string:"
                ], capture_output=True, text=True, timeout=10)
            else:
                # For UnInhibit, we'd need the cookie from Inhibit
                # Simpler approach: use KDE-specific qdbus
                result = subprocess.run([
                    "qdbus", "org.kde.plasmashell", "/org/kde/plasmashell",
                    "org.kde.PlasmaShell.evaluateScript",
                    "var dnd = dataEngine('notifications'); dnd.connectSource('Inhibited'); dnd.serviceAction('notifications', 'DoNotDisturb').trigger();"
                ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return {"success": True, "message": f"KDE DND {'enabled' if enable else 'disabled'}"}

            return {"success": False, "message": "KDE DND command failed"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @classmethod
    def _gnome_dnd(cls, enable: bool) -> Dict[str, Any]:
        """Toggle GNOME Do Not Disturb via gsettings."""
        try:
            value = "true" if enable else "false"
            result = subprocess.run([
                "gsettings", "set", "org.gnome.desktop.notifications",
                "show-banners", value
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return {"success": True, "message": f"GNOME DND {'enabled' if enable else 'disabled'}"}

            return {"success": False, "message": "GNOME DND command failed"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # -------------------------------------------------------------------------
    # Process Management
    # -------------------------------------------------------------------------

    @classmethod
    def _kill_processes(cls, process_names: List[str]) -> List[str]:
        """
        Kill specified processes by name.

        Returns:
            List of successfully killed process names
        """
        killed = []
        for name in process_names:
            try:
                result = subprocess.run(
                    ["pkill", "-", name],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    killed.append(name)
            except Exception:
                pass
        return killed

    @classmethod
    def get_running_distractions(cls, process_list: Optional[List[str]] = None) -> List[str]:
        """
        Check which distraction processes are currently running.

        Returns:
            List of running process names
        """
        if process_list is None:
            process_list = cls.DEFAULT_KILL_PROCESSES

        running = []
        try:
            result = subprocess.run(
                ["ps", "-eo", "comm"],
                capture_output=True, text=True, timeout=5
            )
            processes = result.stdout.lower()

            for name in process_list:
                if name.lower() in processes:
                    running.append(name)
        except Exception:
            pass

        return running
