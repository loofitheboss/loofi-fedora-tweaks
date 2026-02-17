"""
Community Tab - Consolidated Presets + Marketplace interface.
Part of v11.0 "Aurora Update" - merges Presets and Marketplace tabs.

Sub-tabs:
- Presets: Local presets, community presets, backup/sync
- Marketplace: Browse, search, download community presets with drift detection
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QMessageBox,
    QInputDialog,
    QGroupBox,
    QTabWidget,
    QFileDialog,
    QLineEdit,
    QListWidgetItem,
    QComboBox,
    QTextEdit,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal

from utils.presets import PresetManager
from utils.config_manager import ConfigManager
from utils.cloud_sync import CloudSyncManager
from utils.marketplace import PresetMarketplace, MarketplaceResult
from utils.drift import DriftDetector
from utils.plugin_base import PluginLoader
from utils.plugin_installer import PluginInstaller
from utils.plugin_marketplace import PluginMarketplace
from utils.plugin_analytics import PluginAnalytics
from utils.settings import SettingsManager
from ui.tab_utils import configure_top_tabs
from ui.permission_consent_dialog import PermissionConsentDialog
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata


class FetchPresetsThread(QThread):
    """Background thread for fetching community presets (from PresetsTab)."""

    finished = pyqtSignal(bool, object)

    def run(self):
        success, result = CloudSyncManager.fetch_community_presets()
        self.finished.emit(success, result)


class FetchMarketplaceThread(QThread):
    """Background thread for fetching marketplace data (from MarketplaceTab)."""

    finished = pyqtSignal(object)

    def __init__(
        self, marketplace: PresetMarketplace, category: str = "", query: str = ""
    ):
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


class CommunityTab(QWidget, PluginInterface):
    """Consolidated Community tab: Presets + Marketplace."""

    _METADATA = PluginMetadata(
        id="community",
        name="Community",
        description="Browse and apply community presets and configurations from the marketplace.",
        category="System",
        icon="🌍",
        badge="",
        order=40,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self.manager = PresetManager()
        self.marketplace = PresetMarketplace()
        self.drift_detector = DriftDetector()
        # v26 compatibility: plugin marketplace helpers used by CLI/UI tests.
        self.plugin_marketplace = PluginMarketplace()
        self.plugin_installer = PluginInstaller()
        self.settings_manager = SettingsManager.instance()
        self.plugin_analytics = PluginAnalytics(settings_manager=self.settings_manager)
        self.selected_marketplace_plugin = None
        self.selected_marketplace_plugin_id = None
        self.marketplace_plugin_metadata = {}
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
        configure_top_tabs(self.sub_tabs)
        layout.addWidget(self.sub_tabs)

        # Sub-tab 1: Presets (from PresetsTab)
        self.sub_tabs.addTab(self._create_presets_tab(), self.tr("Presets"))

        # Sub-tab 2: Marketplace (from MarketplaceTab)
        self.sub_tabs.addTab(self._create_marketplace_tab(), self.tr("Marketplace"))

        # Sub-tab 3: Plugins
        self.sub_tabs.addTab(self._create_plugins_tab(), self.tr("Plugins"))

        # Sub-tab 4: Featured Plugins (v37.0 Pinnacle)
        self.sub_tabs.addTab(self._create_featured_tab(), self.tr("Featured"))

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
        configure_top_tabs(preset_tabs)
        layout.addWidget(preset_tabs)

        # Inner Tab 1: Local Presets
        preset_tabs.addTab(self._create_local_presets_tab(), self.tr("My Presets"))

        # Inner Tab 2: Community Presets
        preset_tabs.addTab(self._create_community_presets_tab(), self.tr("Community"))

        # Inner Tab 3: Export/Import
        preset_tabs.addTab(self._create_sync_tab(), self.tr("Backup & Sync"))

        return widget

    # ================================================================
    # PLUGINS SUB-TAB
    # ================================================================

    def _create_plugins_tab(self) -> QWidget:
        """Create the plugins sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel(self.tr("Plugin Manager"))
        header.setObjectName("header")
        layout.addWidget(header)

        desc = QLabel(self.tr("Enable or disable installed plugins."))
        layout.addWidget(desc)

        self.plugins_list = QListWidget()
        self.plugins_list.currentItemChanged.connect(self._on_plugin_selected)
        layout.addWidget(self.plugins_list)

        self.plugin_details = QTextEdit()
        self.plugin_details.setReadOnly(True)
        self.plugin_details.setMinimumHeight(120)
        layout.addWidget(self.plugin_details)

        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.setAccessibleName(self.tr("Refresh plugins"))
        refresh_btn.clicked.connect(self.refresh_plugins)
        btn_layout.addWidget(refresh_btn)

        self.enable_btn = QPushButton(self.tr("Enable"))
        self.enable_btn.setAccessibleName(self.tr("Enable plugin"))
        self.enable_btn.clicked.connect(lambda: self._set_selected_plugin(True))
        btn_layout.addWidget(self.enable_btn)

        self.disable_btn = QPushButton(self.tr("Disable"))
        self.disable_btn.setAccessibleName(self.tr("Disable plugin"))
        self.disable_btn.clicked.connect(lambda: self._set_selected_plugin(False))
        btn_layout.addWidget(self.disable_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.refresh_plugins()
        return widget

    def refresh_plugins(self):
        """Reload the plugin list."""
        self.plugins_list.clear()
        loader = PluginLoader()
        plugins = loader.list_plugins()

        if not plugins:
            self.plugin_details.setText(self.tr("No plugins found."))
            self.enable_btn.setEnabled(False)
            self.disable_btn.setEnabled(False)
            return

        for plugin in plugins:
            name = plugin["name"]
            enabled = plugin.get("enabled", True)
            status = "✅" if enabled else "❌"
            item = QListWidgetItem(f"{status} {name}")
            item.setData(Qt.ItemDataRole.UserRole, plugin)
            self.plugins_list.addItem(item)

        self.plugins_list.setCurrentRow(0)

    def _on_plugin_selected(self, current, previous):
        """Show selected plugin details."""
        if not current:
            self.plugin_details.clear()
            return

        plugin = current.data(Qt.ItemDataRole.UserRole) or {}
        manifest = plugin.get("manifest") or {}
        enabled = plugin.get("enabled", True)

        lines = [
            f"Name: {manifest.get('name', plugin.get('name', 'unknown'))}",
            f"Version: {manifest.get('version', 'unknown')}",
            f"Author: {manifest.get('author', 'unknown')}",
            f"Enabled: {'Yes' if enabled else 'No'}",
            f"Description: {manifest.get('description', '')}",
        ]

        perms = manifest.get("permissions") or []
        if perms:
            lines.append(f"Permissions: {', '.join(perms)}")

        min_version = manifest.get("min_app_version")
        if min_version:
            lines.append(f"Min App Version: {min_version}")

        self.plugin_details.setText("\n".join(lines).strip())
        self.enable_btn.setEnabled(not enabled)
        self.disable_btn.setEnabled(enabled)

    def _set_selected_plugin(self, enabled: bool):
        """Enable or disable the selected plugin."""
        item = self.plugins_list.currentItem()
        if not item:
            return
        plugin = item.data(Qt.ItemDataRole.UserRole) or {}
        name = plugin.get("name")
        if not name:
            return

        loader = PluginLoader()
        loader.set_enabled(name, enabled)
        self.refresh_plugins()

    # ================================================================
    # FEATURED PLUGINS SUB-TAB (v37.0 Pinnacle)
    # ================================================================

    def _create_featured_tab(self) -> QWidget:
        """Create the featured/curated plugins showcase tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel(self.tr("Featured Plugins"))
        header.setObjectName("header")
        layout.addWidget(header)

        desc = QLabel(self.tr("Curated, high-quality plugins from the community."))
        layout.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton(self.tr("Refresh Featured"))
        btn_refresh.setAccessibleName(self.tr("Refresh Featured"))
        btn_refresh.clicked.connect(self._load_featured_plugins)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.featured_list = QListWidget()
        self.featured_list.setMinimumHeight(200)
        self.featured_list.currentItemChanged.connect(self._on_featured_selected)
        layout.addWidget(self.featured_list)

        self.featured_details = QTextEdit()
        self.featured_details.setReadOnly(True)
        self.featured_details.setMaximumHeight(120)
        layout.addWidget(self.featured_details)

        # Load on creation
        QTimer.singleShot(500, self._load_featured_plugins)

        return widget

    def _load_featured_plugins(self):
        """Load curated plugins from marketplace."""
        try:
            from utils.plugin_marketplace import PluginMarketplace

            curated = PluginMarketplace.get_curated_plugins()
            self.featured_list.clear()
            for p in curated:
                badge = "⭐ " if p.featured else ""
                verified = " ✓" if p.verified else ""
                item = QListWidgetItem(
                    f"{badge}{p.name} v{p.version} by {p.author}{verified}  "
                    f"(★ {p.rating:.1f}, {p.downloads} downloads)"
                )
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.featured_list.addItem(item)
            if not curated:
                self.featured_list.addItem(
                    QListWidgetItem(self.tr("No featured plugins available."))
                )
        except (ImportError, RuntimeError, OSError, ValueError, TypeError) as e:
            self.featured_list.clear()
            self.featured_list.addItem(QListWidgetItem(f"Error: {e}"))

    def _on_featured_selected(self, current, previous):
        """Show details for selected featured plugin."""
        if not current:
            self.featured_details.clear()
            return
        plugin = current.data(Qt.ItemDataRole.UserRole)
        if not plugin:
            self.featured_details.clear()
            return
        lines = [
            f"Name: {plugin.name}",
            f"Author: {plugin.author}",
            f"Version: {plugin.version}",
            f"Category: {plugin.category}",
            f"Rating: {plugin.rating:.1f}/5.0",
            f"Downloads: {plugin.downloads}",
            f"Verified: {'Yes' if plugin.verified else 'No'}",
            f"Featured: {'Yes' if plugin.featured else 'No'}",
            "",
            f"{plugin.description}",
        ]
        self.featured_details.setText("\n".join(lines))

    # -- Local Presets --

    def _create_local_presets_tab(self) -> QWidget:
        """Create the local presets tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(
            QLabel(self.tr("Save and restore your system configuration presets."))
        )

        # List Area
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_load = QPushButton(self.tr("Load Selected"))
        self.btn_load.setAccessibleName(self.tr("Load Selected"))
        self.btn_load.clicked.connect(self.load_preset)

        self.btn_save = QPushButton(self.tr("Save Current State"))
        self.btn_save.setAccessibleName(self.tr("Save Current State"))
        self.btn_save.clicked.connect(self.save_preset)

        self.btn_delete = QPushButton(self.tr("Delete Selected"))
        self.btn_delete.setAccessibleName(self.tr("Delete Selected"))
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
                    self,
                    self.tr("Success"),
                    self.tr("Preset '{}' saved successfully.").format(name),
                )
            else:
                QMessageBox.warning(
                    self, self.tr("Error"), self.tr("Failed to save preset.")
                )

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
                self,
                self.tr("Success"),
                self.tr("Preset '{}' loaded.\nSettings applied.").format(name),
            )
        else:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Failed to load preset '{}'.").format(name),
            )

    def delete_preset(self):
        """Delete selected preset."""
        item = self.list_widget.currentItem()
        if not item:
            return

        name = item.text()
        confirm = QMessageBox.question(
            self, self.tr("Confirm Delete"), self.tr("Delete preset '{}'?").format(name)
        )
        if confirm == QMessageBox.StandardButton.Yes:
            if self.manager.delete_preset(name):
                self.refresh_list()
            else:
                QMessageBox.warning(
                    self, self.tr("Error"), self.tr("Failed to delete preset.")
                )

    # -- Community Presets --

    def _create_community_presets_tab(self) -> QWidget:
        """Create the community presets tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(
            QLabel(self.tr("Browse and download presets shared by the community."))
        )

        # Community presets list
        self.community_list = QListWidget()
        layout.addWidget(self.community_list)

        # Status label
        self.lbl_community_status = QLabel(
            self.tr("Click 'Refresh' to load community presets.")
        )
        self.lbl_community_status.setObjectName("communityStatusLabel")
        layout.addWidget(self.lbl_community_status)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_refresh = QPushButton(self.tr("Refresh"))
        btn_refresh.setAccessibleName(self.tr("Refresh community presets"))
        btn_refresh.clicked.connect(self.refresh_community_presets)

        btn_download = QPushButton(self.tr("Download Selected"))
        btn_download.setAccessibleName(self.tr("Download Selected"))
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
                            preset.get("name", "Unknown"),
                            preset.get("author", "anonymous"),
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
                self,
                self.tr("Success"),
                self.tr("Preset '{}' downloaded and saved!").format(preset.get("name")),
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

        export_layout.addWidget(
            QLabel(
                self.tr("Backup all your settings to a file, or restore from a backup.")
            )
        )

        btn_row = QHBoxLayout()

        btn_export = QPushButton(self.tr("Export to File"))
        btn_export.setAccessibleName(self.tr("Export to File"))
        btn_export.clicked.connect(self.export_config)
        btn_row.addWidget(btn_export)

        btn_import = QPushButton(self.tr("Import from File"))
        btn_import.setAccessibleName(self.tr("Import from File"))
        btn_import.clicked.connect(self.import_config)
        btn_row.addWidget(btn_import)

        export_layout.addLayout(btn_row)
        layout.addWidget(export_group)

        # Cloud Sync Section
        cloud_group = QGroupBox(self.tr("GitHub Gist Sync"))
        cloud_layout = QVBoxLayout(cloud_group)

        cloud_layout.addWidget(
            QLabel(
                self.tr(
                    "Sync your config to a private GitHub Gist for cross-machine access."
                )
            )
        )

        # Token status
        self.lbl_sync_status = QLabel()
        self.lbl_sync_status.setObjectName("communitySyncStatus")
        self.update_sync_status()
        cloud_layout.addWidget(self.lbl_sync_status)

        # Token input
        token_row = QHBoxLayout()
        token_row.addWidget(QLabel(self.tr("GitHub Token:")))

        self.txt_token = QLineEdit()
        self.txt_token.setAccessibleName(self.tr("GitHub token"))
        self.txt_token.setPlaceholderText("ghp_xxxxxxxxxxxx...")
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        token = CloudSyncManager.get_gist_token()
        if token:
            self.txt_token.setText("••••••••••••••••")
        token_row.addWidget(self.txt_token)

        btn_save_token = QPushButton(self.tr("Save"))
        btn_save_token.setAccessibleName(self.tr("Save token"))
        btn_save_token.clicked.connect(self.save_token)
        token_row.addWidget(btn_save_token)

        cloud_layout.addLayout(token_row)

        # Sync buttons
        sync_row = QHBoxLayout()

        btn_push = QPushButton(self.tr("Push to Gist"))
        btn_push.setAccessibleName(self.tr("Push to Gist"))
        btn_push.clicked.connect(self.push_to_gist)
        sync_row.addWidget(btn_push)

        btn_pull = QPushButton(self.tr("Pull from Gist"))
        btn_pull.setAccessibleName(self.tr("Pull from Gist"))
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
            self.lbl_sync_status.setProperty("state", "connected")
            if self.lbl_sync_status.style() is not None:
                self.lbl_sync_status.style().unpolish(self.lbl_sync_status)
                self.lbl_sync_status.style().polish(self.lbl_sync_status)
        elif token:
            self.lbl_sync_status.setText(
                self.tr("Token set, but no Gist yet. Push to create one.")
            )
            self.lbl_sync_status.setProperty("state", "partial")
            if self.lbl_sync_status.style() is not None:
                self.lbl_sync_status.style().unpolish(self.lbl_sync_status)
                self.lbl_sync_status.style().polish(self.lbl_sync_status)
        else:
            self.lbl_sync_status.setText(
                self.tr("Not configured. Add your GitHub Personal Access Token.")
            )
            self.lbl_sync_status.setProperty("state", "error")
            if self.lbl_sync_status.style() is not None:
                self.lbl_sync_status.style().unpolish(self.lbl_sync_status)
                self.lbl_sync_status.style().polish(self.lbl_sync_status)

    def save_token(self):
        """Save GitHub Personal Access Token."""
        token = self.txt_token.text()
        if token.startswith("\u2022"):
            QMessageBox.information(
                self, self.tr("Info"), self.tr("Token already saved.")
            )
            return

        if not token or not token.startswith("ghp_"):
            QMessageBox.warning(
                self,
                self.tr("Invalid Token"),
                self.tr(
                    "Please enter a valid GitHub Personal Access Token (starts with 'ghp_')."
                ),
            )
            return

        if CloudSyncManager.save_gist_token(token):
            self.txt_token.setText("••••••••••••••••")
            self.update_sync_status()
            QMessageBox.information(
                self, self.tr("Success"), self.tr("Token saved securely.")
            )
        else:
            QMessageBox.warning(
                self, self.tr("Error"), self.tr("Failed to save token.")
            )

    def export_config(self):
        """Export configuration to file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Configuration"),
            "loofi-fedora-tweaks-backup.json",
            self.tr("JSON Files (*.json)"),
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
            self, self.tr("Import Configuration"), "", self.tr("JSON Files (*.json)")
        )
        if path:
            confirm = QMessageBox.question(
                self,
                self.tr("Confirm Import"),
                self.tr("This will apply settings from the backup file. Continue?"),
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
                self,
                self.tr("Not Configured"),
                self.tr("Please add your GitHub token first."),
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
                self,
                self.tr("Enter Gist ID"),
                self.tr("Enter the Gist ID to pull from:"),
            )
            if not ok or not gist_id:
                return

        success, result = CloudSyncManager.sync_from_gist(gist_id)

        if success:
            confirm = QMessageBox.question(
                self,
                self.tr("Apply Config?"),
                self.tr("Downloaded config from '{}'. Apply these settings?").format(
                    result.get("system", {}).get("hostname", "unknown")
                ),
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
        header.setObjectName("communityMarketplaceHeader")
        layout.addWidget(header)

        # Search and Filter
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setAccessibleName(self.tr("Search presets"))
        self.search_input.setPlaceholderText(self.tr("Search presets..."))
        self.search_input.returnPressed.connect(self.search_presets)
        search_layout.addWidget(self.search_input)

        self.category_combo = QComboBox()
        self.category_combo.setAccessibleName(self.tr("Preset category"))
        self.category_combo.addItem(self.tr("All Categories"), "")
        for cat in self.marketplace.get_categories():
            self.category_combo.addItem(cat.capitalize(), cat)
        self.category_combo.currentIndexChanged.connect(self.filter_by_category)
        search_layout.addWidget(self.category_combo)

        search_btn = QPushButton(self.tr("Search"))
        search_btn.setAccessibleName(self.tr("Search marketplace"))
        search_btn.clicked.connect(self.search_presets)
        search_layout.addWidget(search_btn)

        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.setAccessibleName(self.tr("Refresh marketplace"))
        refresh_btn.clicked.connect(lambda: self.refresh_marketplace(force=True))
        search_layout.addWidget(refresh_btn)

        layout.addLayout(search_layout)

        # Preset List
        list_group = QGroupBox(self.tr("Available Presets"))
        list_layout = QVBoxLayout(list_group)

        self.marketplace_preset_list = QListWidget()
        self.marketplace_preset_list.itemClicked.connect(
            self.on_marketplace_preset_selected
        )
        list_layout.addWidget(self.marketplace_preset_list)
        # Compatibility alias used by plugin marketplace tests.
        self.marketplace_plugin_list = self.marketplace_preset_list

        self.marketplace_status_label = QLabel(self.tr("Loading..."))
        self.marketplace_status_label.setObjectName("communityMarketplaceStatus")
        list_layout.addWidget(self.marketplace_status_label)

        layout.addWidget(list_group)

        # Preset Details
        details_group = QGroupBox(self.tr("Preset Details"))
        details_layout = QVBoxLayout(details_group)

        self.detail_name = QLabel("")
        self.detail_name.setObjectName("communityDetailName")
        details_layout.addWidget(self.detail_name)

        self.detail_author = QLabel("")
        self.detail_author.setObjectName("communityDetailAuthor")
        details_layout.addWidget(self.detail_author)

        self.detail_desc = QLabel("")
        self.detail_desc.setWordWrap(True)
        details_layout.addWidget(self.detail_desc)

        self.detail_stats = QLabel("")
        details_layout.addWidget(self.detail_stats)

        self.detail_verification = QLabel("")
        self.detail_verification.setObjectName("communityDetailVerification")
        details_layout.addWidget(self.detail_verification)

        self.detail_rating_summary = QLabel("")
        self.detail_rating_summary.setObjectName("communityDetailRating")
        details_layout.addWidget(self.detail_rating_summary)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton(self.tr("Download"))
        self.download_btn.setAccessibleName(self.tr("Download preset"))
        self.download_btn.clicked.connect(self.download_marketplace_preset)
        self.download_btn.setEnabled(False)
        btn_layout.addWidget(self.download_btn)
        # Compatibility alias used by plugin marketplace tests.
        self.install_plugin_btn = self.download_btn

        self.apply_btn = QPushButton(self.tr("Download & Apply"))
        self.apply_btn.setAccessibleName(self.tr("Download and Apply preset"))
        self.apply_btn.clicked.connect(self.download_and_apply)
        self.apply_btn.setEnabled(False)
        btn_layout.addWidget(self.apply_btn)

        btn_layout.addStretch()
        details_layout.addLayout(btn_layout)

        layout.addWidget(details_group)

        # Reviews section
        reviews_group = QGroupBox(self.tr("Ratings & Reviews"))
        reviews_layout = QVBoxLayout(reviews_group)

        self.reviews_summary_label = QLabel(
            self.tr("Select a preset to view ratings and reviews.")
        )
        self.reviews_summary_label.setObjectName("communityReviewsSummary")
        reviews_layout.addWidget(self.reviews_summary_label)

        self.reviews_text = QTextEdit()
        self.reviews_text.setReadOnly(True)
        self.reviews_text.setMinimumHeight(130)
        reviews_layout.addWidget(self.reviews_text)

        review_form_row_1 = QHBoxLayout()
        self.review_reviewer_input = QLineEdit()
        self.review_reviewer_input.setAccessibleName(self.tr("Reviewer name"))
        self.review_reviewer_input.setPlaceholderText(self.tr("Reviewer name"))
        review_form_row_1.addWidget(self.review_reviewer_input)

        self.review_rating_combo = QComboBox()
        self.review_rating_combo.setAccessibleName(self.tr("Review rating"))
        for rating in range(5, 0, -1):
            self.review_rating_combo.addItem(
                self.tr("{} star(s)").format(rating), rating
            )
        review_form_row_1.addWidget(self.review_rating_combo)
        reviews_layout.addLayout(review_form_row_1)

        self.review_title_input = QLineEdit()
        self.review_title_input.setAccessibleName(self.tr("Review title"))
        self.review_title_input.setPlaceholderText(self.tr("Review title (optional)"))
        reviews_layout.addWidget(self.review_title_input)

        self.review_comment_input = QTextEdit()
        self.review_comment_input.setPlaceholderText(
            self.tr("Write your review (optional)")
        )
        self.review_comment_input.setMaximumHeight(90)
        reviews_layout.addWidget(self.review_comment_input)

        review_actions_layout = QHBoxLayout()
        self.submit_review_btn = QPushButton(self.tr("Submit Review"))
        self.submit_review_btn.setAccessibleName(self.tr("Submit Review"))
        self.submit_review_btn.setEnabled(False)
        self.submit_review_btn.clicked.connect(self.submit_marketplace_review)
        review_actions_layout.addWidget(self.submit_review_btn)

        self.review_feedback_label = QLabel("")
        self.review_feedback_label.setObjectName("communityReviewFeedback")
        review_actions_layout.addWidget(self.review_feedback_label)
        review_actions_layout.addStretch()
        reviews_layout.addLayout(review_actions_layout)

        layout.addWidget(reviews_group)

        analytics_group = QGroupBox(self.tr("Usage Analytics (Opt-in)"))
        analytics_layout = QVBoxLayout(analytics_group)

        self.analytics_opt_in_checkbox = QCheckBox(
            self.tr("Share anonymous plugin marketplace usage analytics")
        )
        self.analytics_opt_in_checkbox.setAccessibleName(
            self.tr("Share anonymous plugin marketplace usage analytics")
        )
        self.analytics_opt_in_checkbox.setChecked(self.plugin_analytics.is_enabled())
        self.analytics_opt_in_checkbox.stateChanged.connect(
            self._on_analytics_opt_in_changed
        )
        analytics_layout.addWidget(self.analytics_opt_in_checkbox)

        self.analytics_status_label = QLabel("")
        self.analytics_status_label.setObjectName("communityAnalyticsStatus")
        analytics_layout.addWidget(self.analytics_status_label)
        self._update_analytics_status_label(self.plugin_analytics.is_enabled())

        layout.addWidget(analytics_group)

        # Drift Detection Section
        drift_group = QGroupBox(self.tr("Configuration Drift"))
        drift_layout = QVBoxLayout(drift_group)

        self.drift_status = QLabel(self.tr("No baseline set"))
        drift_layout.addWidget(self.drift_status)

        drift_btn_layout = QHBoxLayout()

        check_drift_btn = QPushButton(self.tr("Check Drift"))
        check_drift_btn.setAccessibleName(self.tr("Check Drift"))
        check_drift_btn.clicked.connect(self.check_drift)
        drift_btn_layout.addWidget(check_drift_btn)

        clear_baseline_btn = QPushButton(self.tr("Clear Baseline"))
        clear_baseline_btn.setAccessibleName(self.tr("Clear Baseline"))
        clear_baseline_btn.clicked.connect(self.clear_baseline)
        drift_btn_layout.addWidget(clear_baseline_btn)

        drift_btn_layout.addStretch()
        drift_layout.addLayout(drift_btn_layout)

        layout.addWidget(drift_group)

        # Check drift on load
        self.update_drift_status()

        return widget

    def _search_marketplace_plugins(self):
        """Compatibility helper for v26 plugin marketplace tests."""
        if hasattr(self.plugin_marketplace, "search_plugins"):
            results = self.plugin_marketplace.search_plugins()
        else:
            result = self.plugin_marketplace.search()
            results = (
                result.data if result and getattr(result, "success", False) else []
            )

        if results:
            self.selected_marketplace_plugin = results[0]
        return results

    def _install_marketplace_plugin(self):
        """Compatibility helper for v26 plugin marketplace tests."""
        plugin_package = self.selected_marketplace_plugin
        if not plugin_package:
            return None

        manifest = getattr(plugin_package, "manifest", None)
        permissions = getattr(manifest, "permissions", []) if manifest else []

        if permissions:
            consent = PermissionConsentDialog(plugin_package, self)
            if consent.exec() != consent.DialogCode.Accepted:
                return None

        metadata = getattr(plugin_package, "metadata", None)
        plugin_id = getattr(metadata, "id", None) or getattr(metadata, "name", None)
        if not plugin_id:
            return None

        return self.plugin_installer.install(plugin_id)

    # -- Marketplace actions --

    def refresh_marketplace(self, force: bool = False):
        """Refresh the marketplace preset list."""
        self.marketplace_status_label.setText(self.tr("Loading presets..."))
        self.marketplace_preset_list.clear()

        self.fetch_marketplace_thread = FetchMarketplaceThread(self.marketplace)
        self.fetch_marketplace_thread.finished.connect(
            self.on_marketplace_fetch_complete
        )
        self.fetch_marketplace_thread.start()

    def on_marketplace_fetch_complete(self, result: MarketplaceResult):
        """Handle marketplace fetch completion."""
        if result.success:
            self.current_presets = result.data or []
            self._refresh_plugin_metadata_cache()
            self.populate_marketplace_preset_list()
            self.marketplace_status_label.setText(result.message)
        else:
            self.marketplace_status_label.setText(result.message)

    def _normalize_marketplace_key(self, value) -> str:
        """Normalize identifiers for matching preset records with plugin metadata."""
        if value is None:
            return ""
        return str(value).strip().lower().replace(" ", "-").replace("_", "-")

    def _refresh_plugin_metadata_cache(self):
        """Best-effort cache of marketplace plugin metadata for ratings/badges in UI."""
        self.marketplace_plugin_metadata = {}
        result = self.plugin_marketplace.search()
        if not result or not getattr(result, "success", False) or not result.data:
            return

        for plugin in result.data:
            plugin_id = self._normalize_marketplace_key(getattr(plugin, "id", ""))
            plugin_name = self._normalize_marketplace_key(getattr(plugin, "name", ""))
            if plugin_id:
                self.marketplace_plugin_metadata[plugin_id] = plugin
            if plugin_name:
                self.marketplace_plugin_metadata[plugin_name] = plugin

    def _resolve_plugin_metadata_for_preset(self, preset):
        """Resolve plugin metadata using common preset/plugin identifiers."""
        candidates = [
            self._normalize_marketplace_key(getattr(preset, "id", "")),
            self._normalize_marketplace_key(getattr(preset, "plugin_id", "")),
            self._normalize_marketplace_key(getattr(preset, "name", "")),
        ]
        for candidate in candidates:
            if candidate and candidate in self.marketplace_plugin_metadata:
                return self.marketplace_plugin_metadata[candidate]
        return None

    def _build_badge_rating_summary(self, plugin_meta) -> str:
        """Build compact badge/rating summary for list rows."""
        if not plugin_meta:
            return self.tr("Unverified | No rating")

        verified = bool(getattr(plugin_meta, "verified_publisher", False))
        badge = getattr(plugin_meta, "publisher_badge", "") or ""
        badge_text = (
            self.tr("Verified {}").format(f"({badge})" if badge else "")
            if verified
            else self.tr("Unverified")
        )

        average = getattr(plugin_meta, "rating_average", None)
        review_count = getattr(plugin_meta, "review_count", 0) or 0
        if average is None:
            rating_text = self.tr("No rating")
        else:
            rating_text = self.tr("{:.1f}/5 ({} reviews)").format(
                float(average), int(review_count)
            )

        return f"{badge_text} | {rating_text}"

    def _set_review_feedback(self, message: str, success: bool):
        """Show inline review form feedback with simple success/error coloring."""
        state = "success" if success else "error"
        self.review_feedback_label.setProperty("state", state)
        if self.review_feedback_label.style() is not None:
            _style = self.review_feedback_label.style()
            assert _style is not None
            _style.unpolish(self.review_feedback_label)
            _style.polish(self.review_feedback_label)
        self.review_feedback_label.setText(message)

    def _update_analytics_status_label(self, enabled: bool):
        if enabled:
            self.analytics_status_label.setText(
                self.tr(
                    "Enabled: only anonymized marketplace usage events are sent in batches."
                )
            )
        else:
            self.analytics_status_label.setText(
                self.tr("Disabled: no usage analytics events are collected or sent.")
            )

    def _on_analytics_opt_in_changed(self, state):
        """Persist analytics consent and update local status copy."""
        enabled = state == Qt.CheckState.Checked.value
        self.plugin_analytics.set_enabled(enabled)
        self._update_analytics_status_label(enabled)

    def _track_analytics_event(
        self, event_type: str, action: str, plugin_id: str = "", metadata=None
    ):
        """Best-effort analytics tracking; never block primary UI actions."""
        self.plugin_analytics.track_event(
            event_type=event_type,
            action=action,
            plugin_id=plugin_id,
            metadata=metadata or {},
        )

    def _load_marketplace_reviews(self):
        """Fetch and render ratings + review list for selected marketplace plugin."""
        self.reviews_text.clear()
        self.reviews_summary_label.setText(self.tr("No review data available."))

        if not self.selected_marketplace_plugin_id:
            return

        aggregate_result = self.plugin_marketplace.get_rating_aggregate(
            self.selected_marketplace_plugin_id
        )
        if aggregate_result.success and aggregate_result.data:
            aggregate = aggregate_result.data
            self.reviews_summary_label.setText(
                self.tr("Average: {:.1f}/5 from {} ratings ({} reviews)").format(
                    aggregate.average_rating,
                    aggregate.rating_count,
                    aggregate.review_count,
                )
            )
            self.detail_rating_summary.setText(
                self.tr("Rating: {:.1f}/5 | {} ratings | {} reviews").format(
                    aggregate.average_rating,
                    aggregate.rating_count,
                    aggregate.review_count,
                )
            )
        else:
            self.reviews_summary_label.setText(
                self.tr("Ratings unavailable: {}").format(
                    aggregate_result.error or "unknown"
                )
            )

        reviews_result = self.plugin_marketplace.fetch_reviews(
            self.selected_marketplace_plugin_id, limit=5, offset=0
        )
        if not reviews_result.success:
            self.reviews_text.setPlainText(
                self.tr("Unable to load reviews: {}").format(
                    reviews_result.error or "unknown"
                )
            )
            return

        reviews = reviews_result.data or []
        if not reviews:
            self.reviews_text.setPlainText(
                self.tr("No reviews yet. Be the first to submit one.")
            )
            return

        lines = []
        for review in reviews:
            lines.append(f"{review.rating}/5 - {review.reviewer}")
            if review.title:
                lines.append(f"{review.title}")
            if review.comment:
                lines.append(f"{review.comment}")
            if review.created_at:
                lines.append(f"{review.created_at}")
            lines.append("")
        self.reviews_text.setPlainText("\n".join(lines).strip())

    def populate_marketplace_preset_list(self):
        """Populate the marketplace list widget with presets."""
        self.marketplace_preset_list.clear()

        for preset in self.current_presets:
            plugin_meta = self._resolve_plugin_metadata_for_preset(preset)
            badge_rating = self._build_badge_rating_summary(plugin_meta)
            item = QListWidgetItem(
                self.tr(
                    "{stars} stars | {name} by {author}\n   [{category}] {desc}...\n   {badge_rating}"
                ).format(
                    stars=preset.stars,
                    name=preset.name,
                    author=preset.author,
                    category=preset.category,
                    desc=preset.description[:60],
                    badge_rating=badge_rating,
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
                preset.stars, preset.download_count, ", ".join(preset.tags)
            )
        )
        plugin_meta = self._resolve_plugin_metadata_for_preset(preset)
        self.selected_marketplace_plugin_id = None

        if plugin_meta:
            self.selected_marketplace_plugin_id = getattr(plugin_meta, "id", None)
            verified = bool(getattr(plugin_meta, "verified_publisher", False))
            badge = getattr(plugin_meta, "publisher_badge", "") or ""
            publisher_id = getattr(plugin_meta, "publisher_id", "") or ""
            verification_label = self.tr("Verified Publisher")
            if verified and badge:
                verification_label = self.tr("Verified Publisher ({})").format(badge)
            if not verified:
                verification_label = self.tr("Publisher not verified")
            if publisher_id:
                verification_label = f"{verification_label} | {publisher_id}"
            self.detail_verification.setText(verification_label)

            if getattr(plugin_meta, "rating_average", None) is not None:
                self.detail_rating_summary.setText(
                    self.tr("Rating: {:.1f}/5 | {} ratings | {} reviews").format(
                        float(plugin_meta.rating_average),
                        int(getattr(plugin_meta, "rating_count", 0) or 0),
                        int(getattr(plugin_meta, "review_count", 0) or 0),
                    )
                )
            else:
                self.detail_rating_summary.setText(self.tr("Rating: No ratings yet"))
        else:
            self.detail_verification.setText(
                self.tr("Publisher verification unavailable for this preset")
            )
            self.detail_rating_summary.setText(
                self.tr("Rating data unavailable for this preset")
            )

        self.submit_review_btn.setEnabled(bool(self.selected_marketplace_plugin_id))
        self._set_review_feedback("", True)
        self._load_marketplace_reviews()
        self._track_analytics_event(
            event_type="marketplace",
            action="select_preset",
            plugin_id=self.selected_marketplace_plugin_id or "",
            metadata={
                "category": getattr(preset, "category", ""),
                "has_metadata": bool(plugin_meta),
            },
        )

        self.download_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)

    def submit_marketplace_review(self):
        """Submit a review for the selected marketplace plugin with inline validation feedback."""
        if not self.selected_marketplace_plugin_id:
            self._set_review_feedback(
                self.tr("Select a preset with marketplace plugin metadata first."),
                False,
            )
            return

        reviewer = self.review_reviewer_input.text().strip()
        rating = int(self.review_rating_combo.currentData() or 0)
        title = self.review_title_input.text().strip()
        comment = self.review_comment_input.toPlainText().strip()

        if not reviewer:
            self._set_review_feedback(self.tr("Reviewer name is required."), False)
            return
        if rating < 1 or rating > 5:
            self._set_review_feedback(self.tr("Rating must be between 1 and 5."), False)
            return
        if len(title) > 120:
            self._set_review_feedback(
                self.tr("Title must be at most 120 characters."), False
            )
            return
        if len(comment) > 5000:
            self._set_review_feedback(
                self.tr("Comment must be at most 5000 characters."), False
            )
            return

        result = self.plugin_marketplace.submit_review(
            plugin_id=self.selected_marketplace_plugin_id,
            reviewer=reviewer,
            rating=rating,
            title=title,
            comment=comment,
        )
        if result.success:
            self.review_title_input.clear()
            self.review_comment_input.clear()
            self._set_review_feedback(self.tr("Review submitted successfully."), True)
            self._load_marketplace_reviews()
            self._track_analytics_event(
                event_type="marketplace",
                action="submit_review",
                plugin_id=self.selected_marketplace_plugin_id,
                metadata={"status": "success", "rating": rating},
            )
            return

        self._track_analytics_event(
            event_type="marketplace",
            action="submit_review",
            plugin_id=self.selected_marketplace_plugin_id,
            metadata={"status": "error"},
        )
        self._set_review_feedback(
            self.tr("Review submit failed: {}").format(result.error or "unknown"), False
        )

    def search_presets(self):
        """Search for presets in the marketplace."""
        query = self.search_input.text()
        category = self.category_combo.currentData()

        self.marketplace_status_label.setText(self.tr("Searching..."))

        self.fetch_marketplace_thread = FetchMarketplaceThread(
            self.marketplace, category, query
        )
        self.fetch_marketplace_thread.finished.connect(
            self.on_marketplace_fetch_complete
        )
        self.fetch_marketplace_thread.start()

    def filter_by_category(self):
        """Filter marketplace by selected category."""
        self.search_presets()

    def download_marketplace_preset(self):
        """Download the selected marketplace preset."""
        if not hasattr(self, "selected_preset"):
            return

        result = self.marketplace.download_preset(self.selected_preset)

        if result.success:
            self._track_analytics_event(
                event_type="marketplace",
                action="download_preset",
                plugin_id=self.selected_marketplace_plugin_id or "",
                metadata={"status": "success"},
            )
            QMessageBox.information(
                self,
                self.tr("Downloaded"),
                self.tr("Preset '{}' downloaded successfully!").format(
                    self.selected_preset.name
                ),
            )
        else:
            self._track_analytics_event(
                event_type="marketplace",
                action="download_preset",
                plugin_id=self.selected_marketplace_plugin_id or "",
                metadata={"status": "error"},
            )
            QMessageBox.warning(self, self.tr("Error"), result.message)

    def download_and_apply(self):
        """Download and apply the selected marketplace preset."""
        if not hasattr(self, "selected_preset"):
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
                        self,
                        self.tr("Applied"),
                        self.tr(
                            "Preset '{}' applied! Baseline saved for drift detection."
                        ).format(self.selected_preset.name),
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
                self,
                self.tr("No Baseline"),
                self.tr("No baseline set. Apply a preset first."),
            )
            return

        if report.is_drifted:
            items_text = "\n".join(
                [
                    self.tr("[{}] {}: {} -> {}").format(
                        d.category, d.setting, d.expected, d.actual
                    )
                    for d in report.items[:10]
                ]
            )

            QMessageBox.warning(
                self,
                self.tr("Drift Detected"),
                self.tr("Found {} changes since preset '{}' was applied:\n\n{}").format(
                    report.drift_count, report.preset_name, items_text
                ),
            )
        else:
            QMessageBox.information(
                self,
                self.tr("No Drift"),
                self.tr("Configuration matches preset '{}'.").format(
                    report.preset_name
                ),
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
                    snapshot.preset_name, snapshot.timestamp[:10]
                )
            )
        else:
            self.drift_status.setText(self.tr("No baseline set"))
