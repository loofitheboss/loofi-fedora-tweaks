from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit, QGroupBox, QCheckBox
from utils.process import CommandRunner

class ReposTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("Repository Management")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)
        
        # RPM Fusion Group
        fusion_group = QGroupBox("RPM Fusion (Essential for media codecs & drivers)")
        fusion_layout = QVBoxLayout()
        fusion_group.setLayout(fusion_layout)
        
        self.btn_enable_fusion = QPushButton("Enable RPM Fusion (Free & Non-Free)")
        self.btn_enable_fusion.clicked.connect(self.enable_rpm_fusion)
        fusion_layout.addWidget(self.btn_enable_fusion)
        
        self.btn_install_codecs = QPushButton("Install Multimedia Codecs (ffmpeg, gstreamer, etc.)")
        self.btn_install_codecs.clicked.connect(self.install_multimedia_codecs)
        fusion_layout.addWidget(self.btn_install_codecs)
        
        layout.addWidget(fusion_group)

        # Flatpak Flathub
        flathub_group = QGroupBox("Flathub (Flatpak)")
        flathub_layout = QVBoxLayout()
        flathub_group.setLayout(flathub_layout)
        
        self.btn_enable_flathub = QPushButton("Enable Flathub Remote")
        self.btn_enable_flathub.clicked.connect(self.enable_flathub)
        flathub_layout.addWidget(self.btn_enable_flathub)
        
        layout.addWidget(flathub_group)
        
        # COPR Repos Section (Placeholder for future expansion)
        copr_group = QGroupBox("COPR Repositories")
        copr_layout = QVBoxLayout()
        copr_group.setLayout(copr_layout)
        
        copr_layout.addWidget(QLabel("Common COPR Repositories:"))
        
        self.btn_copr_loofi = QPushButton("Enable Loofi Fedora Tweaks COPR")
        # Placeholder command
        self.btn_copr_loofi.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "copr", "enable", "-y", "loofitheboss/loofi-fedora-tweaks"], "Enabling Loofi COPR..."))
        copr_layout.addWidget(self.btn_copr_loofi)
        
        layout.addWidget(copr_group)

        # Output Area
        layout.addWidget(QLabel("Output Log:"))
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        layout.addWidget(self.output_area)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

    def enable_rpm_fusion(self):
        cmd = """
        dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm;
        dnf groupupdate -y core;
        """
        self.run_command("pkexec", ["sh", "-c", cmd], "Enabling RPM Fusion repositories...")

    def install_multimedia_codecs(self):
        # Command based on Fedora docs for full multimedia support
        cmd = "dnf groupupdate -y multimedia --setop='install_weak_deps=False' --exclude=PackageKit-gstreamer-plugin && dnf groupupdate -y sound-and-video"
        self.run_command("pkexec", ["sh", "-c", cmd], "Installing Multimedia Codecs...")

    def enable_flathub(self):
        self.run_command("flatpak", ["remote-add", "--if-not-exists", "flathub", "https://flathub.org/repo/flathub.flatpakrepo"], "Enabling Flathub...")

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
