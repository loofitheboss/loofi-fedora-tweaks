from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QRadioButton, QButtonGroup, QTextEdit, QHBoxLayout, QComboBox
from utils.command_runner import CommandRunner
import threading
import time

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
        power_group = QGroupBox(self.tr("HP Elitebook Power Profiles"))
        power_layout = QVBoxLayout()
        power_group.setLayout(power_layout)
        
        self.profile_group = QButtonGroup()
        
        self.rb_performance = QRadioButton(self.tr("Performance"))
        self.rb_balanced = QRadioButton(self.tr("Balanced"))
        self.rb_saver = QRadioButton(self.tr("Power Saver"))
        
        self.profile_group.addButton(self.rb_performance)
        self.profile_group.addButton(self.rb_balanced)
        self.profile_group.addButton(self.rb_saver)
        
        power_layout.addWidget(self.rb_performance)
        power_layout.addWidget(self.rb_balanced)
        power_layout.addWidget(self.rb_saver)
        
        btn_set_profile = QPushButton(self.tr("Apply Power Profile"))
        btn_set_profile.clicked.connect(self.apply_power_profile)
        power_layout.addWidget(btn_set_profile)
        
        layout.addWidget(power_group)

        # Audio Group
        audio_group = QGroupBox(self.tr("Audio Optimization"))
        audio_layout = QVBoxLayout()
        audio_group.setLayout(audio_layout)
        
        btn_restart_audio = QPushButton(self.tr("Restart Audio Services (Pipewire)"))
        btn_restart_audio.clicked.connect(lambda: self.run_command("systemctl", ["--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"], self.tr("Restarting Audio Services...")))
        audio_layout.addWidget(btn_restart_audio)
        
        layout.addWidget(audio_group)

        # Battery Charge Limit Group
        battery_group = QGroupBox(self.tr("Battery Charge Limit (HP Elitebook)"))
        battery_layout = QVBoxLayout()
        battery_group.setLayout(battery_layout)
        
        battery_btn_layout = QHBoxLayout()
        
        btn_limit_80 = QPushButton(self.tr("Limit to 80%"))
        # We use a helper script or direct echo via sh -c with pkexec
        # Note: writing to sysfs requires root.
        # Path: /sys/class/power_supply/BAT0/charge_control_end_threshold
        btn_limit_80.clicked.connect(lambda: self.set_battery_limit(80))
        battery_btn_layout.addWidget(btn_limit_80)
        
        btn_limit_100 = QPushButton(self.tr("Limit to 100% (Full)"))
        btn_limit_100.clicked.connect(lambda: self.set_battery_limit(100))
        battery_btn_layout.addWidget(btn_limit_100)
        
        battery_layout.addLayout(battery_btn_layout)
        layout.addWidget(battery_group)

        # HP Fan Control
        fan_group = QGroupBox(self.tr("HP Fan Control (nbfc-linux)"))
        fan_group.setObjectName("HP Fan Control (nbfc-linux)")
        fan_layout = QHBoxLayout()
        fan_group.setLayout(fan_layout)
        
        self.btn_install_nbfc = QPushButton(self.tr("Install NBFC (Fan Control)"))
        self.btn_install_nbfc.clicked.connect(self.install_nbfc)
        fan_layout.addWidget(self.btn_install_nbfc)
        
        layout.addWidget(fan_group)

        # Fingerprint Reader
        finger_group = QGroupBox(self.tr("Fingerprint Reader"))
        finger_layout = QHBoxLayout()
        finger_group.setLayout(finger_layout)
        
        self.btn_enroll_finger = QPushButton(self.tr("Enroll Fingerprint (GUI)"))
        self.btn_enroll_finger.clicked.connect(self.enroll_fingerprint)
        finger_layout.addWidget(self.btn_enroll_finger)
        
        layout.addWidget(finger_group)

        layout.addWidget(QLabel(self.tr("Output Log:")))
        layout.addWidget(self.output_area)
        
        # Check current profile on load (async)
        self.check_current_profile()
        self.check_nbfc_status()

    def install_nbfc(self):
        self.run_command("pkexec", ["sh", "-c", "dnf install -y nbfc-linux && systemctl enable --now nbfc_service"], self.tr("Installing and enabling nbfc-linux..."))

    def check_nbfc_status(self):
        import shutil
        if shutil.which("nbfc"):
            self.btn_install_nbfc.setText(self.tr("NBFC Installed"))
            self.btn_install_nbfc.setEnabled(False)
            
            # Fan Profile Dropdown
            self.lbl_fan_profile = QLabel(self.tr("Fan Profile:"))
            self.combo_fan_profile = QComboBox()
            self.combo_fan_profile.addItems([self.tr("Quiet"), self.tr("Balanced"), self.tr("Performance"), self.tr("Cool")])
            self.combo_fan_profile.setCurrentIndex(1) # Balanced default
            
            self.btn_apply_fan = QPushButton(self.tr("Apply Fan Profile"))
            self.btn_apply_fan.clicked.connect(self.apply_fan_profile)
            
            # Add to layout dynamically if not already there
            # (Ideally this should be in __init__ but hidden, but for now we append)
            # Find the fan layout
            fan_group = self.findChild(QGroupBox, "HP Fan Control (nbfc-linux)")
            if fan_group:
                 layout = fan_group.layout()
                 layout.addWidget(self.lbl_fan_profile)
                 layout.addWidget(self.combo_fan_profile)
                 layout.addWidget(self.btn_apply_fan)

    def apply_fan_profile(self):
        profile = self.combo_fan_profile.currentText().lower()
        # nbfc config -a <profile>
        self.run_command("nbfc", ["config", "-a", profile], self.tr("Setting NBFC Fan Profile to {}...").format(profile))

    def enroll_fingerprint(self):
        from ui.fingerprint_dialog import FingerprintDialog
        dialog = FingerprintDialog(self)
        dialog.exec()

    def set_battery_limit(self, limit):
        from utils.battery import BatteryManager
        manager = BatteryManager()
        cmd, args = manager.set_limit(limit)
        
        if cmd:
            self.run_command(cmd, args, self.tr("Setting Battery Limit to {}% (Persistent)...").format(limit))
        else:
            self.append_output(self.tr("Failed to prepare battery script.\n"))


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
        
        self.run_command("powerprofilesctl", ["set", profile], self.tr("Setting power profile to {}...").format(profile))

    def run_command(self, cmd, args, description):
        self.output_area.clear()
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

    def append_output(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def command_finished(self, exit_code):
        self.append_output(self.tr("\nCommand finished with exit code: {}").format(exit_code))

