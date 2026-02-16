"""
System information query utilities.

Extracted from ui/system_info_tab.py (v34.0.0 Citadel) to keep
subprocess calls out of the UI layer.

v42.0.0 Sentinel: Replaced subprocess.getoutput() with safe alternatives.
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess
from typing import Optional

from utils.log import get_logger

logger = get_logger(__name__)


def get_hostname() -> str:
    """Return the system hostname."""
    try:
        return socket.gethostname()
    except OSError as e:
        logger.debug("Failed to get hostname: %s", e)
        return "Unknown"


def get_kernel_version() -> str:
    """Return the running kernel version."""
    return platform.release() or "Unknown"


def get_fedora_release() -> str:
    """Return the Fedora release string."""
    try:
        with open("/etc/fedora-release", "r", encoding="utf-8") as f:
            return f.read().strip()
    except (OSError, IOError) as e:
        logger.debug("Failed to get Fedora release: %s", e)
        return "Unknown"


def get_cpu_model() -> str:
    """Return the CPU model name from lscpu."""
    try:
        result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Model name" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
        return "Unknown"
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("Failed to get CPU model: %s", e)
        return "Unknown"


def get_ram_usage() -> str:
    """Return human-readable RAM total and used."""
    try:
        result = subprocess.run(
            ["free", "-h"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("Mem:"):
                    fields = line.split()
                    if len(fields) >= 3:
                        return f"{fields[1]} total, {fields[2]} used"
        return "Unknown"
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("Failed to get RAM usage: %s", e)
        return "Unknown"


def get_disk_usage() -> str:
    """Return root partition usage summary."""
    try:
        result = subprocess.run(
            ["df", "-h", "/"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            if len(lines) >= 2:
                fields = lines[1].split()
                if len(fields) >= 5:
                    return f"{fields[2]}/{fields[1]} ({fields[4]} used)"
        return "Unknown"
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("Failed to get disk usage: %s", e)
        return "Unknown"


def get_uptime() -> str:
    """Return human-readable uptime."""
    try:
        result = subprocess.run(
            ["uptime", "-p"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return "Unknown"
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("Failed to get uptime: %s", e)
        return "Unknown"


def get_battery_status() -> Optional[str]:
    """Return battery percentage and status, or None if no battery."""
    bat_cap_path = "/sys/class/power_supply/BAT0/capacity"
    bat_status_path = "/sys/class/power_supply/BAT0/status"
    if not os.path.exists(bat_cap_path):
        return None
    try:
        with open(bat_cap_path, "r", encoding="utf-8") as f:
            capacity = f.read().strip()
        with open(bat_status_path, "r", encoding="utf-8") as f:
            status = f.read().strip()
        return f"{capacity}% ({status})"
    except (OSError, IOError) as e:
        logger.debug("Failed to get battery status: %s", e)
        return None
