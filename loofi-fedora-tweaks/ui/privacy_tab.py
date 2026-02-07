from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QHBoxLayout, QTextEdit
from utils.process import CommandRunner

class PrivacyTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # Firewall Group
        fw_group = QGroupBox("Firewall (firewalld)")
        fw_layout = QHBoxLayout()
        fw_group.setLayout(fw_layout)
        
        btn_fw_status = QPushButton("Check Status")
        btn_fw_status.clicked.connect(lambda: self.run_command("systemctl", ["status", "firewalld"], "Checking Firewall Status..."))
        fw_layout.addWidget(btn_fw_status)
        
        btn_fw_enable = QPushButton("Enable Firewall")
        btn_fw_enable.clicked.connect(lambda: self.run_command("pkexec", ["systemctl", "enable", "--now", "firewalld"], "Enabling Firewall..."))
        fw_layout.addWidget(btn_fw_enable)
        
        btn_fw_disable = QPushButton("Disable Firewall")
        btn_fw_disable.clicked.connect(lambda: self.run_command("pkexec", ["systemctl", "disable", "--now", "firewalld"], "Disabling Firewall..."))
        fw_layout.addWidget(btn_fw_disable)
        
        layout.addWidget(fw_group)

        # Telemetry Group
        tele_group = QGroupBox("Telemetry & Tracking")
        tele_layout = QVBoxLayout()
        tele_group.setLayout(tele_layout)
        
        btn_remove_tele = QPushButton("Remove Fedora Telemetry Packages")
        # gnome-abrt, gnome-initial-setup (optional), fedora-workstation-backgrounds (not telemetry but can be removed)
        # The main one is python3-abrt-addon, abrt, abrt-cli, etc.
        tele_cmd = "dnf remove -y abrt* gnome-abrt* || true"
        btn_remove_tele.clicked.connect(lambda: self.run_command("pkexec", ["sh", "-c", tele_cmd], "Removing Telemetry Packages..."))
        tele_layout.addWidget(btn_remove_tele)
        
        layout.addWidget(tele_group)

        # Security Checks Group
        sec_group = QGroupBox("Security Checks")
        sec_layout = QVBoxLayout()
        sec_group.setLayout(sec_layout)
        
        btn_check_updates = QPushButton("Check for Security Updates")
        btn_check_updates.clicked.connect(lambda: self.run_command("dnf", ["check-update", "--security"], "Checking for Security Updates..."))
        sec_layout.addWidget(btn_check_updates)
        
        layout.addWidget(sec_group)

        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_area)

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
