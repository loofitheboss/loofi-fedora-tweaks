"""
Battery Manager - Battery charge limit control via systemd service.
Part of hardware services layer (v23.0 Architecture Hardening).
"""

import logging
import os
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class BatteryManager:
    SCRIPT_PATH = "/usr/local/bin/loofi-battery-limit.sh"
    SERVICE_PATH = "/etc/systemd/system/loofi-battery.service"
    CONFIG_PATH = "/etc/loofi-fedora-tweaks/battery.conf"

    def set_limit(self, limit: int) -> Tuple[Optional[str], Optional[list]]:
        """
        Sets the battery charge limit (80 or 100) using a persistent Systemd service.

        Returns:
            Tuple of (cmd, args) for the caller, or (None, None) on error.
            The command is now a multi-step operation run internally;
            returns ("echo", ["Battery limit set"]) on success.
        """
        # 1. Save config for the UI to read back
        try:
            os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
            with open(self.CONFIG_PATH, "w") as f:
                f.write(str(limit))
        except Exception as e:
            logger.debug("Failed to save battery config: %s", e)

        # 2. Create the Systemd Service content
        service_content = f"""[Unit]
Description=Restore HP Battery Charge Limit ({limit}%)
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo {limit} > /sys/class/power_supply/BAT0/charge_control_end_threshold'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""

        # 3. Write to a temporary file to prepare for pkexec move
        tmp_service = "/tmp/loofi-battery.service"
        try:
            with open(tmp_service, "w") as f:
                f.write(service_content)

            # 4. Move service file to systemd directory
            result = subprocess.run(
                ["pkexec", "mv", tmp_service, self.SERVICE_PATH],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                logger.debug("Failed to move service file: %s", result.stderr)
                return None, None

            # 5. Reload systemd daemon
            result = subprocess.run(
                ["pkexec", "systemctl", "daemon-reload"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                logger.debug("daemon-reload failed: %s", result.stderr)
                return None, None

            # 6. Enable and start the service
            result = subprocess.run(
                ["pkexec", "systemctl", "enable", "--now", "loofi-battery.service"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                logger.debug("Service enable failed: %s", result.stderr)
                return None, None

            # 7. Apply immediately by writing to sysfs
            result = subprocess.run(
                [
                    "pkexec",
                    "tee",
                    "/sys/class/power_supply/BAT0/charge_control_end_threshold",
                ],
                input=str(limit),
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                logger.debug("sysfs write failed: %s", result.stderr)
                # Service is installed but immediate apply failed
                return "echo", [
                    f"Battery limit service installed, reboot to apply {limit}%"
                ]

            return "echo", [f"Battery limit set to {limit}%"]

        except Exception as e:
            logger.debug("Error preparing battery service: %s", e)
            return None, None
