"""
Overlays Tab - Manage rpm-ostree layered packages.
Only visible on Fedora Atomic systems (Silverblue, Kinoite, etc.)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QMessageBox, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt
from utils.system import SystemManager
from utils.package_manager import PackageManager


class OverlaysTab(QWidget):
    """Tab for managing rpm-ostree layered packages."""
    
    def __init__(self):
        super().__init__()
        self.pkg_manager = PackageManager()
        self.init_ui()
        self.refresh_list()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # Header
        header = QLabel(self.tr("System Overlays (rpm-ostree)"))
        header.setObjectName("header")
        layout.addWidget(header)
        
        # Info Card
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        variant = SystemManager.get_variant_name()
        info_label = QLabel(self.tr("📦 System: Fedora {} (Immutable)").format(variant))
        info_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        info_layout.addWidget(info_label)
        
        desc_label = QLabel(self.tr(
            "Layered packages are RPMs installed on top of the base OS image.\n"
            "Changes require a reboot to fully apply."
        ))
        desc_label.setStyleSheet("color: #a6adc8;")
        info_layout.addWidget(desc_label)
        
        # Pending Reboot Warning
        self.reboot_warning = QLabel(self.tr("⚠️ Pending changes require reboot!"))
        self.reboot_warning.setStyleSheet("color: #f9e2af; font-weight: bold;")
        self.reboot_warning.setVisible(False)
        info_layout.addWidget(self.reboot_warning)
        
        layout.addWidget(info_frame)
        
        # Layered Packages List
        packages_group = QGroupBox(self.tr("Layered Packages"))
        packages_layout = QVBoxLayout(packages_group)
        
        self.packages_list = QListWidget()
        self.packages_list.setMinimumHeight(200)
        packages_layout.addWidget(self.packages_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton(self.tr("🔄 Refresh"))
        self.btn_refresh.clicked.connect(self.refresh_list)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_remove = QPushButton(self.tr("➖ Remove Selected"))
        self.btn_remove.setObjectName("dangerAction")
        self.btn_remove.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.btn_remove)
        
        btn_layout.addStretch()
        
        self.btn_reset = QPushButton(self.tr("🗑️ Reset to Base Image"))
        self.btn_reset.setObjectName("dangerAction")
        self.btn_reset.clicked.connect(self.reset_to_base)
        btn_layout.addWidget(self.btn_reset)
        
        packages_layout.addLayout(btn_layout)
        layout.addWidget(packages_group)
        
        # Reboot Button
        self.btn_reboot = QPushButton(self.tr("🔁 Reboot to Apply Changes"))
        self.btn_reboot.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
        """)
        self.btn_reboot.clicked.connect(self.reboot_system)
        self.btn_reboot.setVisible(False)
        layout.addWidget(self.btn_reboot)
        
        layout.addStretch()
    
    def refresh_list(self):
        """Refresh the list of layered packages."""
        self.packages_list.clear()
        
        packages = SystemManager.get_layered_packages()
        
        if packages:
            for pkg in packages:
                item = QListWidgetItem(f"📦 {pkg}")
                self.packages_list.addItem(item)
        else:
            item = QListWidgetItem(self.tr("No layered packages (clean base image)"))
            item.setForeground(Qt.GlobalColor.darkGray)
            self.packages_list.addItem(item)
        
        # Check for pending reboot
        has_pending = SystemManager.has_pending_deployment()
        self.reboot_warning.setVisible(has_pending)
        self.btn_reboot.setVisible(has_pending)
    
    def remove_selected(self):
        """Remove the selected layered package."""
        selected = self.packages_list.currentItem()
        if not selected:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a package to remove."))
            return
        
        # Extract package name (remove emoji prefix)
        pkg_name = selected.text().replace("📦 ", "").strip()
        
        if "No layered" in pkg_name:
            return
        
        reply = QMessageBox.question(
            self, self.tr("Confirm Removal"),
            self.tr("Remove '{}' from system overlays?\n\nThis requires a reboot.").format(pkg_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self.pkg_manager.remove([pkg_name])
            if result.success:
                QMessageBox.information(self, self.tr("Success"), result.message)
                self.refresh_list()
            else:
                QMessageBox.critical(self, self.tr("Error"), result.message)
    
    def reset_to_base(self):
        """Reset to base image, removing all layered packages."""
        reply = QMessageBox.warning(
            self, self.tr("⚠️ Reset to Base Image"),
            self.tr("This will REMOVE ALL layered packages and reset to the clean base image.\n\n"
            "Are you absolutely sure?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self.pkg_manager.reset_to_base()
            if result.success:
                QMessageBox.information(
                    self, self.tr("Reset Complete"),
                    self.tr("System reset to base image.\n\nPlease reboot to apply changes.")
                )
                self.refresh_list()
            else:
                QMessageBox.critical(self, self.tr("Error"), result.message)
    
    def reboot_system(self):
        """Offer to reboot the system."""
        reply = QMessageBox.question(
            self, self.tr("Reboot Now?"),
            self.tr("Reboot now to apply pending changes?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess
            subprocess.run(["systemctl", "reboot"])
