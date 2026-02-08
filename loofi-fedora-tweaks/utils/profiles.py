"""
System Profiles Manager - Quick-switch system configurations.
Part of v13.0 "Nexus Update".

Predefined profiles for Gaming, Development, Battery Saver,
Presentation, and Server. Each profile adjusts power governor,
compositor settings, notification rules, and services.
"""

import os
import json
import subprocess
import shutil

from utils.containers import Result


class ProfileManager:
    """
    Manages system profiles for quick-switching between configurations.

    Supports built-in profiles (Gaming, Development, Battery Saver,
    Presentation, Server) and user-created custom profiles stored as
    JSON files in PROFILES_DIR.
    """

    PROFILES_DIR = os.path.expanduser("~/.config/loofi-fedora-tweaks/profiles")
    STATE_FILE = os.path.expanduser("~/.config/loofi-fedora-tweaks/active_profile.json")

    BUILTIN_PROFILES = {
        "gaming": {
            "name": "Gaming",
            "description": "Optimized for gaming performance",
            "icon": "\U0001f3ae",
            "settings": {
                "governor": "performance",
                "compositor": "disabled",
                "notifications": "dnd",
                "swappiness": 10,
                "gamemode": True,
                "services_enable": ["gamemode"],
                "services_disable": ["tracker-miner-fs-3"],
            },
        },
        "development": {
            "name": "Development",
            "description": "Tuned for software development workflows",
            "icon": "\U0001f4bb",
            "settings": {
                "governor": "schedutil",
                "compositor": "enabled",
                "notifications": "all",
                "docker": True,
                "services_enable": ["docker", "podman"],
                "services_disable": [],
            },
        },
        "battery_saver": {
            "name": "Battery Saver",
            "description": "Maximise battery life on laptops",
            "icon": "\U0001f50b",
            "settings": {
                "governor": "powersave",
                "compositor": "reduced",
                "notifications": "critical",
                "swappiness": 60,
                "services_enable": [],
                "services_disable": ["bluetooth"],
            },
        },
        "presentation": {
            "name": "Presentation",
            "description": "No distractions during presentations",
            "icon": "\U0001f4fa",
            "settings": {
                "governor": "performance",
                "compositor": "enabled",
                "notifications": "dnd",
                "screen_timeout": 0,
                "services_enable": [],
                "services_disable": [],
            },
        },
        "server": {
            "name": "Server",
            "description": "Headless server optimisation",
            "icon": "\U0001f5a5",
            "settings": {
                "governor": "performance",
                "compositor": "disabled",
                "notifications": "critical",
                "swappiness": 10,
                "services_enable": [],
                "services_disable": [],
            },
        },
    }

    # ==================== PROFILE LISTING ====================

    @classmethod
    def list_profiles(cls) -> list[dict]:
        """
        Return all available profiles (built-in + custom).

        Returns:
            List of profile dicts with keys: key, name, description, icon,
            builtin (bool), and settings.
        """
        profiles = []

        # Built-in profiles
        for key, profile in cls.BUILTIN_PROFILES.items():
            profiles.append({
                "key": key,
                "name": profile["name"],
                "description": profile["description"],
                "icon": profile["icon"],
                "builtin": True,
                "settings": profile["settings"],
            })

        # Custom profiles from disk
        if os.path.isdir(cls.PROFILES_DIR):
            try:
                for filename in sorted(os.listdir(cls.PROFILES_DIR)):
                    if not filename.endswith(".json"):
                        continue
                    filepath = os.path.join(cls.PROFILES_DIR, filename)
                    try:
                        with open(filepath, "r") as f:
                            data = json.load(f)
                        profiles.append({
                            "key": os.path.splitext(filename)[0],
                            "name": data.get("name", filename),
                            "description": data.get("description", ""),
                            "icon": data.get("icon", "\U0001f527"),
                            "builtin": False,
                            "settings": data.get("settings", {}),
                        })
                    except (json.JSONDecodeError, OSError):
                        continue
            except OSError:
                pass

        return profiles

    @classmethod
    def get_profile(cls, name: str) -> dict:
        """
        Get a single profile by its key name.

        Checks built-in profiles first, then custom profiles on disk.

        Args:
            name: Profile key name.

        Returns:
            Profile dict, or empty dict if not found.
        """
        # Check built-ins
        if name in cls.BUILTIN_PROFILES:
            profile = cls.BUILTIN_PROFILES[name]
            return {
                "key": name,
                "name": profile["name"],
                "description": profile["description"],
                "icon": profile["icon"],
                "builtin": True,
                "settings": profile["settings"],
            }

        # Check custom profiles
        safe_name = cls._sanitize_name(name)
        filepath = os.path.join(cls.PROFILES_DIR, f"{safe_name}.json")
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                return {
                    "key": safe_name,
                    "name": data.get("name", safe_name),
                    "description": data.get("description", ""),
                    "icon": data.get("icon", "\U0001f527"),
                    "builtin": False,
                    "settings": data.get("settings", {}),
                }
            except (json.JSONDecodeError, OSError):
                pass

        return {}

    # ==================== PROFILE APPLICATION ====================

    @classmethod
    def apply_profile(cls, name: str) -> Result:
        """
        Apply a profile's settings to the system.

        Sets CPU governor, toggles services, adjusts swappiness,
        and records the active profile in the state file.

        Args:
            name: Profile key name to apply.

        Returns:
            Result with success status and detail message.
        """
        profile = cls.get_profile(name)
        if not profile:
            return Result(False, f"Profile '{name}' not found.")

        settings = profile.get("settings", {})
        errors = []

        # Apply governor
        governor = settings.get("governor")
        if governor:
            if not cls._set_governor(governor):
                errors.append(f"Failed to set governor to '{governor}'")

        # Toggle services
        enable = settings.get("services_enable", [])
        disable = settings.get("services_disable", [])
        cls._toggle_services(enable, disable)

        # Set swappiness
        swappiness = settings.get("swappiness")
        if swappiness is not None:
            if not cls._set_swappiness(swappiness):
                errors.append(f"Failed to set swappiness to {swappiness}")

        # Record active profile
        cls._save_active_profile(name)

        if errors:
            return Result(
                False,
                f"Profile '{profile['name']}' applied with errors: {'; '.join(errors)}",
                {"profile": name, "errors": errors},
            )

        return Result(
            True,
            f"Profile '{profile['name']}' applied successfully.",
            {"profile": name},
        )

    # ==================== CUSTOM PROFILE CRUD ====================

    @classmethod
    def create_custom_profile(cls, name: str, settings: dict) -> Result:
        """
        Save a custom profile to JSON in PROFILES_DIR.

        Args:
            name: Human-readable profile name.
            settings: Dict of profile settings (governor, services, etc.).

        Returns:
            Result with success status.
        """
        if not name or not name.strip():
            return Result(False, "Profile name cannot be empty.")

        safe_name = cls._sanitize_name(name)

        # Do not overwrite built-in profiles
        if safe_name in cls.BUILTIN_PROFILES:
            return Result(False, f"Cannot overwrite built-in profile '{safe_name}'.")

        try:
            os.makedirs(cls.PROFILES_DIR, exist_ok=True)
        except OSError as e:
            return Result(False, f"Cannot create profiles directory: {e}")

        data = {
            "name": name.strip(),
            "description": settings.get("description", f"Custom profile: {name}"),
            "icon": settings.get("icon", "\U0001f527"),
            "settings": {k: v for k, v in settings.items() if k not in ("description", "icon")},
        }

        filepath = os.path.join(cls.PROFILES_DIR, f"{safe_name}.json")
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)
            return Result(True, f"Custom profile '{name}' saved.", {"path": filepath})
        except OSError as e:
            return Result(False, f"Failed to save profile: {e}")

    @classmethod
    def delete_custom_profile(cls, name: str) -> Result:
        """
        Delete a custom profile from disk.

        Built-in profiles cannot be deleted.

        Args:
            name: Profile key name to delete.

        Returns:
            Result with success status.
        """
        if name in cls.BUILTIN_PROFILES:
            return Result(False, "Cannot delete built-in profiles.")

        safe_name = cls._sanitize_name(name)
        filepath = os.path.join(cls.PROFILES_DIR, f"{safe_name}.json")

        if not os.path.isfile(filepath):
            return Result(False, f"Custom profile '{name}' not found.")

        try:
            os.remove(filepath)
            return Result(True, f"Profile '{name}' deleted.")
        except OSError as e:
            return Result(False, f"Failed to delete profile: {e}")

    # ==================== ACTIVE PROFILE ====================

    @classmethod
    def get_active_profile(cls) -> str:
        """
        Read the currently active profile name from the state file.

        Returns:
            Profile key name, or empty string if none is active.
        """
        try:
            with open(cls.STATE_FILE, "r") as f:
                data = json.load(f)
            return data.get("active_profile", "")
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return ""

    @classmethod
    def _save_active_profile(cls, name: str) -> None:
        """Persist the active profile name to the state file."""
        try:
            state_dir = os.path.dirname(cls.STATE_FILE)
            os.makedirs(state_dir, exist_ok=True)
            with open(cls.STATE_FILE, "w") as f:
                json.dump({"active_profile": name}, f)
        except OSError:
            pass

    # ==================== CAPTURE CURRENT STATE ====================

    @classmethod
    def capture_current_as_profile(cls, name: str) -> Result:
        """
        Capture the current system state and save it as a custom profile.

        Reads the current CPU governor, swappiness, and records them
        in a new custom profile.

        Args:
            name: Name for the new profile.

        Returns:
            Result with success status.
        """
        if not name or not name.strip():
            return Result(False, "Profile name cannot be empty.")

        settings = {}

        # Read current governor
        try:
            result = subprocess.run(
                ["cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                settings["governor"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Read current swappiness
        try:
            with open("/proc/sys/vm/swappiness", "r") as f:
                settings["swappiness"] = int(f.read().strip())
        except (FileNotFoundError, ValueError, OSError):
            pass

        return cls.create_custom_profile(name, settings)

    # ==================== INTERNAL HELPERS ====================

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize profile name to prevent path traversal."""
        safe = os.path.basename(name.strip())
        safe = safe.replace("..", "").replace("/", "").replace("\\", "")
        safe = safe.replace(" ", "_").lower()
        if not safe:
            safe = "unnamed_profile"
        return safe

    @staticmethod
    def _set_governor(governor: str) -> bool:
        """
        Set the CPU frequency governor using cpupower.

        Args:
            governor: Governor name (performance, powersave, schedutil, etc.).

        Returns:
            True if the command succeeded, False otherwise.
        """
        if not shutil.which("cpupower"):
            return False
        try:
            result = subprocess.run(
                ["pkexec", "cpupower", "frequency-set", "-g", governor],
                capture_output=True, text=True, timeout=30,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def _toggle_services(enable: list, disable: list) -> None:
        """
        Enable and disable systemd services.

        Args:
            enable: List of service names to start and enable.
            disable: List of service names to stop and disable.
        """
        for service in enable:
            try:
                subprocess.run(
                    ["systemctl", "start", service],
                    capture_output=True, text=True, timeout=30,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass

        for service in disable:
            try:
                subprocess.run(
                    ["systemctl", "stop", service],
                    capture_output=True, text=True, timeout=30,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass

    @staticmethod
    def _set_swappiness(value: int) -> bool:
        """
        Set the kernel swappiness value.

        Args:
            value: Swappiness value (0-100).

        Returns:
            True on success, False otherwise.
        """
        if not (0 <= value <= 100):
            return False
        try:
            result = subprocess.run(
                ["pkexec", "sysctl", f"vm.swappiness={value}"],
                capture_output=True, text=True, timeout=15,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False
