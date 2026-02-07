from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QStackedWidget, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

from ui.dashboard_tab import DashboardTab
from ui.system_info_tab import SystemInfoTab
from ui.updates_tab import UpdatesTab
from ui.cleanup_tab import CleanupTab
from ui.tweaks_tab import TweaksTab
from ui.apps_tab import AppsTab
from ui.advanced_tab import AdvancedTab
from ui.repos_tab import ReposTab
from ui.gaming_tab import GamingTab
from ui.network_tab import NetworkTab
from ui.presets_tab import PresetsTab
from ui.privacy_tab import PrivacyTab
from ui.theming_tab import ThemingTab
from ui.overlays_tab import OverlaysTab
from ui.hardware_tab import HardwareTab
from ui.doctor import DependencyDoctor
from utils.system import SystemManager
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loofi Fedora Tweaks v5.5.0")
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
        
        # Initialize Pages
        self.pages = {}
        
        self.add_page("Home", "🏠", DashboardTab(self))
        self.add_page("System Info", "ℹ️", SystemInfoTab())
        self.add_page("Updates", "📦", UpdatesTab())
        self.add_page("Cleanup", "🧹", CleanupTab())
        self.add_page("Hardware", "⚡", HardwareTab())  # v5.2: Consolidated hardware controls
        self.add_page("HP Tweaks", "💻", TweaksTab())  # Legacy, kept for battery/fingerprint
        self.add_page("Apps", "🚀", AppsTab())
        self.add_page("Advanced", "⚙️", AdvancedTab())
        self.add_page("Gaming", "🎮", GamingTab())
        self.add_page("Network", "🌐", NetworkTab())
        self.add_page("Presets", "💾", PresetsTab())
        # Atomic-only: Overlays tab
        if SystemManager.is_atomic():
            self.add_page("Overlays", "📦", OverlaysTab())
        
        # Group less used ones
        self.add_page("Repos", "📂", ReposTab())
        self.add_page("Privacy", "🔒", PrivacyTab())
        self.add_page("Theming", "🎨", ThemingTab())
        
        # Select first item
        self.sidebar.setCurrentRow(0)

        # System Tray logic (Keep existing logic, simplified here)
        self.setup_tray()
        self.check_dependencies()

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
            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            quit_action = QAction("Quit", self)
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
                "Loofi Fedora Tweaks",
                "Minimized to tray.",
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
        doctor = DependencyDoctor(self)
        doctor.exec()
