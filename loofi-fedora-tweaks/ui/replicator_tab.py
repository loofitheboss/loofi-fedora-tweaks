"""
Replicator Tab - Infrastructure as Code exports.
Part of v8.0 "Replicator" update.

Allows users to export their system configuration as:
- Ansible playbooks for any Linux machine
- Kickstart files for automated Fedora installs
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QTextEdit, QScrollArea, QFrame, QCheckBox,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

from utils.ansible_export import AnsibleExporter
from utils.kickstart import KickstartGenerator


class ReplicatorTab(QWidget):
    """Export system configuration as Infrastructure as Code."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(self.tr("🔄 Replicator - Infrastructure as Code"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)
        
        info = QLabel(self.tr(
            "Export your system configuration to recreate it on any machine.\n"
            "No Loofi needed on the target - just standard tools."
        ))
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Ansible section
        layout.addWidget(self._create_ansible_section())
        
        # Kickstart section
        layout.addWidget(self._create_kickstart_section())
        
        # Output log
        log_group = QGroupBox(self.tr("Export Log:"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_ansible_section(self) -> QGroupBox:
        """Create Ansible export section."""
        group = QGroupBox(self.tr("📘 Ansible Playbook"))
        layout = QVBoxLayout(group)
        
        desc = QLabel(self.tr(
            "Generate a standard Ansible playbook that installs your packages, "
            "Flatpaks, and applies your settings on any Fedora/RHEL machine."
        ))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888;")
        layout.addWidget(desc)
        
        # Options
        opts_layout = QHBoxLayout()
        
        self.ansible_packages = QCheckBox(self.tr("📦 DNF Packages"))
        self.ansible_packages.setChecked(True)
        opts_layout.addWidget(self.ansible_packages)
        
        self.ansible_flatpaks = QCheckBox(self.tr("📱 Flatpak Apps"))
        self.ansible_flatpaks.setChecked(True)
        opts_layout.addWidget(self.ansible_flatpaks)
        
        self.ansible_settings = QCheckBox(self.tr("⚙️ GNOME Settings"))
        self.ansible_settings.setChecked(True)
        opts_layout.addWidget(self.ansible_settings)
        
        opts_layout.addStretch()
        layout.addLayout(opts_layout)
        
        # Preview / Export buttons
        btn_layout = QHBoxLayout()
        
        preview_btn = QPushButton(self.tr("👁️ Preview"))
        preview_btn.clicked.connect(self._preview_ansible)
        btn_layout.addWidget(preview_btn)
        
        export_btn = QPushButton(self.tr("💾 Export"))
        export_btn.setStyleSheet("background-color: #28a745; color: white;")
        export_btn.clicked.connect(self._export_ansible)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _create_kickstart_section(self) -> QGroupBox:
        """Create Kickstart export section."""
        group = QGroupBox(self.tr("🚀 Kickstart File"))
        layout = QVBoxLayout(group)
        
        desc = QLabel(self.tr(
            "Generate an Anaconda Kickstart file for automated Fedora installation. "
            "Use this with inst.ks= during installation."
        ))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888;")
        layout.addWidget(desc)
        
        # Options
        opts_layout = QHBoxLayout()
        
        self.ks_packages = QCheckBox(self.tr("📦 DNF Packages"))
        self.ks_packages.setChecked(True)
        opts_layout.addWidget(self.ks_packages)
        
        self.ks_flatpaks = QCheckBox(self.tr("📱 Flatpak Apps"))
        self.ks_flatpaks.setChecked(True)
        opts_layout.addWidget(self.ks_flatpaks)
        
        opts_layout.addStretch()
        layout.addLayout(opts_layout)
        
        # Preview / Export buttons
        btn_layout = QHBoxLayout()
        
        preview_btn = QPushButton(self.tr("👁️ Preview"))
        preview_btn.clicked.connect(self._preview_kickstart)
        btn_layout.addWidget(preview_btn)
        
        export_btn = QPushButton(self.tr("💾 Export"))
        export_btn.setStyleSheet("background-color: #28a745; color: white;")
        export_btn.clicked.connect(self._export_kickstart)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _preview_ansible(self):
        """Preview the generated Ansible playbook."""
        content = AnsibleExporter.generate_playbook(
            include_packages=self.ansible_packages.isChecked(),
            include_flatpaks=self.ansible_flatpaks.isChecked(),
            include_settings=self.ansible_settings.isChecked()
        )
        self.output_text.setText(content[:3000] + "\n\n... (truncated)")
        self.log(self.tr("Preview generated. Full content will be in exported file."))
    
    def _export_ansible(self):
        """Export Ansible playbook to file."""
        result = AnsibleExporter.save_playbook(
            include_packages=self.ansible_packages.isChecked(),
            include_flatpaks=self.ansible_flatpaks.isChecked(),
            include_settings=self.ansible_settings.isChecked()
        )
        
        self.log(result.message)
        
        if result.success:
            QMessageBox.information(
                self,
                self.tr("Ansible Playbook Exported"),
                self.tr(f"Playbook saved to:\n{result.data['path']}\n\n"
                       f"Run with:\n"
                       f"  cd ~/loofi-playbook\n"
                       f"  ansible-playbook site.yml --ask-become-pass")
            )
    
    def _preview_kickstart(self):
        """Preview the generated Kickstart file."""
        content = KickstartGenerator.generate_kickstart(
            include_packages=self.ks_packages.isChecked(),
            include_flatpaks=self.ks_flatpaks.isChecked()
        )
        self.output_text.setText(content[:3000] + "\n\n... (truncated)")
        self.log(self.tr("Preview generated. Full content will be in exported file."))
    
    def _export_kickstart(self):
        """Export Kickstart file."""
        result = KickstartGenerator.save_kickstart(
            include_packages=self.ks_packages.isChecked(),
            include_flatpaks=self.ks_flatpaks.isChecked()
        )
        
        self.log(result.message)
        
        if result.success:
            QMessageBox.information(
                self,
                self.tr("Kickstart File Exported"),
                self.tr(f"Kickstart saved to:\n{result.data['path']}\n\n"
                       f"Use during installation with:\n"
                       f"  inst.ks=file:///path/to/loofi.ks")
            )
    
    def log(self, message: str):
        """Add message to output log."""
        self.output_text.append(message)
