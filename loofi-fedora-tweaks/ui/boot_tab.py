"""
Boot Tab - Kernel parameters, ZRAM, and Secure Boot management.
Part of v6.2 "Engine Room" update.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QComboBox, QSlider, QLineEdit, QTextEdit,
    QCheckBox, QScrollArea, QFrame, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt

from utils.kernel import KernelManager
from utils.zram import ZramManager
from utils.secureboot import SecureBootManager


class BootTab(QWidget):
    """Boot management tab with kernel, ZRAM, and Secure Boot controls."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh_all()
    
    def init_ui(self):
        """Initialize the UI components."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # Kernel Parameters Section
        layout.addWidget(self.create_kernel_section())
        
        # ZRAM Section
        layout.addWidget(self.create_zram_section())
        
        # Secure Boot Section
        layout.addWidget(self.create_secureboot_section())
        
        # Output Log
        output_group = QGroupBox(self.tr("Output Log:"))
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)
        output_layout.addWidget(self.output_text)
        layout.addWidget(output_group)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def create_kernel_section(self) -> QGroupBox:
        """Create the kernel parameters section."""
        group = QGroupBox(self.tr("⚙️ Kernel Parameters"))
        layout = QVBoxLayout(group)
        
        # Current parameters display
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel(self.tr("Current cmdline:")))
        self.current_params_label = QLabel()
        self.current_params_label.setWordWrap(True)
        self.current_params_label.setStyleSheet("color: #888; font-size: 11px;")
        current_layout.addWidget(self.current_params_label, 1)
        layout.addLayout(current_layout)
        
        # Common parameters checkboxes
        params_group = QGroupBox(self.tr("Quick Add Parameters"))
        params_layout = QVBoxLayout(params_group)
        
        self.param_checkboxes = {}
        common_params = [
            ("amdgpu.ppfeaturemask=0xffffffff", self.tr("AMD GPU: Enable all power features")),
            ("intel_iommu=on", self.tr("Intel IOMMU: GPU passthrough support")),
            ("nvidia-drm.modeset=1", self.tr("NVIDIA: Kernel modesetting")),
            ("mitigations=off", self.tr("⚠️ Disable CPU mitigations (unsafe but faster)")),
            ("nowatchdog", self.tr("Disable watchdog (reduce interrupts)")),
        ]
        
        for param, desc in common_params:
            cb = QCheckBox(desc)
            cb.setProperty("param", param)
            cb.stateChanged.connect(lambda state, p=param: self.on_param_toggled(p, state))
            self.param_checkboxes[param] = cb
            params_layout.addWidget(cb)
        
        layout.addWidget(params_group)
        
        # Custom parameter input
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel(self.tr("Custom:")))
        self.custom_param_input = QLineEdit()
        self.custom_param_input.setPlaceholderText("e.g., mem=4G")
        custom_layout.addWidget(self.custom_param_input)
        
        add_btn = QPushButton(self.tr("Add"))
        add_btn.clicked.connect(self.add_custom_param)
        custom_layout.addWidget(add_btn)
        
        remove_btn = QPushButton(self.tr("Remove"))
        remove_btn.clicked.connect(self.remove_custom_param)
        custom_layout.addWidget(remove_btn)
        
        layout.addLayout(custom_layout)
        
        # Backup/Restore
        backup_layout = QHBoxLayout()
        backup_btn = QPushButton(self.tr("📦 Backup GRUB"))
        backup_btn.clicked.connect(self.backup_grub)
        backup_layout.addWidget(backup_btn)
        
        restore_btn = QPushButton(self.tr("♻️ Restore Backup"))
        restore_btn.clicked.connect(self.restore_grub)
        backup_layout.addWidget(restore_btn)
        
        backup_layout.addStretch()
        layout.addLayout(backup_layout)
        
        return group
    
    def create_zram_section(self) -> QGroupBox:
        """Create the ZRAM configuration section."""
        group = QGroupBox(self.tr("💾 ZRAM (Compressed Swap)"))
        layout = QVBoxLayout(group)
        
        # Status
        status_layout = QHBoxLayout()
        self.zram_status_label = QLabel()
        status_layout.addWidget(self.zram_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Size slider
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel(self.tr("Size (% of RAM):")))
        
        self.zram_slider = QSlider(Qt.Orientation.Horizontal)
        self.zram_slider.setMinimum(25)
        self.zram_slider.setMaximum(150)
        self.zram_slider.setValue(100)
        self.zram_slider.setTickInterval(25)
        self.zram_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zram_slider.valueChanged.connect(self.on_zram_slider_changed)
        size_layout.addWidget(self.zram_slider)
        
        self.zram_size_label = QLabel("100%")
        self.zram_size_label.setMinimumWidth(50)
        size_layout.addWidget(self.zram_size_label)
        
        layout.addLayout(size_layout)
        
        # Algorithm
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel(self.tr("Compression:")))
        
        self.zram_algo_combo = QComboBox()
        for algo, desc in ZramManager.ALGORITHMS.items():
            self.zram_algo_combo.addItem(f"{algo} - {desc}", algo)
        algo_layout.addWidget(self.zram_algo_combo, 1)
        
        layout.addLayout(algo_layout)
        
        # Apply button
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton(self.tr("✅ Apply ZRAM Settings"))
        apply_btn.clicked.connect(self.apply_zram)
        btn_layout.addWidget(apply_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def create_secureboot_section(self) -> QGroupBox:
        """Create the Secure Boot section."""
        group = QGroupBox(self.tr("🔐 Secure Boot (MOK Management)"))
        layout = QVBoxLayout(group)
        
        # Status
        self.sb_status_label = QLabel()
        layout.addWidget(self.sb_status_label)
        
        # Key status
        self.mok_status_label = QLabel()
        layout.addWidget(self.mok_status_label)
        
        # Actions
        btn_layout = QHBoxLayout()
        
        generate_btn = QPushButton(self.tr("🔑 Generate MOK Key"))
        generate_btn.clicked.connect(self.generate_mok_key)
        btn_layout.addWidget(generate_btn)
        
        enroll_btn = QPushButton(self.tr("📝 Enroll Key"))
        enroll_btn.clicked.connect(self.enroll_mok_key)
        btn_layout.addWidget(enroll_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Help text
        help_label = QLabel(self.tr(
            "ℹ️ MOK keys are needed to sign third-party kernel modules "
            "(NVIDIA, VirtualBox) when Secure Boot is enabled."
        ))
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(help_label)
        
        return group
    
    def refresh_all(self):
        """Refresh all sections with current data."""
        self.refresh_kernel()
        self.refresh_zram()
        self.refresh_secureboot()
    
    def refresh_kernel(self):
        """Refresh kernel parameters display."""
        current = KernelManager.get_current_params()
        self.current_params_label.setText(" ".join(current[:10]) + ("..." if len(current) > 10 else ""))
        
        # Update checkboxes
        for param, cb in self.param_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(KernelManager.has_param(param))
            cb.blockSignals(False)
    
    def refresh_zram(self):
        """Refresh ZRAM status."""
        config = ZramManager.get_current_config()
        usage = ZramManager.get_current_usage()
        
        status_parts = []
        if config.enabled:
            status_parts.append(f"✅ {self.tr('Active')}")
            if usage:
                status_parts.append(f"{usage[0]}MB / {usage[1]}MB")
        else:
            status_parts.append(f"⚪ {self.tr('Inactive')}")
        
        status_parts.append(f"{config.size_percent}% RAM ({config.size_mb}MB)")
        status_parts.append(f"{config.algorithm}")
        
        self.zram_status_label.setText(" | ".join(status_parts))
        
        self.zram_slider.blockSignals(True)
        self.zram_slider.setValue(config.size_percent)
        self.zram_slider.blockSignals(False)
        self.zram_size_label.setText(f"{config.size_percent}%")
        
        # Set algorithm combobox
        idx = self.zram_algo_combo.findData(config.algorithm)
        if idx >= 0:
            self.zram_algo_combo.setCurrentIndex(idx)
    
    def refresh_secureboot(self):
        """Refresh Secure Boot status."""
        status = SecureBootManager.get_status()
        
        if status.secure_boot_enabled:
            self.sb_status_label.setText(f"🔒 {self.tr('Secure Boot: Enabled')}")
        else:
            self.sb_status_label.setText(f"🔓 {self.tr('Secure Boot: Disabled')}")
        
        if SecureBootManager.has_keys():
            self.mok_status_label.setText(f"🔑 {self.tr('MOK Key: Generated')}")
        else:
            self.mok_status_label.setText(f"⚪ {self.tr('MOK Key: Not generated')}")
        
        if status.pending_mok:
            self.mok_status_label.setText(self.mok_status_label.text() + f" ({self.tr('Pending enrollment')})")
    
    def log(self, message: str):
        """Add message to output log."""
        self.output_text.append(message)
    
    # Kernel actions
    def on_param_toggled(self, param: str, state: int):
        """Handle parameter checkbox toggle."""
        if state == Qt.CheckState.Checked.value:
            result = KernelManager.add_param(param)
        else:
            result = KernelManager.remove_param(param)
        
        self.log(result.message)
        if not result.success:
            self.refresh_kernel()  # Revert checkbox
    
    def add_custom_param(self):
        """Add a custom kernel parameter."""
        param = self.custom_param_input.text().strip()
        if param:
            result = KernelManager.add_param(param)
            self.log(result.message)
            self.custom_param_input.clear()
            self.refresh_kernel()
    
    def remove_custom_param(self):
        """Remove a custom kernel parameter."""
        param = self.custom_param_input.text().strip()
        if param:
            result = KernelManager.remove_param(param)
            self.log(result.message)
            self.custom_param_input.clear()
            self.refresh_kernel()
    
    def backup_grub(self):
        """Create GRUB backup."""
        result = KernelManager.backup_grub()
        self.log(result.message)
        if result.backup_path:
            self.log(f"Saved to: {result.backup_path}")
    
    def restore_grub(self):
        """Restore GRUB from backup."""
        backups = KernelManager.get_backups()
        if not backups:
            self.log(self.tr("No backups available."))
            return
        
        # Show backup selection
        items = [str(b.name) for b in backups[:10]]
        item, ok = QInputDialog.getItem(
            self, 
            self.tr("Select Backup"),
            self.tr("Choose a backup to restore:"),
            items, 0, False
        )
        
        if ok and item:
            backup_path = KernelManager.BACKUP_DIR / item
            result = KernelManager.restore_backup(str(backup_path))
            self.log(result.message)
    
    # ZRAM actions
    def on_zram_slider_changed(self, value: int):
        """Update ZRAM size label."""
        self.zram_size_label.setText(f"{value}%")
    
    def apply_zram(self):
        """Apply ZRAM settings."""
        size = self.zram_slider.value()
        algo = self.zram_algo_combo.currentData()
        
        result = ZramManager.set_config(size, algo)
        self.log(result.message)
        self.refresh_zram()
    
    # Secure Boot actions
    def generate_mok_key(self):
        """Generate new MOK signing key."""
        password, ok = QInputDialog.getText(
            self,
            self.tr("MOK Password"),
            self.tr("Enter a password (8+ chars) for the MOK key.\n"
                   "You'll need this during reboot enrollment:"),
            QLineEdit.EchoMode.Password
        )
        
        if ok and password:
            if len(password) < 8:
                self.log(self.tr("Password too short (minimum 8 characters)."))
                return
            
            result = SecureBootManager.generate_key(password)
            self.log(result.message)
            self.refresh_secureboot()
    
    def enroll_mok_key(self):
        """Enroll MOK key for Secure Boot."""
        if not SecureBootManager.has_keys():
            self.log(self.tr("No MOK key found. Generate one first."))
            return
        
        password, ok = QInputDialog.getText(
            self,
            self.tr("MOK Password"),
            self.tr("Enter your MOK password to queue enrollment:"),
            QLineEdit.EchoMode.Password
        )
        
        if ok and password:
            result = SecureBootManager.import_key(password)
            self.log(result.message)
            
            if result.requires_reboot:
                QMessageBox.information(
                    self,
                    self.tr("Reboot Required"),
                    self.tr("MOK enrollment queued.\n\n"
                           "On next reboot, follow the blue MOK Manager prompts "
                           "to complete enrollment.")
                )
            
            self.refresh_secureboot()
