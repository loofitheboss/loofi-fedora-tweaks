"""
ZRAM Manager - Memory compression configuration.
Manages ZRAM (compressed swap in RAM) settings on Fedora.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path


@dataclass
class ZramResult:
    """Result of a ZRAM operation."""
    success: bool
    message: str
    output: str = ""


@dataclass
class ZramConfig:
    """Current ZRAM configuration."""
    enabled: bool
    size_mb: int
    size_percent: int  # Percentage of RAM
    algorithm: str
    total_ram_mb: int


class ZramManager:
    """
    Manages ZRAM (compressed swap on RAM) configuration.
    Fedora uses systemd-zram-generator by default.
    """

    # Config file locations (in order of priority)
    CONFIG_PATHS = [
        Path("/etc/systemd/zram-generator.conf"),
        Path("/usr/lib/systemd/zram-generator.conf"),
    ]

    # Available compression algorithms
    ALGORITHMS = {
        "zstd": "Zstandard (best compression, recommended)",
        "lz4": "LZ4 (fastest, less compression)",
        "lzo": "LZO (balanced, legacy)",
        "lzo-rle": "LZO-RLE (LZO with run-length encoding)",
    }

    @classmethod
    def get_total_ram_mb(cls) -> int:
        """Get total system RAM in MB."""
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb // 1024
        except Exception:
            pass
        return 8192  # Default fallback

    @classmethod
    def get_current_config(cls) -> ZramConfig:
        """
        Get current ZRAM configuration.

        Returns:
            ZramConfig with current settings.
        """
        total_ram = cls.get_total_ram_mb()

        # Check if ZRAM is active
        try:
            result = subprocess.run(
                ["zramctl", "--noheadings", "--raw"],
                capture_output=True, text=True, check=False
            )
            enabled = bool(result.stdout.strip())
        except Exception:
            enabled = False

        # Read config file
        size_percent = 100  # Fedora default
        algorithm = "zstd"  # Fedora default

        for config_path in cls.CONFIG_PATHS:
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("zram-size"):
                                # Parse: zram-size = ram / 2 OR zram-size = 8192
                                value = line.split("=")[1].strip()
                                if "ram" in value.lower():
                                    if "/" in value:
                                        divisor = int(value.split("/")[1].strip())
                                        size_percent = 100 // divisor
                                    else:
                                        size_percent = 100
                                else:
                                    # Absolute value in MB
                                    size_mb = int(value)
                                    size_percent = (size_mb * 100) // total_ram
                            elif line.startswith("compression-algorithm"):
                                algorithm = line.split("=")[1].strip()
                except Exception:
                    pass
                break

        size_mb = (total_ram * size_percent) // 100

        return ZramConfig(
            enabled=enabled,
            size_mb=size_mb,
            size_percent=size_percent,
            algorithm=algorithm,
            total_ram_mb=total_ram
        )

    @classmethod
    def set_config(cls, size_percent: int, algorithm: str) -> ZramResult:
        """
        Set ZRAM configuration.

        Args:
            size_percent: ZRAM size as percentage of RAM (10-200).
            algorithm: Compression algorithm (zstd, lz4, lzo, lzo-rle).

        Returns:
            ZramResult with operation status.
        """
        if not 10 <= size_percent <= 200:
            return ZramResult(False, "Size must be between 10% and 200%")

        if algorithm not in cls.ALGORITHMS:
            return ZramResult(False, f"Invalid algorithm: {algorithm}")

        # Generate config content
        if size_percent == 100:
            size_line = "zram-size = ram"
        elif size_percent == 50:
            size_line = "zram-size = ram / 2"
        elif size_percent == 25:
            size_line = "zram-size = ram / 4"
        else:
            total_ram = cls.get_total_ram_mb()
            size_mb = (total_ram * size_percent) // 100
            size_line = f"zram-size = {size_mb}"

        config_content = f"""# ZRAM configuration managed by Loofi Fedora Tweaks
# See zram-generator.conf(5) for details

[zram0]
{size_line}
compression-algorithm = {algorithm}
"""

        # Write config using pkexec
        config_path = "/etc/systemd/zram-generator.conf"

        try:
            # Write to temp file first
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
                f.write(config_content)
                temp_path = f.name

            # Copy with elevated privileges
            cmd = ["pkexec", "cp", temp_path, config_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            # Clean up temp file
            os.unlink(temp_path)

            if result.returncode == 0:
                return ZramResult(
                    success=True,
                    message=f"ZRAM configured: {size_percent}% RAM, {algorithm}\nReboot to apply changes.",
                    output=config_content
                )
            else:
                return ZramResult(False, f"Failed to write config: {result.stderr}")

        except Exception as e:
            return ZramResult(False, f"Error: {str(e)}")

    @classmethod
    def disable(cls) -> ZramResult:
        """Disable ZRAM by removing the config."""
        try:
            config_path = "/etc/systemd/zram-generator.conf"
            if os.path.exists(config_path):
                cmd = ["pkexec", "rm", config_path]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    return ZramResult(True, "ZRAM disabled. Reboot to apply.")
                else:
                    return ZramResult(False, f"Failed: {result.stderr}")
            return ZramResult(True, "ZRAM already disabled.")
        except Exception as e:
            return ZramResult(False, f"Error: {str(e)}")

    @classmethod
    def get_current_usage(cls) -> Optional[Tuple[int, int]]:
        """
        Get current ZRAM usage.

        Returns:
            Tuple of (used_mb, total_mb) or None if not available.
        """
        try:
            result = subprocess.run(
                ["zramctl", "--noheadings", "--bytes", "-o", "DATA,DISKSIZE"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().split("\n")[0]
                parts = line.split()
                if len(parts) >= 2:
                    used = int(parts[0]) // (1024 * 1024)
                    total = int(parts[1]) // (1024 * 1024)
                    return (used, total)
        except Exception:
            pass
        return None
