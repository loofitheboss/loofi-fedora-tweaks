"""
Boot Configuration Manager — GRUB2 configuration management.
Part of v37.0.0 "Pinnacle".

Provides GRUB timeout, default kernel, and theme management
for Fedora Workstation systems.
"""

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from utils.commands import CommandTuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GrubConfig:
    """Parsed GRUB2 configuration."""
    timeout: int = 5
    default_entry: str = "0"
    theme: str = ""
    cmdline_linux: str = ""
    cmdline_linux_default: str = ""
    raw: Dict[str, str] = field(default_factory=dict)


@dataclass
class KernelEntry:
    """Represents an installed kernel."""
    index: int = 0
    title: str = ""
    kernel: str = ""
    initrd: str = ""
    root: str = ""
    args: str = ""
    default: bool = False


# ---------------------------------------------------------------------------
# BootConfigManager
# ---------------------------------------------------------------------------

class BootConfigManager:
    """GRUB2 boot configuration management.

    All public methods are ``@staticmethod`` so the class can be used without
    instantiation, consistent with other ``utils/*`` managers.
    """

    GRUB_DEFAULT = "/etc/default/grub"
    GRUB_CFG_PATHS = [
        "/boot/grub2/grub.cfg",
        "/boot/efi/EFI/fedora/grub.cfg",
    ]
    THEME_DIR = "/boot/grub2/themes"

    # -----------------------------------------------------------------
    # Configuration parsing
    # -----------------------------------------------------------------

    @staticmethod
    def get_grub_config() -> GrubConfig:
        """Parse the current GRUB2 configuration.

        Reads ``/etc/default/grub`` and extracts key settings.

        Returns:
            GrubConfig with current settings.
        """
        config = GrubConfig()

        try:
            grub_path = BootConfigManager.GRUB_DEFAULT
            if not os.path.exists(grub_path):
                logger.warning("GRUB config not found at %s", grub_path)
                return config

            with open(grub_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        config.raw[key] = value

                        if key == "GRUB_TIMEOUT":
                            try:
                                config.timeout = int(value)
                            except ValueError:
                                pass
                        elif key == "GRUB_DEFAULT":
                            config.default_entry = value
                        elif key == "GRUB_THEME":
                            config.theme = value
                        elif key == "GRUB_CMDLINE_LINUX":
                            config.cmdline_linux = value
                        elif key == "GRUB_CMDLINE_LINUX_DEFAULT":
                            config.cmdline_linux_default = value

        except OSError as e:
            logger.error("Failed to read GRUB config: %s", e)
        return config

    # -----------------------------------------------------------------
    # Kernel listing
    # -----------------------------------------------------------------

    @staticmethod
    def list_kernels() -> List[KernelEntry]:
        """List installed kernels via grubby.

        Returns:
            List of KernelEntry for each installed kernel.
        """
        kernels: List[KernelEntry] = []

        if not shutil.which("grubby"):
            logger.warning("grubby not found; cannot list kernels")
            return kernels

        try:
            result = subprocess.run(
                ["grubby", "--info=ALL"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                current: dict = {}
                index = 0
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        if current:
                            kernels.append(KernelEntry(
                                index=current.get("index", index),
                                title=current.get("title", ""),
                                kernel=current.get("kernel", ""),
                                initrd=current.get("initrd", ""),
                                root=current.get("root", ""),
                                args=current.get("args", ""),
                            ))
                            index += 1
                        current = {}
                        continue

                    if "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip().lower()
                        val = val.strip().strip('"')
                        current[key] = val

                # Don't forget last entry
                if current:
                    kernels.append(KernelEntry(
                        index=current.get("index", index),
                        title=current.get("title", ""),
                        kernel=current.get("kernel", ""),
                        initrd=current.get("initrd", ""),
                        root=current.get("root", ""),
                        args=current.get("args", ""),
                    ))

            # Mark the default kernel
            default_result = subprocess.run(
                ["grubby", "--default-kernel"],
                capture_output=True, text=True, timeout=10,
            )
            if default_result.returncode == 0:
                default_kernel = default_result.stdout.strip()
                for k in kernels:
                    if k.kernel == default_kernel:
                        k.default = True
                        break

        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to list kernels: %s", e)
        return kernels

    # -----------------------------------------------------------------
    # Theme listing
    # -----------------------------------------------------------------

    @staticmethod
    def list_themes() -> List[str]:
        """List available GRUB2 themes.

        Scans ``/boot/grub2/themes/`` for theme directories containing
        a ``theme.txt`` file.

        Returns:
            List of theme directory names.
        """
        themes: List[str] = []
        theme_dir = Path(BootConfigManager.THEME_DIR)

        if not theme_dir.exists():
            return themes

        try:
            for entry in theme_dir.iterdir():
                if entry.is_dir() and (entry / "theme.txt").exists():
                    themes.append(entry.name)
        except OSError as e:
            logger.error("Failed to list GRUB themes: %s", e)
        return themes

    # -----------------------------------------------------------------
    # Settings modification (returns CommandTuples)
    # -----------------------------------------------------------------

    @staticmethod
    def set_timeout(seconds: int) -> CommandTuple:
        """Build command to set GRUB timeout.

        Args:
            seconds: Timeout value (0 = no delay, -1 = wait forever).

        Returns:
            CommandTuple to apply the change.
        """
        return BootConfigManager._build_grub_set_command(
            "GRUB_TIMEOUT", str(seconds),
            f"Setting GRUB timeout to {seconds}s...",
        )

    @staticmethod
    def set_default_kernel(entry: str) -> CommandTuple:
        """Build command to set the default kernel.

        Args:
            entry: Kernel index, title, or path.

        Returns:
            CommandTuple to apply the change.
        """
        if shutil.which("grubby"):
            return ("pkexec", ["grubby", "--set-default", entry],
                    f"Setting default kernel to {entry}...")
        return BootConfigManager._build_grub_set_command(
            "GRUB_DEFAULT", entry,
            f"Setting default boot entry to {entry}...",
        )

    @staticmethod
    def set_theme(theme_path: str) -> CommandTuple:
        """Build command to set the GRUB theme.

        Args:
            theme_path: Full path to theme.txt or theme directory name.

        Returns:
            CommandTuple to apply the change.
        """
        # If just a name, construct full path
        if "/" not in theme_path:
            theme_path = f"{BootConfigManager.THEME_DIR}/{theme_path}/theme.txt"

        return BootConfigManager._build_grub_set_command(
            "GRUB_THEME", theme_path,
            f"Setting GRUB theme to {theme_path}...",
        )

    @staticmethod
    def _build_grub_set_command(key: str, value: str, description: str) -> CommandTuple:
        """Build a sed command to modify a GRUB default variable.

        Args:
            key: GRUB variable name.
            value: New value.
            description: Human-readable description.

        Returns:
            CommandTuple using pkexec + sed.
        """
        # Use sed to replace or append the key
        # Pattern: replace existing line or append if not found
        sed_expr = f's/^{key}=.*/{key}="{value}"/'
        return ("pkexec", [
            "sed", "-i", sed_expr, BootConfigManager.GRUB_DEFAULT,
        ], description)

    # -----------------------------------------------------------------
    # Apply changes (regenerate grub.cfg)
    # -----------------------------------------------------------------

    @staticmethod
    def apply_grub_changes() -> CommandTuple:
        """Build command to regenerate the GRUB configuration.

        Runs ``grub2-mkconfig`` to apply changes from ``/etc/default/grub``.

        Returns:
            CommandTuple for the regeneration.
        """
        # Determine the correct grub.cfg path
        grub_cfg = "/boot/grub2/grub.cfg"
        for path in BootConfigManager.GRUB_CFG_PATHS:
            if os.path.exists(path):
                grub_cfg = path
                break

        return ("pkexec", [
            "grub2-mkconfig", "-o", grub_cfg,
        ], f"Regenerating GRUB configuration ({grub_cfg})...")

    # -----------------------------------------------------------------
    # Kernel cmdline helpers
    # -----------------------------------------------------------------

    @staticmethod
    def get_current_cmdline() -> str:
        """Read the current kernel command line.

        Returns:
            Contents of /proc/cmdline.
        """
        try:
            with open("/proc/cmdline", "r") as f:
                return f.read().strip()
        except OSError:
            return ""

    @staticmethod
    def set_cmdline_param(key: str, value: str = "") -> CommandTuple:
        """Build command to add/modify a kernel command line parameter.

        Modifies GRUB_CMDLINE_LINUX in /etc/default/grub.

        Args:
            key: Parameter name.
            value: Parameter value (empty for flag-only params).

        Returns:
            CommandTuple to apply the change.
        """
        param = f"{key}={value}" if value else key
        config = BootConfigManager.get_grub_config()

        # Check if param already exists and replace it, or append
        current = config.cmdline_linux
        # Remove existing instance of this key
        existing_pattern = re.compile(rf'\b{re.escape(key)}(=\S+)?\b')
        new_cmdline = existing_pattern.sub("", current).strip()
        new_cmdline = f"{new_cmdline} {param}".strip()

        return BootConfigManager._build_grub_set_command(
            "GRUB_CMDLINE_LINUX", new_cmdline,
            f"Setting kernel parameter {param}...",
        )
