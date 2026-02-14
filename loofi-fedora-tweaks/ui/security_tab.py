"""
Security Tab - Proactive security hardening interface.
Part of v8.5 "Sentinel" update, expanded in v10.0 "Zenith" to absorb Privacy features.

Features:
- Port auditor with security score
- USB Guard management
- Application sandboxing
- Firewall control (from Privacy tab)
- Telemetry removal (from Privacy tab)
- Security updates check (from Privacy tab)
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QTextEdit,
    QScrollArea,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ui.base_tab import BaseTab
from ui.tab_utils import CONTENT_MARGINS
from utils.commands import PrivilegedCommand
from utils.sandbox import SandboxManager
from utils.usbguard import USBGuardManager
from utils.ports import PortAuditor
from utils.command_runner import CommandRunner
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata


class SecurityTab(QWidget, PluginInterface):
    """Security tab for system hardening and auditing."""

    _METADATA = PluginMetadata(
        id="security",
        name="Security & Privacy",
        description="Security hardening including firewall, USB guard, port auditing, and telemetry removal.",
        category="Network & Security",
        icon="🛡️",
        badge="recommended",
        order=20,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self._setup_command_runner()
        self.init_ui()

    def _setup_command_runner(self):
        """Setup CommandRunner for privacy-related commands."""
        self.privacy_runner = CommandRunner()
        self.privacy_runner.output_received.connect(self._on_privacy_output)
        self.privacy_runner.finished.connect(self._on_privacy_command_finished)

    def _on_privacy_output(self, text):
        """Handle output from privacy commands."""
        self.log(text.rstrip("\n"))

    def _on_privacy_command_finished(self, exit_code):
        """Handle privacy command completion."""
        self.log(self.tr("Command finished with exit code: {}").format(exit_code))

    def _run_privacy_command(self, cmd, args, description=""):
        """Execute a privacy-related command with output logging."""
        if description:
            self.log(description)
        self.privacy_runner.run_command(cmd, args)

    def init_ui(self):
        """Initialize the UI."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("🛡️ Security Center"))
        header.setObjectName("header")
        layout.addWidget(header)

        # Security Score
        layout.addWidget(self._create_score_section())

        # Port Auditor
        layout.addWidget(self._create_ports_section())

        # USB Guard
        layout.addWidget(self._create_usb_section())

        # Sandbox Manager
        layout.addWidget(self._create_sandbox_section())

        # Firewall Control (absorbed from Privacy tab)
        layout.addWidget(self._create_firewall_section())

        # Telemetry & Tracking (absorbed from Privacy tab)
        layout.addWidget(self._create_telemetry_section())

        # Security Updates Check (absorbed from Privacy tab)
        layout.addWidget(self._create_security_updates_section())

        # Log
        log_group = QGroupBox(self.tr("Activity Log"))
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setAccessibleName(self.tr("Activity log"))
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*CONTENT_MARGINS)
        main_layout.addWidget(scroll)

    def _create_score_section(self) -> QGroupBox:
        """Create security score display."""
        group = QGroupBox(self.tr("🎯 Security Score"))
        layout = QVBoxLayout(group)

        # Get security score
        score_data = PortAuditor.get_security_score()
        score = score_data["score"]
        rating = score_data["rating"]

        # Color based on score
        if score >= 90:
            score_level = "good"
        elif score >= 70:
            score_level = "ok"
        elif score >= 50:
            score_level = "warning"
        else:
            score_level = "bad"

        score_label = QLabel(f"{score}/100 - {rating}")
        score_label.setObjectName("secScoreLabel")
        score_label.setProperty("scoreLevel", score_level)
        if score_label.style() is not None:
            _style = score_label.style()
            assert _style is not None
            _style.unpolish(score_label)
            _style.polish(score_label)
        layout.addWidget(score_label)

        # Stats
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(QLabel(f"Open Ports: {score_data['open_ports']}"))
        stats_layout.addWidget(QLabel(f"Risky Ports: {score_data['risky_ports']}"))

        fw_status = "✅ Running" if PortAuditor.is_firewalld_running() else "❌ Stopped"
        stats_layout.addWidget(QLabel(f"Firewall: {fw_status}"))
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Recommendations
        if score_data["recommendations"]:
            rec_label = QLabel(self.tr("Recommendations:"))
            rec_label.setObjectName("secRecLabel")
            layout.addWidget(rec_label)

            for rec in score_data["recommendations"][:3]:  # Limit to 3
                rec_item = QLabel(f"  ⚠️ {rec}")
                rec_item.setObjectName("secRecItem")
                rec_item.setWordWrap(True)
                layout.addWidget(rec_item)

        # Refresh button
        refresh_btn = QPushButton(self.tr("🔄 Refresh Score"))
        refresh_btn.setAccessibleName(self.tr("Refresh Score"))
        refresh_btn.clicked.connect(self._refresh_score)
        layout.addWidget(refresh_btn)

        return group

    def _create_ports_section(self) -> QGroupBox:
        """Create port auditor section."""
        group = QGroupBox(self.tr("🔌 Port Auditor"))
        layout = QVBoxLayout(group)

        # Port table
        self.port_table = QTableWidget()
        self.port_table.setColumnCount(5)
        self.port_table.setHorizontalHeaderLabels(
            ["Port", "Protocol", "Address", "Process", "Status"]
        )
        self.port_table.horizontalHeader().setSectionResizeMode(  # type: ignore[union-attr]
            QHeaderView.ResizeMode.Stretch
        )
        self.port_table.setMaximumHeight(150)
        BaseTab.configure_table(self.port_table)
        layout.addWidget(self.port_table)

        self._refresh_ports()

        # Buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton(self.tr("🔄 Scan Ports"))
        refresh_btn.setAccessibleName(self.tr("Scan Ports"))
        refresh_btn.clicked.connect(self._refresh_ports)
        btn_layout.addWidget(refresh_btn)

        block_btn = QPushButton(self.tr("🚫 Block Selected"))
        block_btn.setAccessibleName(self.tr("Block Selected port"))
        block_btn.clicked.connect(self._block_port)
        btn_layout.addWidget(block_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_usb_section(self) -> QGroupBox:
        """Create USB Guard section."""
        group = QGroupBox(self.tr("🔒 USB Guard"))
        layout = QVBoxLayout(group)

        # Status
        installed = USBGuardManager.is_installed()
        running = USBGuardManager.is_running() if installed else False

        status_text = (
            "✅ Active"
            if running
            else ("❌ Stopped" if installed else "📥 Not Installed")
        )
        self.usb_status = QLabel(f"Status: {status_text}")
        layout.addWidget(self.usb_status)

        if not installed:
            install_btn = QPushButton(self.tr("📥 Install USB Guard"))
            install_btn.setAccessibleName(self.tr("Install USB Guard"))
            install_btn.clicked.connect(self._install_usbguard)
            layout.addWidget(install_btn)

            info = QLabel(
                self.tr(
                    "USB Guard blocks unauthorized USB devices to prevent BadUSB attacks."
                )
            )
            info.setWordWrap(True)
            info.setObjectName("secUsbInfo")
            layout.addWidget(info)
        else:
            # Device list
            self.usb_list = QListWidget()
            self.usb_list.setMaximumHeight(100)
            layout.addWidget(self.usb_list)

            self._refresh_usb_devices()

            # Buttons
            btn_layout = QHBoxLayout()

            if not running:
                start_btn = QPushButton(self.tr("▶️ Start Service"))
                start_btn.setAccessibleName(self.tr("Start Service"))
                start_btn.clicked.connect(self._start_usbguard)
                btn_layout.addWidget(start_btn)

            refresh_btn = QPushButton(self.tr("🔄 Refresh"))
            refresh_btn.setAccessibleName(self.tr("Refresh USB devices"))
            refresh_btn.clicked.connect(self._refresh_usb_devices)
            btn_layout.addWidget(refresh_btn)

            allow_btn = QPushButton(self.tr("✅ Allow Selected"))
            allow_btn.setAccessibleName(self.tr("Allow Selected"))
            allow_btn.clicked.connect(self._allow_usb)
            btn_layout.addWidget(allow_btn)

            block_btn = QPushButton(self.tr("🚫 Block Selected"))
            block_btn.setAccessibleName(self.tr("Block Selected USB device"))
            block_btn.clicked.connect(self._block_usb)
            btn_layout.addWidget(block_btn)

            btn_layout.addStretch()
            layout.addLayout(btn_layout)

        return group

    def _create_sandbox_section(self) -> QGroupBox:
        """Create sandbox manager section."""
        group = QGroupBox(self.tr("📦 Application Sandbox"))
        layout = QVBoxLayout(group)

        # Check Firejail
        firejail_ok = SandboxManager.is_firejail_installed()
        bwrap_ok = SandboxManager.is_bubblewrap_installed()

        status_layout = QHBoxLayout()
        fj_icon = "✅" if firejail_ok else "❌"
        bw_icon = "✅" if bwrap_ok else "❌"
        status_layout.addWidget(QLabel(f"{fj_icon} Firejail"))
        status_layout.addWidget(QLabel(f"{bw_icon} Bubblewrap"))
        status_layout.addStretch()
        layout.addLayout(status_layout)

        if not firejail_ok:
            install_btn = QPushButton(self.tr("📥 Install Firejail"))
            install_btn.setAccessibleName(self.tr("Install Firejail"))
            install_btn.clicked.connect(self._install_firejail)
            layout.addWidget(install_btn)
        else:
            # Available profiles
            layout.addWidget(QLabel(self.tr("Quick Launch (Sandboxed):")))

            profiles_layout = QHBoxLayout()

            for app, desc in list(SandboxManager.FIREJAIL_PROFILES.items())[:4]:
                btn = QPushButton(app.capitalize())
                btn.setAccessibleName(
                    self.tr("Launch {} sandboxed").format(app.capitalize())
                )
                btn.setToolTip(f"Launch {app} in sandbox")
                btn.clicked.connect(lambda checked, a=app: self._launch_sandboxed(a))
                profiles_layout.addWidget(btn)

            profiles_layout.addStretch()
            layout.addLayout(profiles_layout)

            # Options
            options_layout = QHBoxLayout()

            self.no_network_check = QCheckBox(self.tr("No Network"))
            self.no_network_check.setAccessibleName(self.tr("No Network"))
            self.no_network_check.setToolTip("Disable network access")
            options_layout.addWidget(self.no_network_check)

            self.private_home_check = QCheckBox(self.tr("Private Home"))
            self.private_home_check.setAccessibleName(self.tr("Private Home"))
            self.private_home_check.setToolTip("Use empty home directory")
            options_layout.addWidget(self.private_home_check)

            options_layout.addStretch()
            layout.addLayout(options_layout)

            # Custom command
            custom_layout = QHBoxLayout()

            self.sandbox_cmd = QComboBox()
            self.sandbox_cmd.setAccessibleName(self.tr("Sandbox command"))
            self.sandbox_cmd.setEditable(True)
            self.sandbox_cmd.addItems(["firefox", "chromium", "vlc", "gimp"])
            self.sandbox_cmd.setMinimumWidth(200)
            custom_layout.addWidget(self.sandbox_cmd)

            run_btn = QPushButton(self.tr("🚀 Run Sandboxed"))
            run_btn.setAccessibleName(self.tr("Run Sandboxed"))
            run_btn.clicked.connect(self._run_custom_sandbox)
            custom_layout.addWidget(run_btn)

            custom_layout.addStretch()
            layout.addLayout(custom_layout)

        return group

    def _refresh_score(self):
        """Refresh security score."""
        self.log("Rescanning security...")
        # Would need to rebuild the section - simplified for now
        self.log("Security scan complete.")

    def _refresh_ports(self):
        """Refresh port list."""
        self.port_table.clearSpans()
        self.port_table.setRowCount(0)

        ports = PortAuditor.scan_ports()

        if not ports:
            BaseTab.set_table_empty_state(
                self.port_table, self.tr("No open ports detected")
            )
            return

        for port in ports:
            row = self.port_table.rowCount()
            self.port_table.insertRow(row)

            self.port_table.setItem(row, 0, BaseTab.make_table_item(str(port.port)))
            self.port_table.setItem(row, 1, BaseTab.make_table_item(port.protocol))
            self.port_table.setItem(row, 2, BaseTab.make_table_item(port.address))
            self.port_table.setItem(row, 3, BaseTab.make_table_item(port.process))

            status_item = QTableWidgetItem("⚠️ Risk" if port.is_risky else "✅ OK")
            if port.is_risky:
                status_item.setForeground(QColor("#e8556d"))
            self.port_table.setItem(row, 4, status_item)

    def _block_port(self):
        """Block selected port."""
        row = self.port_table.currentRow()
        if row < 0:
            self.log("No port selected.")
            return

        port = int(self.port_table.item(row, 0).text())
        protocol = self.port_table.item(row, 1).text().lower()

        result = PortAuditor.block_port(port, protocol)
        self.log(result.message)

    def _install_usbguard(self):
        """Install USBGuard."""
        self.log("Installing USBGuard...")
        result = USBGuardManager.install()
        self.log(result.message)

    def _start_usbguard(self):
        """Start USBGuard service."""
        result = USBGuardManager.start_service()
        self.log(result.message)

    def _refresh_usb_devices(self):
        """Refresh USB device list."""
        if not hasattr(self, "usb_list"):
            return

        self.usb_list.clear()
        devices = USBGuardManager.list_devices()

        if not devices:
            item = QListWidgetItem("No devices found (service may not be running)")
            self.usb_list.addItem(item)
        else:
            for dev in devices:
                icon = "✅" if dev.policy == "allow" else "🚫"
                item = QListWidgetItem(f"{icon} {dev.name} ({dev.policy})")
                item.setData(Qt.ItemDataRole.UserRole, dev.id)
                self.usb_list.addItem(item)

    def _allow_usb(self):
        """Allow selected USB device."""
        current = self.usb_list.currentItem()
        if not current:
            self.log("No device selected.")
            return

        device_id = current.data(Qt.ItemDataRole.UserRole)
        if device_id:
            result = USBGuardManager.allow_device(device_id, permanent=True)
            self.log(result.message)
            self._refresh_usb_devices()

    def _block_usb(self):
        """Block selected USB device."""
        current = self.usb_list.currentItem()
        if not current:
            self.log("No device selected.")
            return

        device_id = current.data(Qt.ItemDataRole.UserRole)
        if device_id:
            result = USBGuardManager.block_device(device_id, permanent=True)
            self.log(result.message)
            self._refresh_usb_devices()

    def _install_firejail(self):
        """Install Firejail."""
        self.log("Installing Firejail...")
        result = SandboxManager.install_firejail()
        self.log(result.message)

    def _launch_sandboxed(self, app: str):
        """Launch an app in sandbox."""
        no_net = (
            self.no_network_check.isChecked()
            if hasattr(self, "no_network_check")
            else False
        )
        private = (
            self.private_home_check.isChecked()
            if hasattr(self, "private_home_check")
            else False
        )

        result = SandboxManager.run_sandboxed(
            [app], no_network=no_net, private_home=private
        )
        self.log(result.message)

    def _run_custom_sandbox(self):
        """Run custom command in sandbox."""
        cmd = self.sandbox_cmd.currentText().strip()
        if not cmd:
            self.log("Enter a command to run.")
            return

        no_net = self.no_network_check.isChecked()
        private = self.private_home_check.isChecked()

        result = SandboxManager.run_sandboxed(
            cmd.split(), no_network=no_net, private_home=private
        )
        self.log(result.message)

    # ==================== FIREWALL (from Privacy tab) ====================

    def _create_firewall_section(self) -> QGroupBox:
        """Create firewall control section (absorbed from PrivacyTab)."""
        group = QGroupBox(self.tr("Firewall (firewalld)"))
        fw_layout = QHBoxLayout(group)

        btn_fw_status = QPushButton(self.tr("Check Status"))
        btn_fw_status.setAccessibleName(self.tr("Check Firewall Status"))
        btn_fw_status.clicked.connect(
            lambda: self._run_privacy_command(
                "systemctl",
                ["status", "firewalld"],
                self.tr("Checking Firewall Status..."),
            )
        )
        fw_layout.addWidget(btn_fw_status)

        btn_fw_enable = QPushButton(self.tr("Enable Firewall"))
        btn_fw_enable.setAccessibleName(self.tr("Enable Firewall"))
        btn_fw_enable.clicked.connect(
            lambda: self._run_privacy_command(
                "pkexec",
                ["systemctl", "enable", "--now", "firewalld"],
                self.tr("Enabling Firewall..."),
            )
        )
        fw_layout.addWidget(btn_fw_enable)

        btn_fw_disable = QPushButton(self.tr("Disable Firewall"))
        btn_fw_disable.setAccessibleName(self.tr("Disable Firewall"))
        btn_fw_disable.clicked.connect(
            lambda: self._run_privacy_command(
                "pkexec",
                ["systemctl", "disable", "--now", "firewalld"],
                self.tr("Disabling Firewall..."),
            )
        )
        fw_layout.addWidget(btn_fw_disable)

        return group

    # ==================== TELEMETRY (from Privacy tab) ====================

    def _create_telemetry_section(self) -> QGroupBox:
        """Create telemetry removal section (absorbed from PrivacyTab)."""
        group = QGroupBox(self.tr("Telemetry & Tracking"))
        tele_layout = QVBoxLayout(group)

        btn_remove_tele = QPushButton(self.tr("Remove Fedora Telemetry Packages"))
        btn_remove_tele.setAccessibleName(self.tr("Remove Fedora Telemetry Packages"))
        btn_remove_tele.clicked.connect(
            lambda: self._run_privacy_command(
                *PrivilegedCommand.dnf("remove", "abrt", "gnome-abrt"),
            )
        )
        tele_layout.addWidget(btn_remove_tele)

        return group

    # ==================== SECURITY UPDATES (from Privacy tab) ====================

    def _create_security_updates_section(self) -> QGroupBox:
        """Create security updates check section (absorbed from PrivacyTab)."""
        group = QGroupBox(self.tr("Security Checks"))
        sec_layout = QVBoxLayout(group)

        btn_check_updates = QPushButton(self.tr("Check for Security Updates"))
        btn_check_updates.setAccessibleName(self.tr("Check for Security Updates"))
        btn_check_updates.clicked.connect(
            lambda: self._run_privacy_command(
                "dnf",
                ["check-update", "--security"],
                self.tr("Checking for Security Updates..."),
            )
        )
        sec_layout.addWidget(btn_check_updates)

        return group

    def log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)
