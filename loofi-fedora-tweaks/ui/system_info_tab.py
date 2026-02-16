from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QGridLayout,
    QPushButton,
    QComboBox,
    QFileDialog,
)
from PyQt6.QtCore import QTimer
import os

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata
from utils.report_exporter import ReportExporter
from utils.log import get_logger
from utils import system_info_utils

logger = get_logger(__name__)


class SystemInfoTab(QWidget, PluginInterface):
    _METADATA = PluginMetadata(
        id="system_info",
        name="System Info",
        description="Detailed system information including hardware specs, kernel, and uptime.",
        category="Overview",
        icon="ℹ️",
        badge="recommended",
        order=20,
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
            (self.tr("Battery"), "battery"),
        ]

        for i, (label, key) in enumerate(fields):
            lbl = QLabel(f"<b>{label}:</b>")
            val = QLabel(self.tr("Loading..."))
            self.labels[key] = val
            info_layout.addWidget(lbl, i, 0)
            info_layout.addWidget(val, i, 1)

        layout.addWidget(info_group)

        # v31.0: Export Report section
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        self.export_format = QComboBox()
        self.export_format.addItems(["Markdown", "HTML"])
        self.export_format.setAccessibleName(self.tr("Export format"))
        export_layout.addWidget(QLabel(self.tr("Format:")))
        export_layout.addWidget(self.export_format)

        btn_export = QPushButton(self.tr("📄 Export Report"))
        btn_export.setAccessibleName(self.tr("Export system report"))
        btn_export.clicked.connect(self._export_report)
        export_layout.addWidget(btn_export)

        layout.addLayout(export_layout)
        layout.addStretch()

        # Refresh info on load
        QTimer.singleShot(100, self.refresh_info)

    def refresh_info(self):
        try:
            self.labels["hostname"].setText(system_info_utils.get_hostname())
            self.labels["kernel"].setText(system_info_utils.get_kernel_version())
            self.labels["fedora"].setText(system_info_utils.get_fedora_release())
            self.labels["cpu"].setText(system_info_utils.get_cpu_model())
            self.labels["ram"].setText(system_info_utils.get_ram_usage())
            self.labels["disk"].setText(system_info_utils.get_disk_usage())
            self.labels["uptime"].setText(system_info_utils.get_uptime())

            # Battery
            battery = system_info_utils.get_battery_status()
            if battery is not None:
                self.labels["battery"].setText(battery)
            else:
                self.labels["battery"].setText(self.tr("No battery detected"))
        except (RuntimeError, OSError, ValueError, TypeError) as e:
            logger.debug("Failed to refresh system info: %s", e)

    def _export_report(self):
        """Export system report as Markdown or HTML."""
        fmt = "html" if self.export_format.currentText() == "HTML" else "markdown"
        ext = ".html" if fmt == "html" else ".md"
        default_name = f"system-report{ext}"

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save System Report"),
            os.path.expanduser(f"~/Documents/{default_name}"),
            self.tr("HTML files (*.html);;Markdown files (*.md);;All files (*)"),
        )
        if path:
            try:
                ReportExporter.save_report(path, fmt)
            except (RuntimeError, OSError, ValueError, TypeError) as e:
                logger.debug("Failed to export system report: %s", e)
