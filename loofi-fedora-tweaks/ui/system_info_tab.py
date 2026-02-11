from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout
from PyQt6.QtCore import QTimer
import subprocess
import os

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata


class SystemInfoTab(QWidget, PluginInterface):

    _METADATA = PluginMetadata(
        id="system_info",
        name="System Info",
        description="Detailed system information including hardware specs, kernel, and uptime.",
        category="System",
        icon="ℹ️",
        badge="recommended",
        order=10,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # System Info Group
        info_group = QGroupBox(self.tr("System Information"))
        info_layout = QGridLayout()
        info_group.setLayout(info_layout)

        self.labels = {}
        fields = [
            (self.tr("Hostname"), "hostname"),
            (self.tr("Kernel"), "kernel"),
            (self.tr("Fedora Version"), "fedora"),
            (self.tr("CPU"), "cpu"),
            (self.tr("RAM"), "ram"),
            (self.tr("Disk Usage (/)"), "disk"),
            (self.tr("Uptime"), "uptime"),
            (self.tr("Battery"), "battery")
        ]

        for i, (label, key) in enumerate(fields):
            lbl = QLabel(f"<b>{label}:</b>")
            val = QLabel(self.tr("Loading..."))
            self.labels[key] = val
            info_layout.addWidget(lbl, i, 0)
            info_layout.addWidget(val, i, 1)

        layout.addWidget(info_group)
        layout.addStretch()

        # Refresh info on load
        QTimer.singleShot(100, self.refresh_info)

    def refresh_info(self):
        try:
            self.labels["hostname"].setText(subprocess.getoutput("hostname"))
            self.labels["kernel"].setText(subprocess.getoutput("uname -r"))
            self.labels["fedora"].setText(subprocess.getoutput("cat /etc/fedora-release"))

            cpu_info = subprocess.getoutput("lscpu | grep 'Model name' | cut -d: -f2").strip()
            self.labels["cpu"].setText(cpu_info if cpu_info else "Unknown")

            mem = subprocess.getoutput("free -h | awk '/^Mem:/ {print $2 \" total, \" $3 \" used\"}'")
            self.labels["ram"].setText(mem)

            disk = subprocess.getoutput("df -h / | awk 'NR==2 {print $3 \"/\" $2 \" (\" $5 \" used)\"}'")
            self.labels["disk"].setText(disk)

            uptime = subprocess.getoutput("uptime -p")
            self.labels["uptime"].setText(uptime)

            # Battery
            if os.path.exists("/sys/class/power_supply/BAT0/capacity"):
                capacity = subprocess.getoutput("cat /sys/class/power_supply/BAT0/capacity")
                status = subprocess.getoutput("cat /sys/class/power_supply/BAT0/status")
                self.labels["battery"].setText(f"{capacity}% ({status})")
            else:
                self.labels["battery"].setText(self.tr("No battery detected"))
        except Exception:
            pass
