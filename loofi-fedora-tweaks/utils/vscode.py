"""
VS Code configuration management utilities.
Part of v7.1 "Developer" update.

Handles extension recommendations and settings injection for
Python, C++, and other development profiles.
"""

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Operation result with message."""

    success: bool
    message: str
    data: Optional[dict] = None


class VSCodeManager:
    """
    Manages VS Code extensions and settings.

    Supports:
    - Standard VS Code (code)
    - VSCodium (codium)
    - Flatpak VS Code (com.visualstudio.code)
    """

    # Extension profiles for different development scenarios
    EXTENSION_PROFILES = {
        "python": {
            "name": "Python Development",
            "description": "Python language support, linting, debugging, and Jupyter",
            "extensions": [
                "ms-python.python",
                "ms-python.vscode-pylance",
                "ms-python.debugpy",
                "ms-python.black-formatter",
                "ms-toolsai.jupyter",
                "charliermarsh.ruff",
            ],
        },
        "cpp": {
            "name": "C/C++ Development",
            "description": "C/C++ language support, CMake, and debugging",
            "extensions": [
                "ms-vscode.cpptools",
                "ms-vscode.cpptools-extension-pack",
                "ms-vscode.cmake-tools",
                "twxs.cmake",
                "xaver.clang-format",
            ],
        },
        "rust": {
            "name": "Rust Development",
            "description": "Rust analyzer and TOML support",
            "extensions": [
                "rust-lang.rust-analyzer",
                "tamasfe.even-better-toml",
                "vadimcn.vscode-lldb",
            ],
        },
        "web": {
            "name": "Web Development",
            "description": "JavaScript, TypeScript, HTML, CSS",
            "extensions": [
                "esbenp.prettier-vscode",
                "dbaeumer.vscode-eslint",
                "bradlc.vscode-tailwindcss",
                "formulahendry.auto-rename-tag",
                "ecmel.vscode-html-css",
            ],
        },
        "containers": {
            "name": "Container Development",
            "description": "Docker and container tools",
            "extensions": [
                "ms-azuretools.vscode-docker",
                "ms-vscode-remote.remote-containers",
                "exiasr.hadolint",
            ],
        },
    }

    @classmethod
    def get_vscode_command(cls) -> Optional[str]:
        """
        Find the VS Code command available on the system.

        Returns:
            Command name if found, None otherwise.
        """
        # Priority order: native > flatpak > codium
        candidates = ["code", "codium", "code-oss"]

        for cmd in candidates:
            if shutil.which(cmd):
                return cmd

        # Check for Flatpak
        if shutil.which("flatpak"):
            flatpak_apps = ["com.visualstudio.code", "com.vscodium.codium"]
            for app in flatpak_apps:
                try:
                    result = subprocess.run(
                        ["flatpak", "info", app], capture_output=True, timeout=5
                    )
                    if result.returncode == 0:
                        return f"flatpak run {app}"
                except (subprocess.SubprocessError, OSError) as e:
                    logger.debug("Flatpak VS Code detection failed: %s", e)

        return None

    @classmethod
    def is_available(cls) -> bool:
        """Check if any VS Code variant is available."""
        return cls.get_vscode_command() is not None

    @classmethod
    def get_installed_extensions(cls) -> list[str]:
        """
        Get list of currently installed extensions.

        Returns:
            List of extension IDs.
        """
        cmd = cls.get_vscode_command()
        if not cmd:
            return []

        try:
            if cmd.startswith("flatpak"):
                result = subprocess.run(
                    cmd.split() + ["--list-extensions"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                result = subprocess.run(
                    [cmd, "--list-extensions"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            if result.returncode == 0:
                return [
                    ext.strip().lower()
                    for ext in result.stdout.strip().split("\n")
                    if ext.strip()
                ]
            return []
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list installed extensions: %s", e)
            return []

    @classmethod
    def install_extension(cls, extension_id: str) -> Result:
        """
        Install a single extension.

        Args:
            extension_id: Extension identifier (e.g., "ms-python.python")

        Returns:
            Result object with success status.
        """
        cmd = cls.get_vscode_command()
        if not cmd:
            return Result(False, "VS Code is not installed.")

        try:
            if cmd.startswith("flatpak"):
                result = subprocess.run(
                    cmd.split() + ["--install-extension", extension_id, "--force"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            else:
                result = subprocess.run(
                    [cmd, "--install-extension", extension_id, "--force"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

            if result.returncode == 0:
                return Result(True, f"Extension '{extension_id}' installed.")
            else:
                return Result(False, f"Failed to install: {result.stderr}")

        except subprocess.TimeoutExpired:
            return Result(False, "Installation timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def install_profile(cls, profile: str) -> Result:
        """
        Install all extensions from a profile.

        Args:
            profile: Profile key (python, cpp, rust, web, containers)

        Returns:
            Result with success count.
        """
        if profile not in cls.EXTENSION_PROFILES:
            return Result(False, f"Unknown profile: {profile}")

        extensions = cls.EXTENSION_PROFILES[profile]["extensions"]
        installed = cls.get_installed_extensions()

        success_count = 0
        fail_count = 0

        for ext in extensions:
            if ext.lower() in installed:
                success_count += 1
                continue

            result = cls.install_extension(ext)
            if result.success:
                success_count += 1
            else:
                fail_count += 1

        profile_name = cls.EXTENSION_PROFILES[profile]["name"]
        return Result(
            fail_count == 0,
            f"{profile_name}: {success_count}/{len(extensions)} extensions installed"
            + (f" ({fail_count} failed)" if fail_count else ""),
            {"installed": success_count, "failed": fail_count},
        )

    @classmethod
    def get_settings_path(cls) -> Optional[Path]:
        """
        Get the path to VS Code settings.json.

        Returns:
            Path to settings file, or None if not found.
        """
        home = Path.home()

        # Check different VS Code data directories
        paths = [
            home / ".config" / "Code" / "User" / "settings.json",  # Standard
            home / ".config" / "Code - OSS" / "User" / "settings.json",  # OSS
            home / ".config" / "VSCodium" / "User" / "settings.json",  # VSCodium
            home
            / ".var"
            / "app"
            / "com.visualstudio.code"
            / "config"
            / "Code"
            / "User"
            / "settings.json",  # Flatpak
        ]

        for path in paths:
            if path.parent.exists():
                return path

        return None

    @classmethod
    def backup_settings(cls) -> Optional[Path]:
        """
        Create a backup of current settings.json.

        Returns:
            Path to backup file, or None if no settings exist.
        """
        settings_path = cls.get_settings_path()
        if not settings_path or not settings_path.exists():
            return None

        backup_path = settings_path.with_suffix(".json.bak")
        shutil.copy2(settings_path, backup_path)
        return backup_path

    @classmethod
    def inject_settings(cls, profile: str) -> Result:
        """
        Inject recommended settings for a development profile.

        This merges recommended settings with existing settings,
        without overwriting user customizations.

        Args:
            profile: Development profile (python, cpp, rust, etc.)

        Returns:
            Result with success status.
        """
        settings_path = cls.get_settings_path()
        if not settings_path:
            return Result(False, "Could not find VS Code settings directory.")

        # Profile-specific settings
        profile_settings: Dict[str, Dict[str, Any]] = {
            "python": {
                "python.analysis.typeCheckingMode": "basic",
                "python.formatting.provider": "none",
                "[python]": {
                    "editor.formatOnSave": True,
                    "editor.defaultFormatter": "ms-python.black-formatter",
                },
            },
            "cpp": {
                "C_Cpp.default.cppStandard": "c++20",
                "C_Cpp.default.cStandard": "c17",
                "cmake.configureOnOpen": True,
            },
            "rust": {
                "rust-analyzer.checkOnSave.command": "clippy",
                "[rust]": {
                    "editor.formatOnSave": True,
                    "editor.defaultFormatter": "rust-lang.rust-analyzer",
                },
            },
            "web": {
                "[javascript]": {
                    "editor.formatOnSave": True,
                    "editor.defaultFormatter": "esbenp.prettier-vscode",
                },
                "[typescript]": {
                    "editor.formatOnSave": True,
                    "editor.defaultFormatter": "esbenp.prettier-vscode",
                },
            },
        }

        if profile not in profile_settings:
            return Result(False, f"No settings defined for profile: {profile}")

        try:
            # Backup existing settings
            cls.backup_settings()

            # Load existing settings or create new
            if settings_path.exists():
                with open(settings_path) as f:
                    current_settings = json.load(f)
            else:
                current_settings = {}
                settings_path.parent.mkdir(parents=True, exist_ok=True)

            # Deep merge new settings
            new_settings = profile_settings[profile]
            for key, value in new_settings.items():
                if isinstance(value, dict) and isinstance(
                    current_settings.get(key), dict
                ):
                    current_settings[key].update(value)
                else:
                    current_settings[key] = value

            # Write updated settings
            with open(settings_path, "w") as f:
                json.dump(current_settings, f, indent=4)

            return Result(
                True, f"Settings for {profile} profile injected successfully."
            )

        except json.JSONDecodeError:
            return Result(False, "Could not parse existing settings.json")
        except (OSError, json.JSONDecodeError) as e:
            return Result(False, f"Error updating settings: {e}")

    @classmethod
    def get_available_profiles(cls) -> list[dict]:
        """
        Get list of available extension profiles.

        Returns:
            List of profile info dicts.
        """
        return [
            {
                "key": key,
                "name": info["name"],
                "description": info["description"],
                "extension_count": len(info["extensions"]),
            }
            for key, info in cls.EXTENSION_PROFILES.items()
        ]
