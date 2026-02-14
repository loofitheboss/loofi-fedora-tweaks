"""
Dependency Doctor — System health check dialog.
Part of v10.0 "Aurora", refactored in v38.0 "Clarity".

Checks for critical and recommended system tools, offers to install
missing dependencies via the correct package manager (dnf or rpm-ostree).

Uses PrivilegedCommand and SystemManager.get_package_manager() instead of
hardcoded dnf calls.  All user-visible strings are wrapped in self.tr()
for i18n readiness.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QHBoxLayout, QMessageBox,
)
from PyQt6.QtGui import QIcon, QColor
import shutil

from utils.command_runner import CommandRunner
from utils.commands import PrivilegedCommand
from utils.system import SystemManager


class DependencyDoctor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Dependency Doctor"))
        self.setFixedSize(400, 500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("System Health Check"))
        header.setObjectName("doctorHeader")
        layout.addWidget(header)

        desc = QLabel(self.tr(
            "The following tools are recommended for full functionality."
        ))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # List of Tools
        self.tool_list = QListWidget()
        self.tool_list.setAccessibleName(self.tr("Tool status list"))
        layout.addWidget(self.tool_list)

        self.tools = {
            "gamemode": self.tr("Gaming optimization daemon"),
            "mangohud": self.tr("Gaming FPS overlay"),
            "timeshift": self.tr("System backup/snapshot tool"),
            "flatpak": self.tr("Application sandboxing"),
            "git": self.tr("Version control (for updates)"),
            SystemManager.get_package_manager(): self.tr(
                "Package manager (Critical)"
            ),
            "pkexec": self.tr("Authorization agent (Critical)"),
        }

        self.missing_tools = []

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.btn_fix = QPushButton(self.tr("Fix Missing Dependencies"))
        self.btn_fix.setObjectName("doctorFixButton")
        self.btn_fix.setAccessibleName(self.tr("Install missing tools"))
        self.btn_fix.clicked.connect(self.fix_dependencies)
        self.btn_fix.setEnabled(False)
        btn_layout.addWidget(self.btn_fix)

        self.btn_close = QPushButton(self.tr("Close"))
        self.btn_close.setAccessibleName(self.tr("Close doctor dialog"))
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        # Populate tool list after action buttons are created.
        self.check_tools()

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
                item.setIcon(QIcon.fromTheme("emblem-default"))
                item.setForeground(QColor("#3dd68c"))
            else:
                item.setIcon(QIcon.fromTheme("emblem-important"))
                item.setForeground(QColor("#e8556d"))
                self.missing_tools.append(tool)

            self.tool_list.addItem(item)

        if self.missing_tools:
            self.btn_fix.setEnabled(True)
            self.btn_fix.setText(
                self.tr("Install {n} Missing Tools").format(
                    n=len(self.missing_tools)
                )
            )
        else:
            self.btn_fix.setEnabled(False)
            self.btn_fix.setText(self.tr("All Systems Go!"))

    def fix_dependencies(self):
        if not self.missing_tools:
            return

        # Use PrivilegedCommand for proper package manager detection
        binary, args, desc = PrivilegedCommand.dnf(
            "install", *self.missing_tools
        )
        cmd = args  # CommandRunner takes binary + args separately

        # Disable UI
        self.btn_fix.setEnabled(False)
        self.btn_fix.setText(self.tr("Installing..."))
        self.tool_list.setEnabled(False)

        # Run install via correct package manager
        self.runner.run_command(binary, cmd)

    def on_fix_complete(self, exit_code):
        self.tool_list.setEnabled(True)
        self.check_tools()  # Re-check

        if exit_code == 0:
            QMessageBox.information(
                self,
                self.tr("Success"),
                self.tr("Dependencies installed successfully!"),
            )
        else:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr(
                    "Failed to install dependencies. "
                    "Check your internet connection or try manually."
                ),
            )
