from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtCore import Qt
import shutil
from utils.command_runner import CommandRunner

class DependencyDoctor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dependency Doctor")
        self.setFixedSize(400, 500)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("System Health Check")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        
        desc = QLabel("The following tools are recommended for full functionality.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # List of Tools
        self.tool_list = QListWidget()
        layout.addWidget(self.tool_list)
        
        self.tools = {
            "gamemode": "Gaming optimization daemon",
            "mangohud": "Gaming FPS overlay",
            "timeshift": "System backup/snapshot tool",
            "flatpak": "Application sandboxing",
            "git": "Version control (for updates)",
            "dnf": "Package manager (Critical)",
            "pkexec": "Authorization agent (Critical)"
        }
        
        self.missing_tools = []
        self.check_tools()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_fix = QPushButton("Fix Missing Dependencies")
        self.btn_fix.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_fix.clicked.connect(self.fix_dependencies)
        self.btn_fix.setEnabled(False) # Enabled only if missing found
        btn_layout.addWidget(self.btn_fix)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        # Command Runner for installation
        self.runner = CommandRunner()
        self.runner.finished.connect(self.on_fix_complete)

    def check_tools(self):
        self.tool_list.clear()
        self.missing_tools = []
        
        for tool, desc in self.tools.items():
            item = QListWidgetItem(f"{tool} - {desc}")
            path = shutil.which(tool)
            
            if path:
                item.setIcon(QIcon.fromTheme("emblem-default")) # Checkmark usually
                item.setForeground(QColor("#27ae60")) # Green
            else:
                item.setIcon(QIcon.fromTheme("emblem-important")) # Warning/X
                item.setForeground(QColor("#c0392b")) # Red
                self.missing_tools.append(tool)
                
            self.tool_list.addItem(item)
            
        if self.missing_tools:
            self.btn_fix.setEnabled(True)
            self.btn_fix.setText(f"Install {len(self.missing_tools)} Missing Tools")
        else:
            self.btn_fix.setEnabled(False)
            self.btn_fix.setText("All Systems Go!")

    def fix_dependencies(self):
        if not self.missing_tools:
            return
            
        packages = " ".join(self.missing_tools)
        cmd = ["dnf", "install", "-y"] + self.missing_tools
        
        # Disable UI
        self.btn_fix.setEnabled(False)
        self.btn_fix.setText("Installing...")
        self.tool_list.setEnabled(False)
        
        # Run dnf install
        self.runner.run_command("pkexec", cmd)

    def on_fix_complete(self, exit_code):
        self.tool_list.setEnabled(True)
        self.check_tools() # Re-check
        
        if exit_code == 0:
            QMessageBox.information(self, "Success", "Dependencies installed successfully!")
        else:
            QMessageBox.warning(self, "Error", "Failed to install dependencies. Check your internet connection or try manually.")
