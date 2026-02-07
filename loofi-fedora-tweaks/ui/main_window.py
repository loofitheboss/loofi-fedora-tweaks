from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QStackedWidget, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

# Only import essential tabs eagerly (Dashboard is always shown first)
from ui.dashboard_tab import DashboardTab
from ui.system_info_tab import SystemInfoTab
from ui.lazy_widget import LazyWidget
from utils.system import SystemManager
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Loofi Fedora Tweaks v7.1.0"))
        self.resize(1100, 700)
        
        # Load Modern Theme
        self.load_theme()
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout (Horizontal: Sidebar | Content)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)
        
        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(240)
        # Prevent focus rectangle
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.currentRowChanged.connect(self.change_page)
        main_layout.addWidget(self.sidebar)
        
        # Content Area
        self.content_area = QStackedWidget()
        main_layout.addWidget(self.content_area)
        
        # Initialize Pages - Eager loading for essential tabs only
        self.pages = {}
        
        # Dashboard is always shown first - load eagerly
        self.add_page(self.tr("Home"), "🏠", DashboardTab(self))
        self.add_page(self.tr("System Info"), "ℹ️", SystemInfoTab())
        
        # All other tabs use lazy loading for faster startup
        self.add_page(self.tr("Updates"), "📦", self._lazy_tab("updates"))
        self.add_page(self.tr("Cleanup"), "🧹", self._lazy_tab("cleanup"))
        self.add_page(self.tr("Hardware"), "⚡", self._lazy_tab("hardware"))
        self.add_page(self.tr("HP Tweaks"), "💻", self._lazy_tab("tweaks"))
        self.add_page(self.tr("Apps"), "🚀", self._lazy_tab("apps"))
        self.add_page(self.tr("Advanced"), "⚙️", self._lazy_tab("advanced"))
        self.add_page(self.tr("Gaming"), "🎮", self._lazy_tab("gaming"))
        self.add_page(self.tr("Network"), "🌐", self._lazy_tab("network"))
        self.add_page(self.tr("Presets"), "💾", self._lazy_tab("presets"))
        self.add_page(self.tr("Marketplace"), "🌐", self._lazy_tab("marketplace"))
        self.add_page(self.tr("Scheduler"), "⏰", self._lazy_tab("scheduler"))
        self.add_page(self.tr("Boot"), "🔧", self._lazy_tab("boot"))
        
        # v7.1: Developer tools
        self.add_page(self.tr("Containers"), "📦", self._lazy_tab("containers"))
        self.add_page(self.tr("Developer"), "🛠️", self._lazy_tab("developer"))
        
        # v7.5: Watchtower diagnostics
        self.add_page(self.tr("Watchtower"), "🔭", self._lazy_tab("watchtower"))
        
        # v8.0: Replicator (IaC exports)
        self.add_page(self.tr("Replicator"), "🔄", self._lazy_tab("replicator"))
        
        # Atomic-only: Overlays tab
        if SystemManager.is_atomic():
            self.add_page(self.tr("Overlays"), "📦", self._lazy_tab("overlays"))
        
        # Group less used ones
        self.add_page(self.tr("Repos"), "📂", self._lazy_tab("repos"))
        self.add_page(self.tr("Privacy"), "🔒", self._lazy_tab("privacy"))
        self.add_page(self.tr("Theming"), "🎨", self._lazy_tab("theming"))
        
        # Select first item
        self.sidebar.setCurrentRow(0)

        # System Tray logic (Keep existing logic, simplified here)
        self.setup_tray()
        self.check_dependencies()
    
    def _lazy_tab(self, tab_name: str) -> LazyWidget:
        """Create a lazy-loaded tab widget."""
        loaders = {
            "updates": lambda: __import__("ui.updates_tab", fromlist=["UpdatesTab"]).UpdatesTab(),
            "cleanup": lambda: __import__("ui.cleanup_tab", fromlist=["CleanupTab"]).CleanupTab(),
            "hardware": lambda: __import__("ui.hardware_tab", fromlist=["HardwareTab"]).HardwareTab(),
            "tweaks": lambda: __import__("ui.tweaks_tab", fromlist=["TweaksTab"]).TweaksTab(),
            "apps": lambda: __import__("ui.apps_tab", fromlist=["AppsTab"]).AppsTab(),
            "advanced": lambda: __import__("ui.advanced_tab", fromlist=["AdvancedTab"]).AdvancedTab(),
            "gaming": lambda: __import__("ui.gaming_tab", fromlist=["GamingTab"]).GamingTab(),
            "network": lambda: __import__("ui.network_tab", fromlist=["NetworkTab"]).NetworkTab(),
            "presets": lambda: __import__("ui.presets_tab", fromlist=["PresetsTab"]).PresetsTab(),
            "marketplace": lambda: __import__("ui.marketplace_tab", fromlist=["MarketplaceTab"]).MarketplaceTab(),
            "scheduler": lambda: __import__("ui.scheduler_tab", fromlist=["SchedulerTab"]).SchedulerTab(),
            "boot": lambda: __import__("ui.boot_tab", fromlist=["BootTab"]).BootTab(),
            "overlays": lambda: __import__("ui.overlays_tab", fromlist=["OverlaysTab"]).OverlaysTab(),
            "repos": lambda: __import__("ui.repos_tab", fromlist=["ReposTab"]).ReposTab(),
            "privacy": lambda: __import__("ui.privacy_tab", fromlist=["PrivacyTab"]).PrivacyTab(),
            "theming": lambda: __import__("ui.theming_tab", fromlist=["ThemingTab"]).ThemingTab(),
            "containers": lambda: __import__("ui.containers_tab", fromlist=["ContainersTab"]).ContainersTab(),
            "developer": lambda: __import__("ui.developer_tab", fromlist=["DeveloperTab"]).DeveloperTab(),
            "watchtower": lambda: __import__("ui.watchtower_tab", fromlist=["WatchtowerTab"]).WatchtowerTab(),
            "replicator": lambda: __import__("ui.replicator_tab", fromlist=["ReplicatorTab"]).ReplicatorTab(),
        }
        return LazyWidget(loaders[tab_name])


    def load_theme(self):
        theme_path = os.path.join(os.path.dirname(__file__), "..", "assets", "modern.qss")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as f:
                self.setStyleSheet(f.read())

    def add_page(self, name, icon, widget):
        item = QListWidgetItem(f"{icon}   {name}")
        # center vertically
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.sidebar.addItem(item)
        self.content_area.addWidget(widget)
        self.pages[name] = widget

    def change_page(self, index):
        self.content_area.setCurrentIndex(index)
        
    def switch_to_tab(self, name):
        """Helper for Dashboard to switch tabs"""
        # Find index by name
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            if name in item.text():
                self.sidebar.setCurrentRow(i)
                return

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
            quit_action = QAction(self.tr("Quit"), self)
            quit_action.triggered.connect(self.quit_app)
            
            tray_menu.addAction(show_action)
            tray_menu.addAction(quit_action)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
        else:
            self.tray_icon = None

    def quit_app(self):
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

