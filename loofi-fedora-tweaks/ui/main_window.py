"""
Main Window - v19.0 "Vanguard"
26-tab layout with sidebar navigation, breadcrumb, and status bar.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QLabel, QFrame, QTreeWidgetItemIterator, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut, QKeySequence, QFontMetrics

# Only import essential tabs eagerly (Dashboard is always shown first)
from ui.dashboard_tab import DashboardTab
from ui.system_info_tab import SystemInfoTab
from ui.lazy_widget import LazyWidget
from utils.pulse import SystemPulse, PulseThread
from utils.focus_mode import FocusMode
from utils.config_manager import ConfigManager
from utils.system import SystemManager  # Backward-compatible symbol for legacy tests
from version import __version__
import os
import logging

# Custom data roles for sidebar items
_ROLE_DESC = Qt.ItemDataRole.UserRole + 1   # Tab description string
_ROLE_BADGE = Qt.ItemDataRole.UserRole + 2  # "recommended" | "advanced" | ""

# Tab metadata: (description, badge)
_TAB_META = {
    "Home": ("System overview and quick actions", "recommended"),
    "Agents": ("Automated system management agents", ""),
    "Automation": ("Scheduled tasks and cron jobs", ""),
    "System Info": ("Hardware and OS details", "recommended"),
    "System Monitor": ("Live CPU, memory, and process monitoring", "recommended"),
    "Health": ("System health timeline and trends", ""),
    "Logs": ("Systemd journal and log viewer", "advanced"),
    "Hardware": ("CPU, GPU, fan, and power controls", "recommended"),
    "Performance": ("Kernel tuning and I/O scheduler", "advanced"),
    "Storage": ("Disk usage and mount management", ""),
    "Software": ("Package management and repos", "recommended"),
    "Maintenance": ("System updates and cache cleanup", "recommended"),
    "Snapshots": ("Btrfs/LVM snapshot management", "advanced"),
    "Virtualization": ("Virtual machines and containers", "advanced"),
    "Development": ("Developer tools and SDKs", ""),
    "Network": ("Network interfaces and firewall", "recommended"),
    "Loofi Link": ("Device mesh networking", "advanced"),
    "Security & Privacy": ("Firewall, SELinux, audit tools", "recommended"),
    "Desktop": ("GNOME/KDE customization", ""),
    "Profiles": ("User profile and workspace management", ""),
    "Gaming": ("Game mode and GPU optimization", ""),
    "AI Lab": ("AI-powered system suggestions", "advanced"),
    "State Teleport": ("System state transfer between machines", "advanced"),
    "Diagnostics": ("System diagnostics and health checks", ""),
    "Community": ("Community tweaks and shared configs", ""),
    "Settings": ("App preferences and theme", ""),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize logger for this class
        self.logger = logging.getLogger(__name__)

        # Check frameless mode feature flag
        frameless_enabled = self._get_frameless_mode_flag()

        if frameless_enabled:
            self.logger.warning(
                "Frameless mode requested but not yet fully implemented. "
                "Using native title bar. Set ui.frameless_mode=false or "
                "unset LOOFI_FRAMELESS to disable this warning."
            )
            # Stub: future frameless implementation would go here
            # For now, keep native title bar even when flag is True

        # Keep native title-bar decorations enabled.
        # This avoids KDE/Wayland/X11 edge-cases where client content can
        # appear to bleed into the top chrome when frameless/custom hints are used.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
        self.setWindowFlag(Qt.WindowType.CustomizeWindowHint, False)
        self.setWindowTitle(self.tr(f"Loofi Fedora Tweaks v{__version__}"))
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        # HiDPI safety: compute scalable dimensions from font metrics
        fm = QFontMetrics(self.font())
        self._line_height = fm.height()

        # Initialize Pulse event listener
        self.pulse = None
        self.pulse_thread = None
        self._start_pulse_listener()

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Layout (Horizontal: Sidebar | Content)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # Sidebar container with search
        sidebar_container = QWidget()
        # HiDPI: 15*line_height = approx 240px at 1x DPI
        sidebar_width = int(self._line_height * 15)
        sidebar_container.setFixedWidth(sidebar_width)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 10, 0, 0)
        sidebar_layout.setSpacing(0)

        # Search box
        from PyQt6.QtWidgets import QLineEdit
        self.sidebar_search = QLineEdit()
        self.sidebar_search.setPlaceholderText(self.tr("Search tabs..."))
        self.sidebar_search.setClearButtonEnabled(True)
        # HiDPI: 2*line_height + padding (4+10)*2 = approx 36px at 1x DPI
        search_height = int(self._line_height * 2 + 28)
        self.sidebar_search.setFixedHeight(search_height)
        self.sidebar_search.setStyleSheet(
            "QLineEdit { margin: 5px 10px; border-radius: 8px; padding: 4px 10px; }"
        )
        self.sidebar_search.textChanged.connect(self._filter_sidebar)
        sidebar_layout.addWidget(self.sidebar_search)

        # Sidebar tree
        self.sidebar = QTreeWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setHeaderHidden(True)
        self.sidebar.setIndentation(20)
        self.sidebar.setRootIsDecorated(True)
        self.sidebar.setUniformRowHeights(True)
        self.sidebar.setAnimated(True)
        self.sidebar.currentItemChanged.connect(self.change_page)
        sidebar_layout.addWidget(self.sidebar)

        # Sidebar footer
        sidebar_footer = QLabel(f"v{__version__}")
        sidebar_footer.setObjectName("sidebarFooter")
        sidebar_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # HiDPI: 2*line_height = approx 28px at 1x DPI
        footer_height = int(self._line_height * 2)
        sidebar_footer.setFixedHeight(footer_height)
        sidebar_layout.addWidget(sidebar_footer)

        main_layout.addWidget(sidebar_container)

        # Right side: breadcrumb + content + status bar
        right_side = QVBoxLayout()
        right_side.setContentsMargins(0, 0, 0, 0)
        right_side.setSpacing(0)

        # Breadcrumb bar
        self._breadcrumb_frame = QFrame()
        self._breadcrumb_frame.setObjectName("breadcrumbBar")
        # HiDPI: 3*line_height = approx 44px at 1x DPI
        breadcrumb_height = int(self._line_height * 3)
        self._breadcrumb_frame.setFixedHeight(breadcrumb_height)
        bc_layout = QHBoxLayout(self._breadcrumb_frame)
        bc_layout.setContentsMargins(16, 0, 16, 0)
        self._bc_category = QLabel("")
        self._bc_category.setObjectName("bcCategory")
        self._bc_sep = QLabel("  ›  ")
        self._bc_sep.setObjectName("bcSep")
        self._bc_page = QLabel("")
        self._bc_page.setObjectName("bcPage")
        self._bc_desc = QLabel("")
        self._bc_desc.setObjectName("bcDesc")
        bc_layout.addWidget(self._bc_category)
        bc_layout.addWidget(self._bc_sep)
        bc_layout.addWidget(self._bc_page)
        bc_layout.addSpacing(12)
        bc_layout.addWidget(self._bc_desc)
        bc_layout.addStretch()
        right_side.addWidget(self._breadcrumb_frame)

        # Content Area
        self.content_area = QStackedWidget()
        right_side.addWidget(self.content_area)

        # Status bar
        self._status_frame = QFrame()
        self._status_frame.setObjectName("statusBar")
        # HiDPI: 2*line_height = approx 28px at 1x DPI
        status_height = int(self._line_height * 2)
        self._status_frame.setFixedHeight(status_height)
        sb_layout = QHBoxLayout(self._status_frame)
        sb_layout.setContentsMargins(12, 0, 12, 0)
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusText")
        sb_layout.addWidget(self._status_label)
        sb_layout.addStretch()
        shortcuts_hint = QLabel(
            self.tr("Ctrl+K Search  |  Ctrl+Shift+K Actions  |  F1 Help")
        )
        shortcuts_hint.setObjectName("statusHints")
        sb_layout.addWidget(shortcuts_hint)
        version_lbl = QLabel(f"v{__version__}")
        version_lbl.setObjectName("statusVersion")
        sb_layout.addWidget(version_lbl)
        right_side.addWidget(self._status_frame)

        main_layout.addLayout(right_side)

        # Initialize Pages
        self.pages = {}

        # ==================== Dashboard ====================
        self.add_page(self.tr("Home"), "\U0001f3e0", DashboardTab(self), "Dashboard")

        # ==================== Automation ====================
        self.add_page(self.tr("Agents"), "\U0001f916", self._lazy_tab("agents"), "Automation")
        self.add_page(self.tr("Automation"), "\u23f0", self._lazy_tab("automation"), "Automation")

        # ==================== System ====================
        self.add_page(self.tr("System Info"), "\u2139\ufe0f", SystemInfoTab(), "System")
        self.add_page(self.tr("System Monitor"), "\U0001f4ca", self._lazy_tab("monitor"), "System")
        self.add_page(self.tr("Health"), "\U0001f4c8", self._lazy_tab("health"), "System")
        self.add_page(self.tr("Logs"), "\U0001f4cb", self._lazy_tab("logs"), "System")

        # ==================== Hardware ====================
        self.add_page(self.tr("Hardware"), "\u26a1", self._lazy_tab("hardware"), "Hardware")
        self.add_page(self.tr("Performance"), "\u2699\ufe0f", self._lazy_tab("performance"), "Hardware")
        self.add_page(self.tr("Storage"), "\U0001f4be", self._lazy_tab("storage"), "Hardware")

        # ==================== Software ====================
        self.add_page(self.tr("Software"), "\U0001f4e6", self._lazy_tab("software"), "Software")
        self.add_page(self.tr("Maintenance"), "\U0001f527", self._lazy_tab("maintenance"), "Software")
        self.add_page(self.tr("Snapshots"), "\U0001f4f8", self._lazy_tab("snapshots"), "Software")
        self.add_page(self.tr("Virtualization"), "\U0001f5a5\ufe0f", self._lazy_tab("virtualization"), "Software")
        self.add_page(self.tr("Development"), "\U0001f6e0\ufe0f", self._lazy_tab("development"), "Software")

        # ==================== Network ====================
        self.add_page(self.tr("Network"), "\U0001f310", self._lazy_tab("network"), "Network")
        self.add_page(self.tr("Loofi Link"), "\U0001f517", self._lazy_tab("mesh"), "Network")

        # ==================== Security ====================
        self.add_page(self.tr("Security & Privacy"), "\U0001f6e1\ufe0f", self._lazy_tab("security"), "Security")

        # ==================== Desktop ====================
        self.add_page(self.tr("Desktop"), "\U0001f3a8", self._lazy_tab("desktop"), "Desktop")
        self.add_page(self.tr("Profiles"), "\U0001f464", self._lazy_tab("profiles"), "Desktop")
        self.add_page(self.tr("Gaming"), "\U0001f3ae", self._lazy_tab("gaming"), "Desktop")

        # ==================== Tools ====================
        self.add_page(self.tr("AI Lab"), "\U0001f9e0", self._lazy_tab("ai"), "Tools")
        self.add_page(self.tr("State Teleport"), "\U0001f4e1", self._lazy_tab("teleport"), "Tools")
        self.add_page(self.tr("Diagnostics"), "\U0001f52d", self._lazy_tab("diagnostics"), "Tools")
        self.add_page(self.tr("Community"), "\U0001f30d", self._lazy_tab("community"), "Tools")

        # ==================== Settings ====================
        self.add_page(self.tr("Settings"), "\u2699\ufe0f", self._lazy_tab("settings"), "Settings")

        # Expand Dashboard by default
        self.sidebar.topLevelItem(0).setExpanded(True)
        # Select Home
        self.sidebar.setCurrentItem(self.sidebar.topLevelItem(0).child(0))

        # v15.0 Nebula - Quick Actions Bar (Ctrl+Shift+K)
        self._setup_quick_actions()

        # Select first item
        if self.sidebar.topLevelItemCount() > 0:
            first_category = self.sidebar.topLevelItem(0)
            if first_category.childCount() > 0:
                self.sidebar.setCurrentItem(first_category.child(0))

        # System Tray
        self.setup_tray()
        self.check_dependencies()

        # Ctrl+K Command Palette shortcut
        self._setup_command_palette_shortcut()

        # v13.5 UX Polish - keyboard shortcuts
        self._setup_keyboard_shortcuts()

        # v13.5 UX Polish - notification bell
        self._setup_notification_bell()

        # First-run wizard
        self._check_first_run()

    def _lazy_tab(self, tab_name: str) -> LazyWidget:
        """Create a lazy-loaded tab widget."""
        loaders = {
            # v10.0 consolidated tabs
            "monitor": lambda: __import__("ui.monitor_tab", fromlist=["MonitorTab"]).MonitorTab(),
            "maintenance": lambda: __import__("ui.maintenance_tab", fromlist=["MaintenanceTab"]).MaintenanceTab(),
            "hardware": lambda: __import__("ui.hardware_tab", fromlist=["HardwareTab"]).HardwareTab(),
            "software": lambda: __import__("ui.software_tab", fromlist=["SoftwareTab"]).SoftwareTab(),
            "security": lambda: __import__("ui.security_tab", fromlist=["SecurityTab"]).SecurityTab(),
            "network": lambda: __import__("ui.network_tab", fromlist=["NetworkTab"]).NetworkTab(),
            "gaming": lambda: __import__("ui.gaming_tab", fromlist=["GamingTab"]).GamingTab(),
            "desktop": lambda: __import__("ui.desktop_tab", fromlist=["DesktopTab"]).DesktopTab(),
            "development": lambda: __import__("ui.development_tab", fromlist=["DevelopmentTab"]).DevelopmentTab(),
            "ai": lambda: __import__("ui.ai_enhanced_tab", fromlist=["AIEnhancedTab"]).AIEnhancedTab(),
            "automation": lambda: __import__("ui.automation_tab", fromlist=["AutomationTab"]).AutomationTab(),
            "community": lambda: __import__("ui.community_tab", fromlist=["CommunityTab"]).CommunityTab(),
            "diagnostics": lambda: __import__("ui.diagnostics_tab", fromlist=["DiagnosticsTab"]).DiagnosticsTab(),
            # v11.5 / v12.0 tabs
            "virtualization": lambda: __import__("ui.virtualization_tab", fromlist=["VirtualizationTab"]).VirtualizationTab(),
            "mesh": lambda: __import__("ui.mesh_tab", fromlist=["MeshTab"]).MeshTab(),
            "teleport": lambda: __import__("ui.teleport_tab", fromlist=["TeleportTab"]).TeleportTab(),
            # v13.0 Nexus Update tabs
            "profiles": lambda: __import__("ui.profiles_tab", fromlist=["ProfilesTab"]).ProfilesTab(),
            "health": lambda: __import__("ui.health_timeline_tab", fromlist=["HealthTimelineTab"]).HealthTimelineTab(),
            # v13.5 UX Polish
            "settings": lambda: __import__("ui.settings_tab", fromlist=["SettingsTab"]).SettingsTab(self),
            # v17.0 Atlas — New tabs
            "performance": lambda: __import__("ui.performance_tab", fromlist=["PerformanceTab"]).PerformanceTab(),
            "snapshots": lambda: __import__("ui.snapshot_tab", fromlist=["SnapshotTab"]).SnapshotTab(),
            "logs": lambda: __import__("ui.logs_tab", fromlist=["LogsTab"]).LogsTab(),
            "storage": lambda: __import__("ui.storage_tab", fromlist=["StorageTab"]).StorageTab(),
            # v18.0 Sentinel — Agents
            "agents": lambda: __import__("ui.agents_tab", fromlist=["AgentsTab"]).AgentsTab(),
        }
        return LazyWidget(loaders[tab_name])

    def _start_pulse_listener(self):
        """Initialize and start the Pulse event listener."""
        try:
            self.pulse = SystemPulse()
            self.pulse_thread = PulseThread(self.pulse)
            self.pulse.moveToThread(self.pulse_thread)
            self.pulse_thread.start()
        except Exception:
            pass

    def add_page(self, name, icon, widget, category="General"):
        # Find or create category item
        category_item = None
        for i in range(self.sidebar.topLevelItemCount()):
            item = self.sidebar.topLevelItem(i)
            if item.text(0) == category:
                category_item = item
                break

        if not category_item:
            category_item = QTreeWidgetItem(self.sidebar)
            category_item.setText(0, category)
            category_item.setExpanded(True)

        # Badge suffix
        meta = _TAB_META.get(name, ("", ""))
        desc, badge = meta
        badge_suffix = ""
        if badge == "recommended":
            badge_suffix = "  ★"
        elif badge == "advanced":
            badge_suffix = "  ⚙"

        item = QTreeWidgetItem(category_item)
        item.setText(0, f"{icon}  {name}{badge_suffix}")
        page_widget = self._wrap_page_widget(widget)
        # Store widget, description, and badge type
        item.setData(0, Qt.ItemDataRole.UserRole, page_widget)
        item.setData(0, _ROLE_DESC, desc)
        item.setData(0, _ROLE_BADGE, badge)
        if desc:
            item.setToolTip(0, desc)

        self.content_area.addWidget(page_widget)
        self.pages[name] = widget

    def _wrap_page_widget(self, widget: QWidget) -> QScrollArea:
        """
        Wrap a page widget in a scroll area.

        Prevents dense tabs from being vertically compressed on smaller
        displays; users can scroll instead of seeing clipped/collapsed controls.
        """
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(widget)
        return scroll

    def change_page(self, current, previous):
        if not current:
            return

        widget = current.data(0, Qt.ItemDataRole.UserRole)
        if widget:
            self.content_area.setCurrentWidget(widget)
            self._update_breadcrumb(current)
        else:
            # Category item: expand and auto-select first child
            if current.childCount() > 0:
                current.setExpanded(True)
                self.sidebar.setCurrentItem(current.child(0))

    def _update_breadcrumb(self, item):
        """Update breadcrumb bar with current category > page."""
        parent = item.parent()
        category = parent.text(0) if parent else ""
        # Strip badge suffixes for display
        raw = item.text(0)
        page_name = raw.replace("  ★", "").replace("  ⚙", "")
        desc = item.data(0, _ROLE_DESC) or ""
        self._bc_category.setText(category)
        self._bc_page.setText(page_name)
        self._bc_desc.setText(desc)

    def set_status(self, text: str):
        """Set status bar message (can be called from any tab)."""
        self._status_label.setText(text)

    def switch_to_tab(self, name):
        """Helper for Dashboard and Command Palette to switch tabs."""
        # Search all items
        iterator = QTreeWidgetItemIterator(self.sidebar)
        while iterator.value():
            item = iterator.value()
            # Check if it matches and is a page (has widget data)
            if name in item.text(0) and item.data(0, Qt.ItemDataRole.UserRole):
                self.sidebar.setCurrentItem(item)
                return
            iterator += 1

    def _setup_command_palette_shortcut(self):
        """Register Ctrl+K shortcut for the command palette."""
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self._show_command_palette)

    def _show_command_palette(self):
        """Show the command palette dialog."""
        try:
            from ui.command_palette import CommandPalette
            palette = CommandPalette(self.switch_to_tab, self)
            palette.exec()
        except ImportError:
            pass

    def _filter_sidebar(self, text: str):
        """Filter sidebar items by search text."""
        search = text.lower()

        # Iterate top-level categories
        for i in range(self.sidebar.topLevelItemCount()):
            category = self.sidebar.topLevelItem(i)
            category_visible = False

            # Check children
            for j in range(category.childCount()):
                child = category.child(j)
                if search in child.text(0).lower():
                    child.setHidden(False)
                    category_visible = True
                else:
                    child.setHidden(True)

            # Check category itself
            if search in category.text(0).lower():
                category_visible = True
                # Show all children if category matches? Or just show category?
                # Let's show all children if category matches
                for j in range(category.childCount()):
                    category.child(j).setHidden(False)

            category.setHidden(not category_visible)
            if category_visible:
                category.setExpanded(True)

    def _setup_keyboard_shortcuts(self):
        """Register keyboard shortcuts for tab navigation."""
        # Ctrl+1 through Ctrl+9 - switch to category 1-9
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i - 1: self._select_category(idx))

        # Ctrl+Tab - next tab
        next_tab = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab.activated.connect(self._select_next_item)

        # Ctrl+Shift+Tab - previous tab
        prev_tab = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab.activated.connect(self._select_prev_item)

        # Ctrl+Q - Quit
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.quit_app)

        # F1 - Show shortcut help
        help_shortcut = QShortcut(QKeySequence("F1"), self)
        help_shortcut.activated.connect(self._show_shortcut_help)

    def _select_category(self, index: int):
        if index < self.sidebar.topLevelItemCount():
            item = self.sidebar.topLevelItem(index)
            self.sidebar.setCurrentItem(item)
            item.setExpanded(True)

    def _select_next_item(self):
        current = self.sidebar.currentItem()
        if not current:
            return

        # Try to find next item below
        next_item = self.sidebar.itemBelow(current)
        if next_item:
            self.sidebar.setCurrentItem(next_item)
        else:
            # Wrap around to top
            if self.sidebar.topLevelItemCount() > 0:
                self.sidebar.setCurrentItem(self.sidebar.topLevelItem(0))

    def _select_prev_item(self):
        current = self.sidebar.currentItem()
        if not current:
            return

        # Try to find item above
        prev_item = self.sidebar.itemAbove(current)
        if prev_item:
            self.sidebar.setCurrentItem(prev_item)
        else:
            # Wrap around to bottom
            last_top = self.sidebar.topLevelItem(self.sidebar.topLevelItemCount() - 1)
            # Find last visible item
            while last_top.childCount() > 0 and last_top.isExpanded():
                last_top = last_top.child(last_top.childCount() - 1)
            self.sidebar.setCurrentItem(last_top)

    def _show_shortcut_help(self):
        """Show keyboard shortcuts help dialog."""
        from PyQt6.QtWidgets import QMessageBox
        shortcuts = (
            "Ctrl+K — Command Palette\n"
            "Ctrl+Shift+K — Quick Actions\n"
            "Ctrl+1..9 — Switch to tab 1-9\n"
            "Ctrl+Tab — Next tab\n"
            "Ctrl+Shift+Tab — Previous tab\n"
            "Ctrl+Q — Quit\n"
            "F1 — This help"
        )
        QMessageBox.information(self, self.tr("Keyboard Shortcuts"), shortcuts)

    def _setup_notification_bell(self):
        """Add notification bell to the header area."""
        from PyQt6.QtWidgets import QToolButton
        self.notif_panel = None
        self.notif_bell = QToolButton()
        self.notif_bell.setText("\U0001f514")  # Bell emoji
        self.notif_bell.setStyleSheet(
            "QToolButton { border: none; font-size: 20px; padding: 5px; }"
            "QToolButton:hover { background-color: #313244; border-radius: 6px; }"
        )
        self.notif_bell.clicked.connect(self._toggle_notification_panel)

    def _toggle_notification_panel(self):
        """Toggle the notification panel."""
        if self.notif_panel is None:
            from ui.notification_panel import NotificationPanel
            self.notif_panel = NotificationPanel(self)

        if self.notif_panel.isVisible():
            self.notif_panel.hide()
        else:
            self.notif_panel.refresh()
            # Position at top-right
            x = self.width() - self.notif_panel.width() - 10
            y = 40
            self.notif_panel.move(x, y)
            self.notif_panel.show()
            self.notif_panel.raise_()

    def _setup_quick_actions(self):
        """Register Ctrl+Shift+K shortcut for Quick Actions bar."""
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+K"), self)
        shortcut.activated.connect(self._show_quick_actions)

    def _show_quick_actions(self):
        """Show the Quick Actions bar."""
        try:
            from ui.quick_actions import QuickActionsBar, QuickActionRegistry, register_default_actions
            registry = QuickActionRegistry.instance()
            if not registry.get_all():
                register_default_actions(registry)
            bar = QuickActionsBar(self)
            bar.exec()
        except ImportError:
            pass

    def _check_first_run(self):
        """Show first-run wizard if this is the first launch."""
        config_dir = os.path.expanduser("~/.config/loofi-fedora-tweaks")
        first_run_file = os.path.join(config_dir, "first_run_complete")

        if not os.path.exists(first_run_file):
            try:
                from ui.wizard import FirstRunWizard
                wizard = FirstRunWizard(self)
                wizard.exec()
            except ImportError:
                pass

    def setup_tray(self):
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
        from PyQt6.QtGui import QIcon, QAction

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "loofi-fedora-tweaks.png")
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
            else:
                self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

            tray_menu = QMenu()
            show_action = QAction(self.tr("Show"), self)
            show_action.triggered.connect(self.show)

            # Focus Mode toggle
            self.focus_action = QAction(self.tr("Focus Mode"), self)
            self.focus_action.setCheckable(True)
            self.focus_action.setChecked(FocusMode.is_active())
            self.focus_action.triggered.connect(self._toggle_focus_mode)

            quit_action = QAction(self.tr("Quit"), self)
            quit_action.triggered.connect(self.quit_app)

            tray_menu.addAction(show_action)
            tray_menu.addSeparator()
            tray_menu.addAction(self.focus_action)
            tray_menu.addSeparator()
            tray_menu.addAction(quit_action)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
        else:
            self.tray_icon = None

    def _toggle_focus_mode(self):
        """Toggle Focus Mode from tray."""
        result = FocusMode.toggle()
        self.focus_action.setChecked(FocusMode.is_active())

        if self.tray_icon:
            message = result.get("message", "Focus Mode toggled")
            self.tray_icon.showMessage(
                self.tr("Focus Mode"),
                message,
                self.tray_icon.MessageIcon.Information,
                2000
            )

    def quit_app(self):
        # Stop Pulse listener
        if self.pulse_thread:
            self.pulse_thread.stop()

        if self.tray_icon:
            self.tray_icon.hide()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                self.tr("Loofi Fedora Tweaks"),
                self.tr("Minimized to tray."),
                self.tray_icon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            # Clean up page resources (timers, schedulers)
            for page in self.pages.values():
                if hasattr(page, "cleanup"):
                    try:
                        page.cleanup()
                    except Exception:
                        pass
            event.accept()

    def check_dependencies(self):
        import shutil
        critical = ["dnf", "pkexec"]
        missing = [tool for tool in critical if not shutil.which(tool)]
        if missing:
            self.show_doctor()

    def show_doctor(self):
        from ui.doctor import DependencyDoctor
        doctor = DependencyDoctor(self)
        doctor.exec()

    # ==================== v13.5 Theme Management ====================

    def load_theme(self, name: str = "dark") -> None:
        """
        Load and apply a QSS theme by name.

        Supported names: ``"dark"`` (modern.qss) and ``"light"`` (light.qss).
        Falls back silently to no stylesheet if the file is missing.
        """
        theme_map = {
            "dark": "modern.qss",
            "light": "light.qss",
        }
        filename = theme_map.get(name, "modern.qss")
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        qss_path = os.path.join(assets_dir, filename)

        try:
            with open(qss_path, "r") as fh:
                stylesheet = fh.read()
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.setStyleSheet(stylesheet)
        except OSError:
            pass

    @staticmethod
    def detect_system_theme() -> str:
        """
        Detect the system colour-scheme preference via
        ``gsettings`` (GNOME / GTK) and return ``"dark"`` or ``"light"``.

        Returns ``"dark"`` when detection fails.
        """
        import subprocess
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=3,
            )
            value = result.stdout.strip().strip("'\"")
            if "light" in value:
                return "light"
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "dark"

    def _get_frameless_mode_flag(self) -> bool:
        """
        Check if frameless window mode is requested.

        Priority:
        1. Config file: ui.frameless_mode key
        2. Environment variable: LOOFI_FRAMELESS=1

        Returns:
            True if frameless mode is enabled, False otherwise (default).
        """
        # Check config file first
        config = ConfigManager.load_config()
        if config is not None:
            ui_settings = config.get("ui", {})
            if "frameless_mode" in ui_settings:
                return bool(ui_settings["frameless_mode"])

        # Fallback to environment variable
        env_value = os.environ.get("LOOFI_FRAMELESS", "").strip()
        return env_value == "1"
