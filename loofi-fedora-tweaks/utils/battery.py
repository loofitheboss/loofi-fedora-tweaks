import os
from utils.process import CommandRunner

class BatteryManager:
    SCRIPT_PATH = "/usr/local/bin/loofi-battery-limit.sh"
    SERVICE_PATH = "/etc/systemd/system/loofi-battery.service"
    CONFIG_PATH = "/etc/loofi-fedora-tweaks/battery.conf"
    
    def __init__(self):
        self.runner = CommandRunner()

    def set_limit(self, limit):
        """
        Sets the battery charge limit (80 or 100).
        Creates a persistent script and systemd service.
        """
        script_content = f"""#!/bin/bash
# Apply immediate limit
echo {limit} | tee /sys/class/power_supply/BAT0/charge_control_end_threshold

# Save config
mkdir -p /etc/loofi-fedora-tweaks
echo {limit} > {self.CONFIG_PATH}

# Create wrapper script for boot
cat <<EOF > {self.SCRIPT_PATH}
#!/bin/bash
if [ -f {self.CONFIG_PATH} ]; then
    cat {self.CONFIG_PATH} > /sys/class/power_supply/BAT0/charge_control_end_threshold
fi
EOF
chmod +x {self.SCRIPT_PATH}

# Create Systemd Service
cat <<EOF > {self.SERVICE_PATH}
[Unit]
Description=Restore Loofi Battery Limit
After=multi-user.target

[Service]
Type=oneshot
ExecStart={self.SCRIPT_PATH}

[Install]
WantedBy=multi-user.target
EOF

# Reload and Enable
systemctl daemon-reload
systemctl enable loofi-battery.service
"""
        # Write to temp file
        tmp_script = "/tmp/loofi_battery_setup.sh"
        try:
            with open(tmp_script, "w") as f:
                f.write(script_content)
            os.chmod(tmp_script, 0o755)
            
            # Execute with pkexec
            # We assume the caller handles the async execution or we run it and return the command details
            # Here we return the command args so the UI can run it via its CommandRunner to show output
            return "pkexec", [tmp_script]
        except Exception as e:
            print(f"Error preparing battery script: {e}")
            return None, None
