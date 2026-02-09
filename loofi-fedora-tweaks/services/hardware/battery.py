"""
Battery Manager - Battery charge limit control via systemd service.
Part of hardware services layer (v23.0 Architecture Hardening).
"""

import os
from typing import Optional, Tuple

class BatteryManager:
    SCRIPT_PATH = "/usr/local/bin/loofi-battery-limit.sh"
    SERVICE_PATH = "/etc/systemd/system/loofi-battery.service"
    CONFIG_PATH = "/etc/loofi-fedora-tweaks/battery.conf"
    
    def set_limit(self, limit: int) -> Tuple[Optional[str], Optional[list]]:
        """
        Sets the battery charge limit (80 or 100) using a persistent Systemd service.
        """
        # 1. Save config for the UI to read back
        try:
            os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
            with open(self.CONFIG_PATH, "w") as f:
                f.write(str(limit))
        except Exception as e:
            print(f"Failed to save battery config: {e}")

        # 2. Create the Systemd Service content
        # We use a oneshot service that simple echoes the value at boot.
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
            
            # 4. Construct the command to move it and enable it
            # We chain commands: mv temp -> /etc/... && daemon-reload && enable --now
            # Note: We also apply it immediately via the shell command in the chain for instant feedback
            
            cmd = f"mv {tmp_service} {self.SERVICE_PATH} && " \
                  f"systemctl daemon-reload && " \
                  f"systemctl enable --now loofi-battery.service && " \
                  f"to_apply={limit}; echo $to_apply > /sys/class/power_supply/BAT0/charge_control_end_threshold"
            
            return "pkexec", ["sh", "-c", cmd]
            
        except Exception as e:
            print(f"Error preparing battery service: {e}")
            return None, None
