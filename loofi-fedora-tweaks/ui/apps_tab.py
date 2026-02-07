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

        # App List definition (v2.0 - Fixed and expanded)
        self.apps = [
            {
                "name": "Google Chrome",
                "desc": "Web Browser",
                "cmd": "pkexec",
                "args": ["dnf", "install", "-y", "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm"]
            },
            {
                "name": "Visual Studio Code",
                "desc": "Code Editor (Flatpak)",
                "cmd": "flatpak",
                "args": ["install", "-y", "flathub", "com.visualstudio.code"]
            },
            {
                "name": "Steam",
                "desc": "Gaming Platform",
                "cmd": "pkexec",
                "args": ["sh", "-c", "dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm && dnf install -y steam"]
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
            },
            {
                "name": "Spotify",
                "desc": "Music Streaming (Flatpak)",
                "cmd": "flatpak",
                "args": ["install", "-y", "flathub", "com.spotify.Client"]
            },
            {
                "name": "OBS Studio",
                "desc": "Streaming & Recording (Flatpak)",
                "cmd": "flatpak",
                "args": ["install", "-y", "flathub", "com.obsproject.Studio"]
            },
            {
                "name": "GIMP",
                "desc": "Image Editor",
                "cmd": "pkexec",
                "args": ["dnf", "install", "-y", "gimp"]
            },
            {
                "name": "LibreOffice",
                "desc": "Office Suite",
                "cmd": "pkexec",
                "args": ["dnf", "install", "-y", "libreoffice"]
            },
            {
                "name": "Brave Browser",
                "desc": "Privacy Browser",
                "cmd": "pkexec",
                "args": ["sh", "-c", "dnf config-manager addrepo --from-repofile=https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo && dnf install -y brave-browser"]
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
        btn_install.clicked.connect(lambda checked, app=app_data: self.install_app(app))
        
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
