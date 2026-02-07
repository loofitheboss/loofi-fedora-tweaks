"""
Marketplace Tab - Browse and download community presets.
Part of v7.0 "Community" update.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QComboBox, QLineEdit, QTextEdit, QListWidget,
    QListWidgetItem, QScrollArea, QFrame, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from utils.marketplace import PresetMarketplace, CommunityPreset, MarketplaceResult
from utils.drift import DriftDetector
from utils.presets import PresetManager


class FetchThread(QThread):
    """Background thread for fetching marketplace data."""
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


class MarketplaceTab(QWidget):
    """Marketplace tab for browsing and downloading community presets."""
    
    def __init__(self):
        super().__init__()
        self.marketplace = PresetMarketplace()
        self.drift_detector = DriftDetector()
        self.preset_manager = PresetManager()
        self.current_presets = []
        
        self.init_ui()
        self.refresh_marketplace()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(self.tr("🌐 Community Preset Marketplace"))
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
        
        search_btn = QPushButton(self.tr("🔍 Search"))
        search_btn.clicked.connect(self.search_presets)
        search_layout.addWidget(search_btn)
        
        refresh_btn = QPushButton(self.tr("🔄 Refresh"))
        refresh_btn.clicked.connect(lambda: self.refresh_marketplace(force=True))
        search_layout.addWidget(refresh_btn)
        
        layout.addLayout(search_layout)
        
        # Preset List
        list_group = QGroupBox(self.tr("Available Presets"))
        list_layout = QVBoxLayout(list_group)
        
        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self.on_preset_selected)
        list_layout.addWidget(self.preset_list)
        
        self.status_label = QLabel(self.tr("Loading..."))
        self.status_label.setStyleSheet("color: #888;")
        list_layout.addWidget(self.status_label)
        
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
        
        self.download_btn = QPushButton(self.tr("📥 Download"))
        self.download_btn.clicked.connect(self.download_preset)
        self.download_btn.setEnabled(False)
        btn_layout.addWidget(self.download_btn)
        
        self.apply_btn = QPushButton(self.tr("✅ Download & Apply"))
        self.apply_btn.clicked.connect(self.download_and_apply)
        self.apply_btn.setEnabled(False)
        btn_layout.addWidget(self.apply_btn)
        
        btn_layout.addStretch()
        details_layout.addLayout(btn_layout)
        
        layout.addWidget(details_group)
        
        # Drift Detection Section
        drift_group = QGroupBox(self.tr("📊 Configuration Drift"))
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
    
    def refresh_marketplace(self, force: bool = False):
        """Refresh the preset list from the marketplace."""
        self.status_label.setText(self.tr("Loading presets..."))
        self.preset_list.clear()
        
        self.fetch_thread = FetchThread(self.marketplace)
        self.fetch_thread.finished.connect(self.on_fetch_complete)
        self.fetch_thread.start()
    
    def on_fetch_complete(self, result: MarketplaceResult):
        """Handle fetch completion."""
        if result.success:
            self.current_presets = result.data or []
            self.populate_preset_list()
            self.status_label.setText(result.message)
        else:
            self.status_label.setText(f"❌ {result.message}")
    
    def populate_preset_list(self):
        """Populate the list widget with presets."""
        self.preset_list.clear()
        
        for preset in self.current_presets:
            item = QListWidgetItem(
                f"⭐ {preset.stars}  |  {preset.name} by {preset.author}\n"
                f"   [{preset.category}] {preset.description[:60]}..."
            )
            item.setData(Qt.ItemDataRole.UserRole, preset)
            self.preset_list.addItem(item)
        
        if not self.current_presets:
            self.preset_list.addItem(QListWidgetItem(self.tr("No presets available yet.")))
    
    def on_preset_selected(self, item: QListWidgetItem):
        """Handle preset selection."""
        preset = item.data(Qt.ItemDataRole.UserRole)
        if not preset:
            return
        
        self.selected_preset = preset
        self.detail_name.setText(preset.name)
        self.detail_author.setText(f"by {preset.author} • {preset.category}")
        self.detail_desc.setText(preset.description)
        self.detail_stats.setText(
            f"⭐ {preset.stars} stars  •  📥 {preset.download_count} downloads  •  "
            f"Tags: {', '.join(preset.tags)}"
        )
        
        self.download_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
    
    def search_presets(self):
        """Search for presets."""
        query = self.search_input.text()
        category = self.category_combo.currentData()
        
        self.status_label.setText(self.tr("Searching..."))
        
        self.fetch_thread = FetchThread(self.marketplace, category, query)
        self.fetch_thread.finished.connect(self.on_fetch_complete)
        self.fetch_thread.start()
    
    def filter_by_category(self):
        """Filter by selected category."""
        self.search_presets()
    
    def download_preset(self):
        """Download the selected preset."""
        if not hasattr(self, 'selected_preset'):
            return
        
        result = self.marketplace.download_preset(self.selected_preset)
        
        if result.success:
            QMessageBox.information(
                self, self.tr("Downloaded"),
                self.tr("Preset '{}' downloaded successfully!").format(self.selected_preset.name)
            )
        else:
            QMessageBox.warning(self, self.tr("Error"), result.message)
    
    def download_and_apply(self):
        """Download and apply the selected preset."""
        if not hasattr(self, 'selected_preset'):
            return
        
        result = self.marketplace.download_preset(self.selected_preset)
        
        if result.success:
            # Apply the preset
            preset_path = result.data.get("path")
            if preset_path:
                apply_result = self.preset_manager.apply_preset(preset_path)
                
                if apply_result:
                    # Save baseline for drift detection
                    snapshot = self.drift_detector.capture_snapshot(self.selected_preset.name)
                    self.drift_detector.save_snapshot(snapshot)
                    self.update_drift_status()
                    
                    QMessageBox.information(
                        self, self.tr("Applied"),
                        self.tr("Preset '{}' applied! Baseline saved for drift detection.").format(
                            self.selected_preset.name
                        )
                    )
                else:
                    QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to apply preset"))
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
                f"• [{d.category}] {d.setting}: {d.expected} → {d.actual}"
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
