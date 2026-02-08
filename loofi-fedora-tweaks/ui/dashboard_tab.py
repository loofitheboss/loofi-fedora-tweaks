from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon
import shutil
import subprocess
from utils.system import SystemManager
from utils.disk import DiskManager
from utils.monitor import SystemMonitor

class DashboardTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # Welcome Header
        header = QLabel(self.tr("Welcome back, Loofi! 👋"))
        header.setObjectName("header") # Styled in modern.qss
        layout.addWidget(header)
        
        # System Health Card
        health_card = self.create_card(self.tr("System Health"))
        h_layout = QHBoxLayout()
        health_card.setLayout(h_layout)
        
        # Snapshot Status
        self.lbl_snapshot = QLabel(self.tr("🛡️ Snapshots: Checking..."))
        h_layout.addWidget(self.lbl_snapshot)
        
        # Update Status
        self.lbl_updates = QLabel(self.tr("📦 Updates: Checking..."))
        h_layout.addWidget(self.lbl_updates)
        
        # Disk Usage
        self.lbl_disk = QLabel(self.tr("💿 Disk: Checking..."))
        h_layout.addWidget(self.lbl_disk)
        
        # Memory Usage
        self.lbl_memory = QLabel(self.tr("🧠 Memory: Checking..."))
        h_layout.addWidget(self.lbl_memory)

        # CPU Load
        self.lbl_cpu = QLabel(self.tr("🔥 CPU: Checking..."))
        h_layout.addWidget(self.lbl_cpu)
        
        # System Type (Atomic/Workstation)
        variant = SystemManager.get_variant_name()
        pkg_mgr = SystemManager.get_package_manager()
        self.lbl_system_type = QLabel(f"💻 {variant} ({pkg_mgr})")
        self.lbl_system_type.setStyleSheet("color: #89b4fa; font-weight: bold;")
        h_layout.addWidget(self.lbl_system_type)
        
        layout.addWidget(health_card)
        
        # Pending Reboot Warning (Atomic only)
        self.reboot_banner = QFrame()
        self.reboot_banner.setStyleSheet("""
            QFrame {
                background-color: #f9e2af;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        reboot_layout = QHBoxLayout(self.reboot_banner)
        reboot_label = QLabel(self.tr("⚠️ Pending changes require reboot!"))
        reboot_label.setStyleSheet("color: #1e1e2e; font-weight: bold;")
        reboot_layout.addWidget(reboot_label)
        reboot_layout.addStretch()
        reboot_btn = QPushButton(self.tr("🔁 Reboot Now"))
        reboot_btn.setStyleSheet("background-color: #1e1e2e; color: #f9e2af; padding: 5px 10px; border-radius: 5px;")
        reboot_btn.clicked.connect(self.reboot_system)
        reboot_layout.addWidget(reboot_btn)
        layout.addWidget(self.reboot_banner)
        self.reboot_banner.setVisible(SystemManager.has_pending_deployment())
        
        # Quick Actions Grid
        actions_label = QLabel(self.tr("Quick Actions"))
        actions_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(actions_label)

        grid = QGridLayout()
        grid.setSpacing(15)
        
        self.btn_clean = self.create_action_button(self.tr("Clean Cache"), "🧹", "#f9e2af", self.go_to_cleanup)
        grid.addWidget(self.btn_clean, 0, 0)
        
        self.btn_update = self.create_action_button(self.tr("Update All"), "🔄", "#89b4fa", self.go_to_updates)
        grid.addWidget(self.btn_update, 0, 1)
        
        self.btn_profile = self.create_action_button(self.tr("Power Profile"), "🔋", "#a6e3a1", self.toggle_power_profile)
        grid.addWidget(self.btn_profile, 1, 0)
        
        self.btn_gaming = self.create_action_button(self.tr("Gaming Mode"), "🎮", "#f38ba8", self.go_to_gaming)
        grid.addWidget(self.btn_gaming, 1, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        # Start initial checks
        self.check_status()

        # Auto-refresh health metrics every 5 seconds
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_status)
        self.refresh_timer.start(5000)

    def create_card(self, title):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        return card

    def create_action_button(self, text, icon, color, callback):
        btn = QPushButton(f"{icon}  {text}")
        # Custom styling for big dashboard buttons
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e2e;
                border: 2px solid {color};
                color: {color};
                border-radius: 12px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: #1e1e2e;
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    def check_status(self):
        # Check Timeshift
        if shutil.which("timeshift"):
            self.lbl_snapshot.setText(self.tr("🛡️ Snapshots: Ready"))
            self.lbl_snapshot.setStyleSheet("color: #a6e3a1;") # Green
        else:
            self.lbl_snapshot.setText(self.tr("🛡️ Snapshots: Missing!"))
            self.lbl_snapshot.setStyleSheet("color: #f38ba8;") # Red

        # Simple updates check (just existence of dnf)
        self.lbl_updates.setText(self.tr("📦 Updates: Idle"))
        
        # Disk usage check
        disk_level, disk_msg = DiskManager.check_disk_health("/")
        if disk_level == "critical":
            self.lbl_disk.setText(self.tr("💿 Disk: Critical!"))
            self.lbl_disk.setStyleSheet("color: #f38ba8; font-weight: bold;")
        elif disk_level == "warning":
            self.lbl_disk.setText(self.tr("💿 Disk: Low Space"))
            self.lbl_disk.setStyleSheet("color: #f9e2af; font-weight: bold;")
        else:
            usage = DiskManager.get_disk_usage("/")
            if usage:
                self.lbl_disk.setText(f"💿 {usage.free_human} free")
            else:
                self.lbl_disk.setText(self.tr("💿 Disk: OK"))
            self.lbl_disk.setStyleSheet("color: #a6e3a1;")
        self.lbl_disk.setToolTip(disk_msg)
        
        # Memory usage check
        mem = SystemMonitor.get_memory_info()
        if mem:
            if mem.percent_used >= 90:
                self.lbl_memory.setText(f"🧠 RAM: {mem.percent_used}%")
                self.lbl_memory.setStyleSheet("color: #f38ba8; font-weight: bold;")
            elif mem.percent_used >= 75:
                self.lbl_memory.setText(f"🧠 RAM: {mem.percent_used}%")
                self.lbl_memory.setStyleSheet("color: #f9e2af; font-weight: bold;")
            else:
                self.lbl_memory.setText(f"🧠 RAM: {mem.used_human}/{mem.total_human}")
                self.lbl_memory.setStyleSheet("color: #a6e3a1;")
            self.lbl_memory.setToolTip(
                f"Used: {mem.used_human} / Total: {mem.total_human} ({mem.percent_used}%)"
            )
        else:
            self.lbl_memory.setText(self.tr("🧠 Memory: N/A"))
            self.lbl_memory.setStyleSheet("color: #6c7086;")

        # CPU load check
        cpu = SystemMonitor.get_cpu_info()
        if cpu:
            if cpu.load_percent >= 90:
                self.lbl_cpu.setText(f"🔥 CPU: {cpu.load_percent}%")
                self.lbl_cpu.setStyleSheet("color: #f38ba8; font-weight: bold;")
            elif cpu.load_percent >= 60:
                self.lbl_cpu.setText(f"🔥 CPU: {cpu.load_percent}%")
                self.lbl_cpu.setStyleSheet("color: #f9e2af; font-weight: bold;")
            else:
                self.lbl_cpu.setText(f"🔥 CPU: {cpu.load_1min}")
                self.lbl_cpu.setStyleSheet("color: #a6e3a1;")
            self.lbl_cpu.setToolTip(
                f"Load: {cpu.load_1min}/{cpu.load_5min}/{cpu.load_15min} ({cpu.core_count} cores)"
            )
        else:
            self.lbl_cpu.setText(self.tr("🔥 CPU: N/A"))
            self.lbl_cpu.setStyleSheet("color: #6c7086;")
        
    def go_to_cleanup(self):
        if hasattr(self.main_window, "switch_to_tab"):
            self.main_window.switch_to_tab("Maintenance")

    def go_to_updates(self):
        if hasattr(self.main_window, "switch_to_tab"):
            self.main_window.switch_to_tab("Maintenance")

    def go_to_gaming(self):
        if hasattr(self.main_window, "switch_to_tab"):
            self.main_window.switch_to_tab("Gaming")

    def toggle_power_profile(self):
        if hasattr(self.main_window, "switch_to_tab"):
            self.main_window.switch_to_tab("Hardware")
    
    def reboot_system(self):
        """Reboot the system to apply pending changes."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, self.tr("Reboot Now?"),
            self.tr("Reboot now to apply pending changes?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            subprocess.run(["systemctl", "reboot"])
