from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit, QScrollArea, QFrame
from utils.process import CommandRunner

class AppsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Scroll Area for apps list if it gets long
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        
        layout.addWidget(scroll)
        
        # Output Area (Shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # App List definition
        self.apps = [
            {
                "name": "Google Chrome",
                "desc": "Web Browser",
                "cmd": "pkexec",
                "args": ["dnf", "install", "-y", "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm"]
            },
            {
                "name": "Visual Studio Code",
                "desc": "Code Editor",
                "cmd": "pkexec",
                 # Simplified for robustness: separate repo add and install might be better, 
                 # but for a single button we can try to chain or just assume repo exists? 
                 # Let's do a reliable install script approach or just DNF if repo is commonly added manually?
                 # Better approach for this demo: simple DNF install if repo exists, or flatpak. 
                 # Let's use the official repo import command sequence wrapped in sh -c
                "args": ["sh", "-c", "rpm --import https://packages.microsoft.com/keys/microsoft.asc && sh -c 'echo -e \"[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc\" > /etc/yum.repos.d/vscode.repo' && dnf check-update && dnf install -y code"]
            },
            {
                "name": "Steam",
                "desc": "Gaming Platform (RPM Fusion)",
                "cmd": "pkexec",
                "args": ["dnf", "install", "-y", "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm", "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm", "&&", "dnf", "install", "-y", "steam"]
            },
            {
                "name": "VLC Media Player",
                "desc": "Media Player",
                "cmd": "pkexec",
                "args": ["dnf", "install", "-y", "vlc"]
            },
             {
                "name": "Discord",
                "desc": "Chat & Voice (Flatpak)",
                "cmd": "flatpak",
                "args": ["install", "-y", "flathub", "com.discordapp.Discord"]
            }
        ]

        for app in self.apps:
            self.add_app_row(scroll_layout, app)

        scroll_layout.addStretch()
        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_area)

    def add_app_row(self, layout, app_data):
        row_widget = QFrame()
        row_widget.setFrameShape(QFrame.Shape.StyledPanel)
        row_layout = QHBoxLayout()
        row_widget.setLayout(row_layout)
        
        lbl_name = QLabel(f"<b>{app_data['name']}</b>")
        lbl_desc = QLabel(app_data['desc'])
        
        btn_install = QPushButton("Install")
        btn_install.clicked.connect(lambda: self.install_app(app_data))
        
        row_layout.addWidget(lbl_name)
        row_layout.addWidget(lbl_desc)
        row_layout.addStretch()
        row_layout.addWidget(btn_install)
        
        layout.addWidget(row_widget)

    def install_app(self, app_data):
        self.output_area.clear()
        self.append_output(f"Installing {app_data['name']}...\n")
        self.runner.run_command(app_data['cmd'], app_data['args'])

    def append_output(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def command_finished(self, exit_code):
        self.append_output(f"\nCommand finished with exit code: {exit_code}")
