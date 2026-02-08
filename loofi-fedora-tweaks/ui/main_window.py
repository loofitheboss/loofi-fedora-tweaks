"""
Main Window - v13.5 "UX Polish"
21-tab layout with sidebar navigation.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence

# Only import essential tabs eagerly (Dashboard is always shown first)
from ui.dashboard_tab import DashboardTab
from ui.system_info_tab import SystemInfoTab
from ui.lazy_widget import LazyWidget
from utils.system import SystemManager
from utils.pulse import SystemPulse, PulseThread
from utils.focus_mode import FocusMode
from version import __version__
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr(f"Loofi Fedora Tweaks v{__version__}"))
        self.resize(1100, 700)

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
        sidebar_container.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 10, 0, 0)
        sidebar_layout.setSpacing(0)

        # Search box
        from PyQt6.QtWidgets import QLineEdit
        self.sidebar_search = QLineEdit()
        self.sidebar_search.setPlaceholderText(self.tr("Search tabs..."))
        self.sidebar_search.setClearButtonEnabled(True)
        self.sidebar_search.setFixedHeight(36)
        self.sidebar_search.setStyleSheet(
            "QLineEdit { margin: 5px 10px; border-radius: 8px; padding: 4px 10px; }"
        )
        self.sidebar_search.textChanged.connect(self._filter_sidebar)
        sidebar_layout.addWidget(self.sidebar_search)

        # Sidebar list
        self.sidebar = QListWidget()
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.currentRowChanged.connect(self.change_page)
        sidebar_layout.addWidget(self.sidebar)

        main_layout.addWidget(sidebar_container)

        # Content Area
        self.content_area = QStackedWidget()
        main_layout.addWidget(self.content_area)

        # Initialize Pages
        self.pages = {}

        # ==================== V12.0 TABS (18) ====================

        # Eagerly loaded
        self.add_page(self.tr("Home"), "\U0001f3e0", DashboardTab(self))
        self.add_page(self.tr("System Info"), "\u2139\ufe0f", SystemInfoTab())

        # System monitoring (Performance + Processes)
        self.add_page(self.tr("System Monitor"), "\U0001f4ca", self._lazy_tab("monitor"))

        # Maintenance (Updates + Cleanup + Overlays)
        self.add_page(self.tr("Maintenance"), "\U0001f527", self._lazy_tab("maintenance"))

        # Hardware (CPU/GPU/Fan/Battery/Audio/Fingerprint - merged with HP Tweaks)
        self.add_page(self.tr("Hardware"), "\u26a1", self._lazy_tab("hardware"))

        # Software (Apps + Repos)
        self.add_page(self.tr("Software"), "\U0001f4e6", self._lazy_tab("software"))

        # Security & Privacy (merged)
        self.add_page(self.tr("Security & Privacy"), "\U0001f6e1\ufe0f", self._lazy_tab("security"))

        # Network
        self.add_page(self.tr("Network"), "\U0001f310", self._lazy_tab("network"))

        # Gaming
        self.add_page(self.tr("Gaming"), "\U0001f3ae", self._lazy_tab("gaming"))

        # Desktop (Director + Theming)
        self.add_page(self.tr("Desktop"), "\U0001f3a8", self._lazy_tab("desktop"))

        # Development (Containers + Developer Tools)
        self.add_page(self.tr("Development"), "\U0001f6e0\ufe0f", self._lazy_tab("development"))

        # AI Lab
        self.add_page(self.tr("AI Lab"), "\U0001f9e0", self._lazy_tab("ai"))

        # Automation (Scheduler + Replicator + Pulse)
        self.add_page(self.tr("Automation"), "\u23f0", self._lazy_tab("automation"))

        # Community (Presets + Marketplace)
        self.add_page(self.tr("Community"), "\U0001f30d", self._lazy_tab("community"))

        # Diagnostics (Watchtower + Boot)
        self.add_page(self.tr("Diagnostics"), "\U0001f52d", self._lazy_tab("diagnostics"))

        # v11.5 Hypervisor Update
        self.add_page(self.tr("Virtualization"), "\U0001f5a5\ufe0f", self._lazy_tab("virtualization"))

        # v12.0 Sovereign Update
        self.add_page(self.tr("Loofi Link"), "\U0001f517", self._lazy_tab("mesh"))
        self.add_page(self.tr("State Teleport"), "\U0001f4e1", self._lazy_tab("teleport"))

        # v13.0 Nexus Update
        self.add_page(self.tr("Profiles"), "\U0001f464", self._lazy_tab("profiles"))
        self.add_page(self.tr("Health"), "\U0001f4c8", self._lazy_tab("health"))

        # v13.5 UX Polish
        self.add_page(self.tr("Settings"), "\u2699\ufe0f", self._lazy_tab("settings"))

        # v15.0 Nebula - Quick Actions Bar (Ctrl+Shift+K)
        self._setup_quick_actions()

        # Select first item
        self.sidebar.setCurrentRow(0)

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
            "monitor": lambda: __import__("ui.monitor_tab", fromlist=["MonitorTab"]).MonitorTab(self),
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

    def add_page(self, name, icon, widget):
        item = QListWidgetItem(f"{icon}   {name}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.sidebar.addItem(item)
        self.content_area.addWidget(widget)
        self.pages[name] = widget

    def change_page(self, index):
        self.content_area.setCurrentIndex(index)

    def switch_to_tab(self, name):
        """Helper for Dashboard and Command Palette to switch tabs."""
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            if name in item.text():
                self.sidebar.setCurrentRow(i)
                return

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
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            item.setHidden(search not in item.text().lower())

    def _setup_keyboard_shortcuts(self):
        """Register keyboard shortcuts for tab navigation."""
        # Ctrl+1 through Ctrl+9 - switch to tab 1-9
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i-1: self.sidebar.setCurrentRow(idx))

        # Ctrl+Tab - next tab
        next_tab = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab.activated.connect(lambda: self.sidebar.setCurrentRow(
            (self.sidebar.currentRow() + 1) % self.sidebar.count()
        ))

        # Ctrl+Shift+Tab - previous tab
        prev_tab = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab.activated.connect(lambda: self.sidebar.setCurrentRow(
            (self.sidebar.currentRow() - 1) % self.sidebar.count()
        ))

        # Ctrl+Q - Quit
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.quit_app)

        # F1 - Show shortcut help
        help_shortcut = QShortcut(QKeySequence("F1"), self)
        help_shortcut.activated.connect(self._show_shortcut_help)

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
