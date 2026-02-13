"""
Config Manager - Central configuration export/import.
Handles backup and restore of all app settings.
"""

import json
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.containers import Result

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration export, import, and versioning."""

    CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    PRESETS_DIR = CONFIG_DIR / "presets"

    @classmethod
    def ensure_dirs(cls):
        """Ensure config directories exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cls.PRESETS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_config_version(cls) -> str:
        """Get current config format version."""
        return "5.5.0"

    @classmethod
    def get_system_info(cls) -> dict:
        """Gather system information for config export."""
        info = {
            "hostname": platform.node(),
            "kernel": platform.release(),
            "arch": platform.machine(),
        }

        # Get Fedora version
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        info["os"] = line.split("=")[1].strip().strip('"')
                        break
        except OSError as e:
            logger.debug("Failed to read /etc/os-release: %s", e)
            info["os"] = "Fedora Linux"

        # Get hardware model
        try:
            with open("/sys/class/dmi/id/product_name", "r") as f:
                info["hardware"] = f.read().strip()
        except OSError as e:
            logger.debug("Failed to read hardware model: %s", e)
            info["hardware"] = "Unknown"

        return info

    @classmethod
    def gather_hardware_settings(cls) -> dict:
        """Gather current hardware settings."""
        from utils.hardware import HardwareManager

        return {
            "cpu_governor": HardwareManager.get_current_governor(),
            "power_profile": HardwareManager.get_power_profile(),
            "gpu_mode": HardwareManager.get_gpu_mode() if HardwareManager.is_hybrid_gpu() else None,
        }

    @classmethod
    def gather_repo_settings(cls) -> dict:
        """Gather enabled repositories."""
        repos: dict[str, list[str]] = {"enabled": [], "disabled": []}

        try:
            result = subprocess.run(
                ["dnf", "repolist", "--enabled", "-q"],
                capture_output=True, text=True, check=False
            )
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                if line.strip():
                    repo_id = line.split()[0]
                    repos["enabled"].append(repo_id)
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list repos: %s", e)

        return repos

    @classmethod
    def gather_flatpak_apps(cls) -> list:
        """Get list of installed Flatpak apps."""
        apps = []
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True, text=True, check=False
            )
            apps = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list flatpak apps: %s", e)
        return apps

    @classmethod
    def export_all(cls) -> dict:
        """
        Export all current settings to a config dict.

        Returns:
            Complete configuration dictionary.
        """
        cls.ensure_dirs()

        config = {
            "version": cls.get_config_version(),
            "exported_at": datetime.now().isoformat(),
            "system": cls.get_system_info(),
            "settings": {
                "hardware": cls.gather_hardware_settings(),
                "repos": cls.gather_repo_settings(),
                "flatpak_apps": cls.gather_flatpak_apps(),
            }
        }

        # Include local presets if any
        presets = []
        if cls.PRESETS_DIR.exists():
            for preset_file in cls.PRESETS_DIR.glob("*.json"):
                try:
                    with open(preset_file, "r") as f:
                        presets.append(json.load(f))
                except (OSError, json.JSONDecodeError) as e:
                    logger.debug("Failed to load preset %s: %s", preset_file, e)
        config["presets"] = presets

        return config

    @classmethod
    def export_to_file(cls, path: str) -> Result:
        """
        Export config to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            Result with success status and message.
        """
        try:
            config = cls.export_all()
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            return Result(True, f"Config exported to {path}")
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to export config: %s", e)
            return Result(False, str(e))

    @classmethod
    def import_from_file(cls, path: str) -> Result:
        """
        Import config from a JSON file.

        Args:
            path: Source file path.

        Returns:
            Result with success status and message.
        """
        try:
            with open(path, "r") as f:
                config = json.load(f)
            return cls.import_all(config)
        except FileNotFoundError:
            return Result(False, "File not found")
        except json.JSONDecodeError:
            return Result(False, "Invalid JSON file")
        except OSError as e:
            logger.debug("Failed to import config from file: %s", e)
            return Result(False, str(e))

    @classmethod
    def import_all(cls, config: dict) -> Result:
        """
        Apply all settings from a config dict.

        Args:
            config: Configuration dictionary.

        Returns:
            Result with success status and message.
        """
        cls.ensure_dirs()

        applied = []
        errors = []

        # Validate version
        if "version" not in config:
            return Result(False, "Invalid config: missing version")

        settings = config.get("settings", {})

        # Apply hardware settings
        hardware = settings.get("hardware", {})
        if hardware.get("cpu_governor"):
            try:
                from utils.hardware import HardwareManager
                if HardwareManager.set_governor(hardware["cpu_governor"]):
                    applied.append("CPU Governor")
                else:
                    errors.append("CPU Governor (failed)")
            except (ImportError, OSError) as e:
                logger.debug("Failed to set CPU governor: %s", e)
                errors.append("CPU Governor (error)")

        if hardware.get("power_profile"):
            try:
                from utils.hardware import HardwareManager
                if HardwareManager.set_power_profile(hardware["power_profile"]):
                    applied.append("Power Profile")
                else:
                    errors.append("Power Profile (failed)")
            except (ImportError, OSError) as e:
                logger.debug("Failed to set power profile: %s", e)
                errors.append("Power Profile (error)")

        # Import presets
        presets = config.get("presets", [])
        for preset in presets:
            if "name" in preset:
                try:
                    preset_path = cls.PRESETS_DIR / f"{preset['name'].lower().replace(' ', '_')}.json"
                    with open(preset_path, "w") as f:
                        json.dump(preset, f, indent=2)
                    applied.append(f"Preset: {preset['name']}")
                except (OSError, json.JSONDecodeError) as e:
                    logger.debug("Failed to import preset %s: %s", preset.get('name', 'unknown'), e)
                    errors.append(f"Preset: {preset.get('name', 'unknown')}")

        if errors:
            return Result(True, f"Imported: {', '.join(applied)}. Errors: {', '.join(errors)}")
        else:
            return Result(True, f"Successfully imported: {', '.join(applied) if applied else 'No settings changed'}")

    @classmethod
    def save_config(cls, config: dict) -> bool:
        """Save current runtime config."""
        cls.ensure_dirs()
        try:
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to save config: %s", e)
            return False

    @classmethod
    def load_config(cls) -> Optional[dict]:
        """Load saved config."""
        try:
            with open(cls.CONFIG_FILE, "r") as f:
                config: dict = json.load(f)
                return config
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to load config: %s", e)
            return None
