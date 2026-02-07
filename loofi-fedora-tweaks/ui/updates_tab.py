from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout, QGroupBox
from utils.process import CommandRunner

class UpdatesTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("System Updates")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)
        
        # Update All Button (Prominent)
        self.btn_update_all = QPushButton("🔄 Update All (DNF + Flatpak + Firmware)")
        self.btn_update_all.setStyleSheet("font-size: 14px; padding: 10px; background-color: #3daee9; color: white;")
        self.btn_update_all.clicked.connect(self.run_update_all)
        layout.addWidget(self.btn_update_all)
        
        # Individual Update Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_dnf = QPushButton("Update System (DNF)")
        self.btn_dnf.clicked.connect(self.run_dnf_update)
        btn_layout.addWidget(self.btn_dnf)
        
        self.btn_flatpak = QPushButton("Update Flatpaks")
        self.btn_flatpak.clicked.connect(self.run_flatpak_update)
        btn_layout.addWidget(self.btn_flatpak)

        self.btn_fw = QPushButton("Update Firmware")
        self.btn_fw.clicked.connect(self.run_fw_update)
        btn_layout.addWidget(self.btn_fw)
        
        layout.addLayout(btn_layout)
        
        # Kernel Management Group
        kernel_group = QGroupBox("Kernel Management")
        kernel_layout = QHBoxLayout()
        kernel_group.setLayout(kernel_layout)
        
        btn_list_kernels = QPushButton("List Installed Kernels")
        btn_list_kernels.clicked.connect(lambda: self.run_single_command("rpm", ["-qa", "kernel"], "Listing Installed Kernels..."))
        kernel_layout.addWidget(btn_list_kernels)
        
        btn_remove_old = QPushButton("Remove Old Kernels")
        btn_remove_old.clicked.connect(lambda: self.run_single_command("pkexec", ["dnf", "remove", "--oldinstallonly", "-y"], "Removing Old Kernels..."))
        kernel_layout.addWidget(btn_remove_old)
        
        layout.addWidget(kernel_group)
        
        # Output Area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)
        
        self.update_queue = []
        self.current_update_index = 0

    def run_dnf_update(self):
        self.output_area.clear()
        self.append_output("Starting System Update...\n")
        # pkexec allows running dnf with root privileges
        # We use 'dnf update -y' to avoid interactive prompts in the background process
        self.runner.run_command("pkexec", ["dnf", "update", "-y"])
        self.btn_dnf.setEnabled(False)
        self.btn_flatpak.setEnabled(False)

    def run_flatpak_update(self):
        self.output_area.clear()
        self.append_output("Starting Flatpak Update...\n")
        # Flatpak updates might run without root for user installs, but system-wide needs root/polkit
        # interactive flatpak update usually just works, but -y is safer for non-interactive
        self.runner.run_command("flatpak", ["update", "-y"])
        self.btn_dnf.setEnabled(False)
        self.btn_flatpak.setEnabled(False)
        self.btn_fw.setEnabled(False)

    def run_fw_update(self):
        self.output_area.clear()
        self.append_output("Starting Firmware Update...\n")
        self.runner.run_command("pkexec", ["fwupdmgr", "update", "-y"])
        self.btn_dnf.setEnabled(False)
        self.btn_flatpak.setEnabled(False)
        self.btn_fw.setEnabled(False)

    def append_output(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def command_finished(self, exit_code):
        self.append_output(f"\nCommand finished with exit code: {exit_code}")
        self.btn_dnf.setEnabled(True)
        self.btn_flatpak.setEnabled(True)
        self.btn_fw.setEnabled(True)
        self.btn_update_all.setEnabled(True)
        
        # Handle sequential update all
        if self.update_queue and self.current_update_index < len(self.update_queue) - 1:
            self.current_update_index += 1
            cmd, args, desc = self.update_queue[self.current_update_index]
            self.append_output(f"\n\n{desc}\n")
            self.runner.run_command(cmd, args)
        else:
            self.update_queue = []
            self.current_update_index = 0

    def run_update_all(self):
        self.output_area.clear()
        self.btn_update_all.setEnabled(False)
        self.btn_dnf.setEnabled(False)
        self.btn_flatpak.setEnabled(False)
        self.btn_fw.setEnabled(False)
        
        # Queue up all updates
        self.update_queue = [
            ("pkexec", ["dnf", "update", "-y"], "Starting System Update (DNF)..."),
            ("flatpak", ["update", "-y"], "Starting Flatpak Update..."),
            ("pkexec", ["fwupdmgr", "update", "-y"], "Starting Firmware Update...")
        ]
        self.current_update_index = 0
        cmd, args, desc = self.update_queue[0]
        self.append_output(desc + "\n")
        self.runner.run_command(cmd, args)

    def run_single_command(self, cmd, args, description):
        self.output_area.clear()
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)
