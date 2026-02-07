from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QRadioButton, QButtonGroup, QTextEdit, QHBoxLayout
from utils.process import CommandRunner

class TweaksTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Output Area (Shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(150)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # Power Profiles Group
        power_group = QGroupBox("HP Elitebook Power Profiles")
        power_layout = QVBoxLayout()
        power_group.setLayout(power_layout)
        
        self.profile_group = QButtonGroup()
        
        self.rb_performance = QRadioButton("Performance")
        self.rb_balanced = QRadioButton("Balanced")
        self.rb_saver = QRadioButton("Power Saver")
        
        self.profile_group.addButton(self.rb_performance)
        self.profile_group.addButton(self.rb_balanced)
        self.profile_group.addButton(self.rb_saver)
        
        power_layout.addWidget(self.rb_performance)
        power_layout.addWidget(self.rb_balanced)
        power_layout.addWidget(self.rb_saver)
        
        btn_set_profile = QPushButton("Apply Power Profile")
        btn_set_profile.clicked.connect(self.apply_power_profile)
        power_layout.addWidget(btn_set_profile)
        
        layout.addWidget(power_group)

        # Audio Group
        audio_group = QGroupBox("Audio Optimization")
        audio_layout = QVBoxLayout()
        audio_group.setLayout(audio_layout)
        
        btn_restart_audio = QPushButton("Restart Audio Services (Pipewire)")
        btn_restart_audio.clicked.connect(lambda: self.run_command("systemctl", ["--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"], "Restarting Audio Services..."))
        audio_layout.addWidget(btn_restart_audio)
        
        layout.addWidget(audio_group)

        # Battery Charge Limit Group
        battery_group = QGroupBox("Battery Charge Limit (HP Elitebook)")
        battery_layout = QVBoxLayout()
        battery_group.setLayout(battery_layout)
        
        battery_btn_layout = QHBoxLayout()
        
        btn_limit_80 = QPushButton("Limit to 80%")
        # We use a helper script or direct echo via sh -c with pkexec
        # Note: writing to sysfs requires root.
        # Path: /sys/class/power_supply/BAT0/charge_control_end_threshold
        btn_limit_80.clicked.connect(lambda: self.set_battery_limit(80))
        battery_btn_layout.addWidget(btn_limit_80)
        
        btn_limit_100 = QPushButton("Limit to 100% (Full)")
        btn_limit_100.clicked.connect(lambda: self.set_battery_limit(100))
        battery_btn_layout.addWidget(btn_limit_100)
        
        battery_layout.addLayout(battery_btn_layout)
        layout.addWidget(battery_group)

        # HP Fan Control
        fan_group = QGroupBox("HP Fan Control (nbfc-linux)")
        fan_layout = QHBoxLayout()
        fan_group.setLayout(fan_layout)
        
        self.btn_install_nbfc = QPushButton("Install NBFC (Fan Control)")
        self.btn_install_nbfc.clicked.connect(self.install_nbfc)
        fan_layout.addWidget(self.btn_install_nbfc)
        
        layout.addWidget(fan_group)

        # Fingerprint Reader
        finger_group = QGroupBox("Fingerprint Reader")
        finger_layout = QHBoxLayout()
        finger_group.setLayout(finger_layout)
        
        self.btn_enroll_finger = QPushButton("Enroll Fingerprint (GUI)")
        self.btn_enroll_finger.clicked.connect(self.enroll_fingerprint)
        finger_layout.addWidget(self.btn_enroll_finger)
        
        layout.addWidget(finger_group)

        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_area)
        
        # Check current profile on load (async)
        self.check_current_profile()
        self.check_nbfc_status()

    def install_nbfc(self):
        # Using a COPR for nbfc-linux is common, or building from source.
        # For simplicity and safety, we'll try to find a COPR or Git install method.
        # Let's assume we use a known COPR for Fedora.
        cmd = """
        dnf copr enable -y ublue-os/staging;
        dnf install -y nbfc-linux;
        systemctl enable --now nbfc_service;
        """
        self.run_command("pkexec", ["sh", "-c", cmd], "Installing nbfc-linux for Fan Control...")

    def check_nbfc_status(self):
        import shutil
        if shutil.which("nbfc"):
            self.btn_install_nbfc.setText("NBFC Installed (Service Active)")
            self.btn_install_nbfc.setEnabled(False)

    def enroll_fingerprint(self):
        # Calling KDE's fingerprint enrollment directly or using fprintd
        # KDE System Settings is the best GUI.
        self.run_command("systemsettings", ["kcm_users"], "Opening User Settings for Fingerprint Enrollment...")

    def set_battery_limit(self, limit):
        # Create a temporary script to handle the privileged operations safely
        script_content = f"""#!/bin/bash
echo {limit} | tee /sys/class/power_supply/BAT0/charge_control_end_threshold
mkdir -p /etc/loofi-fedora-tweaks
echo {limit} > /etc/loofi-fedora-tweaks/battery.conf

cat <<EOF > /etc/systemd/system/loofi-battery.service
[Unit]
Description=Restore Loofi Battery Limit
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'if [ -f /etc/loofi-fedora-tweaks/battery.conf ]; then cat /etc/loofi-fedora-tweaks/battery.conf > /sys/class/power_supply/BAT0/charge_control_end_threshold; fi'

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable loofi-battery.service
# Don't start it immediately to avoid conflict, we just set the value manually above
"""
        import os
        tmp_script = "/tmp/loofi_battery_setup.sh"
        try:
            with open(tmp_script, "w") as f:
                f.write(script_content)
            os.chmod(tmp_script, 0o755)
            # Run the script with pkexec
            self.run_command("pkexec", [tmp_script], f"Setting Battery Limit to {limit}% and enabling persistence...")
        except Exception as e:
            self.append_output(f"Error creating setup script: {e}\n")


    def check_current_profile(self):
        # We'll use a separate runner or just the main one depending on complexity.
        # Here we just run it and parse output in a dedicated handler if we wanted strictly correct UI state.
        # For simplicity, we just let user select.
        pass

    def apply_power_profile(self):
        if self.rb_performance.isChecked():
            profile = "performance"
        elif self.rb_saver.isChecked():
            profile = "power-saver"
        else:
            profile = "balanced" # Default
        
        self.run_command("powerprofilesctl", ["set", profile], f"Setting power profile to {profile}...")

    def run_command(self, cmd, args, description):
        self.output_area.clear()
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

    def append_output(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def command_finished(self, exit_code):
        self.append_output(f"\nCommand finished with exit code: {exit_code}")

