from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QHBoxLayout, QTextEdit, QMessageBox
from utils.process import CommandRunner
from utils.safety import SafetyManager
import shutil

class CleanupTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Output Area (Shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # Cleanup Group
        cleanup_group = QGroupBox("Cleanup")
        cleanup_layout = QVBoxLayout()
        cleanup_group.setLayout(cleanup_layout)
        
        btn_dnf_clean = QPushButton("Clean DNF Cache")
        btn_dnf_clean.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "clean", "all"], "Cleaning DNF Cache..."))
        cleanup_layout.addWidget(btn_dnf_clean)
        
        btn_autoremove = QPushButton("Remove Unused Packages (Risky)")
        btn_autoremove.setStyleSheet("color: red;")
        btn_autoremove.clicked.connect(self.run_autoremove)
        cleanup_layout.addWidget(btn_autoremove)
        
        btn_journal = QPushButton("Vacuum Journal (2 weeks)")
        btn_journal.clicked.connect(lambda: self.run_command("pkexec", ["journalctl", "--vacuum-time=2weeks"], "Vacuuming Journal..."))
        cleanup_layout.addWidget(btn_journal)
        
        layout.addWidget(cleanup_group)

        # Maintenance Group
        maint_group = QGroupBox("Maintenance")
        maint_layout = QVBoxLayout()
        maint_group.setLayout(maint_layout)
        
        btn_trim = QPushButton("SSD Trim (fstrim)")
        btn_trim.clicked.connect(lambda: self.run_command("pkexec", ["fstrim", "-av"], "Trimming SSD..."))
        maint_layout.addWidget(btn_trim)
        
        btn_rpmdb = QPushButton("Rebuild RPM Database")
        btn_rpmdb.clicked.connect(lambda: self.run_command("pkexec", ["rpm", "--rebuilddb"], "Rebuilding RPM Database..."))
        maint_layout.addWidget(btn_rpmdb)
        
        # Timeshift Check
        ts_layout = QHBoxLayout()
        btn_check_ts = QPushButton("Check for Timeshift Snapshots")
        btn_check_ts.clicked.connect(self.check_timeshift)
        ts_layout.addWidget(btn_check_ts)
        maint_layout.addLayout(ts_layout)

        layout.addWidget(maint_group)
        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_area)

    def check_timeshift(self):
        if shutil.which("timeshift"):
            self.run_command("pkexec", ["timeshift", "--list"], "Checking Timeshift Snapshots...")
        else:
            self.append_output("Timeshift not found. Please install it for system safety.\n")

    def run_autoremove(self):
        if SafetyManager.check_dnf_lock():
             QMessageBox.warning(self, "Update Locked", "Another package manager is running.")
             return

        if SafetyManager.confirm_action(self, "Remove Unused Packages (Risky)"):
             self.run_command("pkexec", ["dnf", "autoremove", "-y"], "Removing unused packages...")

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
