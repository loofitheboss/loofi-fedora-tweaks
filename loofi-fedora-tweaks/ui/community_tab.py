"""
Community Tab - Consolidated Presets + Marketplace interface.
Part of v10.0 "Zenith Update" - merges Presets and Marketplace tabs.

Sub-tabs:
- Presets: Local presets, community presets, backup/sync
- Marketplace: Browse, search, download community presets with drift detection
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QMessageBox, QInputDialog, QGroupBox,
    QTabWidget, QFileDialog, QDialog, QLineEdit, QFormLayout,
    QListWidgetItem, QComboBox, QTextEdit, QScrollArea, QFrame,
    QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from utils.presets import PresetManager
from utils.config_manager import ConfigManager
from utils.cloud_sync import CloudSyncManager
from utils.marketplace import PresetMarketplace, CommunityPreset, MarketplaceResult
from utils.drift import DriftDetector


class FetchPresetsThread(QThread):
    """Background thread for fetching community presets (from PresetsTab)."""
    finished = pyqtSignal(bool, object)

    def run(self):
        success, result = CloudSyncManager.fetch_community_presets()
        self.finished.emit(success, result)


class FetchMarketplaceThread(QThread):
    """Background thread for fetching marketplace data (from MarketplaceTab)."""
    finished = pyqtSignal(object)

    def __init__(self, marketplace: PresetMarketplace, category: str = "", query: str = ""):
        super().__init__()
        self.marketplace = marketplace
        self.category = category
        self.query = query

    def run(self):
        if self.query or self.category:
            result = self.marketplace.search_presets(self.query, self.category)
        else:
            result = self.marketplace.get_featured()
        self.finished.emit(result)


class CommunityTab(QWidget):
    """Consolidated Community tab: Presets + Marketplace."""

    def __init__(self):
        super().__init__()
        self.manager = PresetManager()
        self.marketplace = PresetMarketplace()
        self.drift_detector = DriftDetector()
        self.current_presets = []
        self.init_ui()

        # Load marketplace data
        self.refresh_marketplace()

    def init_ui(self):
        """Initialize the UI with sub-tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sub-tab widget
        self.sub_tabs = QTabWidget()
        layout.addWidget(self.sub_tabs)

        # Sub-tab 1: Presets (from PresetsTab)
        self.sub_tabs.addTab(
            self._create_presets_tab(), self.tr("Presets")
        )

        # Sub-tab 2: Marketplace (from MarketplaceTab)
        self.sub_tabs.addTab(
            self._create_marketplace_tab(), self.tr("Marketplace")
        )

    # ================================================================
    # PRESETS SUB-TAB (from PresetsTab)
    # ================================================================

    def _create_presets_tab(self) -> QWidget:
        """Create the Presets sub-tab with its own inner tabs."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel(self.tr("Presets & Sync"))
        header.setObjectName("header")
        layout.addWidget(header)

        # Inner tab widget for preset sections
        preset_tabs = QTabWidget()
        layout.addWidget(preset_tabs)

        # Inner Tab 1: Local Presets
        preset_tabs.addTab(self._create_local_presets_tab(), self.tr("My Presets"))

        # Inner Tab 2: Community Presets
        preset_tabs.addTab(self._create_community_presets_tab(), self.tr("Community"))

        # Inner Tab 3: Export/Import
        preset_tabs.addTab(self._create_sync_tab(), self.tr("Backup & Sync"))

        return widget

    # -- Local Presets --

    def _create_local_presets_tab(self) -> QWidget:
        """Create the local presets tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel(self.tr("Save and restore your system configuration presets.")))

        # List Area
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_load = QPushButton(self.tr("Load Selected"))
        self.btn_load.clicked.connect(self.load_preset)

        self.btn_save = QPushButton(self.tr("Save Current State"))
        self.btn_save.clicked.connect(self.save_preset)

        self.btn_delete = QPushButton(self.tr("Delete Selected"))
        self.btn_delete.clicked.connect(self.delete_preset)

        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)

        self.refresh_list()
        return widget

    def refresh_list(self):
        """Refresh the local presets list."""
        self.list_widget.clear()
        presets = self.manager.list_presets()
        self.list_widget.addItems(presets)

    def save_preset(self):
        """Save current state as a preset."""
        name, ok = QInputDialog.getText(
            self, self.tr("Save Preset"), self.tr("Enter preset name:")
        )
        if ok and name:
            if self.manager.save_preset(name):
                self.refresh_list()
                QMessageBox.information(
                    self, self.tr("Success"),
                    self.tr("Preset '{}' saved successfully.").format(name)
                )
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to save preset."))

    def load_preset(self):
        """Load selected preset."""
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(
                self, self.tr("No Selection"), self.tr("Please select a preset first.")
            )
            return

        name = item.text()
        data = self.manager.load_preset(name)
        if data:
            QMessageBox.information(
                self, self.tr("Success"),
                self.tr("Preset '{}' loaded.\nSettings applied.").format(name)
            )
        else:
            QMessageBox.warning(
                self, self.tr("Error"),
                self.tr("Failed to load preset '{}'.").format(name)
            )

    def delete_preset(self):
        """Delete selected preset."""
        item = self.list_widget.currentItem()
        if not item:
            return

        name = item.text()
        confirm = QMessageBox.question(
            self, self.tr("Confirm Delete"),
            self.tr("Delete preset '{}'?").format(name)
        )
        if confirm == QMessageBox.StandardButton.Yes:
            if self.manager.delete_preset(name):
                self.refresh_list()
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to delete preset."))

    # -- Community Presets --

    def _create_community_presets_tab(self) -> QWidget:
        """Create the community presets tab."""
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

        btn_refresh = QPushButton(self.tr("Refresh"))
        btn_refresh.clicked.connect(self.refresh_community_presets)

        btn_download = QPushButton(self.tr("Download Selected"))
        btn_download.clicked.connect(self.download_community_preset)

        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_download)
        layout.addLayout(btn_layout)

        return widget

    def refresh_community_presets(self):
        """Fetch community presets in background."""
        self.lbl_community_status.setText(self.tr("Fetching presets..."))
        self.community_list.clear()

        self.fetch_presets_thread = FetchPresetsThread()
        self.fetch_presets_thread.finished.connect(self.on_presets_fetched)
        self.fetch_presets_thread.start()

    def on_presets_fetched(self, success: bool, result):
        """Handle community presets fetch completion."""
        if success:
            presets = result
            if not presets:
                self.lbl_community_status.setText(
                    self.tr("No community presets available yet.")
                )
            else:
                self.lbl_community_status.setText(
                    self.tr("Found {} presets").format(len(presets))
                )
                for preset in presets:
                    item = QListWidgetItem(
                        self.tr("{} - by {}").format(
                            preset.get('name', 'Unknown'),
                            preset.get('author', 'anonymous')
                        )
                    )
                    item.setData(Qt.ItemDataRole.UserRole, preset)
                    self.community_list.addItem(item)
        else:
            self.lbl_community_status.setText(str(result))

    def download_community_preset(self):
        """Download selected community preset."""
        item = self.community_list.currentItem()
        if not item:
            QMessageBox.warning(
                self, self.tr("No Selection"), self.tr("Please select a preset first.")
            )
            return

        preset = item.data(Qt.ItemDataRole.UserRole)
        preset_id = preset.get("id")

        if not preset_id:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Invalid preset data."))
            return

        success, result = CloudSyncManager.download_preset(preset_id)
        if success:
            self.manager.save_preset_data(
                preset.get("name", preset_id), result.get("settings", {})
            )
            self.refresh_list()
            QMessageBox.information(
                self, self.tr("Success"),
                self.tr("Preset '{}' downloaded and saved!").format(preset.get('name'))
            )
        else:
            QMessageBox.warning(self, self.tr("Download Failed"), result)

    # -- Backup & Sync --

    def _create_sync_tab(self) -> QWidget:
        """Create the backup and sync tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Export/Import Section
        export_group = QGroupBox(self.tr("Export / Import"))
        export_layout = QVBoxLayout(export_group)

        export_layout.addWidget(QLabel(self.tr(
            "Backup all your settings to a file, or restore from a backup."
        )))

        btn_row = QHBoxLayout()

        btn_export = QPushButton(self.tr("Export to File"))
        btn_export.clicked.connect(self.export_config)
        btn_row.addWidget(btn_export)

        btn_import = QPushButton(self.tr("Import from File"))
        btn_import.clicked.connect(self.import_config)
        btn_row.addWidget(btn_import)

        export_layout.addLayout(btn_row)
        layout.addWidget(export_group)

        # Cloud Sync Section
        cloud_group = QGroupBox(self.tr("GitHub Gist Sync"))
        cloud_layout = QVBoxLayout(cloud_group)

        cloud_layout.addWidget(QLabel(self.tr(
            "Sync your config to a private GitHub Gist for cross-machine access."
        )))

        # Token status
        self.lbl_sync_status = QLabel()
        self.update_sync_status()
        cloud_layout.addWidget(self.lbl_sync_status)

        # Token input
        token_row = QHBoxLayout()
        token_row.addWidget(QLabel(self.tr("GitHub Token:")))

        self.txt_token = QLineEdit()
        self.txt_token.setPlaceholderText("ghp_xxxxxxxxxxxx...")
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        token = CloudSyncManager.get_gist_token()
        if token:
            self.txt_token.setText("••••••••••••••••")
        token_row.addWidget(self.txt_token)

        btn_save_token = QPushButton(self.tr("Save"))
        btn_save_token.clicked.connect(self.save_token)
        token_row.addWidget(btn_save_token)

        cloud_layout.addLayout(token_row)

        # Sync buttons
        sync_row = QHBoxLayout()

        btn_push = QPushButton(self.tr("Push to Gist"))
        btn_push.clicked.connect(self.push_to_gist)
        sync_row.addWidget(btn_push)

        btn_pull = QPushButton(self.tr("Pull from Gist"))
        btn_pull.clicked.connect(self.pull_from_gist)
        sync_row.addWidget(btn_pull)

        cloud_layout.addLayout(sync_row)
        layout.addWidget(cloud_group)

        layout.addStretch()
        return widget

    def update_sync_status(self):
        """Update the cloud sync status label."""
        token = CloudSyncManager.get_gist_token()
        gist_id = CloudSyncManager.get_gist_id()

        if token and gist_id:
            self.lbl_sync_status.setText(
                self.tr("Connected | Gist ID: {}...").format(gist_id[:8])
            )
            self.lbl_sync_status.setStyleSheet("color: #a6e3a1;")
        elif token:
            self.lbl_sync_status.setText(
                self.tr("Token set, but no Gist yet. Push to create one.")
            )
            self.lbl_sync_status.setStyleSheet("color: #f9e2af;")
        else:
            self.lbl_sync_status.setText(
                self.tr("Not configured. Add your GitHub Personal Access Token.")
            )
            self.lbl_sync_status.setStyleSheet("color: #f38ba8;")

    def save_token(self):
        """Save GitHub Personal Access Token."""
        token = self.txt_token.text()
        if token.startswith("\u2022"):
            QMessageBox.information(self, self.tr("Info"), self.tr("Token already saved."))
            return

        if not token or not token.startswith("ghp_"):
            QMessageBox.warning(
                self, self.tr("Invalid Token"),
                self.tr("Please enter a valid GitHub Personal Access Token (starts with 'ghp_').")
            )
            return

        if CloudSyncManager.save_gist_token(token):
            self.txt_token.setText("••••••••••••••••")
            self.update_sync_status()
            QMessageBox.information(self, self.tr("Success"), self.tr("Token saved securely."))
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to save token."))

    def export_config(self):
        """Export configuration to file."""
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
        """Import configuration from file."""
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
        """Push configuration to GitHub Gist."""
        if not CloudSyncManager.get_gist_token():
            QMessageBox.warning(
                self, self.tr("Not Configured"),
                self.tr("Please add your GitHub token first.")
            )
            return

        config = ConfigManager.export_all()
        success, message = CloudSyncManager.sync_to_gist(config)

        if success:
            self.update_sync_status()
            QMessageBox.information(self, self.tr("Sync Complete"), message)
        else:
            QMessageBox.warning(self, self.tr("Sync Failed"), message)

    def pull_from_gist(self):
        """Pull configuration from GitHub Gist."""
        gist_id = CloudSyncManager.get_gist_id()
        if not gist_id:
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
                self.tr("Downloaded config from '{}'. Apply these settings?").format(
                    result.get('system', {}).get('hostname', 'unknown')
                )
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

    # ================================================================
    # MARKETPLACE SUB-TAB (from MarketplaceTab)
    # ================================================================

    def _create_marketplace_tab(self) -> QWidget:
        """Create the Marketplace sub-tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("Community Preset Marketplace"))
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Search and Filter
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Search presets..."))
        self.search_input.returnPressed.connect(self.search_presets)
        search_layout.addWidget(self.search_input)

        self.category_combo = QComboBox()
        self.category_combo.addItem(self.tr("All Categories"), "")
        for cat in self.marketplace.get_categories():
            self.category_combo.addItem(cat.capitalize(), cat)
        self.category_combo.currentIndexChanged.connect(self.filter_by_category)
        search_layout.addWidget(self.category_combo)

        search_btn = QPushButton(self.tr("Search"))
        search_btn.clicked.connect(self.search_presets)
        search_layout.addWidget(search_btn)

        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.clicked.connect(lambda: self.refresh_marketplace(force=True))
        search_layout.addWidget(refresh_btn)

        layout.addLayout(search_layout)

        # Preset List
        list_group = QGroupBox(self.tr("Available Presets"))
        list_layout = QVBoxLayout(list_group)

        self.marketplace_preset_list = QListWidget()
        self.marketplace_preset_list.itemClicked.connect(self.on_marketplace_preset_selected)
        list_layout.addWidget(self.marketplace_preset_list)

        self.marketplace_status_label = QLabel(self.tr("Loading..."))
        self.marketplace_status_label.setStyleSheet("color: #888;")
        list_layout.addWidget(self.marketplace_status_label)

        layout.addWidget(list_group)

        # Preset Details
        details_group = QGroupBox(self.tr("Preset Details"))
        details_layout = QVBoxLayout(details_group)

        self.detail_name = QLabel("")
        self.detail_name.setStyleSheet("font-size: 16px; font-weight: bold;")
        details_layout.addWidget(self.detail_name)

        self.detail_author = QLabel("")
        self.detail_author.setStyleSheet("color: #888;")
        details_layout.addWidget(self.detail_author)

        self.detail_desc = QLabel("")
        self.detail_desc.setWordWrap(True)
        details_layout.addWidget(self.detail_desc)

        self.detail_stats = QLabel("")
        details_layout.addWidget(self.detail_stats)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton(self.tr("Download"))
        self.download_btn.clicked.connect(self.download_marketplace_preset)
        self.download_btn.setEnabled(False)
        btn_layout.addWidget(self.download_btn)

        self.apply_btn = QPushButton(self.tr("Download & Apply"))
        self.apply_btn.clicked.connect(self.download_and_apply)
        self.apply_btn.setEnabled(False)
        btn_layout.addWidget(self.apply_btn)

        btn_layout.addStretch()
        details_layout.addLayout(btn_layout)

        layout.addWidget(details_group)

        # Drift Detection Section
        drift_group = QGroupBox(self.tr("Configuration Drift"))
        drift_layout = QVBoxLayout(drift_group)

        self.drift_status = QLabel(self.tr("No baseline set"))
        drift_layout.addWidget(self.drift_status)

        drift_btn_layout = QHBoxLayout()

        check_drift_btn = QPushButton(self.tr("Check Drift"))
        check_drift_btn.clicked.connect(self.check_drift)
        drift_btn_layout.addWidget(check_drift_btn)

        clear_baseline_btn = QPushButton(self.tr("Clear Baseline"))
        clear_baseline_btn.clicked.connect(self.clear_baseline)
        drift_btn_layout.addWidget(clear_baseline_btn)

        drift_btn_layout.addStretch()
        drift_layout.addLayout(drift_btn_layout)

        layout.addWidget(drift_group)

        # Check drift on load
        self.update_drift_status()

        return widget

    # -- Marketplace actions --

    def refresh_marketplace(self, force: bool = False):
        """Refresh the marketplace preset list."""
        self.marketplace_status_label.setText(self.tr("Loading presets..."))
        self.marketplace_preset_list.clear()

        self.fetch_marketplace_thread = FetchMarketplaceThread(self.marketplace)
        self.fetch_marketplace_thread.finished.connect(self.on_marketplace_fetch_complete)
        self.fetch_marketplace_thread.start()

    def on_marketplace_fetch_complete(self, result: MarketplaceResult):
        """Handle marketplace fetch completion."""
        if result.success:
            self.current_presets = result.data or []
            self.populate_marketplace_preset_list()
            self.marketplace_status_label.setText(result.message)
        else:
            self.marketplace_status_label.setText(result.message)

    def populate_marketplace_preset_list(self):
        """Populate the marketplace list widget with presets."""
        self.marketplace_preset_list.clear()

        for preset in self.current_presets:
            item = QListWidgetItem(
                self.tr("{stars} stars | {name} by {author}\n   [{category}] {desc}...").format(
                    stars=preset.stars,
                    name=preset.name,
                    author=preset.author,
                    category=preset.category,
                    desc=preset.description[:60]
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, preset)
            self.marketplace_preset_list.addItem(item)

        if not self.current_presets:
            self.marketplace_preset_list.addItem(
                QListWidgetItem(self.tr("No presets available yet."))
            )

    def on_marketplace_preset_selected(self, item: QListWidgetItem):
        """Handle marketplace preset selection."""
        preset = item.data(Qt.ItemDataRole.UserRole)
        if not preset:
            return

        self.selected_preset = preset
        self.detail_name.setText(preset.name)
        self.detail_author.setText(
            self.tr("by {} | {}").format(preset.author, preset.category)
        )
        self.detail_desc.setText(preset.description)
        self.detail_stats.setText(
            self.tr("{} stars | {} downloads | Tags: {}").format(
                preset.stars, preset.download_count, ', '.join(preset.tags)
            )
        )

        self.download_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)

    def search_presets(self):
        """Search for presets in the marketplace."""
        query = self.search_input.text()
        category = self.category_combo.currentData()

        self.marketplace_status_label.setText(self.tr("Searching..."))

        self.fetch_marketplace_thread = FetchMarketplaceThread(
            self.marketplace, category, query
        )
        self.fetch_marketplace_thread.finished.connect(self.on_marketplace_fetch_complete)
        self.fetch_marketplace_thread.start()

    def filter_by_category(self):
        """Filter marketplace by selected category."""
        self.search_presets()

    def download_marketplace_preset(self):
        """Download the selected marketplace preset."""
        if not hasattr(self, 'selected_preset'):
            return

        result = self.marketplace.download_preset(self.selected_preset)

        if result.success:
            QMessageBox.information(
                self, self.tr("Downloaded"),
                self.tr("Preset '{}' downloaded successfully!").format(
                    self.selected_preset.name
                )
            )
        else:
            QMessageBox.warning(self, self.tr("Error"), result.message)

    def download_and_apply(self):
        """Download and apply the selected marketplace preset."""
        if not hasattr(self, 'selected_preset'):
            return

        result = self.marketplace.download_preset(self.selected_preset)

        if result.success:
            # Apply the preset
            preset_path = result.data.get("path")
            if preset_path:
                apply_result = self.manager.apply_preset(preset_path)

                if apply_result:
                    # Save baseline for drift detection
                    snapshot = self.drift_detector.capture_snapshot(
                        self.selected_preset.name
                    )
                    self.drift_detector.save_snapshot(snapshot)
                    self.update_drift_status()

                    QMessageBox.information(
                        self, self.tr("Applied"),
                        self.tr("Preset '{}' applied! Baseline saved for drift detection.").format(
                            self.selected_preset.name
                        )
                    )
                else:
                    QMessageBox.warning(
                        self, self.tr("Error"), self.tr("Failed to apply preset")
                    )
        else:
            QMessageBox.warning(self, self.tr("Error"), result.message)

    def check_drift(self):
        """Check for configuration drift."""
        report = self.drift_detector.check_drift()

        if not report:
            QMessageBox.information(
                self, self.tr("No Baseline"),
                self.tr("No baseline set. Apply a preset first.")
            )
            return

        if report.is_drifted:
            items_text = "\n".join([
                self.tr("[{}] {}: {} -> {}").format(
                    d.category, d.setting, d.expected, d.actual
                )
                for d in report.items[:10]
            ])

            QMessageBox.warning(
                self, self.tr("Drift Detected"),
                self.tr("Found {} changes since preset '{}' was applied:\n\n{}").format(
                    report.drift_count, report.preset_name, items_text
                )
            )
        else:
            QMessageBox.information(
                self, self.tr("No Drift"),
                self.tr("Configuration matches preset '{}'.").format(report.preset_name)
            )

        self.update_drift_status()

    def clear_baseline(self):
        """Clear the drift detection baseline."""
        self.drift_detector.clear_baseline()
        self.update_drift_status()

    def update_drift_status(self):
        """Update the drift status label."""
        snapshot = self.drift_detector.load_snapshot()

        if snapshot:
            self.drift_status.setText(
                self.tr("Baseline: '{}' (set {})").format(
                    snapshot.preset_name,
                    snapshot.timestamp[:10]
                )
            )
        else:
            self.drift_status.setText(self.tr("No baseline set"))
