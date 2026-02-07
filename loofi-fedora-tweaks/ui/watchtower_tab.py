"""
Watchtower Tab - System diagnostics and service management.
Part of v7.5 "Watchtower" update.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QTextEdit, QScrollArea, QFrame, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QComboBox, QMenu, QMessageBox,
    QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from utils.services import ServiceManager, UnitScope, UnitState
from utils.boot_analyzer import BootAnalyzer
from utils.journal import JournalManager


class WatchtowerTab(QWidget):
    """System diagnostics tab with services, boot analysis, and journal."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel(self.tr("🔭 Watchtower - System Diagnostics"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff; padding: 10px;")
        layout.addWidget(header)
        
        # Sub-tabs for different diagnostic areas
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_services_tab(), "🔧 Services")
        self.tabs.addTab(self._create_boot_tab(), "⚡ Boot Analysis")
        self.tabs.addTab(self._create_journal_tab(), "📋 Journal")
        
        layout.addWidget(self.tabs)
    
    def _create_services_tab(self) -> QWidget:
        """Create the services management sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(self.tr("Filter:")))
        
        self.service_filter = QComboBox()
        self.service_filter.addItem("🎮 Gaming Services", "gaming")
        self.service_filter.addItem("❌ Failed Services", "failed")
        self.service_filter.addItem("✅ Active Services", "active")
        self.service_filter.addItem("📦 All User Services", "all")
        self.service_filter.currentIndexChanged.connect(self._refresh_services)
        filter_layout.addWidget(self.service_filter)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton(self.tr("🔄 Refresh"))
        refresh_btn.clicked.connect(self._refresh_services)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # Service tree
        self.service_tree = QTreeWidget()
        self.service_tree.setHeaderLabels([self.tr("Service"), self.tr("Status"), self.tr("Description")])
        self.service_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.service_tree.customContextMenuRequested.connect(self._show_service_menu)
        self.service_tree.setColumnWidth(0, 250)
        self.service_tree.setColumnWidth(1, 100)
        layout.addWidget(self.service_tree)
        
        # Status log
        self.service_log = QTextEdit()
        self.service_log.setReadOnly(True)
        self.service_log.setMaximumHeight(100)
        layout.addWidget(self.service_log)
        
        self._refresh_services()
        return widget
    
    def _create_boot_tab(self) -> QWidget:
        """Create the boot analysis sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Boot stats summary
        stats_group = QGroupBox(self.tr("Boot Time Summary"))
        stats_layout = QVBoxLayout(stats_group)
        
        self.boot_stats_label = QLabel()
        self.boot_stats_label.setWordWrap(True)
        stats_layout.addWidget(self.boot_stats_label)
        
        # Visual bars for boot phases
        self.boot_bars_layout = QVBoxLayout()
        stats_layout.addLayout(self.boot_bars_layout)
        
        layout.addWidget(stats_group)
        
        # Slow services
        slow_group = QGroupBox(self.tr("Slowest Services (>5s)"))
        slow_layout = QVBoxLayout(slow_group)
        
        self.slow_services_list = QTextEdit()
        self.slow_services_list.setReadOnly(True)
        slow_layout.addWidget(self.slow_services_list)
        
        layout.addWidget(slow_group)
        
        # Optimization suggestions
        opt_group = QGroupBox(self.tr("💡 Optimization Suggestions"))
        opt_layout = QVBoxLayout(opt_group)
        
        self.suggestions_label = QLabel()
        self.suggestions_label.setWordWrap(True)
        opt_layout.addWidget(self.suggestions_label)
        
        layout.addWidget(opt_group)
        
        # Refresh button
        refresh_btn = QPushButton(self.tr("🔄 Analyze Boot"))
        refresh_btn.clicked.connect(self._refresh_boot_analysis)
        layout.addWidget(refresh_btn)
        
        self._refresh_boot_analysis()
        return widget
    
    def _create_journal_tab(self) -> QWidget:
        """Create the journal viewer sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Quick diagnostic
        diag_group = QGroupBox(self.tr("🏥 Quick Diagnostic"))
        diag_layout = QHBoxLayout(diag_group)
        
        self.error_count_label = QLabel()
        diag_layout.addWidget(self.error_count_label)
        
        self.failed_count_label = QLabel()
        diag_layout.addWidget(self.failed_count_label)
        
        diag_layout.addStretch()
        
        layout.addWidget(diag_group)
        
        # Journal output
        journal_group = QGroupBox(self.tr("Recent Errors"))
        journal_layout = QVBoxLayout(journal_group)
        
        self.journal_output = QTextEdit()
        self.journal_output.setReadOnly(True)
        self.journal_output.setStyleSheet("font-family: monospace;")
        journal_layout.addWidget(self.journal_output)
        
        layout.addWidget(journal_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton(self.tr("🔄 Refresh"))
        refresh_btn.clicked.connect(self._refresh_journal)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        panic_btn = QPushButton(self.tr("🆘 Export Panic Log"))
        panic_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        panic_btn.clicked.connect(self._export_panic_log)
        btn_layout.addWidget(panic_btn)
        
        layout.addLayout(btn_layout)
        
        self._refresh_journal()
        return widget
    
    def _refresh_services(self):
        """Refresh the services list."""
        self.service_tree.clear()
        filter_type = self.service_filter.currentData()
        
        # Get user services
        services = ServiceManager.list_units(UnitScope.USER, filter_type)
        
        # Add gaming services from system scope too
        if filter_type == "gaming":
            services.extend(ServiceManager.list_units(UnitScope.SYSTEM, filter_type))
        
        for service in services:
            item = QTreeWidgetItem([
                service.name,
                self._state_to_emoji(service.state),
                service.description[:50] if service.description else ""
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, service)
            self.service_tree.addTopLevelItem(item)
        
        self.service_log.append(self.tr(f"Loaded {len(services)} services"))
    
    def _state_to_emoji(self, state: UnitState) -> str:
        """Convert service state to emoji."""
        mapping = {
            UnitState.ACTIVE: "✅ active",
            UnitState.INACTIVE: "⚪ inactive",
            UnitState.FAILED: "❌ failed",
            UnitState.ACTIVATING: "🔄 starting",
            UnitState.UNKNOWN: "❓ unknown",
        }
        return mapping.get(state, "❓")
    
    def _show_service_menu(self, position):
        """Show context menu for service actions."""
        item = self.service_tree.itemAt(position)
        if not item:
            return
        
        service = item.data(0, Qt.ItemDataRole.UserRole)
        if not service:
            return
        
        menu = QMenu()
        
        if service.state == UnitState.ACTIVE:
            stop_action = menu.addAction("⏹️ Stop")
            stop_action.triggered.connect(lambda: self._service_action("stop", service))
            
            restart_action = menu.addAction("🔄 Restart")
            restart_action.triggered.connect(lambda: self._service_action("restart", service))
        else:
            start_action = menu.addAction("▶️ Start")
            start_action.triggered.connect(lambda: self._service_action("start", service))
        
        menu.addSeparator()
        
        mask_action = menu.addAction("🚫 Mask (Disable)")
        mask_action.triggered.connect(lambda: self._service_action("mask", service))
        
        unmask_action = menu.addAction("✅ Unmask")
        unmask_action.triggered.connect(lambda: self._service_action("unmask", service))
        
        menu.exec(self.service_tree.viewport().mapToGlobal(position))
    
    def _service_action(self, action: str, service):
        """Execute a service action."""
        actions = {
            "start": ServiceManager.start_unit,
            "stop": ServiceManager.stop_unit,
            "restart": ServiceManager.restart_unit,
            "mask": ServiceManager.mask_unit,
            "unmask": ServiceManager.unmask_unit,
        }
        
        func = actions.get(action)
        if func:
            result = func(service.name, service.scope)
            self.service_log.append(result.message)
            if result.success:
                self._refresh_services()
    
    def _refresh_boot_analysis(self):
        """Refresh boot analysis data."""
        stats = BootAnalyzer.get_boot_stats()
        
        # Stats summary
        if stats.total_time:
            summary = f"Total boot time: {stats.total_time:.1f}s\n"
            if stats.firmware_time:
                summary += f"  • Firmware: {stats.firmware_time:.1f}s\n"
            if stats.loader_time:
                summary += f"  • Bootloader: {stats.loader_time:.1f}s\n"
            if stats.kernel_time:
                summary += f"  • Kernel: {stats.kernel_time:.1f}s\n"
            if stats.userspace_time:
                summary += f"  • Userspace: {stats.userspace_time:.1f}s"
            self.boot_stats_label.setText(summary)
        else:
            self.boot_stats_label.setText("Unable to analyze boot (run as user, after first boot)")
        
        # Slow services
        slow = BootAnalyzer.get_slow_services()
        if slow:
            slow_text = "\n".join(
                f"🐢 {s.service}: {s.time_seconds:.1f}s" for s in slow[:10]
            )
            self.slow_services_list.setText(slow_text)
        else:
            self.slow_services_list.setText("No services taking >5s to start")
        
        # Suggestions
        suggestions = BootAnalyzer.get_optimization_suggestions()
        self.suggestions_label.setText("\n".join(suggestions))
    
    def _refresh_journal(self):
        """Refresh journal diagnostic view."""
        diag = JournalManager.get_quick_diagnostic()
        
        self.error_count_label.setText(f"⚠️ Errors: {diag['error_count']}")
        self.failed_count_label.setText(f"❌ Failed Services: {len(diag['failed_services'])}")
        
        # Show recent errors
        errors = JournalManager.get_boot_errors()
        self.journal_output.setText(errors if errors else "No errors in current boot")
    
    def _export_panic_log(self):
        """Export panic log for forum support."""
        result = JournalManager.export_panic_log()
        
        if result.success:
            QMessageBox.information(
                self,
                self.tr("Panic Log Exported"),
                self.tr(f"Log saved to:\n{result.data['path']}\n\n"
                       f"You can share this file when asking for help online.")
            )
        else:
            QMessageBox.warning(self, self.tr("Export Failed"), result.message)
