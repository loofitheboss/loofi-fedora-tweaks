"""
Hardware profile detection and configuration.
Part of v11.0 "Aurora Update".

Auto-detects laptop/desktop model via DMI data and returns
hardware-specific capabilities (battery control, fan control, etc.).
Expands beyond HP Elitebook to support ThinkPad, Dell XPS, Framework, etc.
"""

import os
import re

# Known hardware profiles with their capabilities
PROFILES = {
    "hp-elitebook": {
        "label": "HP EliteBook",
        "battery_limit": True,
        "nbfc": True,
        "fingerprint": True,
        "power_profiles": True,
        "thermal_management": "hp-wmi",
    },
    "hp-probook": {
        "label": "HP ProBook",
        "battery_limit": True,
        "nbfc": True,
        "fingerprint": True,
        "power_profiles": True,
        "thermal_management": "hp-wmi",
    },
    "thinkpad": {
        "label": "Lenovo ThinkPad",
        "battery_limit": True,
        "nbfc": True,
        "fingerprint": True,
        "power_profiles": True,
        "thermal_management": "thinkpad_acpi",
        "battery_path": "/sys/class/power_supply/BAT0/charge_control_end_threshold",
    },
    "dell-xps": {
        "label": "Dell XPS",
        "battery_limit": True,
        "nbfc": False,
        "fingerprint": True,
        "power_profiles": True,
        "thermal_management": "dell-smm-hwmon",
    },
    "dell-latitude": {
        "label": "Dell Latitude",
        "battery_limit": True,
        "nbfc": False,
        "fingerprint": True,
        "power_profiles": True,
        "thermal_management": "dell-smm-hwmon",
    },
    "framework": {
        "label": "Framework Laptop",
        "battery_limit": True,
        "nbfc": False,
        "fingerprint": True,
        "power_profiles": True,
        "thermal_management": "ectool",
        "battery_path": "/sys/class/power_supply/BAT1/charge_control_end_threshold",
    },
    "asus-zenbook": {
        "label": "ASUS ZenBook",
        "battery_limit": True,
        "nbfc": True,
        "fingerprint": False,
        "power_profiles": True,
        "thermal_management": "asus-wmi",
    },
    "generic-laptop": {
        "label": "Generic Laptop",
        "battery_limit": False,
        "nbfc": False,
        "fingerprint": False,
        "power_profiles": True,
        "thermal_management": None,
    },
    "generic-desktop": {
        "label": "Desktop",
        "battery_limit": False,
        "nbfc": False,
        "fingerprint": False,
        "power_profiles": True,
        "thermal_management": None,
    },
}

# Detection patterns: regex -> profile key
_DETECTION_PATTERNS = [
    (r"(?i)hp.*elitebook", "hp-elitebook"),
    (r"(?i)hp.*probook", "hp-probook"),
    (r"(?i)thinkpad", "thinkpad"),
    (r"(?i)dell.*xps", "dell-xps"),
    (r"(?i)dell.*latitude", "dell-latitude"),
    (r"(?i)framework", "framework"),
    (r"(?i)asus.*zenbook", "asus-zenbook"),
]


def _read_dmi(field):
    """Read a DMI field from sysfs."""
    path = f"/sys/class/dmi/id/{field}"
    try:
        with open(path) as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError):
        return ""


def detect_hardware_profile():
    """Auto-detect hardware profile from DMI data.

    Returns (profile_key, profile_dict) tuple.
    Falls back to generic-laptop or generic-desktop.
    """
    product_name = _read_dmi("product_name")
    product_family = _read_dmi("product_family")
    sys_vendor = _read_dmi("sys_vendor")

    combined = f"{sys_vendor} {product_name} {product_family}"

    for pattern, profile_key in _DETECTION_PATTERNS:
        if re.search(pattern, combined):
            return profile_key, PROFILES[profile_key]

    # Fallback: check if laptop (has battery) or desktop
    has_battery = os.path.exists("/sys/class/power_supply/BAT0") or os.path.exists("/sys/class/power_supply/BAT1")
    fallback = "generic-laptop" if has_battery else "generic-desktop"
    return fallback, PROFILES[fallback]


def get_profile_label(profile_key):
    """Get human-readable label for a profile."""
    return PROFILES.get(profile_key, {}).get("label", profile_key)


def get_all_profiles():
    """Return all known profiles."""
    return dict(PROFILES)
