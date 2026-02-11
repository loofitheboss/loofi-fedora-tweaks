"""
Gaming Tab - Gaming optimization tools.
Normalized to BaseTab in v17.0 "Atlas".
Uses PrivilegedCommand for package installation.
"""

import subprocess

from PyQt6.QtWidgets import (
    QGroupBox, QLabel, QMessageBox, QPushButton,
    QVBoxLayout,
)

from ui.base_tab import BaseTab
from utils.commands import PrivilegedCommand
from utils.log import get_logger

logger = get_logger(__name__)


class GamingTab(BaseTab):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("Gaming Optimizations"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)

        # Performance Tools Group
        perf_group = QGroupBox(self.tr("Performance Tools"))
        perf_layout = QVBoxLayout()
        perf_group.setLayout(perf_layout)

        # Feral Gamemode
        self.btn_gamemode = QPushButton(self.tr("Install Feral GameMode"))
        self.btn_gamemode.clicked.connect(self.install_gamemode)
        perf_layout.addWidget(self.btn_gamemode)

        self.lbl_gamemode_status = QLabel(self.tr("GameMode Status: Unknown"))
        perf_layout.addWidget(self.lbl_gamemode_status)

        # MangoHud
        btn_mangohud = QPushButton(self.tr("Install MangoHud & Goverlay"))
        btn_mangohud.clicked.connect(self.install_mangohud)
        perf_layout.addWidget(btn_mangohud)

        layout.addWidget(perf_group)

        # Steam Utilities
        steam_group = QGroupBox(self.tr("Steam Utilities"))
        steam_layout = QVBoxLayout()
        steam_group.setLayout(steam_layout)

        # ProtonUp-Qt
        btn_protonup = QPushButton(self.tr("Install ProtonUp-Qt (Flatpak)"))
        btn_protonup.clicked.connect(self.install_protonup)
        steam_layout.addWidget(btn_protonup)

        # Steam Devices
        btn_steam_devices = QPushButton(self.tr("Install Steam Devices (Controller Support)"))
        btn_steam_devices.clicked.connect(self.install_steam_devices)
        steam_layout.addWidget(btn_steam_devices)

        layout.addWidget(steam_group)

        # Output area
        self.add_output_section(layout)
        layout.addStretch()

        # Check status
        self.check_gamemode_status()

    def install_gamemode(self):
        binary, args, desc = PrivilegedCommand.dnf("install", "gamemode")
        self.run_command(binary, args, desc)
        QMessageBox.information(self, self.tr("Installing"),
                                self.tr("GameMode installation started."))

    def check_gamemode_status(self):
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "gamemoded"],
                capture_output=True, text=True
            )
            if "active" in result.stdout:
                self.lbl_gamemode_status.setText(
                    self.tr("GameMode Status: ✅ Active (Service Running)"))
                self.btn_gamemode.setEnabled(False)
                self.btn_gamemode.setText(self.tr("GameMode Installed"))
            else:
                res_rpm = subprocess.run(
                    ["rpm", "-q", "gamemode"], capture_output=True)
                if res_rpm.returncode == 0:
                    self.lbl_gamemode_status.setText(
                        self.tr("GameMode Status: ⚠️ Installed but Inactive"))
                    self.btn_gamemode.setText(self.tr("Reinstall GameMode"))
                else:
                    self.lbl_gamemode_status.setText(
                        self.tr("GameMode Status: ❌ Not Installed"))
        except Exception as e:
            self.lbl_gamemode_status.setText(
                self.tr("Status check failed: {}").format(e))

    def install_mangohud(self):
        binary, args, desc = PrivilegedCommand.dnf("install", "mangohud", "goverlay")
        self.run_command(binary, args, desc)
        QMessageBox.information(self, self.tr("Installing"),
                                self.tr("MangoHud & Goverlay installation started."))

    def install_protonup(self):
        self.run_command("flatpak",
                         ["install", "flathub", "net.davidotek.pupgui2", "-y"],
                         self.tr("Installing ProtonUp-Qt..."))
        QMessageBox.information(self, self.tr("Installing"),
                                self.tr("ProtonUp-Qt installation started."))

    def install_steam_devices(self):
        binary, args, desc = PrivilegedCommand.dnf("install", "steam-devices")
        self.run_command(binary, args, desc)
        QMessageBox.information(self, self.tr("Installing"),
                                self.tr("Steam Devices support installation started."))
