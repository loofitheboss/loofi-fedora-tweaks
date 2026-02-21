"""
System Profiles Manager - Quick-switch system configurations.
Part of v24.0 "Power Features".

Predefined profiles for Gaming, Development, Battery Saver,
Presentation, and Server. Each profile adjusts power governor,
compositor settings, notification rules, and services.
"""

import json
import logging
import os
import shutil
import subprocess
import time

from core.profiles.models import ProfileRecord
from core.profiles.storage import ProfileStore

from utils.containers import Result
from utils.snapshot_manager import SnapshotManager

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Manages system profiles for quick-switching between configurations.

    Supports built-in profiles and user-created custom profiles.
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

    @classmethod
    def _store(cls) -> ProfileStore:
        return ProfileStore(cls.PROFILES_DIR, cls.BUILTIN_PROFILES)

    # ==================== PROFILE LISTING ====================

    @classmethod
    def list_profiles(cls) -> list[dict]:
        """Return all available profiles (built-in + custom)."""
        store = cls._store()
        return [record.to_dict() for record in store.list_profiles()]

    @classmethod
    def get_profile(cls, name: str) -> dict:
        """Get one profile by key (builtin first, then custom)."""
        key = name if name in cls.BUILTIN_PROFILES else cls._sanitize_name(name)
        record = cls._store().get_profile(key)
        return record.to_dict() if record else {}

    # ==================== PROFILE APPLICATION ====================

    @classmethod
    def apply_profile(cls, name: str, create_snapshot: bool = True) -> Result:
        """
        Apply a profile's settings to the system.

        Args:
            name: Profile key name to apply.
            create_snapshot: Attempt a snapshot before applying.
        """
        profile = cls.get_profile(name)
        if not profile:
            return Result(False, f"Profile '{name}' not found.")

        settings = profile.get("settings", {})
        errors = []
        warnings: list[str] = []

        # Snapshot hook (best-effort, never blocks profile application).
        if create_snapshot:
            cls._create_pre_apply_snapshot(profile.get("key", name), warnings)

        governor = settings.get("governor")
        if governor and not cls._set_governor(governor):
            errors.append(f"Failed to set governor to '{governor}'")

        enable = settings.get("services_enable", [])
        disable = settings.get("services_disable", [])
        cls._toggle_services(enable, disable)

        swappiness = settings.get("swappiness")
        if swappiness is not None and not cls._set_swappiness(swappiness):
            errors.append(f"Failed to set swappiness to {swappiness}")

        cls._save_active_profile(profile.get("key", name))

        data = {
            "profile": profile.get("key", name),
            "warnings": warnings,
            "errors": errors,
        }

        if errors:
            message = f"Profile '{profile['name']}' applied with errors: {'; '.join(errors)}"
            if warnings:
                message += f" | Warnings: {'; '.join(warnings)}"
            return Result(False, message, data)

        message = f"Profile '{profile['name']}' applied successfully."
        if warnings:
            message += f" Warnings: {'; '.join(warnings)}"
        return Result(True, message, data)

    @classmethod
    def _create_pre_apply_snapshot(cls, profile_key: str, warnings: list):
        """Attempt snapshot creation before profile apply (best effort)."""
        backend = SnapshotManager.get_preferred_backend()
        if not backend:
            warnings.append("No snapshot backend available; applying without snapshot")
            return

        label = f"profile-{cls._sanitize_name(profile_key)}-{int(time.time())}"
        binary, args, _desc = SnapshotManager.create_snapshot(label, backend=backend)

        # SnapshotManager returns an echo tuple when backend selection fails.
        if binary == "echo":
            warnings.append("Snapshot operation unavailable; applying without snapshot")
            return

        try:
            result = subprocess.run(
                [binary] + args,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                err = result.stderr.strip() or result.stdout.strip() or "unknown error"
                warnings.append(f"Snapshot creation failed ({backend}): {err}")
        except (subprocess.TimeoutExpired, OSError) as exc:
            warnings.append(f"Snapshot creation failed ({backend}): {exc}")

    # ==================== CUSTOM PROFILE CRUD ====================

    @classmethod
    def create_custom_profile(cls, name: str, settings: dict) -> Result:
        """Save a custom profile to JSON in PROFILES_DIR."""
        if not name or not name.strip():
            return Result(False, "Profile name cannot be empty.")

        safe_name = cls._sanitize_name(name)
        if safe_name in cls.BUILTIN_PROFILES:
            return Result(False, f"Cannot overwrite built-in profile '{safe_name}'.")

        try:
            record = ProfileRecord(
                key=safe_name,
                name=name.strip(),
                description=settings.get("description", f"Custom profile: {name}"),
                icon=settings.get("icon", "\U0001f527"),
                builtin=False,
                settings={k: v for k, v in settings.items() if k not in ("description", "icon")},
            )
        except ValueError as exc:
            return Result(False, f"Invalid profile: {exc}")

        ok, message, path = cls._store().save_custom_profile(record, overwrite=False)
        return Result(ok, message, {"path": path} if path else {})

    @classmethod
    def delete_custom_profile(cls, name: str) -> Result:
        """Delete a custom profile from disk."""
        key = cls._sanitize_name(name)
        ok, message = cls._store().delete_custom_profile(key)
        return Result(ok, message)

    # ==================== PROFILE IMPORT/EXPORT ====================

    @classmethod
    def export_profile_data(cls, name: str) -> dict:
        """Export one profile as JSON payload for API usage."""
        key = name if name in cls.BUILTIN_PROFILES else cls._sanitize_name(name)
        ok, _message, payload = cls._store().export_profile_data(key)
        return payload if ok else {}

    @classmethod
    def import_profile_data(cls, payload: dict, overwrite: bool = False) -> Result:
        """Import one profile from a JSON payload."""
        ok, message, data = cls._store().import_profile_data(payload, overwrite=overwrite)
        return Result(ok, message, data)

    @classmethod
    def export_bundle_data(cls, include_builtins: bool = False) -> dict:
        """Export full profile bundle payload for API usage."""
        _ok, _message, payload = cls._store().export_bundle_data(include_builtins=include_builtins)
        return payload

    @classmethod
    def import_bundle_data(cls, payload: dict, overwrite: bool = False) -> Result:
        """Import a full profile bundle from JSON payload."""
        ok, message, data = cls._store().import_bundle_data(payload, overwrite=overwrite)
        return Result(ok, message, data)

    @classmethod
    def export_profile_json(cls, name: str, path: str) -> Result:
        """Export one profile to a JSON file."""
        key = name if name in cls.BUILTIN_PROFILES else cls._sanitize_name(name)
        ok, message = cls._store().export_profile(key, path)
        return Result(ok, message, {"profile": key, "path": path})

    @classmethod
    def import_profile_json(cls, path: str, overwrite: bool = False) -> Result:
        """Import one profile from a JSON file."""
        ok, message, data = cls._store().import_profile(path, overwrite=overwrite)
        return Result(ok, message, data)

    @classmethod
    def export_bundle_json(cls, path: str, include_builtins: bool = False) -> Result:
        """Export all profiles to a bundle JSON file."""
        ok, message = cls._store().export_bundle(path, include_builtins=include_builtins)
        return Result(ok, message, {"path": path, "include_builtins": include_builtins})

    @classmethod
    def import_bundle_json(cls, path: str, overwrite: bool = False) -> Result:
        """Import a bundle JSON file."""
        ok, message, data = cls._store().import_bundle(path, overwrite=overwrite)
        return Result(ok, message, data)

    # ==================== ACTIVE PROFILE ====================

    @classmethod
    def get_active_profile(cls) -> str:
        """Read active profile key from STATE_FILE."""
        try:
            with open(cls.STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return str(data.get("active_profile", ""))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return ""

    @classmethod
    def _save_active_profile(cls, name: str) -> None:
        """Persist active profile key to state file."""
        try:
            state_dir = os.path.dirname(cls.STATE_FILE)
            os.makedirs(state_dir, exist_ok=True)
            with open(cls.STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"active_profile": name}, f)
        except OSError as e:
            logger.debug("Failed to save active profile: %s", e)

    @classmethod
    def capture_current_as_profile(cls, name: str) -> Result:
        """Capture current system state and save as a custom profile."""
        if not name or not name.strip():
            return Result(False, "Profile name cannot be empty.")

        settings: dict[str, object] = {}

        try:
            result = subprocess.run(
                ["cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                settings["governor"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.debug("Failed to read current governor: %s", e)

        try:
            with open("/proc/sys/vm/swappiness", "r", encoding="utf-8") as f:
                settings["swappiness"] = int(f.read().strip())
        except (FileNotFoundError, ValueError, OSError) as e:
            logger.debug("Failed to read swappiness: %s", e)

        return cls.create_custom_profile(name, settings)

    # ==================== INTERNAL HELPERS ====================

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize profile key for safe file usage."""
        safe = os.path.basename((name or "").strip())
        safe = safe.replace("..", "").replace("/", "").replace("\\", "")
        safe = safe.replace(" ", "_").lower()
        if not safe:
            safe = "unnamed_profile"
        return safe

    @staticmethod
    def _set_governor(governor: str) -> bool:
        """Set CPU governor using cpupower."""
        if not shutil.which("cpupower"):
            return False
        try:
            result = subprocess.run(
                ["pkexec", "cpupower", "frequency-set", "-g", governor],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def _toggle_services(enable: list, disable: list) -> None:
        """Enable/disable service lists (best effort)."""
        for service in enable:
            try:
                subprocess.run(
                    ["systemctl", "start", service],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, OSError) as e:
                logger.debug("Failed to start service %s: %s", service, e)

        for service in disable:
            try:
                subprocess.run(
                    ["systemctl", "stop", service],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, OSError) as e:
                logger.debug("Failed to stop service %s: %s", service, e)

    @staticmethod
    def _set_swappiness(value: int) -> bool:
        """Set kernel swappiness value."""
        if not (0 <= value <= 100):
            return False
        try:
            result = subprocess.run(
                ["pkexec", "sysctl", f"vm.swappiness={value}"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False
