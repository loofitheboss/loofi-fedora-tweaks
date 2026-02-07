"""
Presets Tab - User presets and cloud sync functionality.
Now with community presets and export/import features.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QMessageBox, QInputDialog, QGroupBox,
    QTabWidget, QFileDialog, QDialog, QLineEdit, QFormLayout, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from utils.presets import PresetManager
from utils.config_manager import ConfigManager
from utils.cloud_sync import CloudSyncManager


class FetchPresetsThread(QThread):
    """Background thread for fetching community presets."""
    finished = pyqtSignal(bool, object)
    
    def run(self):
        success, result = CloudSyncManager.fetch_community_presets()
        self.finished.emit(success, result)


class PresetsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = PresetManager()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # Header
        header = QLabel(self.tr("💾 Presets & Sync"))
        header.setObjectName("header")
        layout.addWidget(header)
        
        # Tab widget for different sections
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1: Local Presets
        tabs.addTab(self.create_local_presets_tab(), self.tr("📁 My Presets"))
        
        # Tab 2: Community Presets
        tabs.addTab(self.create_community_tab(), self.tr("🌐 Community"))
        
        # Tab 3: Export/Import
        tabs.addTab(self.create_sync_tab(), self.tr("☁️ Backup & Sync"))
    
    # ==================== LOCAL PRESETS TAB ====================
    
    def create_local_presets_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel(self.tr("Save and restore your system configuration presets.")))
        
        # List Area
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_load = QPushButton(self.tr("▶️ Load Selected"))
        self.btn_load.clicked.connect(self.load_preset)
        
        self.btn_save = QPushButton(self.tr("💾 Save Current State"))
        self.btn_save.clicked.connect(self.save_preset)
        
        self.btn_delete = QPushButton(self.tr("🗑️ Delete Selected"))
        self.btn_delete.clicked.connect(self.delete_preset)
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
        
        layout.addLayout(btn_layout)
        
        self.refresh_list()
        return widget
    
    def refresh_list(self):
        self.list_widget.clear()
        presets = self.manager.list_presets()
        self.list_widget.addItems(presets)
    
    def save_preset(self):
        name, ok = QInputDialog.getText(self, self.tr("Save Preset"), self.tr("Enter preset name:"))
        if ok and name:
            if self.manager.save_preset(name):
                self.refresh_list()
                QMessageBox.information(self, self.tr("Success"), self.tr("Preset '{}' saved successfully.").format(name))
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to save preset."))
    
    def load_preset(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a preset first."))
            return
            
        name = item.text()
        data = self.manager.load_preset(name)
        if data:
            QMessageBox.information(self, self.tr("Success"), self.tr("Preset '{}' loaded.\nSettings applied.").format(name))
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to load preset '{}'.").format(name))
    
    def delete_preset(self):
        item = self.list_widget.currentItem()
        if not item:
            return
            
        name = item.text()
        confirm = QMessageBox.question(self, self.tr("Confirm Delete"), self.tr("Delete preset '{}'?").format(name))
        if confirm == QMessageBox.StandardButton.Yes:
            if self.manager.delete_preset(name):
                self.refresh_list()
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to delete preset."))
    
    # ==================== COMMUNITY PRESETS TAB ====================
    
    def create_community_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel(self.tr("Browse and download presets shared by the community.")))
        
        # Community presets list
        self.community_list = QListWidget()
        layout.addWidget(self.community_list)
        
        # Status label
        self.lbl_community_status = QLabel(self.tr("Click 'Refresh' to load community presets."))
        self.lbl_community_status.setStyleSheet("color: #6c7086;")
        layout.addWidget(self.lbl_community_status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_refresh = QPushButton(self.tr("🔄 Refresh"))
        btn_refresh.clicked.connect(self.refresh_community_presets)
        
        btn_download = QPushButton(self.tr("⬇️ Download Selected"))
        btn_download.clicked.connect(self.download_community_preset)
        
        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_download)
        layout.addLayout(btn_layout)
        
        return widget
    
    def refresh_community_presets(self):
        self.lbl_community_status.setText(self.tr("⏳ Fetching presets..."))
        self.community_list.clear()
        
        # Run in background thread
        self.fetch_thread = FetchPresetsThread()
        self.fetch_thread.finished.connect(self.on_presets_fetched)
        self.fetch_thread.start()
    
    def on_presets_fetched(self, success: bool, result):
        if success:
            presets = result
            if not presets:
                self.lbl_community_status.setText(self.tr("ℹ️ No community presets available yet."))
            else:
                self.lbl_community_status.setText(self.tr("✅ Found {} presets").format(len(presets)))
                for preset in presets:
                    item = QListWidgetItem(self.tr("📦 {} - by {}").format(preset.get('name', 'Unknown'), preset.get('author', 'anonymous')))
                    item.setData(Qt.ItemDataRole.UserRole, preset)
                    self.community_list.addItem(item)
        else:
            self.lbl_community_status.setText(self.tr("❌ {}").format(result))
    
    def download_community_preset(self):
        item = self.community_list.currentItem()
        if not item:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a preset first."))
            return
        
        preset = item.data(Qt.ItemDataRole.UserRole)
        preset_id = preset.get("id")
        
        if not preset_id:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Invalid preset data."))
            return
        
        success, result = CloudSyncManager.download_preset(preset_id)
        if success:
            # Save to local presets
            self.manager.save_preset_data(preset.get("name", preset_id), result.get("settings", {}))
            self.refresh_list()
            QMessageBox.information(self, self.tr("Success"), self.tr("Preset '{}' downloaded and saved!").format(preset.get('name')))
        else:
            QMessageBox.warning(self, self.tr("Download Failed"), result)
    
    # ==================== BACKUP & SYNC TAB ====================
    
    def create_sync_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Export/Import Section
        export_group = QGroupBox(self.tr("📤 Export / Import"))
        export_layout = QVBoxLayout(export_group)
        
        export_layout.addWidget(QLabel(self.tr("Backup all your settings to a file, or restore from a backup.")))
        
        btn_row = QHBoxLayout()
        
        btn_export = QPushButton(self.tr("📥 Export to File"))
        btn_export.clicked.connect(self.export_config)
        btn_row.addWidget(btn_export)
        
        btn_import = QPushButton(self.tr("📤 Import from File"))
        btn_import.clicked.connect(self.import_config)
        btn_row.addWidget(btn_import)
        
        export_layout.addLayout(btn_row)
        layout.addWidget(export_group)
        
        # Cloud Sync Section
        cloud_group = QGroupBox(self.tr("☁️ GitHub Gist Sync"))
        cloud_layout = QVBoxLayout(cloud_group)
        
        cloud_layout.addWidget(QLabel(self.tr("Sync your config to a private GitHub Gist for cross-machine access.")))
        
        # Token status
        token = CloudSyncManager.get_gist_token()
        gist_id = CloudSyncManager.get_gist_id()
        
        self.lbl_sync_status = QLabel()
        self.update_sync_status()
        cloud_layout.addWidget(self.lbl_sync_status)
        
        # Token input
        token_row = QHBoxLayout()
        token_row.addWidget(QLabel(self.tr("GitHub Token:")))
        
        self.txt_token = QLineEdit()
        self.txt_token.setPlaceholderText("ghp_xxxxxxxxxxxx...")
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        if token:
            self.txt_token.setText("••••••••••••••••")
        token_row.addWidget(self.txt_token)
        
        btn_save_token = QPushButton(self.tr("Save"))
        btn_save_token.clicked.connect(self.save_token)
        token_row.addWidget(btn_save_token)
        
        cloud_layout.addLayout(token_row)
        
        # Sync buttons
        sync_row = QHBoxLayout()
        
        btn_push = QPushButton(self.tr("⬆️ Push to Gist"))
        btn_push.clicked.connect(self.push_to_gist)
        sync_row.addWidget(btn_push)
        
        btn_pull = QPushButton(self.tr("⬇️ Pull from Gist"))
        btn_pull.clicked.connect(self.pull_from_gist)
        sync_row.addWidget(btn_pull)
        
        cloud_layout.addLayout(sync_row)
        layout.addWidget(cloud_group)
        
        layout.addStretch()
        return widget
    
    def update_sync_status(self):
        token = CloudSyncManager.get_gist_token()
        gist_id = CloudSyncManager.get_gist_id()
        
        if token and gist_id:
            self.lbl_sync_status.setText(self.tr("✅ Connected | Gist ID: {}...").format(gist_id[:8]))
            self.lbl_sync_status.setStyleSheet("color: #a6e3a1;")
        elif token:
            self.lbl_sync_status.setText(self.tr("⚠️ Token set, but no Gist yet. Push to create one."))
            self.lbl_sync_status.setStyleSheet("color: #f9e2af;")
        else:
            self.lbl_sync_status.setText(self.tr("❌ Not configured. Add your GitHub Personal Access Token."))
            self.lbl_sync_status.setStyleSheet("color: #f38ba8;")
    
    def save_token(self):
        token = self.txt_token.text()
        if token.startswith("•"):
            QMessageBox.information(self, self.tr("Info"), self.tr("Token already saved."))
            return
        
        if not token or not token.startswith("ghp_"):
            QMessageBox.warning(self, self.tr("Invalid Token"), self.tr("Please enter a valid GitHub Personal Access Token (starts with 'ghp_')."))
            return
        
        if CloudSyncManager.save_gist_token(token):
            self.txt_token.setText("••••••••••••••••")
            self.update_sync_status()
            QMessageBox.information(self, self.tr("Success"), self.tr("Token saved securely."))
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to save token."))
    
    def export_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Configuration"),
            "loofi-fedora-tweaks-backup.json",
            self.tr("JSON Files (*.json)")
        )
        if path:
            success, message = ConfigManager.export_to_file(path)
            if success:
                QMessageBox.information(self, self.tr("Export Complete"), message)
            else:
                QMessageBox.warning(self, self.tr("Export Failed"), message)
    
    def import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Import Configuration"),
            "",
            self.tr("JSON Files (*.json)")
        )
        if path:
            confirm = QMessageBox.question(
                self, self.tr("Confirm Import"),
                self.tr("This will apply settings from the backup file. Continue?")
            )
            if confirm == QMessageBox.StandardButton.Yes:
                success, message = ConfigManager.import_from_file(path)
                if success:
                    QMessageBox.information(self, self.tr("Import Complete"), message)
                    self.refresh_list()
                else:
                    QMessageBox.warning(self, self.tr("Import Failed"), message)
    
    def push_to_gist(self):
        if not CloudSyncManager.get_gist_token():
            QMessageBox.warning(self, self.tr("Not Configured"), self.tr("Please add your GitHub token first."))
            return
        
        config = ConfigManager.export_all()
        success, message = CloudSyncManager.sync_to_gist(config)
        
        if success:
            self.update_sync_status()
            QMessageBox.information(self, self.tr("Sync Complete"), message)
        else:
            QMessageBox.warning(self, self.tr("Sync Failed"), message)
    
    def pull_from_gist(self):
        gist_id = CloudSyncManager.get_gist_id()
        if not gist_id:
            # Ask for Gist ID
            gist_id, ok = QInputDialog.getText(
                self, self.tr("Enter Gist ID"),
                self.tr("Enter the Gist ID to pull from:")
            )
            if not ok or not gist_id:
                return
        
        success, result = CloudSyncManager.sync_from_gist(gist_id)
        
        if success:
            confirm = QMessageBox.question(
                self, self.tr("Apply Config?"),
                self.tr("Downloaded config from '{}'. Apply these settings?").format(result.get('system', {}).get('hostname', 'unknown'))
            )
            if confirm == QMessageBox.StandardButton.Yes:
                apply_success, apply_msg = ConfigManager.import_all(result)
                if apply_success:
                    self.refresh_list()
                    QMessageBox.information(self, self.tr("Success"), apply_msg)
                else:
                    QMessageBox.warning(self, self.tr("Error"), apply_msg)
        else:
            QMessageBox.warning(self, self.tr("Download Failed"), result)
