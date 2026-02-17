"""
USB Guard Manager - USB device security.
Part of v8.5 "Sentinel" update.

Provides integration with usbguard to protect against
BadUSB attacks by controlling USB device access.
"""

import logging
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional

from utils.commands import PrivilegedCommand

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Operation result."""

    success: bool
    message: str
    data: Optional[dict] = None


@dataclass
class USBDevice:
    """Represents a USB device."""

    id: str
    name: str
    hash: str
    policy: str  # allow, block, reject
    serial: str = ""


class USBGuardManager:
    """
    Manages USB device access via usbguard.

    Features:
    - Block new USB devices when screen is locked
    - Whitelist trusted devices
    - Monitor USB events
    """

    @classmethod
    def is_installed(cls) -> bool:
        """Check if USBGuard is installed."""
        return shutil.which("usbguard") is not None

    @classmethod
    def is_running(cls) -> bool:
        """Check if USBGuard daemon is running."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "usbguard"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check USBGuard service status: %s", e)
            return False

    @classmethod
    def install(cls) -> Result:
        """Install USBGuard via DNF."""
        if cls.is_installed():
            return Result(True, "USBGuard is already installed")

        try:
            binary, args, desc = PrivilegedCommand.dnf(
                "install", "usbguard", "usbguard-tools"
            )
            result = subprocess.run(
                [binary] + args, capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                return Result(True, "USBGuard installed successfully")
            else:
                return Result(False, f"Installation failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Installation error: {e}")

    @classmethod
    def start_service(cls) -> Result:
        """Start USBGuard daemon."""
        if not cls.is_installed():
            return Result(False, "USBGuard is not installed")

        try:
            result = subprocess.run(
                ["pkexec", "systemctl", "enable", "--now", "usbguard"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return Result(True, "USBGuard service started")
            else:
                return Result(False, f"Failed to start: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def list_devices(cls) -> list[USBDevice]:
        """List all USB devices and their policies."""
        if not cls.is_installed():
            return []

        devices = []

        try:
            result = subprocess.run(
                ["usbguard", "list-devices"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return []

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                # Parse: ID: [POLICY] Name via Port ...
                parts = line.split(": ", 1)
                if len(parts) < 2:
                    continue

                device_id = parts[0].strip()
                rest = parts[1]

                # Extract policy
                policy = "unknown"
                if rest.startswith("allow"):
                    policy = "allow"
                elif rest.startswith("block"):
                    policy = "block"
                elif rest.startswith("reject"):
                    policy = "reject"

                # Extract name (simplified parsing)
                name = (
                    rest.split("name ")[1].split(" ")[0]
                    if "name " in rest
                    else "Unknown"
                )

                # Extract hash
                device_hash = ""
                if "hash " in rest:
                    device_hash = rest.split("hash ")[1].split(" ")[0]

                devices.append(
                    USBDevice(
                        id=device_id,
                        name=name.strip('"'),
                        hash=device_hash,
                        policy=policy,
                    )
                )

            return devices

        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list USB devices: %s", e)
            return []

    @classmethod
    def allow_device(cls, device_id: str, permanent: bool = False) -> Result:
        """Allow a USB device."""
        if not cls.is_installed():
            return Result(False, "USBGuard is not installed")

        try:
            cmd = ["usbguard", "allow-device", device_id]
            if permanent:
                cmd.append("-p")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return Result(True, f"Device {device_id} allowed")
            else:
                return Result(False, f"Failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def block_device(cls, device_id: str, permanent: bool = False) -> Result:
        """Block a USB device."""
        if not cls.is_installed():
            return Result(False, "USBGuard is not installed")

        try:
            cmd = ["usbguard", "block-device", device_id]
            if permanent:
                cmd.append("-p")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return Result(True, f"Device {device_id} blocked")
            else:
                return Result(False, f"Failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def set_default_policy(cls, policy: str) -> Result:
        """
        Set default policy for new devices.

        Args:
            policy: "allow", "block", or "reject"
        """
        if policy not in ["allow", "block", "reject"]:
            return Result(False, "Invalid policy. Use: allow, block, reject")

        config_path = "/etc/usbguard/usbguard-daemon.conf"

        # This requires root, provide instructions
        return Result(
            False,
            f"To change default policy to '{policy}', edit {config_path}:\n"
            f"  ImplicitPolicyTarget={policy}\n"
            "Then restart usbguard: pkexec systemctl restart usbguard",
        )

    @classmethod
    def get_lock_screen_rule(cls) -> str:
        """
        Generate a rule script to block USB on screen lock.

        This integrates with GNOME/KDE screen lock signals.
        """
        script = """#!/bin/bash
# Block new USB devices when screen is locked
# Place in /etc/usbguard/on-lock.sh

# For GNOME
dbus-monitor --session "interface='org.gnome.ScreenSaver'" 2>/dev/null | while read line; do
    if echo "$line" | grep -q "boolean true"; then
        # Screen locked - block USB
        usbguard set-parameter ImplicitPolicyTarget block 2>/dev/null
    elif echo "$line" | grep -q "boolean false"; then
        # Screen unlocked - allow USB
        usbguard set-parameter ImplicitPolicyTarget allow 2>/dev/null
    fi
done
"""
        return script

    @classmethod
    def generate_initial_policy(cls) -> Result:
        """
        Generate initial USBGuard policy from currently connected devices.
        This whitelists all currently connected devices.
        """
        if not cls.is_installed():
            return Result(False, "USBGuard is not installed")

        try:
            result = subprocess.run(
                ["pkexec", "usbguard", "generate-policy"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return Result(
                    True,
                    "Policy generated. Save to /etc/usbguard/rules.conf",
                    {"policy": result.stdout},
                )
            else:
                return Result(False, f"Failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")
