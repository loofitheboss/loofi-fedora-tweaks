"""
System information query utilities.

Extracted from ui/system_info_tab.py (v34.0.0 Citadel) to keep
subprocess calls out of the UI layer.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional

from utils.log import get_logger

logger = get_logger(__name__)


def get_hostname() -> str:
    """Return the system hostname."""
    try:
        return subprocess.getoutput("hostname").strip()
    except Exception:
        logger.debug("Failed to get hostname", exc_info=True)
        return "Unknown"


def get_kernel_version() -> str:
    """Return the running kernel version."""
    try:
        return subprocess.getoutput("uname -r").strip()
    except Exception:
        logger.debug("Failed to get kernel version", exc_info=True)
        return "Unknown"


def get_fedora_release() -> str:
    """Return the Fedora release string."""
    try:
        return subprocess.getoutput("cat /etc/fedora-release").strip()
    except Exception:
        logger.debug("Failed to get Fedora release", exc_info=True)
        return "Unknown"


def get_cpu_model() -> str:
    """Return the CPU model name from lscpu."""
    try:
        info = subprocess.getoutput(
            "lscpu | grep 'Model name' | cut -d: -f2"
        ).strip()
        return info if info else "Unknown"
    except Exception:
        logger.debug("Failed to get CPU model", exc_info=True)
        return "Unknown"


def get_ram_usage() -> str:
    """Return human-readable RAM total and used."""
    try:
        return subprocess.getoutput(
            "free -h | awk '/^Mem:/ {print $2 \" total, \" $3 \" used\"}'"
        ).strip()
    except Exception:
        logger.debug("Failed to get RAM usage", exc_info=True)
        return "Unknown"


def get_disk_usage() -> str:
    """Return root partition usage summary."""
    try:
        return subprocess.getoutput(
            'df -h / | awk \'NR==2 {print $3 "/" $2 " (" $5 " used)"}\''
        ).strip()
    except Exception:
        logger.debug("Failed to get disk usage", exc_info=True)
        return "Unknown"


def get_uptime() -> str:
    """Return human-readable uptime."""
    try:
        return subprocess.getoutput("uptime -p").strip()
    except Exception:
        logger.debug("Failed to get uptime", exc_info=True)
        return "Unknown"


def get_battery_status() -> Optional[str]:
    """Return battery percentage and status, or None if no battery."""
    bat_path = "/sys/class/power_supply/BAT0/capacity"
    if not os.path.exists(bat_path):
        return None
    try:
        capacity = subprocess.getoutput(
            "cat /sys/class/power_supply/BAT0/capacity"
        ).strip()
        status = subprocess.getoutput(
            "cat /sys/class/power_supply/BAT0/status"
        ).strip()
        return f"{capacity}% ({status})"
    except Exception:
        logger.debug("Failed to get battery status", exc_info=True)
        return None
